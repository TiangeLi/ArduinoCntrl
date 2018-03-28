# coding=utf-8

"""Start and Stop buttons, with an entry field for naming experiments"""

from GUI.MiscWidgets import qw, GuiEntryWithWarning, GuiIntOnlyEntry, GuiMessage
import PyQt4.QtCore as qc
import PyQt4.QtGui as qg
from Misc.Names import *
from Misc.CustomClasses import HHMMSS
from Concurrency.MainHandler import NewMessage


class StartStopBtns(qw):
    """Buttons with associated signals/slots, and entry field"""
    def __init__(self, dirs):
        super(StartStopBtns, self).__init__()
        self.dirs = dirs
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        # Setup
        self.setMinimumWidth(200)
        self.setMaximumWidth(200)
        self.init_btns()
        self.init_entry()
        self.add_to_grid()

    def init_btns(self):
        """Create Start/Stop Buttons"""
        self.start_btn = qg.QPushButton('START')
        self.start_btn.setStyleSheet(qBgCyan)
        self.stop_btn = qg.QPushButton('STOP')
        self.stop_btn.setStyleSheet(qBgOrange)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.setEnabled(False)

    def init_entry(self):
        """Creates Entry Field for Naming"""
        self.name_frame = qg.QGroupBox('Trial Name:')
        grid = qg.QGridLayout()
        self.name_frame.setLayout(grid)
        self.name_entry = GuiEntryWithWarning()
        grid.addWidget(self.name_entry)

    def add_to_grid(self):
        """Add widgets to grid"""
        self.grid.addWidget(self.name_frame, 0, 0)
        self.grid.addWidget(self.start_btn, 1, 0)
        self.grid.addWidget(self.stop_btn, 2, 0)

    def get_name(self):
        """Gets the experiment name from user input"""
        name = str(self.name_entry.text()).strip()
        if name == '':
            return False
        # We remove any forbidden naming characters
        for i in name:
            if i in FORBIDDEN_CHARS:
                name = name.replace(i, '_')
        return name

    def start(self):
        """Starts Experiment"""
        name = self.get_name()
        # If we didn't put in a name or name was already used, we warn the user and do not start
        if not name or name in self.dirs.list_file_names():
            self.name_entry.visual_warning()
            return
        # Save directory checks
        self.dirs.check_dirs()
        if not self.dirs.made_date_stamped_dir:
            self.dirs.create_date_stamped_dir()
            msg = NewMessage(cmd=CMD_SET_DIRS, val=self.dirs.date_stamped_dir)
            self.proc_handler_queue.put_nowait(msg)
        # Send Start Signal to ProcHandler
        msg = NewMessage(cmd=CMD_START, val=name)
        self.proc_handler_queue.put_nowait(msg)

    def stop(self):
        """Sends a hardstop signal to prematurely exit experiment"""
        msg = NewMessage(cmd=CMD_STOP)
        self.proc_handler_queue.put_nowait(msg)


class TimeConfig(qw):
    """Entries and Buttons for setting total experiment time"""
    set_time_signal = qc.pyqtSignal(name="SetTimeSignal")

    def __init__(self, dirs):
        super(TimeConfig, self).__init__()
        self.dirs = dirs
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        self.init_entries()
        self.grid.addWidget(self.time_entry_frame)

    def init_entries(self):
        """Create and Connect Time Config Entries"""
        # Entries and Buttons
        self.entries = {}
        time = HHMMSS(ms_equiv=self.dirs.settings.ttl_time)
        self.entries[HOUR] = GuiIntOnlyEntry(max_digits=2, default_text=str(time.hh))
        self.entries[MINS] = GuiIntOnlyEntry(max_digits=2, default_text=str(time.mm))
        self.entries[SECS] = GuiIntOnlyEntry(max_digits=2, default_text=str(time.ss))
        for _, entry in self.entries.items():
            entry.setMaximumWidth(qt_text_metrics.width('00000'))
        self.set_text_in_entries()
        self.confirm_btn = qg.QPushButton('\nOK\n')
        self.confirm_btn.clicked.connect(self.set_time)
        # Construct Frame
        self.time_entry_frame = qg.QGroupBox()
        self.time_entry_frame.setTitle('Total Experiment Time:')
        self.time_entry_frame.setMaximumWidth(200)
        grid = qg.QGridLayout()
        self.time_entry_frame.setLayout(grid)
        # Add to Frame
        grid.addWidget(self.confirm_btn, 2, 0, 1, 5)
        for index, name in enumerate([HOUR, MINS, SECS]):
            label = qg.QLabel(name)
            label.setAlignment(qAlignCenter)
            grid.addWidget(label, 0, index * 2)
            grid.addWidget(self.entries[name], 1, index * 2)
            if index < 2:
                label = qg.QLabel(':')
                label.setAlignment(qAlignCenter)
                grid.addWidget(label, 1, index * 2 + 1)

    def set_text_in_entries(self):
        """Sets entry text from dirs.settings"""
        time = HHMMSS(ms_equiv=self.dirs.settings.ttl_time)
        self.entries[HOUR].setText(str(time.hh))
        self.entries[MINS].setText(str(time.mm))
        self.entries[SECS].setText(str(time.ss))

    def set_time(self):
        """Sets total experiment time"""
        hh = self.entries[HOUR].text()
        mm = self.entries[MINS].text()
        ss = self.entries[SECS].text()
        time = HHMMSS(hh=hh, mm=mm, ss=ss)
        # Check for Errors
        # 1. Minimum time of 5s
        if time.ms < 5000:
            time = HHMMSS(ms=5000)
        # 2. Is total time configured less than max time of any progress bar element?
        if any([(time.ms < cfg.off_ms) for cfg in self.dirs.settings.last_ard.configs]):
            time = HHMMSS(ms_equiv=max([time.ms] + [cfg.off_ms for cfg in self.dirs.settings.last_ard.configs]))
            msg = 'Total Time cannot be less than [{}:{}:{}] ' \
                  'because one of the Arduino Outputs finish beyond this value.\n\n' \
                  'Reconfigure Arduino Outputs to Reduce Total Time.' \
                  ''.format(time.hh, time.mm, time.ss)
            GuiMessage(self, msg=msg)
        # Setting Empty Entries
        self.dirs.settings.ttl_time = time.ms
        self.set_text_in_entries()
        # Notify Proc_handler of updated time
        msg = NewMessage(cmd=CMD_SET_TIME, val=time.ms)
        self.proc_handler_queue.put_nowait(msg)
        # Notify other GUI widgets of updated time
        self.set_time_signal.emit()


class SaveWidget(qw)
