# coding=utf-8

"""Handles IO and Configurations across all modules and devices"""

import sys
from Misc.Names import *


class MainSettings(object):
    """Holds all relevant user configurable settings"""
    def __init__(self):
        # Device Specific Params
        self.ard_ser_port = ''
        # Last Used Settings
        self.last_save_dir = ''
        self.last_fp = PhotometrySettings()
        self.last_lj = LjkSettings()
        self.last_ard = ArdSettings()
        # User configured Presets for future use
        self.ard_presets = {}
        self.ljk_presets = {}

    @property
    def ttl_time(self):
        """Returns total experiment time in ms"""
        return self.last_ard.ttl_time_ms

    @ttl_time.setter
    def ttl_time(self, time_ms):
        """Sets total experiment time in ms"""
        self.last_ard.ttl_time_ms = time_ms

    def load_examples(self):
        """Example settings for first time users"""
        self.last_save_dir = HOME_DIR + '\\Desktop'
        # Set arduino serial port
        if sys.platform.startswith('win'):
            self.ard_ser_port = 'COM4'
        else:
            self.ard_ser_port = '/dev/tty.usbmodem1421'
        # Example Configs for various devices
        self.last_ard.load_blank()
        self.last_lj.load_blank()
        self.last_fp.load_example()
        # Preconfigured Presets
        self.ard_presets = {'example': ArdSettings().load_example()}
        self.ljk_presets = {'example': LjkSettings().load_example()}


class ArdSettings(object):
    """Container of one set of arduino settings"""
    def __init__(self):
        self.ttl_time_ms = 0
        self.configs = []

    def load_blank(self):
        """Blank Config"""
        self.ttl_time_ms = 20000

    def load_example(self):
        """Example Preset Config"""
        self.ttl_time_ms = 180000
        example_tone = ArdSegment(on_ms=120000, off_ms=150000, pin=10, frequency=2800, types=TONE)
        example_output = ArdSegment(on_ms=148000, off_ms=150000, pin=6, types=OUTP)
        # Configs is a list of arduino segment command objects
        self.configs = [example_tone, example_output]
        return self


class ArdSegment(object):
    """A container for a single time segment of arduino settings"""
    def __init__(self, on_ms, off_ms, types, pin, frequency=None, phase_shft=None, duty_cycle=None):
        self.on_ms = on_ms
        self.off_ms = off_ms
        self.types = types
        self.pin = pin
        self.freq = frequency
        self.phast_shift = phase_shft
        self.duty_cycle = duty_cycle


# -------------------------------------------------
class LjkSettings(object):
    """Container for LabJack Configs"""
    def __init__(self):
        self.ch_num = []
        self.scan_freq = 0

    def load_blank(self):
        """Blank Config"""
        self.ch_num = [13]
        self.scan_freq = 100

    def load_example(self):
        """Example Preset Config"""
        self.ch_num = [8, 12, 13]
        self.scan_freq = 6250
        return self


class PhotometrySettings(object):
    """Container for Photometry Configs - mainly for Hardware Lock-In and Wave Generator"""
    # todo: consider some coupling between this module and ljkSettings - labjack note which channels for fp?
    def __init__(self):
        self.data_ch = None
        self.main = {CHANNEL: None, FREQ: None}
        self.isos = {CHANNEL: None, FREQ: None}

    def load_example(self):
        """Example Preset Config"""
        self.data_ch = 8
        self.main = {CHANNEL: 12, FREQ: 211}
        self.isos = {CHANNEL: 13, FREQ: 531}
