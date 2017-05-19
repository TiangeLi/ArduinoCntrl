# coding=utf-8

"""Qt Widgets for Experiment Config and Control"""

import os
from Names import *
from Misc_Classes import *
from Misc_Functions import *
from Custom_Qt_Tools import *
from copy import deepcopy
from Dirs_Settings import ArdDataContainer
from Custom_Qt_Widgets import GUI_LiveScrollingGraph, GUI_LJDataReport
import PyQt4.QtGui as qg
import PyQt4.QtCore as qc


class GUI_ExpControls(qg.QWidget):
    """Settings and Buttons for Configuring the Experiment"""
    def __init__(self, dirs, gui_progbar):
        qg.QWidget.__init__(self)
        self.dirs = dirs
        self.gui_progbar = gui_progbar
        # Initialize Widgets
        self.time_config_widget = GUI_TimeConfig(self.dirs, self.gui_progbar)
        self.start_stop_btns_widget = GUI_StartStopBtns(self.dirs, self.gui_progbar)
        self.save_config_widget = GUI_SaveConfig(self.dirs)
        self.lj_graph_widget = GUI_LiveScrollingGraph(dirs)
        self.lj_table_widget = GUI_LJDataReport()
        self.lj_config_widget = GUI_LabJackConfig(self.dirs, self.lj_graph_widget)
        self.ard_config_widget = GUI_ArdConfig(self.dirs, self.gui_progbar)
        self.device_presets_widget = GUI_DevicePresets(self.dirs, self.gui_progbar,
                                                       self.lj_config_widget,
                                                       self.time_config_widget)
        # Layout
        self.setup_tabs()
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        self.add_to_grid()

    def setup_tabs(self):
        """Sets up the main and config tabs"""
        self.tabs = qg.QTabWidget(self)
        tab_main = qg.QWidget(self.tabs)
        tab_config = qg.QWidget(self.tabs)
        self.tab_grid_main = qg.QGridLayout()
        self.tab_grid_config = qg.QGridLayout()
        tab_main.setLayout(self.tab_grid_main)
        tab_config.setLayout(self.tab_grid_config)
        self.tabs.addTab(tab_main, 'Main')
        self.tabs.addTab(tab_config, 'Config')
        self.add_to_tab_main()
        self.add_to_tab_config()

    def add_to_tab_main(self):
        """Add Widgets to Main Tab"""
        self.tab_grid_main.addWidget(self.lj_graph_widget, 0, 0)
        self.tab_grid_main.addWidget(self.lj_table_widget, 1, 0)

    def add_to_tab_config(self):
        """Add widgets to Config Tab"""
        self.tab_grid_config.addWidget(self.ard_config_widget, 0, 0, 1, 2)
        self.tab_grid_config.addWidget(self.lj_config_widget, 1, 1)
        self.tab_grid_config.addWidget(self.device_presets_widget, 1, 0)

    def add_to_grid(self):
        """Add tabs and non-tabbed widgets to grid"""
        self.grid.addWidget(self.start_stop_btns_widget, 0, 0)
        self.grid.addWidget(self.time_config_widget, 1, 0)
        self.grid.addWidget(self.save_config_widget, 2, 0)
        self.grid.addWidget(self.tabs, 0, 1, 3, 1)

    def enable_disable_widgets(self, exp_running):
        """Enable or Disable Widgets depending on experiment state"""
        # Widgets we enable on running an exp.
        enabled_on_run = [self.start_stop_btns_widget.stop_btn]
        # Widgets we disable on running an exp.
        disable_on_run = [self.start_stop_btns_widget.start_btn,
                          self.start_stop_btns_widget.name_frame,
                          self.save_config_widget, self.time_config_widget,
                          self.lj_config_widget, self.ard_config_widget,
                          self.device_presets_widget]
        # Config Enabled/Disabled:
        for widget in enabled_on_run:
            if exp_running:
                widget.setEnabled(True)
            else:
                widget.setEnabled(False)
        for widget in disable_on_run:
            if exp_running:
                widget.setEnabled(False)
            else:
                widget.setEnabled(True)


class GUI_LabJackConfig(qg.QWidget):
    """Configuring LabJack Options"""
    def __init__(self, dirs, grapher):
        qg.QWidget.__init__(self)
        self.num_ch = 14
        self.dirs = dirs
        self.grapher = grapher
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        # Setup and Layout
        self.initialize()

    def initialize(self):
        """Sets up Config Label and Controls"""
        self.frame = qg.QGroupBox('LabJack Config')
        self.grid.addWidget(self.frame)
        grid = qg.QGridLayout()
        self.frame.setLayout(grid)
        # Create objects and Add to grid
        grid.addWidget(self.init_summary_label(), 0, 0)
        grid.addWidget(self.init_entry(), 1, 0)
        grid.addWidget(self.init_checkboxes(), 2, 0)
        self.load_from_preset()

    def init_summary_label(self):
        """Sets up a label for summarizing labjack settings"""
        self.summ_label = qg.QLabel('')
        self.summ_label.setAlignment(qc.Qt.AlignCenter)
        self.summ_label.setFrameStyle(qg.QFrame.Sunken | qg.QFrame.StyledPanel)
        return self.summ_label

    def init_entry(self):
        """Sets up entry and button for scan freq"""
        frame = qg.QFrame()
        grid = qg.QGridLayout()
        frame.setLayout(grid)
        # Entry
        freq = self.dirs.settings.lj_last_used.scan_freq
        self.scan_freq_entry = GUI_IntOnlyEntry(max_digits=5, default_txt=str(freq))
        self.scan_freq_entry.setText(str(freq))
        # Buttons
        confirm_btn = qg.QPushButton('Confirm')
        confirm_btn.clicked.connect(self.save_scan_freq)
        # Layout
        grid.addWidget(qg.QLabel('Scan Frequency:'), 0, 0, 1, 4)
        grid.addWidget(self.scan_freq_entry, 1, 0, 1, 4)
        grid.addWidget(confirm_btn, 1, 4)
        return frame

    def init_checkboxes(self):
        """Sets up checkboxes for each channel"""
        frame = qg.QFrame()
        grid = qg.QGridLayout()
        frame.setLayout(grid)
        # Generate and Layout checkboxes
        grid.addWidget(qg.QLabel('Channels Currently in Use:\n'), 0, 0, 1, 5)
        self.checkboxes = [qg.QCheckBox('{:0>2}'.format(i)) for i in range(self.num_ch)]
        [grid.addWidget(self.checkboxes[i],
                        i // 5 + 1,
                        i - (i // 5) * 5) for i in range(self.num_ch)]
        [self.checkboxes[i].clicked.connect(self.save_channels) for i in list(range(self.num_ch))]
        return frame

    def set_summ_label(self):
        """Sets the summary label to reflect most updated LJ settings"""
        ch = self.dirs.settings.lj_last_used.ch_num
        freq = self.dirs.settings.lj_last_used.scan_freq
        self.summ_label.setText('Channels:\n{}\n\nScan Freq: [{} Hz]'.format(ch, freq))

    def save_scan_freq(self):
        """Sets the scan frequency"""
        scan_freq = self.scan_freq_entry.text().strip()
        if scan_freq == '':
            self.scan_freq_entry.visual_warning()
            return
        self.dirs.settings.lj_last_used.scan_freq = int(deepcopy(scan_freq))
        self.set_summ_label()

    def save_channels(self):
        """Saves channels selected based on boxes checked"""
        selected = [i for i in range(self.num_ch) if self.checkboxes[i].isChecked()]
        self.dirs.settings.lj_last_used.ch_num = deepcopy(selected)
        self.set_summ_label()
        self.enable_disable_chkboxes()
        self.grapher.reset_plots()

    def enable_disable_chkboxes(self):
        """Enable or disable check boxes depending on number of boxes checked"""
        selected = [i for i in range(self.num_ch) if self.checkboxes[i].isChecked()]
        # All check boxes available if selected between 1-7 channels
        if 1 < len(selected) < 8:
            [self.checkboxes[i].setEnabled(True) for i in range(self.num_ch)]
        # Cannot select more than 8 channels
        elif len(selected) == 8:
            [self.checkboxes[i].setEnabled(False) for i in range(self.num_ch)
             if i not in self.dirs.settings.lj_last_used.ch_num]
        # Cannot select fewer than 1 channel
        elif len(selected) == 1:
            [self.checkboxes[i].setEnabled(False) for i in range(self.num_ch) if self.checkboxes[i].isChecked()]

    def load_from_preset(self):
        """Changes label, entry, boxes checked based on settings file"""
        self.set_summ_label()
        self.scan_freq_entry.setText(str(self.dirs.settings.lj_last_used.scan_freq))
        self.set_channels()
        self.enable_disable_chkboxes()
        self.grapher.reset_plots()

    def set_channels(self):
        """Sets channels based on which ones enabled in dirs.settings"""
        [self.checkboxes[i].setChecked(True) for i in self.dirs.settings.lj_last_used.ch_num]
        [self.checkboxes[i].setChecked(False) for i in range(self.num_ch)
         if i not in self.dirs.settings.lj_last_used.ch_num]


class GUI_ArdConfig(qg.QWidget):
    """Configuring Arduino Input/Output Settings"""
    def __init__(self, dirs, gui_progbar):
        qg.QWidget.__init__(self)
        self.dirs = dirs
        self.gui_progbar = gui_progbar
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        # Setup and Layout
        self.initialize()
        self.setMaximumHeight(120)
        self.grid.addWidget(self.frame)

    def initialize(self):
        """Sets up buttons for arduino configuring"""
        self.frame = qg.QGroupBox('Arduino Config')
        grid = qg.QGridLayout()
        self.frame.setLayout(grid)
        # Dynamic "Types" Label
        self.types_label = qg.QLabel(' ')
        self.types_label.setAlignment(qc.Qt.AlignCenter)
        self.types_label.setFrameStyle(qg.QFrame.Sunken | qg.QFrame.Panel)
        self.types_label.setMaximumWidth(qt_text_metrics.width('Output'))
        self.types_label.setMinimumWidth(qt_text_metrics.width('Output'))
        # Pin Dropdown Menu
        pins = ['', tone_pin, ''] + output_pins + [''] + pwm_pins
        self.pins_dropdown = qg.QComboBox()
        self.pins_dropdown.activated[str].connect(self.pins_dropdown_selection)
        for pin in pins:
            self.pins_dropdown.addItem(str(pin))
        # Other Entries and Labels
        static_labels = ['Pin', 'Type', 'Start Time', 'End Time', 'Freq', 'Phase Shift', 'Duty Cycle']
        self.entries = {}
        for index, label in enumerate(static_labels):
            # Create Entries
            if label not in ['Type', 'Pin']:
                self.entries[label] = GUI_IntOnlyEntry()
                self.entries[label].setEnabled(False)  # Initialize to Disabled
            # Create Column Labels
            static_labels[index] = qg.QLabel(label)
            static_labels[index].setAlignment(qc.Qt.AlignCenter)
        # Add to Grid
        for index, label in enumerate(static_labels):
            grid.addWidget(label, 0, index)
            if label.text() not in ['Type', 'Pin']:
                grid.addWidget(self.entries[label.text()], 1, index)
            elif label.text() == 'Type':
                grid.addWidget(self.types_label, 1, index)
            elif label.text() == 'Pin':
                grid.addWidget(self.pins_dropdown, 1, index)
        # Confirm Button
        self.confirm_btn = qg.QPushButton('\nConfirm\n')
        self.confirm_btn.clicked.connect(self.add_new_config)
        self.confirm_btn.setEnabled(False)  # Initialize to Disabled
        grid.addWidget(self.confirm_btn, 0, len(static_labels), 2, 1)

    def pins_dropdown_selection(self, selection):
        """Changes widget output and enabled entries depending on pin selection"""
        try:
            selection = int(selection)
        except ValueError:
            self.types_label.setText('')
            self.enable_disable_entries(types=None)
        else:
            if selection == tone_pin:
                self.types_label.setText(tone.capitalize())
                self.enable_disable_entries(types=tone)
            elif selection in output_pins:
                self.types_label.setText(output.capitalize())
                self.enable_disable_entries(types=output)
            elif selection in pwm_pins:
                self.types_label.setText(pwm.upper())
                self.enable_disable_entries(types=pwm)

    def enable_disable_entries(self, types):
        """Enables or Disables Entries based on field selection"""
        universal_enabled = ['Start Time', 'End Time']
        self.confirm_btn.setEnabled(True)
        if not types:
            enabled = []
            self.confirm_btn.setEnabled(False)
        elif types == tone:
            enabled = universal_enabled + ['Freq']
        elif types == output:
            enabled = universal_enabled
        elif types == pwm:
            enabled = universal_enabled + ['Freq', 'Phase Shift', 'Duty Cycle']
        for entry in self.entries:
            if entry not in enabled:
                self.entries[entry].setEnabled(False)
            else:
                self.entries[entry].setEnabled(True)

    def add_new_config(self):
        """Adds a new visual and backend config for arduino settings based on user input"""
        if not self.check_entries_not_empty():
            return
        new_config = ArdDataContainer(*self.get_entry_input())
        self.dirs.settings.ard_last_used.configs.append(new_config)
        self.gui_progbar.set_dynamic_background()

    def check_entries_not_empty(self):
        """Checks that entries are not empty before pulling input from them"""
        enabled_but_empty = [self.entries[entry]
                             for entry in self.entries
                             if self.entries[entry].isEnabled()
                             and self.entries[entry].text().strip() == '']
        if len(enabled_but_empty) > 0:
            [entry.visual_warning() for entry in enabled_but_empty]
            return False
        elif len(enabled_but_empty) == 0:
            return True

    def get_entry_input(self):
        """Gets user input from fields and returns specific parameters depending on type specified"""
        # First we get the output of all fields
        types = self.types_label.text().lower()
        pin = int(self.pins_dropdown.currentText())
        time_on_ms = float(self.entries['Start Time'].text()) * 1000
        time_off_ms = float(self.entries['End Time'].text()) * 1000
        freq = self.entries['Freq'].text()
        phase_shift = self.entries['Phase Shift'].text()
        duty_cycle = self.entries['Duty Cycle'].text()
        # Then we distribute necessary information depending on types requested
        if types == tone:
            return time_on_ms, time_off_ms, types, None, freq
        elif types == output:
            return time_on_ms, time_off_ms, types, pin
        elif types == pwm:
            return time_on_ms, time_off_ms, types, pin, freq, phase_shift, duty_cycle


class GUI_DevicePresets(qg.QWidget):
    """Selecting/Saving User Defined Presets"""
    def __init__(self, dirs, gui_progbar, lj_widget, time_widget):
        qg.QWidget.__init__(self)
        self.dirs = dirs
        self.gui_progbar = gui_progbar
        self.lj_widget = lj_widget
        self.time_widget = time_widget
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        self.device_types = [arduino, labjack]
        self.initialize()

    def preset_names(self, device):
        """Returns list of presets depending on device; 
        we use a function since the list is dynamic, makes life easier"""
        if device == labjack:
            return [''] + [name for name in self.dirs.settings.lj_presets]
        elif device == arduino:
            return [''] + [name for name in self.dirs.settings.ard_presets]

    def initialize(self):
        """Set up GUI elements"""
        frame = qg.QGroupBox('Device Presets')
        self.grid.addWidget(frame)
        grid = qg.QGridLayout()
        frame.setLayout(grid)
        # QWidget Containers
        self.entries = {dev: GUI_EntryWithWarning() for dev in self.device_types}
        self.btns = {dev: qg.QPushButton('Save New') for dev in self.device_types}
        self.dropdowns = {dev: qg.QComboBox() for dev in self.device_types}
        # Set frame layout with two inner frames for each device's preset GUI
        [grid.addWidget(self.init_preset_type(dev), i, 0) for i, dev in enumerate(self.device_types)]
        self.connect_widgets()

    def init_preset_type(self, dev):
        """Sets up an inner frame containing preset options depending on type passed"""
        frame = qg.QFrame()
        frame.setFrameStyle(qg.QFrame.Sunken | qg.QFrame.StyledPanel)
        grid = qg.QGridLayout()
        frame.setLayout(grid)
        # Setup Widgets
        grid.addWidget(qg.QLabel('{} Presets'.format(dev.capitalize())), 0, 0, 1, 5)
        grid.addWidget(self.entries[dev], 2, 0, 1, 5)
        grid.addWidget(self.btns[dev], 3, 2, 1, 1)
        grid.addWidget(qg.QLabel('Select: '), 4, 0, 1, 1)
        grid.addWidget(self.dropdowns[dev], 4, 1, 1, 4)
        return frame

    def connect_widgets(self):
        """Connects individual widgets to appropriate slots"""
        for dev in self.device_types:
            [self.dropdowns[dev].addItem(name) for name in sorted(self.preset_names(dev), key=str.lower)]
            self.dropdowns[dev].activated[str].connect(lambda option, device=dev: self.select_preset(option, device))
            self.btns[dev].clicked.connect(lambda cl, device=dev: self.save_preset(device))

    def select_preset(self, option, device):
        """Based on user selection in dropdowns, implement the preset"""
        if option == '':
            return
        if device == arduino:
            self.dirs.settings.ard_last_used = deepcopy(self.dirs.settings.ard_presets[option])
            self.gui_progbar.set_dynamic_background()
            self.time_widget.set_text_in_entries()
        elif device == labjack:
            self.dirs.settings.lj_last_used = deepcopy(self.dirs.settings.lj_presets[option])
            self.lj_widget.load_from_preset()

    def save_preset(self, device):
        """Saves user settings to a hardcopy preset"""
        name = self.entries[device].text().strip()
        # Is the entry empty?
        if len(name) == 0:
            self.entries[device].visual_warning()
            return
        # Is the entry overwriting a previous setting?
        overwrite = None
        if name in self.preset_names(device):
            msg = '[{}]\nAlready exists as a preset!\nOverwrite anyway?'.format(name)
            overwrite = qg.QMessageBox.question(self, 'Overwrite?', msg,
                                                qg.QMessageBox.No | qg.QMessageBox.Yes,
                                                qg.QMessageBox.No)
            if overwrite == qg.QMessageBox.No:
                return
        # If not empty, and [choose to overwrite OR a new name], we proceed to save it.
        if device == arduino:
            self.dirs.settings.ard_presets[name] = deepcopy(self.dirs.settings.ard_last_used)
        elif device == labjack:
            self.dirs.settings.lj_presets[name] = deepcopy(self.dirs.settings.lj_last_used)
        # Insert new preset name in the correct location;
        # if we did an overwrite we don't need to add a new name
        if overwrite != qg.QMessageBox.Yes:
            ind = sorted(self.preset_names(device) + [name], key=str.lower).index(name)
            self.dropdowns[device].insertItem(ind, name)
        # Now we set the dropdown option to display our newly saved (or overwritten) option
        self.dropdowns[device].setCurrentIndex(self.dropdowns[device].findText(name))


class GUI_StartStopBtns(qg.QWidget):
    """Start and Stop buttons and associated signals/slots. 
    Also contains an entry field for naming experiment runs"""
    def __init__(self, dirs, gui_progbar):
        qg.QWidget.__init__(self)
        self.dirs = dirs
        # Synchronization
        self.exp_start_event = EXP_START_EVENT
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        # GUI Objects
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        self.gui_progbar = gui_progbar
        # Setup
        self.setMinimumWidth(200)
        self.setMaximumWidth(200)
        self.init_btns()
        self.init_name_entry()
        self.add_to_grid()

    def init_btns(self):
        """Creates and Connects Start Stop Buttons"""
        self.start_btn = qg.QPushButton('START')
        self.start_btn.setStyleSheet('background-color: cyan')
        self.stop_btn = qg.QPushButton('STOP')
        self.stop_btn.setStyleSheet('background-color: orange')
        self.start_btn.clicked.connect(self.start_exp)
        self.stop_btn.clicked.connect(self.stop_exp)
        self.stop_btn.setEnabled(False)

    def init_name_entry(self):
        """An entry field for user naming"""
        self.name_frame = qg.QGroupBox('Trial Name:')
        grid = qg.QGridLayout()
        self.name_frame.setLayout(grid)
        self.name_entry = GUI_EntryWithWarning()
        grid.addWidget(self.name_entry)

    def get_exp_name(self):
        """Gets the experiment name from user input; if empty, set to no_name"""
        name = str(self.name_entry.text().strip())
        if name == '':
            return False
        for i in name:
            if i in FORBIDDEN_CHARS:
                name = name.replace(i, '_')
        return name

    def add_to_grid(self):
        """Add Buttons to Grid"""
        self.grid.addWidget(self.name_frame, 0, 0)
        self.grid.addWidget(self.start_btn, 1, 0)
        self.grid.addWidget(self.stop_btn, 2, 0)

    def start_exp(self):
        """Starts the experiment"""
        # Get the Exp name
        name = self.get_exp_name()
        if not name or name in self.dirs.list_file_names():
            self.name_entry.visual_warning()
            return
        # Save directory checks and handling
        self.dirs.check_dirs()
        if not self.dirs.created_date_stamped_dir:
            self.dirs.create_date_stamped_dir()
            self.proc_handler_queue.put_nowait('{}{}'.format(DIR_TO_USE_HEADER, self.dirs.date_stamped_dir))
        # Send start message to proc_handler
        self.proc_handler_queue.put_nowait('{}{}'.format(RUN_EXP_HEADER, name))

    def stop_exp(self):
        """Stops the experiment"""
        self.proc_handler_queue.put_nowait(HARDSTOP_HEADER)
        self.gui_progbar.stop_bar()


class GUI_TimeConfig(qg.QWidget):
    """Entries and Buttons for Configuring Experiment Time"""
    def __init__(self, dirs, gui_progbar):
        qg.QWidget.__init__(self)
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        self.dirs = dirs
        self.gui_progbar = gui_progbar
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        self.init_entries()
        self.add_to_grid()

    def init_entries(self):
        """Creates and Connects time config entries"""
        self.entries = []
        entry_types = [hh, mm, ss]
        # Entries and Buttons (Signal Emitters)
        hhmmss = time_convert(ms=self.dirs.settings.ttl_time())
        for index, entry_type in enumerate(entry_types):
            self.entries.append(GUI_IntOnlyEntry(max_digits=2, default_txt=str(hhmmss[index])))
            self.entries[index].setMaximumWidth(qt_text_metrics.width('00000'))
        self.set_text_in_entries()
        self.ttl_time_confirm_btn = qg.QPushButton('\nOk\n')
        self.ttl_time_confirm_btn.clicked.connect(self.confirm_time)
        # Static Labels
        static_labels = ['Hour', 'Min', 'Sec', ':', ':']
        for index, name in enumerate(static_labels):
            static_labels[index] = qg.QLabel(name)
            static_labels[index].setAlignment(qc.Qt.AlignCenter)
        # Keep time entries contained in its own frame
        self.time_entry_frame = qg.QGroupBox()
        self.time_entry_frame.setTitle('Total Experiment Time:')
        self.time_entry_frame.setMaximumWidth(200)
        grid = qg.QGridLayout()
        self.time_entry_frame.setLayout(grid)
        # Add components to frame
        grid.addWidget(self.ttl_time_confirm_btn, 2, 0, 1, 5)
        for index, entry in enumerate(self.entries):
            grid.addWidget(static_labels[index], 0, index * 2)
            grid.addWidget(entry, 1, index * 2)
            if index < 2:
                grid.addWidget(static_labels[index + 3], 1, index * 2 + 1)

    def set_text_in_entries(self):
        """Sets the text based on dirs.settings"""
        hhmmss = time_convert(ms=self.dirs.settings.ttl_time())
        [self.entries[index].setText(str(hhmmss[index])) for index, entry_type in enumerate([hh, mm, ss])]

    def confirm_time(self):
        """Sets the total experiment time"""
        hhmmss = ''
        # Get User Entry
        for entry in self.entries:
            hhmmss += '{:0>2}'.format(str(entry.text()))
        # Error Checking
        if int(hhmmss) < 5:
            ms = 5000
        else:
            ms = time_convert(hhmmss=hhmmss)
        # Setting empty entries
        for index, time in enumerate(time_convert(ms=ms)):
            self.entries[index].setText(str(time))
        self.dirs.settings.set_ttl_time(ms)
        self.proc_handler_queue.put_nowait('{}{}'.format(TTL_TIME_HEADER, ms))
        self.gui_progbar.set_dynamic_background()

    def add_to_grid(self):
        """Add Widgets to Grid"""
        self.grid.addWidget(self.time_entry_frame, 1, 0, 1, 2)


class GUI_SaveConfig(qg.QWidget):
    """User configurable save file names"""
    def __init__(self, dirs):
        qg.QWidget.__init__(self)
        self.dirs = dirs
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        # Setup
        self.setMaximumWidth(200)
        self.initialize()

    def initialize(self):
        """Gets list of existing save directories"""
        grid = qg.QGridLayout()
        frame = qg.QGroupBox('Current Save Directory:')
        change_dir_btn = qg.QPushButton('Change Directory')
        self.dir_label = qg.QLabel('')
        self.set_dirs_label(self.dirs.settings.last_used_save_dir)
        self.dir_label.setFrameStyle(qg.QFrame.Sunken | qg.QFrame.Panel)
        # Connect Signals
        change_dir_btn.clicked.connect(self.change_dirs_dialog)
        # Layout
        frame.setLayout(grid)
        grid.addWidget(self.dir_label, 0, 0)
        grid.addWidget(change_dir_btn, 1, 0)
        self.grid.addWidget(frame)

    def change_dirs_dialog(self):
        """Opens a dialog for user to specify save directory"""
        directory = str(qg.QFileDialog.getExistingDirectory(None, "Select Directory",
                                                            self.dirs.settings.last_used_save_dir))
        # Don't change anything if we cancelled the dialog
        if len(directory) == 0:
            return
        # Otherwise set dir to the one we selected in dialog
        self.dirs.settings.last_used_save_dir = directory
        self.set_dirs_label(directory)
        self.dirs.created_date_stamped_dir = False

    def set_dirs_label(self, dirs):
        """Sets self.dirs_label with word wrapping on '\\' markers"""
        max_len = 23
        lines = []
        curr_line = ''
        for i in [d for d in dirs.split('\\')]:
            if not len(curr_line) == 0:
                curr_line += '\\'
            if len(curr_line + i) < max_len:
                curr_line += i
            else:
                lines.append(curr_line)
                curr_line = '' + i
        lines.append(curr_line)  # Append the final line that hasn't been added yet
        label = '\n'.join([''.join(line) for line in lines])
        self.dir_label.setText(label)
