# coding=utf-8

"""Configuration Widget for LabJack Settings"""

from copy import deepcopy

from Processes.MessageHandling import *

from QT_Mouse_House_2_Backup.Gui.MiscWidgets import *


# todo: THIS ENTIRE CLASS NEEDS TO BE REDONE WITH NEW PROC_HANDLER METHODS

class GuiLjConfig(qw):
    """Config LabJack Options"""
    def __init__(self, lj_grapher):
        super(GuiLjConfig, self).__init__()
        self.num_ch = 14  # 14 accessible analog channels
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        # Related LabJack Objects
        self.lj_grapher = lj_grapher  # Pass the device GUI display object to the config object
        # Begin
        self.initialize()

    # Initial Widgets and layout
    def initialize(self):
        """Sets up Labels and User Configurable Controls"""
        self.frame = qgriddedgroupbox('LabJack Config')
        self.grid.addWidget(self.frame)
        # Create objects, set Layout, add to grid.
        layout = [[self.init_summary_label()],
                  [self.init_scan_freq_configs()],
                  [self.init_ch_select_configs()]]
        self.frame.grid.add_arrayed_layout(layout)
        self.reload_gui_info(reset_gui_elements=True)

    def init_summary_label(self):
        """A label summarizing configured labjack settings"""
        self.summ_label = ql('', qAlignCenter, qStyleSunken | qStylePanel)
        return self.summ_label

    def init_scan_freq_configs(self):
        """An entry and button for configuring scan frequency"""
        frame = qgriddedframe()
        # Entry
        scan_freq = self.dirs.settings.last_lj.scan_freq
        self.scan_freq_entry = GuiIntOnlyEntry(max_digits=5, default_text=str(scan_freq))
        self.scan_freq_entry.setText(str(scan_freq))
        # Max Freq Label
        self.max_freq_label = ql('', qAlignCenter, qStyleSunken | qStylePanel)
        self.set_max_freq_label()
        # Buttons
        btn = qg.QPushButton('Confirm')
        btn.clicked.connect(self.set_scan_freq)
        # Layout
        nl = ql('Scan Frequency')
        fl = self.max_freq_label
        se = self.scan_freq_entry
        cb = btn
        layout = [[nl, '', '', nl, ''],
                  [fl, '', '', '', fl],
                  [se, '', '', se, cb]]
        frame.grid.add_arrayed_layout(layout)
        return frame

    def init_ch_select_configs(self):
        """Sets up selectable checkboxes for each channel"""
        frame = qgriddedframe()
        # Generate Objects
        label = ql('Channels Currently in Use:\n')
        self.checkboxes = [qg.QCheckBox('{:0>2}'.format(i)) for i in range(self.num_ch)]
        [self.checkboxes[i].clicked.connect(self.save_channels) for i in list(range(self.num_ch))]
        # Create and Complete Layout
        row_size = 5
        # -------> We take the list of checkboxes and chunk into a list of lists of length=row_size
        layout = [self.checkboxes[i:i+row_size] for i in xrange(0, len(self.checkboxes), row_size)]
        layout.insert(0, [label]*row_size)  # Then we add the label to the top of the layout
        frame.grid.add_arrayed_layout(layout)
        # Finish
        return frame

    # Set and Save Configs
    def set_max_freq_label(self):
        """Shows user the maximum scan freq allowed depending on num channels in use"""
        msg = 'Max Freq = 50000 / [{}] Channels = [{}] Hz'.format(self.num_ch_in_use(), self.max_freq())
        self.max_freq_label.setText(msg)

    def set_scan_freq(self):
        """Sets the Scan Frequency"""
        sf = self.scan_freq()
        if sf == '' or int(sf) == 0 or int(sf) > self.max_freq():
            self.scan_freq_entry.visual_warning()
            return
        self.update_lj_configs()

    def save_channels(self):
        """"""

    def update_lj_configs(self):
        """Update dirs.settings.last_lj, and notify proc_handler to update labjack process"""
        self.lj_grapher.plots_are_reset = False
        if not ch_num:
            ch_num = deepcopy(self.dirs.settings.last_lj.ch_num)
        if not scan_freq:
            scan_freq = deepcopy(self.dirs.settings.last_lj.scan_freq)
        # Generate the message to send



    # Load from Settings file
    def file_set_channels(self):
        """Sets channels selected based on ones enabled in file"""
        [self.checkboxes[i].setChecked(False) for i in range(self.num_ch)]
        [self.checkboxes[i].setChecked(True) for i
    # Misc. Functions for Convenience
    def num_ch_in_use(self):
        """Returns the number of actively in use channels"""
        return len(self.dirs.settings.last_lj.ch_num)

    def max_freq(self):
        """Returns the max frequency allowed based on num_ch_in_use()"""
        return int(50000 / self.num_ch_in_use())

    def scan_freq(self):
        """Returns the scan_frequency set in the scan_freq_entry box"""
        return self.scan_freq_entry.text().strip() in self.dirs.settings.last_lj.ch_num]

    def reload_gui_info(self, reset_gui_elements):
        """Reloads Visual Information Display based on Settings used from file"""
        if reset_gui_elements:
            self.scan_freq_entry.setText(str(self.dirs.settings.last_lj.scan_freq))
            self.set_channels()

