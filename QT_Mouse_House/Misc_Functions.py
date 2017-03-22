# coding=utf-8

"""Misc. Functions"""


# Imports
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
        return '{}--{}'.format(day, clock)


# Data Functions
def ard_decode_data(dirs, name, data_source):
    """Read Packed Arduino Data and Returns a Readable Format"""

