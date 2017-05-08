# coding=utf-8

"""
Directories(): Controls all IO/Save Operations
Settings(): Use as Pickle file for GUI Settings
"""

import os
import sys
import shutil
import pickle


class Directories(object):
    """Controls all Directories and IO Operations"""

    def __init__(self):
        user_home = os.path.expanduser('~')
        self.main_save_dir = user_home + '/Desktop/Mouse_House_Saves/'
        self.settings_file = user_home + '/Settings.msh'
        self.results_dir = ''
        # Options
        self.save_on_exit = True
        self.settings = Settings()
        self.initialize()

    def initialize(self):
        """Checks for Files/Directories; Create new if not exit"""
        # -- Create Settings.msh if not exit -- #
        if not os.path.isfile(self.settings_file):
            # Load generic examples for first time users
            self.settings.load_examples()
            self.save()
        # -- Create Mouse_House_Saves directory if not exit -- #
        if not os.path.exists(self.main_save_dir):
            os.makedirs(self.main_save_dir)

    def load(self):
        """Load from Settings.msh"""
        with open(self.settings_file, 'rb') as settings_file:
            self.settings = pickle.load(settings_file)
            self.check_dirs()

    def save(self):
        """Save to Settings.msh"""
        with open(self.settings_file, 'wb') as settings_file:
            pickle.dump(self.settings, settings_file)

    def check_dirs(self):
        """
        Checks if last used settings.save_dir exists.
        Creates this directory if it does not exist (e.g. deleted between sessions)
        """
        if self.settings.save_dir != '':
            last_used_dir = self.main_save_dir + self.settings.save_dir
            if not os.path.isdir(last_used_dir):
                os.makedirs(last_used_dir)

    def clear_saves(self):
        """USE WITH CAUTION! Clears all settings and saves"""
        shutil.rmtree(self.main_save_dir)
        os.remove(self.settings_file)


class Settings(object):
    """Holds all relevant user configurable settings"""
    def __init__(self):
        self.ser_port = ''  # Arduino Serial Port
        self.save_dir = ''  # Last Used Save Directory
        self.num_cmrs = 0  # Number of Live Feed Cameras to Use
        # Last Used Settings
        self.fp_last_used = {'ch_num': [], 'main_freq': 0, 'isos_freq': 0}
        self.lj_last_used = {'ch_num': [], 'scan_freq': 0}
        self.ard_last_used = {'packet': [], 'tone_pack': [], 'out_pack': [], 'pwm_pack': []}
        # User Configured Presets
        self.lj_presets = {}
        self.ard_presets = {}

    def load_examples(self):
        """Example settings for first time users"""
        # Arduino Serial Port
        if sys.platform.startswith('win'):
            self.ser_port = 'COM4'
        else:
            self.ser_port = '/dev/tty.usbmodem1421'
        # Last Used Settings
        self.fp_last_used = {'ch_num': [8, 12, 13], 'main_freq': 211, 'isos_freq': 531}
        self.lj_last_used = {'ch_num': [8, 12, 13], 'scan_freq': 6250}
        self.ard_last_used = {'packet': ['<BBLHHH', 0, 0, 20000, 0, 0, 0],
                              'tone_pack': [], 'out_pack': [], 'pwm_pack': []}
        # Example Presets
        self.lj_presets = {'example': {'ch_num': [0, 1, 2, 10, 11], 'scan_freq': 6250}}
        self.ard_presets = {'example':
                            {'packet': ['<BBLHHH', 255, 255, 180000, 1, 2, 0],
                             'tone_pack': [['<LLH', 120000, 150000, 2800]],
                             'out_pack': [['<LB', 148000, 4], ['<LB', 150000, 4]],
                             'pwm_pack': []}}

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
