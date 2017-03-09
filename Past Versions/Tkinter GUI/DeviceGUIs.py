# coding=utf-8
"""
Separate pop up GUIs for configuring devices
"""


import time
import Tkinter as Tk
from copy import deepcopy
import tkMessageBox as tkMb
from GUIElements import GUI, ScrollFrame
from MiscFunctions import deepcopy_lists, dict_flatten


#################################################################
# GUIs
class PhotometryGUI(GUI):
    """GUI for Configuring Photometry Options
    *Does not affect actual program function
        - When saving file outputs, photometry config options
          are appended to aid in Lock-In Analysis
    Options appended: - Channels Used and associated Data column
                      - Sample stimulation frequencies (primary and isosbestic)"""

    def __init__(self, master, dirs):
        GUI.__init__(self, master, dirs)
        self.root.title('Photometry Configuration')
        # Grab last used settings
        self.ch_num = self.dirs.settings.fp_last_used['ch_num']
        self.stim_freq = {'main': self.dirs.settings.fp_last_used['main_freq'],
                          'isos': self.dirs.settings.fp_last_used['isos_freq']}
        # Variables
        self.radio_button_vars = deepcopy_lists(outer=1, inner=3,
                                                populate=Tk.IntVar)
        self.label_names = ['Photometry Data Channel',
                            'Main Reference Channel',
                            'Isosbestic Reference Channel']
        self.main_entry = None
        self.isos_entry = None
        # Setup GUI
        self.setup_radio_buttons()
        self.setup_entry_fields()
        Tk.Button(self.root, text='FINISH', command=self.exit).pack(side=Tk.BOTTOM)

    def setup_radio_buttons(self):
        """sets up radio buttons for LabJack channel selection"""
        for i in range(3):
            self.radio_button_vars[i].set(self.ch_num[i])
        Tk.Label(self.root,
                 text='\nPrevious Settings Loaded\n'
                      'These settings will be saved in your .csv outputs.\n',
                 relief=Tk.RAISED).pack(fill='both', expand='yes')
        data_frame = Tk.LabelFrame(self.root,
                                   text=self.label_names[0])
        true_frame = Tk.LabelFrame(self.root,
                                   text=self.label_names[1])
        isos_frame = Tk.LabelFrame(self.root,
                                   text=self.label_names[2])
        frames = [data_frame, true_frame, isos_frame]
        buttons = deepcopy_lists(outer=3, inner=14)
        for frame in range(3):
            frames[frame].pack(fill='both', expand='yes')
            for i in range(14):
                buttons[frame][i] = Tk.Radiobutton(frames[frame],
                                                   text=str(i), value=i,
                                                   variable=self.radio_button_vars[frame],
                                                   command=lambda (button_var,
                                                                   index)=(self.radio_button_vars[frame],
                                                                           frame):
                                                   self.select_button(button_var, index))
                buttons[frame][i].pack(side=Tk.LEFT)

    def setup_entry_fields(self):
        """sets up entry fields for frequency entries"""
        freq_frame = Tk.LabelFrame(self.root,
                                   text='Primary and Isosbestic '
                                        'Stimulation Frequencies')
        freq_frame.pack(fill='both', expand='yes')
        Tk.Label(freq_frame, text='Main Frequency: ').pack(side=Tk.LEFT)
        self.main_entry = Tk.Entry(freq_frame)
        self.main_entry.pack(side=Tk.LEFT)
        self.isos_entry = Tk.Entry(freq_frame)
        self.isos_entry.pack(side=Tk.RIGHT)
        Tk.Label(freq_frame, text='Isosbestic Frequency: ').pack(side=Tk.RIGHT)
        self.main_entry.insert(Tk.END, '{}'.format(str(self.stim_freq['main'])))
        self.isos_entry.insert(Tk.END, '{}'.format(str(self.stim_freq['isos'])))

    def select_button(self, var, ind):
        """Changes button variables when user selects an option"""
        if var.get() not in self.ch_num:
            self.ch_num[ind] = var.get()
        else:
            temp_report = self.label_names[self.ch_num.index(var.get())]
            tkMb.showinfo('Error!',
                          'You already selected \n['
                          'Channel {}] \n'
                          'for \n'
                          '[{}]!'.format(var.get(), temp_report),
                          parent=self.root)
            self.radio_button_vars[ind].set(self.ch_num[ind])

    def exit(self):
        """Quit Photometry"""
        try:
            true_freq = int(self.main_entry.get().strip())
            isos_freq = int(self.isos_entry.get().strip())
            if true_freq == 0 or isos_freq == 0:
                tkMb.showinfo('Error!', 'Stimulation Frequencies '
                                        'must be higher than 0 Hz!',
                              parent=self.root)
            elif true_freq == isos_freq:
                tkMb.showinfo('Error!', 'Main sample and Isosbestic Frequencies '
                                        'should not be the same value.',
                              parent=self.root)
            else:
                self.stim_freq = {'main': true_freq,
                                  'isos': isos_freq}
                to_save = {'ch_num': self.ch_num,
                           'main_freq': self.stim_freq['main'],
                           'isos_freq': self.stim_freq['isos']}
                self.dirs.threadsafe_edit(recipient='fp_last_used', donor=to_save)
                self.root.destroy()
                self.root.quit()
        except ValueError:
            tkMb.showinfo('Error!', 'Stimulation frequencies must be '
                                    'Integers in Hz.',
                          parent=self.root)


class LabJackGUI(GUI):
    """GUI for LabJack configuration"""

    def __init__(self, master, dirs):
        GUI.__init__(self, master, dirs)
        self.root.title('LabJack Configuration')
        self.lj_save_name = ''
        # Grab last used LJ settings
        self.ch_num = self.dirs.settings.lj_last_used['ch_num']
        self.scan_freq = self.dirs.settings.lj_last_used['scan_freq']
        self.n_ch = len(self.ch_num)
        # Variables
        self.preset_list = []
        self.preset_chosen = Tk.StringVar()
        self.preset_menu = None
        self.new_save_entry = None
        self.button_vars = deepcopy_lists(outer=1, inner=14,
                                          populate=Tk.IntVar)
        self.scan_entry = None
        # Setup GUI
        self.preset_gui()
        self.manual_config_gui()
        Tk.Button(self.root,
                  text='FINISH',
                  command=self.exit).grid(row=1, column=0, columnspan=2)

    def update_preset_list(self):
        """Updates self.preset_list with all available presets"""
        self.preset_list = [i for i in self.dirs.settings.lj_presets]

    def preset_gui(self):
        """Loads all presets into a menu for selection"""
        self.update_preset_list()
        # Create frame
        right_frame = Tk.LabelFrame(self.root, text='Preset Configuration')
        right_frame.grid(row=0, column=1)
        # Load Presets
        Tk.Label(right_frame, text='\nChoose a Preset'
                                   '\nOr Save a '
                                   'New Preset:').pack(fill='both',
                                                       expand='yes')
        # existing presets
        preset_frame = Tk.LabelFrame(right_frame, text='Select a Saved Preset')
        preset_frame.pack(fill='both', expand='yes')
        self.preset_chosen.set(max(self.preset_list, key=len))
        self.preset_menu = Tk.OptionMenu(preset_frame, self.preset_chosen,
                                         *self.preset_list,
                                         command=self.preset_list_choose)
        self.preset_menu.config(width=10)
        self.preset_menu.pack(side=Tk.TOP)
        # Save New Presets
        new_preset_frame = Tk.LabelFrame(right_frame, text='(Optional): '
                                                           'Save New Preset')
        new_preset_frame.pack(fill='both', expand='yes')
        self.new_save_entry = Tk.Entry(new_preset_frame)
        self.new_save_entry.pack()
        Tk.Button(new_preset_frame, text='SAVE',
                  command=self.preset_save).pack()

    def preset_list_choose(self, name):
        """Configures settings based on preset chosen"""
        self.preset_chosen.set(name)
        self.ch_num = self.dirs.settings.lj_presets[name]['ch_num']
        self.scan_freq = self.dirs.settings.lj_presets[name]['scan_freq']
        self.n_ch = len(self.ch_num)
        # Clear settings and set to preset config
        for i in range(14):
            self.button_vars[i].set(0)
        for i in self.ch_num:
            self.button_vars[i].set(1)
        self.scan_entry.delete(0, Tk.END)
        self.scan_entry.insert(Tk.END, self.scan_freq)

    def preset_save(self):
        """Saves settings to new preset if settings are valid"""
        self.update_preset_list()
        validity = self.check_input_validity()
        if validity:
            save_name = self.new_save_entry.get().strip().lower()
            if len(save_name) == 0:
                tkMb.showinfo('Error!',
                              'You must give your Preset a name.',
                              parent=self.root)
            elif len(save_name) != 0:
                if save_name not in self.dirs.settings.lj_presets:
                    to_save = {'ch_num': self.ch_num, 'scan_freq': self.scan_freq}
                    self.dirs.threadsafe_edit(recipient='lj_presets', name=save_name, donor=to_save)
                    tkMb.showinfo('Saved!', 'Preset saved as '
                                            '[{}]'.format(save_name),
                                  parent=self.root)
                    menu = self.preset_menu.children['menu']
                    menu.add_command(label=save_name,
                                     command=lambda:
                                     self.preset_list_choose(save_name))
                    self.preset_chosen.set(save_name)
                elif save_name in self.dirs.settings.lj_presets:
                    if tkMb.askyesno('Overwrite?',
                                     '[{}] already exists.\n'
                                     'Overwrite this preset?'.format(save_name),
                                     parent=self.root):
                        to_save = {'ch_num': self.ch_num, 'scan_freq': self.scan_freq}
                        self.dirs.threadsafe_edit(recipient='lj_presets', name=save_name, donor=to_save)
                        tkMb.showinfo('Saved!', 'Preset saved as '
                                                '[{}]'.format(save_name),
                                      parent=self.root)

    def manual_config_gui(self):
        """Manually configure LabJack settings"""
        left_frame = Tk.LabelFrame(self.root, text='Manual Configuration')
        left_frame.grid(row=0, column=0)
        Tk.Label(left_frame, text='\nMost Recently '
                                  'Used Settings:').pack(fill='both',
                                                         expand='yes')
        # Configure channels
        ch_frame = Tk.LabelFrame(left_frame, text='Channels Selected')
        ch_frame.pack(fill='both', expand='yes')
        # Create Check Buttons
        buttons = deepcopy_lists(outer=1, inner=14)
        for i in range(14):
            buttons[i] = Tk.Checkbutton(ch_frame, text='{:0>2}'.format(i),
                                        variable=self.button_vars[i],
                                        onvalue=1, offvalue=0,
                                        command=self.select_channel)
        for i in range(14):
            buttons[i].grid(row=i // 5, column=i - (i // 5) * 5)
        for i in self.ch_num:
            buttons[i].select()
        # Configure sampling frequency
        scan_frame = Tk.LabelFrame(left_frame, text='Scan Frequency')
        scan_frame.pack(fill='both', expand='yes')
        Tk.Label(scan_frame, text='Freq/Channel (Hz):').pack(side=Tk.LEFT)
        self.scan_entry = Tk.Entry(scan_frame, width=8)
        self.scan_entry.pack(side=Tk.LEFT)
        self.scan_entry.insert(Tk.END, self.scan_freq)

    def select_channel(self):
        """Configures check buttons for LJ channels based
        on user selection"""
        redo = False
        temp_ch_num = deepcopy(self.ch_num)
        self.ch_num = []
        for i in range(14):
            if self.button_vars[i].get() == 1:
                self.ch_num.append(i)
        self.n_ch = len(self.ch_num)
        if self.n_ch > 8:
            tkMb.showinfo('Error!',
                          'You cannot use more than 8 LabJack '
                          'Channels at once.',
                          parent=self.root)
            redo = True
        elif self.n_ch == 0:
            tkMb.showinfo('Error!',
                          'You must configure at least one '
                          'Channel.',
                          parent=self.root)
            redo = True
        if redo:
            self.ch_num = temp_ch_num
            for i in range(14):
                self.button_vars[i].set(0)
            for i in self.ch_num:
                self.button_vars[i].set(1)
            self.n_ch = len(self.ch_num)

    def check_input_validity(self):
        """Checks if user inputs are valid;
        if valid, saves to settings object"""
        validity = False
        button_state = []
        for i in self.button_vars:
            button_state.append(i.get())
        if 1 not in button_state:
            tkMb.showinfo('Error!',
                          'You must pick at least one LabJack '
                          'Channel to Record from.',
                          parent=self.root)
        else:
            try:
                self.scan_freq = int(self.scan_entry.get().strip())
                max_freq = int(50000 / self.n_ch)
                if self.scan_freq == 0:
                    tkMb.showinfo('Error!',
                                  'Scan Frequency must be higher than 0 Hz.',
                                  parent=self.root)
                elif self.scan_freq > max_freq:
                    tkMb.showinfo('Error!',
                                  'SCAN FREQUENCY x NUMBER OF CHANNELS \n'
                                  'must be lower than [50,000Hz]\n\n'
                                  'Max [{} Hz] right now with [{}] Channels '
                                  'in use.'.format(max_freq, self.n_ch),
                                  parent=self.root)
                else:
                    validity = True
                    to_save = {'ch_num': self.ch_num, 'scan_freq': self.scan_freq}
                    self.dirs.threadsafe_edit(recipient='lj_last_used', donor=to_save)
            except ValueError:
                tkMb.showinfo('Error!', 'Scan Frequency must be an '
                                        'Integer in Hz.',
                              parent=self.root)
        return validity

    def exit(self):
        """Validates inputs and closes GUI"""
        validity = self.check_input_validity()
        if validity:
            self.root.destroy()
            self.root.quit()


class ArduinoGUI(GUI):
    """Arduino settings config. Settings are saved to
    self.dirs.settings object, which is pulled by the arduino at
    experiment start"""

    def __init__(self, master, dirs):
        GUI.__init__(self, master, dirs)
        self.types = ''
        self.num_entries = 0
        # Variables
        self.output_ids, self.pwm_ids = (range(2, 8), range(8, 14))
        self.pwm_ids.remove(10)
        self.pin_button_vars = None
        self.entries = None
        self.closebutton = None
        # Default entry validating does not end in closing the GUI
        self.close_gui = False
        # Pull last used settings
        [self.packet, self.tone_pack,
         self.out_pack, self.pwm_pack] = self.dirs.settings.quick_ard()
        self.max_time = 0
        self.data = {'starts': {}, 'middles': {}, 'ends': {}, 'hold': {}}
        self.return_data = []
        self.fields_validated = {}

    def tone_setup(self):
        """Tone GUI"""
        self.root.title('Tone Configuration')
        self.types = 'tone'
        num_pins, self.num_entries = 1, 15
        scroll_frame = ScrollFrame(self.root, num_args=num_pins,
                                   rows=self.num_entries + 1)
        # Setup Toggle Buttons
        self.pin_button_vars = Tk.IntVar()
        self.pin_button_vars.set(0)
        pin_button = Tk.Checkbutton(scroll_frame.top_frame,
                                    text='Enable Tone\n'
                                         '(Arduino Pin 10)',
                                    variable=self.pin_button_vars,
                                    onvalue=1, offvalue=0,
                                    command=lambda: self.button_toggle('tone'))
        pin_button.pack()
        # Setup Entries
        self.entries = [None] * self.num_entries
        Tk.Label(scroll_frame.middle_frame,
                 text='Time On(s), '
                      'Time until Off(s), '
                      'Freq (Hz)').grid(row=0, column=1, sticky=self.ALL)
        for row in range(self.num_entries):
            Tk.Label(scroll_frame.middle_frame,
                     text='{:0>2}'.format(row + 1)).grid(row=row + 1, column=0)
            validate = (scroll_frame.middle_frame.register(self.entry_validate),
                        False, row)
            self.entries[row] = Tk.Entry(scroll_frame.middle_frame,
                                         validate='focusout',
                                         validatecommand=validate)
            self.entries[row].grid(row=row + 1, column=1, sticky=self.ALL)
            self.entries[row].config(state=Tk.DISABLED)
        # Confirm button
        self.closebutton = Tk.Button(scroll_frame.bottom_frame,
                                     text='CONFIRM',
                                     command=self.pre_close)
        self.closebutton.pack(side=Tk.TOP)
        scroll_frame.finalize()
        # Finish setup
        self.platform_geometry(windows='308x420', darwin='257x272')

    def pwm_setup(self):
        """PWM Config"""
        self.root.title('PWM Configuration')
        self.types = 'pwm'
        num_pins, self.num_entries = 5, 15
        scroll_frame = ScrollFrame(self.root, num_pins,
                                   self.num_entries + 1, bottom_padding=50)
        # Usage instructions
        info_frame = Tk.LabelFrame(scroll_frame.top_frame,
                                   text='Enable Arduino Pins')
        info_frame.grid(row=0, column=0, sticky=self.ALL)
        Tk.Label(info_frame, text=' ' * 2).pack(side=Tk.RIGHT)
        Tk.Label(info_frame, text='e.g. 0,180,200,20,90  (Per Field)',
                 relief=Tk.RAISED).pack(side=Tk.RIGHT)
        Tk.Label(info_frame, text=' ' * 2).pack(side=Tk.RIGHT)
        Tk.Label(info_frame,
                 text='Enable pins, then input instructions '
                      'with comma separation.',
                 relief=Tk.RAISED).pack(side=Tk.RIGHT)
        Tk.Label(info_frame,
                 text=' ' * 5).pack(side=Tk.RIGHT)
        # Variables
        self.entries = deepcopy_lists(outer=num_pins, inner=self.num_entries)
        self.pin_button_vars = deepcopy_lists(outer=1, inner=num_pins,
                                              populate=Tk.IntVar)
        pin_buttons = [None] * num_pins
        # Setup items
        for pin in range(num_pins):
            pin_buttons[pin] = Tk.Checkbutton(info_frame,
                                              text='Pin {:0>2}'.format(self.pwm_ids[pin]),
                                              variable=self.pin_button_vars[pin],
                                              onvalue=1, offvalue=0,
                                              command=lambda tags=self.pwm_ids[pin]:
                                              self.button_toggle(tags))
            pin_buttons[pin].pack(side=Tk.LEFT)
            Tk.Label(scroll_frame.middle_frame,
                     text='Pin {:0>2}\n'
                          'Time On(s), '
                          'Time until Off(s), \n'
                          'Freq (Hz), '
                          'Duty Cycle (%),\n'
                          'Phase Shift '.format(self.pwm_ids[pin]) + '(' + u'\u00b0' + ')').grid(row=0, column=1 + pin)
            for row in range(self.num_entries):
                validate = (scroll_frame.middle_frame.register(self.entry_validate),
                            pin, row)
                Tk.Label(scroll_frame.middle_frame,
                         text='{:0>2}'.format(row + 1)).grid(row=row + 1, column=0)
                self.entries[pin][row] = Tk.Entry(scroll_frame.middle_frame, width=25,
                                                  validate='focusout',
                                                  validatecommand=validate)
                self.entries[pin][row].grid(
                    row=row + 1, column=1 + pin)
                self.entries[pin][row].config(state='disabled')
        # Confirm Button
        self.closebutton = Tk.Button(scroll_frame.bottom_frame,
                                     text='CONFIRM',
                                     command=self.pre_close)
        self.closebutton.pack(side=Tk.TOP)
        scroll_frame.finalize()
        # Finish Setup
        self.platform_geometry(windows='1070x440', darwin='1100x280')

    def output_setup(self):
        """Output GUI"""
        self.root.title('Simple Output Configuration')
        self.types = 'output'
        num_pins, self.num_entries = 6, 15
        scroll_frame = ScrollFrame(self.root, num_pins, self.num_entries + 1,
                                   bottom_padding=8)
        # Usage instructions
        info_frame = Tk.LabelFrame(scroll_frame.top_frame,
                                   text='Enable Arduino Pins')
        info_frame.grid(row=0, column=0, sticky=self.ALL)
        Tk.Label(info_frame, text=' ' * 21).pack(side=Tk.RIGHT)
        Tk.Label(info_frame, text='Enable pins, then input instructions '
                                  'line by line with comma '
                                  'separation.',
                 relief=Tk.RAISED).pack(side=Tk.RIGHT)
        Tk.Label(info_frame, text=' ' * 21).pack(side=Tk.RIGHT)
        # Variables
        self.entries = deepcopy_lists(outer=num_pins, inner=self.num_entries)
        self.pin_button_vars = deepcopy_lists(outer=1, inner=num_pins,
                                              populate=Tk.IntVar)
        pin_buttons = [None] * num_pins
        # Setup items
        for pin in range(num_pins):
            pin_buttons[pin] = Tk.Checkbutton(info_frame,
                                              text='PIN {:0>2}'.format(
                                                  self.output_ids[pin]),
                                              variable=self.pin_button_vars[pin],
                                              onvalue=1, offvalue=0,
                                              command=lambda tags=self.output_ids[pin]:
                                              self.button_toggle(tags))
            pin_buttons[pin].pack(side=Tk.LEFT)
            Tk.Label(scroll_frame.middle_frame,
                     text='Pin {:0>2}\n'
                          'Time On(s), '
                          'Time until Off(s)'.format(self.output_ids[pin])).grid(row=0,
                                                                                 column=1 + pin)
            for row in range(self.num_entries):
                validate = (scroll_frame.middle_frame.register(self.entry_validate),
                            pin, row)
                Tk.Label(scroll_frame.middle_frame,
                         text='{:0>2}'.format(row + 1)).grid(row=row + 1, column=0)
                self.entries[pin][row] = Tk.Entry(scroll_frame.middle_frame, width=18,
                                                  validate='focusout',
                                                  validatecommand=validate)
                self.entries[pin][row].grid(row=row + 1, column=1 + pin)
                self.entries[pin][row].config(state=Tk.DISABLED)
        # Confirm Button
        self.closebutton = Tk.Button(scroll_frame.bottom_frame,
                                     text='CONFIRM',
                                     command=self.pre_close)
        self.closebutton.pack(side=Tk.TOP)
        scroll_frame.finalize()
        # Finish Setup
        self.center()
        self.platform_geometry(windows='1198x430', darwin='1110x272')

    def button_toggle(self, tags):
        """Toggles the selected pin button"""
        if tags == 'tone':
            if self.pin_button_vars.get() == 0:
                for row in range(self.num_entries):
                    self.entries[row].configure(state=Tk.DISABLED)
            elif self.pin_button_vars.get() == 1:
                for row in range(self.num_entries):
                    self.entries[row].configure(state=Tk.NORMAL)
        else:
            var, ind = None, None
            if tags in self.output_ids:
                ind = self.output_ids.index(tags)
                var = self.pin_button_vars[ind]
            elif tags in self.pwm_ids:
                ind = self.pwm_ids.index(tags)
                var = self.pin_button_vars[ind]
            if var.get() == 0:
                for entry in range(self.num_entries):
                    self.entries[ind][entry].configure(state=Tk.DISABLED)
            elif var.get() == 1:
                for entry in range(self.num_entries):
                    self.entries[ind][entry].configure(state=Tk.NORMAL)

    # noinspection PyTypeChecker
    def entry_validate(self, pins=False, rows=None):
        """Checks inputs are valid"""
        entry, err_place_msg, arg_types = None, '', []
        row = int(rows)
        pin = None
        if pins:
            pin = int(pins)
        # If we request a close via confirm button, we do a final check
        close_gui = self.close_gui
        if self.close_gui:
            # set to False so if check fails we don't get stuck in a loop
            self.close_gui = False
        pin_ids = 0
        ####################################################################
        if self.types == 'tone':
            pin_ids = 10
            entry = self.entries[row]
            arg_types = ['Time On (s)', 'Time until Off (s)', 'Frequency (Hz)']
            err_place_msg = 'row [{:0>2}]'.format(row + 1)
        elif self.types == 'output':
            pin_ids = self.output_ids[pin]
            entry = self.entries[pin][row]
            arg_types = ['Time On (s)', 'Time until Off (s)']
            err_place_msg = 'row [{:0>2}], pin [{:0>2}]'.format(row + 1, pin_ids)
        elif self.types == 'pwm':
            pin_ids = self.pwm_ids[pin]
            entry = self.entries[pin][row]
            arg_types = ['Time On (s)', 'Time until Off (s)', 'Frequency (Hz)',
                         'Duty Cycle (%)', 'Phase Shift (deg)']
            err_place_msg = 'row [{:0>2}], pin [{:0>2}]'.format(row + 1, pin_ids)
        ####################################################################
        # Grab comma separated user inputs as a list
        inputs = entry.get().strip().split(',')
        for i in range(len(inputs)):
            inputs[i] = inputs[i].strip()
        # Now we begin to check entry validity
        # 1. Check Commas don't occur at ends or there exist any double commas:
        while True:
            time.sleep(0.0001)
            if '' in inputs:
                inputs.pop(inputs.index(''))
            else:
                break
        # 2. Check we have correct number of input arguments
        num_args = len(arg_types)
        error_str = ''
        for i in range(num_args):
            if i == 3:
                error_str += '\n'
            error_str += str(arg_types[i])
            if i < num_args - 1:
                error_str += ', '
        # 2a. More than 0 but not num_args
        if len(inputs) != num_args and len(inputs) > 0:
            tkMb.showinfo('Error!',
                          'Error in {}:\n'
                          'Setup requires [{}] arguments for each entry.\n\n'
                          'Comma separated in this order:\n\n'
                          '[{}]'.format(err_place_msg, num_args, error_str),
                          parent=self.root)
            entry.focus()
            return False
        # 2b. Exactly 0: we don't need to process an empty field
        if len(inputs) == 0:
            if close_gui:
                self.close()
            return False
        # 3. Check input content are valid
        try:
            on, off = int(inputs[0]), int(inputs[1])
            on_ms, off_ms = on * 1000, off * 1000
            refr, freq, phase, duty_cycle = None, 0, 0, 0
            if self.types == 'tone':
                freq = int(inputs[2])
                refr = freq
            elif self.types == 'output':
                refr = pin_ids
            elif self.types == 'pwm':
                freq = int(inputs[2])
                duty_cycle = int(inputs[3])
                phase = int(inputs[4])
                refr = long('{:0>5}{:0>5}{:0>5}'.format(freq, duty_cycle, phase))
            # 3a. Store max time configured; at close, if max_time > self.dirs.settings max time,
            #     we change the max time for procedure
            if (on_ms + off_ms) > self.max_time and off_ms != 0:
                self.max_time = on_ms + off_ms
            # 3b. Time interval for each entry must be > 0
            if off == 0:
                tkMb.showinfo('Error!',
                              'Error in {}:\n\n'
                              'Time Interval (i.e. '
                              'Time until Off) '
                              'cannot be 0s!'.format(err_place_msg),
                              parent=self.root)
                entry.focus()
                return False
            # 3c. Type specific checks
            if self.types == 'tone':
                if freq < 50:
                    tkMb.showinfo('Error!',
                                  'Error in {}:\n\n'
                                  'The TONE function works '
                                  'best for high frequencies.\n\n'
                                  'Use the PWM function '
                                  'instead for low Hz '
                                  'frequency modulation'.format(err_place_msg),
                                  parent=self.root)
                    entry.focus()
                    return False
            if self.types == 'pwm':
                if phase not in range(361):
                    tkMb.showinfo('Error!',
                                  'Error in {}:\n\n'
                                  'Phase Shift must be an integer\n'
                                  'between 0 and 360 degrees.'.format(err_place_msg),
                                  parent=self.root)
                    entry.focus()
                    return False
                if duty_cycle not in range(1, 100):
                    tkMb.showinfo('Error!',
                                  'Error in {}:\n\n'
                                  'Duty Cycle must '
                                  'be an integer '
                                  'percentage between '
                                  '1 and 99 inclusive.'.format(err_place_msg),
                                  parent=self.root)
                    entry.focus()
                    return False
                if freq > 100:
                    tkMb.showinfo('Error!',
                                  'Error in {}:\n\n'
                                  'The PWM function works best'
                                  'for frequencies <= 100 Hz.\n\n'
                                  'Use the TONE function or an'
                                  'external wave '
                                  'generator instead.'.format(err_place_msg),
                                  parent=self.root)
                    entry.focus()
                    return False
        except ValueError:
            tkMb.showinfo('Error!',
                          'Error in {}:\n\n'
                          'Input arguments '
                          'must be comma '
                          'separated integers'.format(err_place_msg),
                          parent=self.root)
            entry.focus()
            return False
        # 4. Check if any time intervals overlap
        #       Rules:
        #       - Time intervals cannot overlap for the same pin
        #       - Time intervals next to each other
        #         at the same [refr] will be joined into a single segment
        #         to save space on arduino
        #       Therefore:
        #       - OUTPUT Pins can always overlap. We just need to combine the time inputs
        #       - PWM Pins can overlap iff same [refr]; else raise error
        #       - Tone is one pin only. Only overlap if same [freq]
        #       (to date only implemented joining adjacent segments; no overlap
        #        managing available)
        ################################################################################
        # ...because pwm is a special butterfly and needs extra steps:
        starts_l, middles_l, ends_l, hold_l = {}, {}, {}, {}
        if self.types == 'pwm':
            pin_int = self.pin_to_int(pin_ids)
            # temporarily hold in starts_l so we can use self.data in the same way
            # for pwm and output/tone in the following
            (starts_l, middles_l, ends_l, hold_l) = (self.data['starts'],
                                                     self.data['middles'],
                                                     self.data['ends'],
                                                     self.data['hold'])
            try:
                starts_l[pin_ids], middles_l[pin_ids], ends_l[pin_ids], hold_l[pin_int]
            except KeyError:
                (starts_l[pin_ids], middles_l[pin_ids],
                 ends_l[pin_ids], hold_l[pin_int]) = {}, {}, {}, {}
            (self.data['starts'], self.data['middles'],
             self.data['ends'], self.data['hold']) = (starts_l[pin_ids], middles_l[pin_ids],
                                                      ends_l[pin_ids], hold_l[pin_int])
        # 4a.
        # Before we validate entries further:
        # If the validation is performed on a field that already had data validated
        # e.g. because user misclicked or needs to edit
        # we will need to remove its previous set of data first to prevent clashing
        self.time_remove(rows, pins, refr)
        # 4b. test for time overlaps
        starts_all, ends_all, middles_all = [], [], []
        try:
            self.data['starts'][refr], self.data['middles'][refr], self.data['ends'][refr]
        except KeyError:
            self.data['starts'][refr], self.data['middles'][refr], self.data['ends'][refr] = [], [], []
        if self.types in ['tone', 'pwm']:
            try:
                self.data['hold'][refr]
            except KeyError:
                self.data['hold'][refr] = []
            (starts_all, middles_all, ends_all) = dict_flatten(self.data['starts'],
                                                               self.data['middles'],
                                                               self.data['ends'])
        elif self.types == 'output':
            (starts_all, middles_all, ends_all) = (self.data['starts'][pin_ids],
                                                   self.data['middles'][pin_ids],
                                                   self.data['ends'][pin_ids])
        if on in starts_all or on + off in ends_all or on in middles_all or on + off in middles_all:
            tkMb.showinfo('Error!', 'Error in {}:\n\n'
                                    'Time intervals '
                                    'should not overlap for the same '
                                    'pin!'.format(err_place_msg),
                          parent=self.root)
            entry.focus()
            return False
        # 4c. We've finished checking for validity.
        #     If the input reached this far, it's ready to be added
        self.data['middles'][refr] += range(on + 1, on + off)
        front, back = 0, 0
        self.time_combine(on_ms, off_ms, front, back, refr)
        if on in self.data['ends'][refr] and on + off not in self.data['starts'][refr]:
            front, back = 1, 0
            self.data['middles'][refr].append(on)
            self.data['ends'][refr].remove(on)
            self.data['ends'][refr].append(on + off)
            self.time_combine(on_ms, off_ms, front, back, refr)
        elif on not in self.data['ends'][refr] and on + off in self.data['starts'][refr]:
            front, back = 0, 1
            self.data['middles'][refr].append(on + off)
            self.data['starts'][refr].remove(on + off)
            self.data['starts'][refr].append(on)
            self.time_combine(on_ms, off_ms, front, back, refr)
        elif on in self.data['ends'][refr] and on + off in self.data['starts'][refr]:
            front, back = 1, 1
            self.data['middles'][refr].append(on)
            self.data['middles'][refr].append(on + off)
            self.data['starts'][refr].remove(on + off)
            self.data['ends'][refr].remove(on)
            self.time_combine(on_ms, off_ms, front, back, refr)
        else:
            self.data['starts'][refr].append(on)
            self.data['ends'][refr].append(on + off)
        # Now we need to make sure this one comes out as an already validated field
        if self.types == 'tone':
            self.fields_validated[rows] = {'starts': on,
                                           'middles': range(on + 1, on + off),
                                           'ends': on + off,
                                           'hold': [on_ms, on_ms + off_ms],
                                           'refr': refr}
        elif self.types == 'output':
            pin_int = self.pin_to_int(refr)
            self.fields_validated[rows + pins] = {'starts': on,
                                                  'middles': range(on + 1, on + off),
                                                  'ends': on + off,
                                                  'hold': {on_ms: pin_int, off_ms: pin_int},
                                                  'refr': refr}
        elif self.types == 'pwm':
            self.fields_validated[rows + pins] = {'starts': on,
                                                  'middles': range(on + 1, on + off),
                                                  'ends': on + off,
                                                  'hold': [on_ms, on_ms + off_ms],
                                                  'refr': refr}
        # again, pwm requires some extra work before we finish...
        if self.types == 'pwm':
            (self.data['starts'],
             self.data['middles'],
             self.data['ends'],
             self.data['hold']) = (starts_l, middles_l, ends_l, hold_l)
        # If all is well and we requested a close, we close the GUI
        if close_gui:
            self.close()
        else:
            return True

    @staticmethod
    def pin_to_int(pin):
        """Returns the integer representation of
        any given arduino pin"""
        if pin < 8:
            return int('1' + '0' * int(pin), 2)
        if 8 <= pin <= 13:
            return int('1' + '0' * (int(pin) - 8), 2)

    # noinspection PyStatementEffect,PyUnresolvedReferences,PyTypeChecker
    def time_remove(self, rows, pins, refr):
        """Removes the indicated time segment"""
        field = {}
        if self.types == 'tone':
            try:
                self.fields_validated[rows]
            except KeyError:
                self.fields_validated[rows] = {'starts': -1, 'middles': [],
                                               'ends': -1, 'hold': [], 'refr': refr}
                return
            field = self.fields_validated[rows]
        elif self.types in ['output', 'pwm']:
            try:
                self.fields_validated[rows + pins]
            except KeyError:
                self.fields_validated[rows + pins] = {'starts': -1, 'middles': [],
                                                      'ends': -1, 'hold': [], 'refr': refr}
                return
            field = self.fields_validated[rows + pins]
        field_refr = field['refr']
        if self.types in ['tone', 'pwm']:
            try:
                # Check that the data exists at refr
                self.data['starts'][field_refr], self.data['middles'][field_refr]
                self.data['ends'][field_refr], self.data['hold'][field_refr]
                # Remove Middles
                for i in field['middles']:
                    if i in self.data['middles'][field_refr]:
                        self.data['middles'][field_refr].remove(i)
                # Remove starts, ends, holds
                if field['starts'] in self.data['starts'][field_refr]:
                    self.data['starts'][field_refr].remove(field['starts'])
                    self.data['hold'][field_refr].remove(field['starts'] * 1000)
                elif field['starts'] in self.data['middles'][field_refr]:
                    self.data['middles'][field_refr].remove(field['starts'])
                    self.data['ends'][field_refr].append(field['starts'])
                    self.data['hold'][field_refr].append(field['starts'] * 1000)
                if field['ends'] in self.data['ends'][field_refr]:
                    self.data['ends'][field_refr].remove(field['ends'])
                    self.data['hold'][field_refr].remove(field['ends'] * 1000)
                elif field['ends'] in self.data['middles'][field_refr]:
                    self.data['middles'][field_refr].remove(field['ends'])
                    self.data['starts'][field_refr].append(field['ends'])
                    self.data['hold'][field_refr].append(field['ends'] * 1000)
                # Set field to empty; we'll have to add back into it in the validate function
                if self.types == 'tone':
                    self.fields_validated[rows] = {'starts': -1, 'middles': [],
                                                   'ends': -1, 'hold': [], 'refr': refr}
                elif self.types == 'pwm':
                    self.fields_validated[rows + pins] = {'starts': -1, 'middles': [],
                                                          'ends': -1, 'hold': [], 'refr': refr}
            except KeyError:
                pass
        elif self.types == 'output':
            pin_int = self.pin_to_int(refr)
            try:
                self.data['starts'][field_refr], self.data['middles'][field_refr]
                self.data['ends'][field_refr]
                self.data['hold'][field['starts'] * 1000], self.data['hold'][field['ends'] * 1000]
                # rm middles
                for i in field['middles']:
                    if i in self.data['middles'][field_refr]:
                        self.data['middles'][field_refr].remove(i)
                # rm s, e, h
                if field['starts'] in self.data['starts'][field_refr]:
                    self.data['starts'][field_refr].remove(field['starts'])
                    if self.data['hold'][field['starts'] * 1000] == pin_int:
                        self.data['hold'] = {key: self.data['hold'][key]
                                             for key in self.data['hold']
                                             if key != field['starts'] * 1000}
                    else:
                        self.data['hold'][field['starts'] * 1000] -= pin_int
                elif field['starts'] in self.data['middles'][field_refr]:
                    self.data['middles'][field_refr].remove(field['starts'])
                    self.data['ends'][field_refr].append(field['starts'])
                    if field['starts'] * 1000 in self.data['hold']:
                        self.data['hold'][field['starts'] * 1000] += pin_int
                    else:
                        self.data['hold'][field['starts'] * 1000] = pin_int
                if field['ends'] in self.data['ends'][field_refr]:
                    self.data['ends'][field_refr].remove(field['ends'])
                    if self.data['hold'][field['ends'] * 1000] == pin_int:
                        self.data['hold'] = {key: self.data['hold'][key]
                                             for key in self.data['hold']
                                             if key != field['ends'] * 1000}
                    else:
                        self.data['hold'][field['ends'] * 1000] -= pin_int
                elif field['ends'] in self.data['middles'][field_refr]:
                    self.data['middles'][field_refr].remove(field['ends'])
                    self.data['starts'][field_refr].append(field['ends'])
                    if field['ends'] * 1000 in self.data['hold']:
                        self.data['hold'][field['ends'] * 1000] += pin_int
                    else:
                        self.data['hold'][field['ends'] * 1000] = pin_int
                # set field to empty
                self.fields_validated[rows + pins] = {'starts': -1, 'middles': [],
                                                      'ends': -1, 'hold': [], 'refr': refr}
            except KeyError:
                pass

    # noinspection PyUnresolvedReferences
    def time_combine(self, on_ms, off_ms, front, back, refr):
        """Looks for adjacent time intervals and joins
        them into a single instruction"""
        if self.types in ['pwm', 'tone']:
            if front == 0 and back == 0:
                self.data['hold'][refr].append(on_ms)
                self.data['hold'][refr].append(on_ms + off_ms)
            if front == 1:
                self.data['hold'][refr].remove(on_ms)
                self.data['hold'][refr].remove(on_ms)
            if back == 1:
                self.data['hold'][refr].remove(on_ms + off_ms)
                self.data['hold'][refr].remove(on_ms + off_ms)
        elif self.types == 'output':
            pin_int = self.pin_to_int(refr)
            if front == 0 and back == 0:
                if on_ms not in self.data['hold']:
                    self.data['hold'][on_ms] = pin_int
                elif on_ms in self.data['hold']:
                    self.data['hold'][on_ms] += pin_int
                if on_ms + off_ms not in self.data['hold']:
                    self.data['hold'][on_ms + off_ms] = pin_int
                elif on_ms + off_ms in self.data['hold']:
                    self.data['hold'][on_ms + off_ms] += pin_int
            if front == 1:
                if self.data['hold'][on_ms] == (2 * pin_int):
                    self.data['hold'].pop(on_ms)
                else:
                    self.data['hold'][on_ms] -= (2 * pin_int)
            if back == 1:
                if self.data['hold'][on_ms + off_ms] == (2 * pin_int):
                    self.data['hold'].pop(on_ms + off_ms)
                else:
                    self.data['hold'][on_ms + off] -= (2 * pin_int)

    def pre_close(self):
        """Forces focus on button to do final validation check
        on last field entered in"""
        focus_is_entry = False
        current_focus = self.root.focus_get()
        if self.types == 'tone':
            if current_focus in self.entries:
                focus_is_entry = True
        elif self.types in ['pwm', 'output']:
            for pin in self.entries:
                if current_focus in pin:
                    focus_is_entry = True
        if focus_is_entry:
            # We indicate to entry_validate that we wish to close gui
            self.close_gui = True
            # then we force focus on the close button to
            # trigger validation on the last used entry field
            self.closebutton.focus()
        else:
            # if we aren't focused on a field, we close
            self.close()

    # noinspection PyUnresolvedReferences,PyTypeChecker
    def close(self):
        """Exits GUI Safely; otherwise we perform self.hard_exit()
        which will not save config settings"""
        # If we configured a max time higher than what it was before, update
        if self.max_time > self.dirs.settings.ard_last_used['packet'][3]:
            to_save = deepcopy(self.dirs.settings.ard_last_used)
            to_save['packet'][3] = self.max_time
            self.dirs.threadsafe_edit(recipient='ard_last_used', donor=to_save)
            main.ttl_time = self.max_time
            main.grab_ard_data(destroy=True)
            mins = format_secs(self.max_time / 1000, option='min')
            secs = format_secs(self.max_time / 1000, option='sec')
            main.min_entry.delete(0, Tk.END)
            main.min_entry.insert(Tk.END, '{:0>2}'.format(mins))
            main.sec_entry.delete(0, Tk.END)
            main.sec_entry.insert(Tk.END, '{:0>2}'.format(secs))
        # Retrieve data that we saved up so masterGUI can load and use
        self.return_data = []
        if self.types == 'output':
            self.return_data = self.data['hold']
        elif self.types == 'tone':
            for freq in self.data['hold']:
                self.data['hold'][freq] = sorted(self.data['hold'][freq])
                for i in range(len(self.data['hold'][freq])):
                    if i % 2 == 0:
                        self.return_data.append([self.data['hold'][freq][i],
                                                 self.data['hold'][freq][i + 1],
                                                 freq])
        elif self.types == 'pwm':
            for pin_int in self.data['hold']:
                for refr in self.data['hold'][pin_int]:
                    refr_i = str(refr)
                    freq_i, duty_i, phase_i = (int(refr_i[:-10]),
                                               int(refr_i[-10:-5]),
                                               int(refr_i[-5:]))
                    self.data['hold'][pin_int][refr] = sorted(self.data['hold'][pin_int][refr])
                    for i in range(len(self.data['hold'][pin_int][refr])):
                        if i % 2 == 0:
                            self.return_data.append([0,
                                                     self.data['hold'][pin_int][refr][i],
                                                     self.data['hold'][pin_int][refr][i + 1],
                                                     freq_i,
                                                     pin_int,
                                                     phase_i,
                                                     duty_i])
        self.root.destroy()
        self.root.quit()
