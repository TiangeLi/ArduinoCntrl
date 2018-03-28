# coding=utf-8

"""PyQt4/Python3 Mouse House"""

import sys
import math
import time
from Misc.Names import *
import multiprocessing as mp
import PyQt4.QtCore as qc
import PyQt4.QtGui as qg
from Concurrency.MainHandler import ProcessHandler
from Misc.CustomClasses import ReadMessage, NewMessage
from GUI.MiscWidgets import qw, GuiMessage
from GUI.CmrDisplay import CameraDisplay
from GUI.ArdProgBar import GuiProgressBar
from DirsSettings.Directories import Directories
if sys.version[0] == '2':
    import Queue as Queue
else:
    import queue as Queue


class MasterGui(qw):
    """Main GUI Window"""
    def __init__(self, dirs, parent=None):
        super(MasterGui, self).__init__(parent)
        self.dirs = dirs
        # Main Window Configs
        self.setWindowTitle('Mouse House')
        # Layout
        self.render_widgets()
        self.set_window_size()
        # Concurrency
        self.create_message_parser()
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        self.master_dump_queue = MASTER_DUMP_QUEUE
        self.set_update_timer()
        self.setup_proc_handler()
        # Experiment running?
        self.exp_running = False
        # Can we close the program safely? (i.e. devices and processes have been closed)
        self.ready_to_exit = False
        # Finalize
        self.setFocusPolicy(qc.Qt.StrongFocus)
        self.show()

    def keyPressEvent(self, event):
        """Implement some keyboard shortcuts for the main window"""
        # -- combo: alt+cntrl+shift+k -- WILL DELETE ALL USER SETTINGS. USE FOR DEBUG ONLY
        if event.key() == qKey_k and event.modifiers() & qMod_shift \
                and event.modifiers() & qMod_cntrl and event.modifiers() & qMod_alt:
            self.nuke_files()

    def nuke_files(self):
        """Deletes ALL USER SETTINGS. USE FOR DEBUG ONLY"""
        if self.exp_running:
            GuiMessage(self, 'Stop the Experiment before attempting this KeyPress Combo')
        else:
            msg = 'You are about to delete all user settings!\n\nContinue anyway?'
            nuke = qg.QMessageBox.warning(self, 'WARNING', msg, qBtnNo | qBtnYes, qBtnNo)
            if nuke == qBtnYes:
                GuiMessage(self, 'Deleting Files and Exiting...', 'Mouse House')
                self.dirs.del_all = True
                self.close()

    def render_widgets(self):
        """Render the interactable GUI objects in our main window"""
        # Create Widget Objects
        self.progbar = GuiProgressBar(dirs=self.dirs, parent=self)
        self.camera_display = CameraDisplay(dirs=self.dirs)
        self.controls = None
        # Add Widgets to Grid
        self.grid.addWidget(self.progbar, 0, 1)
        self.grid.addWidget(self.camera_display, 0, 0, 4, 1)
        # Connect Widget Signals to Slots
        # todo: remove comment
        #self.connect_signals()

    def connect_signals(self):
        """Connects GUI Signals to respective slots"""
        # todo: connect to slots
        self.progbar.new_highlight_signal[object].connect()
        self.progbar.ttl_time_updated_signal.connect()
        # todo: timeconfigwidget.set_time_signal

    def set_window_size(self):
        """Generates sizing params"""
        max_per_col = 3
        num_cmrs = self.camera_display.num_cmrs
        num_cols = max(int(math.ceil(float(num_cmrs) / max_per_col)), 1)
        # Width and Height
        height = 900
        base_width = 1050  # accounts for progbar and borders
        if num_cols > 1:
            width = base_width + num_cols * 375
        else:
            width = base_width + num_cols * 400
        # Set Window Size
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)

    def setup_proc_handler(self):
        """Pass necessary objects to generate a ProcessHandler instance"""
        cmr_pipe_mains = [cmr.cmr_pipe_main for _, cmr in self.camera_display.cameras.items()]
        self.proc_handler = ProcessHandler(cmr_pipe_mains)
        self.proc_handler.start()

    def set_update_timer(self):
        """Creates a timer to check for queued messages"""
        update_timer = qc.QTimer(self)
        update_timer.timeout.connect(self.check_messages)
        update_timer.start(5)

    def create_message_parser(self):
        """Creates a message parser for listening to queued messages and performing instructions"""
        self.message_parser = {
            MSG_STARTED: lambda dev, val: self.cfg_widgets_started(exp_running=True),
            MSG_FINISHED: lambda dev, val: self.cfg_widgets_started(exp_running=False),
            MSG_ERROR: lambda dev, val: self.process_error_msg(dev=dev, val=val),
            CMD_EXIT: lambda dev, val: self.exit_program()
        }

    def check_messages(self):
        """Periodically checks queue for messages"""
        try:
            msg = self.master_dump_queue.get_nowait()
        except Queue.Empty:
            pass
        else:
            msg = ReadMessage(msg)
            self.process_queue_message(msg)

    def process_queue_message(self, msg):
        """Processes Queued message and performs instructions"""
        self.message_parser[msg.command](msg.device, msg.value)

    def cfg_widgets_started(self, exp_running):
        """Change widget states depending on exp_running"""
        self.exp_running = exp_running
        if exp_running:
            self.progbar.start()
        else:
            self.progbar.stop()
        self.progbar.set_ard_bars_selectable(selectable=(not exp_running))

    def process_error_msg(self, dev, val):
        """Processes the message MSG_ERROR, depending on associated device"""
        if dev:
            if dev == CAMERAS:
                stream_index = val
                self.camera_display.display_error_notif(stream_index)
        else:
            GuiMessage(self, msg=val)

    def exit_program(self):
        """Attempt to close child processes before fully exiting program"""
        self.ready_to_exit = True
        self.close()

    def closeEvent(self, event):
        """Reimplement Qt's window close event to exit iff not exp_running and child processes closed
        Called automatically upon clicking close button, or with self.close()"""
        event.ignore()
        if self.exp_running:
            GuiMessage(self, msg='Cannot Close While Experiment is Running!')
        elif self.ready_to_exit:
            while not len(mp.active_children()) <= 1:
                time.sleep(10.0 / 1000.0)
            super(MasterGui, self).closeEvent(event)
        else:
            msg = NewMessage(cmd=CMD_EXIT)
            self.proc_handler_queue.put_nowait(msg)


# -- Main Program -- #
if __name__ == '__main__':  # Always run MainModule.py as primary program
    # Add freeze support if we turn this into a windows .exe program
    mp.freeze_support()
    # Setup directories and save files
    DIRS = Directories()
    # Start GUI application
    app = qg.QApplication(sys.argv)
    window = MasterGui(DIRS)
    app.exec_()
    # Save User Settings to File on exit
    if DIRS.save_on_exit:
        DIRS.save()
    if DIRS.del_all:
        DIRS.nuke_files()
    # Safely Exit Application and Python
    print(mp.active_children())
    sys.exit()
