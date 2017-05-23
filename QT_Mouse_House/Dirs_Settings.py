# coding=utf-8

"""
Directories(): Controls all IO/Save Operations
Settings(): Use as Pickle file for GUI Settings
"""

import os
import sys
import shutil
import pickle
from Names import *
from copy import deepcopy
from Misc_Functions import *


class Directories(object):
    """Controls all Directories and IO Operations"""

    def __init__(self):
        user_home = os.path.expanduser('~')
        self.settings_file = user_home + '\\Settings.msh'
        self.results_dir = ''
        # Options
        self.created_date_stamped_dir = False
        self.save_on_exit = True
        self.del_all = False  # DO NOT CHANGE TO TRUE, WILL DELETE SETTINGS!
        self.settings = Settings()
        self.initialize()

    def initialize(self):
        """Checks for Files/Directories; Create new if not exit"""
        # -- Create Settings.msh if not exit -- #
        if not os.path.isfile(self.settings_file):
            # Load generic examples for first time users
            self.settings.load_examples()
            self.save()

    def list_file_names(self):
        """Returns a list of files in the current save directory"""
        # if we haven't created the date stamped directory yet, obviously no files in there; return empty list
        if not self.created_date_stamped_dir:
            return []
        # if we did create the dir, then we look for files in there.
        else:
            files = os.listdir(self.date_stamped_dir)
            file_names = [file.split('[')[1].split(']')[0] for file in files]
            return file_names

    def load(self):
        """Load from Settings.msh"""
        with open(self.settings_file, 'rb') as settings_file:
            self.settings = pickle.load(settings_file)

    def save(self):
        """Save to Settings.msh"""
        with open(self.settings_file, 'wb') as settings_file:
            pickle.dump(self.settings, settings_file)

    def check_dirs(self):
        """Checks if last used settings.save_dir exists.
        Creates this directory if it does not exist (e.g. deleted between sessions)"""
        dirs = self.settings.last_used_save_dir
        if dirs != '' and not os.path.isdir(dirs):
            os.makedirs(dirs)
            self.created_date_stamped_dir = False

    def nuke_files(self):
        """USE WITH CAUTION! Clears all settings"""
        os.remove(self.settings_file)

    def create_date_stamped_dir(self):
        """Creates date stamped directory to organize results"""
        date_stamp = format_daytime('day', True)
        dirs = [d for d in os.listdir(self.settings.last_used_save_dir)
                if os.path.isdir('{}\\{}'.format(self.settings.last_used_save_dir, d))
                and d.startswith(date_stamp)]
        if len(dirs) > 0:
            num = max([int(d.split('#')[-1]) for d in dirs]) + 1
        else:
            num = 0
        self.date_stamped_dir = '{}\\{}_#{}'.format(self.settings.last_used_save_dir, date_stamp, num)
        os.makedirs(self.date_stamped_dir)
        self.created_date_stamped_dir = True


class Settings(object):
    """Holds all relevant user configurable settings"""
    def __init__(self):
        self.ard_ser_port = ''  # Arduino Serial Port
        self.last_used_save_dir = ''  # Last Used Save Directory
        self.num_cmrs = 0  # Number of Live Feed Cameras to Use
        # Last Used Settings
        self.fp_last_used = PhotometryData()
        self.lj_last_used = LabJackData()
        self.ard_last_used = ArduinoData()
        # User Configured Presets
        self.lj_presets = {}
        self.ard_presets = {}

    def ttl_time(self):
        """Returns total experiment time"""
        return self.ard_last_used.total_time_ms

    def set_ttl_time(self, ms):
        """Sets total experiment time"""
        self.ard_last_used.total_time_ms = ms

    def load_examples(self):
        """Example settings for first time users"""
        self.last_used_save_dir = os.path.expanduser('~') + '\\Desktop'
        # Arduino Serial Port
        if sys.platform.startswith('win'):
            self.ard_ser_port = 'COM4'
        else:
            self.ard_ser_port = '/dev/tty.usbmodem1421'
        # Example Last Used Settings
        self.fp_last_used.load_example()
        self.lj_last_used.load_blank()
        self.ard_last_used.load_blank()
        # Example Presets
        self.lj_presets = {'example': LabJackData().load_example()}
        self.ard_presets = {'example': ArduinoData().load_example()}


class ArduinoData(object):
    """Structure for Arduino Config Settings"""
    def __init__(self):
        self.total_time_ms = 0
        self.configs = []

    def load_blank(self):
        """Blank Config"""
        self.total_time_ms = 20000

    def load_example(self):
        """Example Preset Config"""
        self.total_time_ms = 180000
        self.configs = [ArdDataContainer(time_on_ms=120000, time_off_ms=150000, freq=2800, types=tone),
                        ArdDataContainer(time_on_ms=148000, time_off_ms=150000, pin=6, types=output)]
        return self


class ArdDataContainer(object):
    """A container for a single segment of arduino settings"""
    def __init__(self, time_on_ms, time_off_ms, types,
                 pin=None, freq=None,
                 phase_shift=None, duty_cycle=None):
        self.time_on_ms = time_on_ms
        self.time_off_ms = time_off_ms
        self.types = types
        if types == tone:
            self.pin = 10
        else:
            self.pin = pin
        self.freq = freq
        self.phase_shift = phase_shift
        self.duty_cycle = duty_cycle


class PhotometryData(object):
    """Structure for Photometry Config"""
    def __init__(self):
        self.ch_num = []
        self.main_freq = 0
        self.isos_freq = 0

    def load_example(self):
        """Preset Example Config"""
        self.ch_num = [8, 12, 13]
        self.main_freq = 211
        self.isos_freq = 531


class LabJackData(object):
    """Structure for LabJack Config"""
    def __init__(self):
        self.ch_num = []
        self.scan_freq = 0

    def load_blank(self):
        """Blank Config"""
        self.ch_num = [8, 12, 13]
        self.scan_freq = 6250

    def load_example(self):
        """Preset Example Config"""
        self.ch_num = [8, 12, 13]
        self.scan_freq = 6250
        return self
