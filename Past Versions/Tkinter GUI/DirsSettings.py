# coding=utf-8
"""
Handles all user saves and settings/presets

Directories() handles all settings that don't need to be saved, as well calls and holds 
MainSettings().

MainSettings() holds all relevant user presets. 

On calling Directories, it checks if settings.mshs and /Desktop/Mouse House Saves/
exist, and create them if not.

If settings.mshs exists, dirs.settings will point to a pickle.load() of that file;
otherwise we call MainSettings() and load some example presets, then point self.settings towards that
"""


import os
import sys
import pickle
import shutil
import threading


class Directories(object):
    """File Formats:
    .mshs: Main Settings Pickle
    .csv: Standard comma separated file for data output"""

    def __init__(self):
        # implemented a lock to edit self.settings safely between threads; probably not necessary
        self.lock = threading.Lock()
        self.user_home = os.path.expanduser('~')
        self.main_save_dir = self.user_home + '/desktop/Mouse House Saves/'
        self.main_settings_file = self.user_home + '/settings.mshs'
        # self.results_dir is dynamically generated for each launch using a timestamp
        # if user decides to switch to a different master directory (e.g. saves/tiange -> saves/li)
        # self.results_dir is saved in a directionary for later use
        # that is, each launch, each master directory will only have one results_dir to use
        self.results_dir = ''
        # save settings to dirs.settings?
        self.save_on_exit = True
        # Create directories/saves if necessary
        self.settings = MainSettings()
        if not os.path.isfile(self.main_settings_file):
            # Create Settings file if does not exist
            with open(self.main_settings_file, 'wb') as f:
                # Put in some example settings and presets
                self.settings.load_examples()
                pickle.dump(self.settings, f)
        if not os.path.exists(self.main_save_dir):
            os.makedirs(self.main_save_dir)

    def load(self, EXECUTABLE):
        """Load last used settings"""
        with open(self.main_settings_file, 'rb') as settings_file:
            self.settings = pickle.load(settings_file)
            self.check_dirs()
        if EXECUTABLE:
            self.settings.debug_console = False
        else:
            self.settings.debug_console = True

    def save(self):
        """Save settings for future use"""
        with open(self.main_settings_file, 'wb') as settings_file:
            pickle.dump(self.settings, settings_file)

    def check_dirs(self):
        """Checks that the directory in self.settings.save_dir exists;
        creates if not.
        (self.settings.save_dir is the last used Directory)"""
        if self.settings.save_dir != '':
            if not os.path.isdir(self.main_save_dir + self.settings.save_dir):
                os.makedirs(self.main_save_dir + self.settings.save_dir)

    def clear_saves(self):
        """Removes settings and save directories"""
        shutil.rmtree(self.user_home + '/desktop/Mouse House Saves/')
        os.remove(self.main_settings_file)

    def threadsafe_edit(self, recipient, donor, name=None):
        """Edits settings in a threadsafe manner; again, probably unnecessary"""
        self.lock.acquire()
        if recipient == 'ser_port':
            self.settings.ser_port = donor
        elif recipient == 'save_dir':
            self.settings.save_dir = donor
        elif recipient == 'fp_last_used':
            self.settings.fp_last_used = donor
        elif recipient == 'lj_last_used':
            self.settings.lj_last_used = donor
        elif recipient == 'ard_last_used':
            self.settings.ard_last_used = donor
        elif recipient == 'lj_presets':
            self.settings.lj_presets[name] = donor
        elif recipient == 'ard_presets':
            self.settings.ard_presets[name] = donor
        else:
            raise AttributeError('Settings has no attribute called {}!'.format(recipient))
        self.lock.release()


class MainSettings(object):
    """Object saves and holds all relevant parameters and presets"""

    def __init__(self):
        # arduino serial port
        self.ser_port = ''
        # last used save directory
        self.save_dir = ''
        # ch_num is the list of labjack channels
        self.fp_last_used = {'ch_num': [],
                             'main_freq': 0,
                             'isos_freq': 0}
        self.lj_last_used = {'ch_num': [],
                             'scan_freq': 0}
        # packet contains general instructions (e.g. time, number of total instructions
        # tone_pack contains tone instructions, and out_pack/pwm_pack accordingly
        self.ard_last_used = {'packet': [],
                              'tone_pack': [],
                              'out_pack': [],
                              'pwm_pack': []}
        # contains the same dictionary structure as in fp_last_used or lj_last_used
        self.lj_presets = {}
        self.ard_presets = {}
        # whether to print debug messages or not
        self.debug_console = False

    def load_examples(self):
        """Example settings"""
        if sys.platform.startswith('win'):
            self.ser_port = 'COM4'
        else:
            self.ser_port = '/dev/tty.usbmodem1421'
        self.fp_last_used = {'ch_num': [3, 4, 5],
                             'main_freq': 211,
                             'isos_freq': 531}
        self.lj_last_used = {'ch_num': [0, 1, 2],
                             'scan_freq': 6250}
        self.ard_last_used = {'packet': ['<BBLHHH', 0, 0, 20000, 0, 0, 0],
                              'tone_pack': [],
                              'out_pack': [],
                              'pwm_pack': []}
        # A few example presets for the first load
        self.lj_presets = {'example': {'ch_num': [0, 1, 2, 10, 11],
                                       'scan_freq': 6250}}
        self.ard_presets = {'example':
                            {'packet': ['<BBLHHH', 255, 255, 180000, 1, 2, 0],
                             'tone_pack': [['<LLH', 120000, 150000, 2800]],
                             'out_pack': [['<LB', 148000, 64], ['<LB', 150000, 64]],
                             'pwm_pack': []}}
        self.debug_console = False

    def quick_ard(self):
        """
        Quickly returns all Arduino parameters
        """
        return [self.ard_last_used['packet'],
                self.ard_last_used['tone_pack'],
                self.ard_last_used['out_pack'],
                self.ard_last_used['pwm_pack']]

    def quick_lj(self):
        """
        Quickly return all LabJack parameters
        """
        return [self.lj_last_used['ch_num'],
                self.lj_last_used['scan_freq']]

    def quick_fp(self):
        """
        Quickly return all Photometry parameters
        """
        return [self.fp_last_used['ch_num'],
                self.fp_last_used['main_freq'],
                self.fp_last_used['isos_freq']]
