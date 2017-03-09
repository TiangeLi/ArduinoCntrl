# coding=utf-8

"""
For use with Main_Module.py (QT_Mouse_House)

Directories: Controls all IO Operations
Settings: Pickle File for all GUI Settings
"""

import os
import sys
import shutil
import pickle


class Directories(object):
    """Controls all Directories and IO Operations"""

    def __init__(self):
        user_home = os.path.expanduser('~')
        self.main_save_dir = user_home + '/Desktop/Mouse House Saves/'
        self.settings_file = user_home + '/Settings.mshs'
        self.results_dir = ''
        self.save_on_exit = True
        self.settings = MainSettings()
        self.initialize()

    def initialize(self):
        """Checks files and directories and creates if not exist"""
        if not os.path.isfile(self.settings_file):
            # Create Settings.mshs if does not exist
            with open(self.settings_file, 'wb') as settings_file:
                # We'll use some pre-existing examples to help first time users
                self.settings.load_examples()
                pickle.dump(self.settings, settings_file)
        if not os.path.exists(self.main_save_dir):
            # Create Mouse House save directory if does not exist
            os.makedirs(self.main_save_dir)

    def load(self):
        """Load last used settings"""
        with open(self.settings_file, 'rb') as settings_file:
            self.settings = pickle.load(settings_file)
            self.check_dirs()
        self.settings.debug_console = False

    def save(self):
        """Save settings for future use"""
        with open(self.settings_file, 'wb') as settings_file:
            pickle.dump(self.settings, settings_file)

    def check_dirs(self):
        """Creates a save directory named in our Last Used Dir. records
        if that directory does not exist"""
        if self.settings.save_dir != '':
            if not os.path.isdir(self.main_save_dir + self.settings.save_dir):
                os.makedirs(self.main_save_dir + self.settings.save_dir)

    def clear_saves(self):
        """Removes settings and save directories"""
        shutil.rmtree(self.main_save_dir)
        os.remove(self.settings_file)


class MainSettings(object):
    """Object saves and holds all relevant parameters and presets"""

    def __init__(self):
        self.ser_port = ''
        self.save_dir = ''
        self.fp_last_used = {'ch_num': [], 'main_freq': 0, 'isos_freq': 0}
        self.lj_last_used = {'ch_num': [], 'scan_freq': 0}
        self.ard_last_used = {'packet': [], 'tone_pack': [], 'out_pack': [], 'pwm_pack': []}
        self.lj_presets = {}
        self.ard_presets = {}
        self.debug_console = False

    def load_examples(self):
        """Example settings"""
        if sys.platform.startswith('win'):
            self.ser_port = 'COM4'
        else:
            self.ser_port = '/dev/tty.usbmodem1421'
        self.fp_last_used = {'ch_num': [3, 4, 5], 'main_freq': 211, 'isos_freq': 531}
        self.lj_last_used = {'ch_num': [0, 1, 2], 'scan_freq': 6250}
        self.ard_last_used = {'packet': ['<BBLHHH', 0, 0, 20000, 0, 0, 0],
                              'tone_pack': [], 'out_pack': [], 'pwm_pack': []}
        # A few example presets for the first load
        self.lj_presets = {'example': {'ch_num': [0, 1, 2, 10, 11], 'scan_freq': 6250}}
        self.ard_presets = {'example':
                            {'packet': ['<BBLHHH', 255, 255, 180000, 1, 2, 0],
                             'tone_pack': [['<LLH', 120000, 150000, 2800]],
                             'out_pack': [['<LB', 148000, 4], ['<LB', 150000, 4]],
                             'pwm_pack': []}}
        self.debug_console = False

    def quick_ard(self):
        """Quickly returns all Arduino parameters"""
        return [self.ard_last_used['packet'],
                self.ard_last_used['tone_pack'],
                self.ard_last_used['out_pack'],
                self.ard_last_used['pwm_pack']]

    def quick_lj(self):
        """Quickly return all LabJack parameters"""
        return [self.lj_last_used['ch_num'],
                self.lj_last_used['scan_freq']]

    def quick_fp(self):
        """Quickly return all Photometry parameters"""
        return [self.fp_last_used['ch_num'],
                self.fp_last_used['main_freq'],
                self.fp_last_used['isos_freq']]
