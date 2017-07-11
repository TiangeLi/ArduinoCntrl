# coding=utf-8

"""PyQt4/Python2.7 Mouse House"""

from Dirs_Settings import *
from Custom_Qt_Widgets import *
from Concurrency_Handlers import *
from Qt_Exp_Controls import GUI_ExpControls


class GUI_Master(qg.QWidget):
    """Main GUI Window"""
    def __init__(self, dirs_settings, parent=None):
        super(GUI_Master, self).__init__(parent)
        self.dirs = dirs_settings
        # Main Window Configs
        self.setWindowTitle('Mouse House')
        # Add Module Components
        self.grid = qg.QGridLayout()
        self.render_widgets()
        self.set_window_size()
        # Concurrency
        self.set_queue_check_timer()
        self.setup_proc_handler()
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        self.master_dump_queue = MASTER_DUMP_QUEUE
        # Experiment Running?
        self.exp_is_running = False
        self.ready_to_exit = False
        # Finish and Show Window
        self.setFocusPolicy(qc.Qt.StrongFocus)
        self.show()

    def keyPressEvent(self, event):
        """Reimplement keyPressEvent to handle a combo that will call self.nuke_files
        DO NOT PRESS COMBO FOR FUN! WILL DELETE EVERYTHING IMPORTANT"""
        # Combo: Alt+Cntrl+Shift+K
        if event.key() == qc.Qt.Key_K \
                and event.modifiers() & qc.Qt.ShiftModifier \
                and event.modifiers() & qc.Qt.ControlModifier \
                and event.modifiers() & qc.Qt.AltModifier:
            self.nuke_files()

    def nuke_files(self):
        """Deletes all saved user settings. DO NOT CALL THIS FUNCTION FOR FUN. WILL DELETE IMPORTANT STUFF"""
        if self.exp_is_running:
            print('Stop the Experiment First before attempting this KeyPress Combo')
            return
        msg = 'You are about to delete all user settings!\n\nContinue anyway?'
        nuke = qg.QMessageBox.warning(self, 'WARNING', msg,
                                      qg.QMessageBox.No | qg.QMessageBox.Yes,
                                      qg.QMessageBox.No)
        if nuke == qg.QMessageBox.Yes:
            print('Exiting...')
            self.dirs.del_all = True
            self.close()

    def setup_proc_handler(self):
        """Passes necessary objects to a new ProcessHandler instance"""
        # Pass Camera Pipes
        cmr_pipe_mains = []
        for cmr_pipe_main, cmr_pipe_cmr in self.cameras.msg_pipes:
            cmr_pipe_mains.append(cmr_pipe_main)
        # Pass Labjack Pipe
        lj_pipe_main, lj_pipe_lj = self.exp_cntrls.lj_graph_widget.msg_pipes
        # Initialize proc_handler
        self.proc_handler = ProcessHandler(self.dirs, cmr_pipe_mains, lj_pipe_main)
        self.proc_handler.start()

    def render_widgets(self):
        """Adds all GUI Modules"""
        # Create Widget Objects
        self.progbar = GUI_ProgressBar(self, self.dirs)
        self.cameras = GUI_CameraDisplay(self.dirs)
        self.exp_cntrls = GUI_ExpControls(self.dirs, self.progbar)
        #   We pass the arduino and time config widgets to the progbar for progbar functions to adjust
        self.progbar.ard_widget = self.exp_cntrls.ard_config_widget
        self.progbar.time_config_widget = self.exp_cntrls.time_config_widget
        # Add Widgets to Grid
        self.grid.addWidget(self.progbar, 0, 1)
        self.grid.addWidget(self.cameras, 0, 0, 4, 1)
        self.grid.addWidget(self.exp_cntrls, 1, 1)
        # Finish Layout
        self.setLayout(self.grid)

    def set_queue_check_timer(self):
        """Creates a timer that periodically checks for queued messages"""
        update_timer = qc.QTimer(self)
        update_timer.timeout.connect(self.check_messages)
        update_timer.start(5)

    def check_messages(self):
        """Checks queue for messages"""
        try:
            msg = self.master_dump_queue.get_nowait()
        except Queue.Empty:
            pass
        else:
            if msg == EXP_STARTED_HEADER:
                self.exp_is_running = True
                self.progbar.set_ard_bars_selectable(False)
                self.progbar.start_bar()
                self.exp_cntrls.enable_disable_widgets(True)
            elif msg == EXP_END_HEADER:
                self.exp_is_running = False
                self.progbar.set_ard_bars_selectable(True)
                self.exp_cntrls.enable_disable_widgets(False)
            elif msg.startswith(FAILED_INIT_HEADER):
                print(msg)
            elif msg == LJ_CONFIG:
                self.exp_cntrls.lj_config_widget.lj_proc_updated = True
            elif msg.startswith(CMR_ERROR_EXIT):
                cmr_ind = int(msg.replace(CMR_ERROR_EXIT, '', 1))
                self.cameras.display_error_notif(cmr_ind)
            elif msg == LJ_ERROR_EXIT:
                self.exp_cntrls.lj_graph_widget.display_error_notif()
            elif msg == EXIT_HEADER:
                self.ready_to_exit = True
                self.close()

    def set_window_size(self):
        """Generates sizing parameters for main window"""
        # Window size is based on number of cameras we have
        max_per_col = 3
        num_cmrs = self.cameras.num_cmrs
        num_columns = max(int(math.ceil(float(num_cmrs) / max_per_col)), 1)
        # -- Width -- #
        base_width = 1050  # This accounts for Progress Bar and Bordering
        if num_columns > 1:
            width = base_width + num_columns * 375
        else:
            width = base_width + num_columns * 400
        # -- Height -- #
        height = 900
        """
        # Dynamically adjust height depending on num of imgs to display
        if num_cmrs < 3:
            height = 700
        else:
            height = 900
        """
        # -- Set Window Size -- #
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)

    def closeEvent(self, QCloseEvent):
        """Reimplements self.closeEvent to exit iff experiment not running. Call using self.close()"""
        QCloseEvent.ignore()
        if self.exp_is_running:
            GUI_Message(msg='Cannot Close While Experiment is Running!')
        elif self.ready_to_exit:
            # We wait for all devices to safely exit; the only process remaining should be proc_handler
            # This way we are certain device processes are not daemonically killed but are exiting naturally
            while not len(mp.active_children()) <= 1:
                time.sleep(10.0/1000)
            super(GUI_Master, self).closeEvent(QCloseEvent)
        else:
            self.proc_handler_queue.put_nowait(EXIT_HEADER)


# Actual Program Runs Below #
if __name__ == '__main__':  # Always run Main_Module.py as primary script
    # -- Add Freeze Support for Windows .exe Files -- #
    mp.freeze_support()
    # -- Set up Directories and Save Files -- #
    dirs = Directories()
    dirs.load()
    # -- Start Application -- #
    app = qg.QApplication(sys.argv)  # Tells Python: we're opening a new GUI app
    window = GUI_Master(dirs_settings=dirs)  # Opens our main GUI Window
    app.exec_()  # Execute GUI event loop; program stays here until we close GUI
    # -- Save settings to File -- #
    if dirs.save_on_exit:
        dirs.save()
    # -- FOR DEBUG ONLY: clean out all settings -- #
    if dirs.del_all:
        dirs.nuke_files()
        print('Deleted all User Settings')
    # -- Safely exit application and Python -- #
    print(mp.active_children())
    sys.exit()
