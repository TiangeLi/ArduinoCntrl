# coding=utf-8

"""Misc. Functions"""


# Imports
import math
import numpy as np
from datetime import datetime


# Formatting Functions
def format_secs(time_in_secs, option='norm'):
    """
    Turns Seconds into various time formats
    @time_in_secs: integer seconds; decimal milliseconds
    @option: 'norm', 'with_ms', 'min', 'sec'
    """
    output = ''
    # Check option given is in correct list of options
    if option not in ['norm', 'with_ms', 'min', 'sec']:
        raise ValueError('[{}] is not a valid option!'.format(option))
    # -- Obtain mins, secs, millis -- #
    mins = int(time_in_secs) // 60
    secs = int(time_in_secs) % 60
    millis = int((time_in_secs - int(time_in_secs)) * 1000)
    # -- Report time in specific format specified -- #
    if option == 'norm':  # MM:SS
        output = '{:0>2}:{:0>2}'.format(mins, secs)
    elif option == 'with_ms':  # MM:SS.mss
        output = '{:0>2}:{:0>2}.{:0>3}'.format(mins, secs, millis)
    elif option == 'min':  # MM
        output = '{:0>2}'.format(mins)
    elif option == 'sec':  # SS
        output = '{:0>2}'.format(secs)
    # -- Finish -- #
    return output


def format_daytime(option, use_as_save, dayformat='/', timeformat=':'):
    """
    Returns Day and Time in various formats
    @option = 'day', 'time', 'daytime'
    @use_as_save: True, False
    """
    time_now = datetime.now()
    # Check option given is in correct list of options
    if option not in ['day', 'time', 'daytime']:
        raise ValueError('[{}] is not a valid option!'.format(option))
    # If using this function to create timestamped save file, force format '-':
    if use_as_save:
        dayformat = '-'
        timeformat = '-'
    # -- Format Day and Time -- #
    day = '{:0>4}{}{:0>2}{}{:0>2}'.format(time_now.year, dayformat,
                                          time_now.month, dayformat,
                                          time_now.day)
    clock = '{:0>2}{}{:0>2}{}{:0>2}'.format(time_now.hour, timeformat,
                                            time_now.minute, timeformat,
                                            time_now.second)
    # -- Report DayTime in specific format needed -- #
    if option == 'day':
        return day
    elif option == 'time':
        return clock
    elif option == 'daytime':
        return '{}_{}'.format(day, clock)


def time_convert(ms=None, hhmmss=None):
    """Converts ms to hhmmss, or hhmmss to ms"""
    if ms and isinstance(ms, int):
        ms //= 1000
        hh = ms // 3600
        mm = (ms - hh * 3600) // 60
        ss = (ms - hh * 3600 - mm * 60)
        return hh, mm, ss
    elif hhmmss and isinstance(hhmmss, str) and len(hhmmss) == 6:
        hh, mm, ss = int(hhmmss[:2]), int(hhmmss[2:4]), int(hhmmss[4:6])
        ms = ss + mm * 60 + hh * 3600
        ms *= 1000
        return ms
    elif ms and not isinstance(ms, int):
        raise ValueError('[ms] Parameter must be integer!')
    elif hhmmss and not isinstance(hhmmss, str):
        raise ValueError('[hhmmss] Parameter must be string!')
    elif hhmmss and isinstance(hhmmss, str) and not len(hhmmss) == 6:
        raise ValueError('[hhmmss] string must be a length of 6!')
    else:
        raise ValueError('Check appropriate entries configured')


# Arduino Functions
def check_binary(num, register):
    """Given any number and an arduino register, return set of corresponding arduino pins"""
    dicts = {'binary': 'pin_num'}
    if register == 'D':
        dicts = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5, 64: 6, 128: 7}
    elif register == 'B':
        dicts = {1: 8, 2: 9, 4: 10, 8: 11, 16: 12, 32: 13}
    store = []
    for i in dicts:
        if num & i > 0:
            store.append(dicts[i])
    return store


# List Functions
def take_spread(sequence, num_to_take):
    """From a sequence, take num_to_take number of evenly spaced elements"""
    length = float(len(sequence))
    return [sequence[int(math.ceil(i * length / num_to_take))] for i in range(num_to_take)]
