# coding=utf-8

"""Qt Widgets for Experiment Config and Control"""

import os
from Names import *
from Misc_Classes import *
from Misc_Functions import *
from Custom_Qt_Tools import *
from copy import deepcopy
from Dirs_Settings import ArdDataContainer
from Custom_Qt_Widgets import GUI_LiveScrollingGraph, GUI_LJDataReport, GUI_StatusBars
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
        self.status_bars = GUI_StatusBars()
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
        self.tab_grid_main.addWidget(self.lj_graph_widget, 0, 0, 1, 5)
        self.tab_grid_main.addWidget(self.status_bars, 1, 0, 1, 3)
        self.tab_grid_main.addWidget(self.lj_table_widget, 1, 3, 1, 2)

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
        # Other changes
        if exp_running:
            self.lj_graph_widget.frame.setTitle('LabJack Live Stream (Low Frequency Scanning) - [Recording to File]')
        if not exp_running:
            self.lj_graph_widget.frame.setTitle('LabJack Live Stream (Low Frequency Scanning) - [Not Recording to File]')


class GUI_LabJackConfig(qg.QWidget):
    """Configuring LabJack Options"""
    def __init__(self, dirs, grapher):
        qg.QWidget.__init__(self)
        self.num_ch = 14
        self.dirs = dirs
        self.lj_proc_updated = False
        self.grapher = grapher
        self.proc_handler_queue = PROC_HANDLER_QUEUE
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
        self.reload_gui_info(True)

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
        # Max Freq Label
        self.max_freq_label = qg.QLabel('')
        self.max_freq_label.setAlignment(qc.Qt.AlignCenter)
        self.max_freq_label.setFrameStyle(qg.QFrame.Sunken | qg.QFrame.StyledPanel)
        self.set_max_freq_label()
        # Buttons
        confirm_btn = qg.QPushButton('Confirm')
        confirm_btn.clicked.connect(self.save_scan_freq)
        # Layout
        grid.addWidget(qg.QLabel('Scan Frequency:'), 0, 0, 1, 4)
        grid.addWidget(self.max_freq_label, 1, 0, 1, 5)
        grid.addWidget(self.scan_freq_entry, 2, 0, 1, 4)
        grid.addWidget(confirm_btn, 2, 4)
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

    def set_max_freq_label(self):
        """Shows user the maximum scan freq allowed"""
        num_ch = len(self.dirs.settings.lj_last_used.ch_num)
        msg = 'Max Freq = 50000 / [{}] Channels = [{}] Hz' \
              ''.format(num_ch, int(50000 / num_ch))
        self.max_freq_label.setText(msg)

    def set_summ_label(self):
        """Sets the summary label to reflect most updated LJ settings"""
        ch = self.dirs.settings.lj_last_used.ch_num
        freq = self.dirs.settings.lj_last_used.scan_freq
        self.summ_label.setText('Channels:\n{}\n\nScan Freq: [{} Hz]'.format(ch, freq))

    def save_scan_freq(self):
        """Sets the scan frequency"""
        scan_freq = self.scan_freq_entry.text().strip()
        max_freq = int(50000 / len(self.dirs.settings.lj_last_used.ch_num))
        if scan_freq == '' \
                or int(scan_freq) > max_freq \
                or int(scan_freq) == 0:
            self.scan_freq_entry.visual_warning()
            return
        self.update_lj_last_used(scan_freq=int(deepcopy(scan_freq)), reset_gui_elements=False)

    def update_lj_last_used(self, ch_num=None, scan_freq=None, send_to_proc_handler=True, reset_gui_elements=False):
        """Update dirs.settings.lj_last_used. Also notify proc_handler to update lj_proc settings"""
        self.grapher.plots_are_reset = False
        if not ch_num:
            ch_num = deepcopy(self.dirs.settings.lj_last_used.ch_num)
        if not scan_freq:
            scan_freq = deepcopy(self.dirs.settings.lj_last_used.scan_freq)
        # first notify proc_handler to update lj_proc settings
        if not self.lj_proc_updated:
            # Send Message
            if send_to_proc_handler:
                self.proc_handler_queue.put_nowait('{}{}|{}'.format(LJ_CONFIG, ch_num, scan_freq))
            # check back every 5 ms until lj_proc has been updated
            qc.QTimer.singleShot(5, lambda: self.update_lj_last_used(ch_num, scan_freq, False, reset_gui_elements))
        # once proc_handler has updated lj_procs, we update the GUI
        elif self.lj_proc_updated:
            self.dirs.settings.lj_last_used.ch_num = deepcopy(ch_num)
            self.dirs.settings.lj_last_used.scan_freq = deepcopy(scan_freq)
            self.reload_gui_info(reset_gui_elements)
            self.lj_proc_updated = False
            self.grapher.update_graphs()

    def save_channels(self):
        """Saves channels selected based on boxes checked"""
        selected = [i for i in range(self.num_ch) if self.checkboxes[i].isChecked()]
        max_freq = int(50000 / len(selected))
        freq = self.dirs.settings.lj_last_used.scan_freq
        if freq > max_freq:
            freq = max_freq
            self.scan_freq_entry.setText(str(freq))
        self.update_lj_last_used(ch_num=selected, scan_freq=freq, reset_gui_elements=False)

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

    def reload_gui_info(self, reset_gui_elements):
        """Changes label, entry, boxes checked based on settings file"""
        if reset_gui_elements:
            self.scan_freq_entry.setText(str(self.dirs.settings.lj_last_used.scan_freq))
            self.set_channels()
        self.set_summ_label()
        self.enable_disable_chkboxes()
        self.set_max_freq_label()
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
                self.entries[label] = GUI_IntOnlyEntry(max_digits=6)
                self.entries[label].setEnabled(False)  # Initialize to Disabled
            # Create Column Labels
            static_labels[index] = qg.QLabel(label)
            static_labels[index].setAlignment(qc.Qt.AlignCenter)
        # Some special restrictions on phase shift and duty cycles
        self.entries['Phase Shift'].setMaxLength(3)
        self.entries['Phase Shift'].set_min_max_value(0, 360)
        self.entries['Duty Cycle'].setMaxLength(2)
        self.entries['Duty Cycle'].set_min_max_value(1, 99)
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
            # First we check if our pin selection is a selected arduino progbar
            progbar_selected = self.gui_progbar.scene.selectedItems()
            if not (len(progbar_selected) == 1 and selection == int(progbar_selected[0].data.pin)):
                self.gui_progbar.reset_selection()
            # Then we set the labels and enable or disable necessary entries
            self.pins_dropdown.setCurrentIndex(self.pins_dropdown.findText(str(selection)))
            if selection == tone_pin:
                self.types_label.setText(tone)
                self.enable_disable_entries(types=tone)
            elif selection in output_pins:
                self.types_label.setText(output)
                self.enable_disable_entries(types=output)
            elif selection in pwm_pins:
                self.types_label.setText(pwm)
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
        if not self.check_entries_valid():
            return
        new_config = ArdDataContainer(*self.get_entry_input())
        # Adds the new config and reloads the progbar
        #   First we check if any conflicts exist
        conflicts = self.check_new_config_conflicts(new_config)
        # If we have selected exactly one progbar, then we make adjustments to it
        # BUT: We make adjustments if and only if there are no conflicts or the conflict is with the selected bar
        if len(self.gui_progbar.scene.selectedItems()) == 1 \
                and ((len(conflicts) == 1 and conflicts[0] == self.gui_progbar.scene.selectedItems()[0].data)
                     or len(conflicts) == 0):
            # We change the old config and overwrite it to the new config
            selected_item_data = self.gui_progbar.scene.selectedItems()[0].data
            index = self.dirs.settings.ard_last_used.configs.index(selected_item_data)
            self.dirs.settings.ard_last_used.configs[index] = new_config
            # Set the background
            self.gui_progbar.set_dynamic_background()
            # We then reselect the item so the user knows which bar they adjusted
            for bar in self.gui_progbar.ard_stim_bars():
                if bar.data == new_config:
                    bar.setSelected(True)
            self.gui_progbar.setFocus()
        # If no conflicts, we add the new config
        elif len(conflicts) == 0:
            self.dirs.settings.ard_last_used.configs.append(new_config)
            self.gui_progbar.set_dynamic_background()
        # Otherwise we send a warning to the user
        else:
            [item.visual_warning() for item in self.gui_progbar.ard_stim_bars()
             for config in conflicts if item.data == config]

    def check_entries_valid(self):
        """Checks that user inputs are appropriate inputs"""
        # Are entries empty?
        if not self.check_entries_not_empty():
            return False
        # Is the segment endtime greater than the segment start time?
        elif int(self.entries['End Time'].text()) <= int(self.entries['Start Time'].text()):
            self.entries['End Time'].visual_warning()
            self.entries['Start Time'].visual_warning()
            return False
        # Are tone frequencies at least 50Hz?
        elif self.types_label.text() == tone and int(self.entries['Freq'].text()) < 50:
            self.entries['Freq'].visual_warning()
            GUI_Message('Tone Frequencies must be at least 50Hz;\n\nUse PWM pins for Low Frequencies')
            return False
        # Are PWM frequencies at most 100Hz?
        elif self.types_label.text() == pwm and int(self.entries['Freq'].text()) > 100:
            self.entries['Freq'].visual_warning()
            GUI_Message('PWM Frequencies must be at most 100Hz;\n\nUse Pin 10 (Tone) for High Frequencies')
            return False
        else:
            return True

    def check_new_config_conflicts(self, new_config):
        """Checks if a new user config conflicts with previous entries"""
        conflicts = []
        configs = self.dirs.settings.ard_last_used.configs
        # Is new_config.pin already being used in a pre-existing config?
        configs = [config for config in configs if new_config.pin == config.pin]
        # If new_config.pin is already being used, does the new_config intersect with any previous configs?
        if len(configs) != 0:
            new_start, new_stop = new_config.time_on_ms, new_config.time_off_ms
            time_segments = [(config.time_on_ms, config.time_off_ms) for config in configs]
            conflicts = [configs[time_segments.index(segment)] for segment in time_segments
                         # New timepoints should not be within previous segments
                         if segment[0] < new_start < segment[1]
                         or segment[0] < new_stop < segment[1]
                         # New segments should not be within or encompass previous segments
                         or (segment[0] <= new_start and segment[1] >= new_stop)
                         or (segment[0] >= new_start and segment[1] <= new_stop)]
        return conflicts

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
        types = self.types_label.text()
        pin = int(self.pins_dropdown.currentText())
        time_on_ms = int(self.entries['Start Time'].text().strip()) * 1000
        time_off_ms = int(self.entries['End Time'].text().strip()) * 1000
        freq = self.entries['Freq'].text().strip()
        phase_shift = self.entries['Phase Shift'].text().strip()
        duty_cycle = self.entries['Duty Cycle'].text().strip()
        # Then we distribute necessary information depending on types requested
        if types == tone:
            return time_on_ms, time_off_ms, types, 10, freq
        elif types == output:
            return time_on_ms, time_off_ms, types, pin
        elif types == pwm:
            return time_on_ms, time_off_ms, types, pin, freq, phase_shift, duty_cycle

    def load_from_ard_bar(self, data):
        """Gets data from an implemented arduino bar in gui_progbar"""
        # Parse data
        pin, types, freq, phase_shift, duty_cycle, time_on, time_off = ('',) * 7
        if data:
            types = data.types
            time_on = str(int(data.time_on_ms / 1000))
            time_off = str(int(data.time_off_ms / 1000))
            if data.types == tone:
                pin = '10'
                freq = str(data.freq)
            elif data.types in [output, pwm]:
                pin = str(data.pin)
            if data.types == pwm:
                freq = str(data.freq)
                phase_shift = str(data.phase_shift)
                duty_cycle = str(data.duty_cycle)
        # Set Widgets
        self.pins_dropdown.setCurrentIndex(self.pins_dropdown.findText(pin))
        self.types_label.setText(types)
        self.entries['Start Time'].setText(time_on)
        self.entries['End Time'].setText(time_off)
        self.entries['Freq'].setText(freq)
        self.entries['Phase Shift'].setText(phase_shift)
        self.entries['Duty Cycle'].setText(duty_cycle)
        # Enable/Disable widgets
        self.enable_disable_entries(types)


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
            ch_num = self.dirs.settings.lj_presets[option].ch_num
            scan_freq = self.dirs.settings.lj_presets[option].scan_freq
            self.lj_widget.update_lj_last_used(ch_num=ch_num, scan_freq=scan_freq, reset_gui_elements=True)

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
        # Is the time in the entries lower than the times configured in the prog bars?
        if any([(ms < config.time_off_ms) for config in self.dirs.settings.ard_last_used.configs]):
            ms = max([ms] + [config.time_off_ms for config in self.dirs.settings.ard_last_used.configs])
            hhmmss = time_convert(ms=ms)
            msg = 'Total time cannot be less than [{}:{}:{}] ' \
                  'because one of the arduino output endpoints exceeds this value.\n\n' \
                  'Reconfigure arduino outputs to ' \
                  'reduce total time.'.format(hhmmss[0], hhmmss[1], hhmmss[2])
            GUI_Message(msg)
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
