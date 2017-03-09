# coding=utf-8
"""
Miscellaneous functions for use throughout the program
"""


from copy import deepcopy
from datetime import datetime


def format_secs(time_in_secs, report_ms=False, option=None):
    """Turns Seconds into MM:SS; optionally turns millis inputs into MM:SS.sss
    Optionally report only Min or Sec"""
    output = ''
    secs = int(time_in_secs) % 60
    mins = int(time_in_secs) // 60
    if report_ms:
        millis = int((time_in_secs - int(time_in_secs)) * 1000)
        output = '{:0>2}:{:0>2}.{:0>3}'.format(mins, secs, millis)
    elif not report_ms:
        output = '{:0>2}:{:0>2}'.format(mins, secs)
    if option == 'min':
        output = '{:0>2}'.format(mins)
    elif option == 'sec':
        output = '{:0>2}'.format(secs)
    return output


def format_daytime(options, dayformat='/', timeformat=':'):
    """Returns day and time in various formats"""
    time_now = datetime.now()
    if options == 'daytime':
        dayformat = '-'
        timeformat = '-'
    day = '{}{}{}{}{}'.format(time_now.year, dayformat,
                              time_now.month, dayformat,
                              time_now.day)
    clock = '{:0>2}{}{:0>2}{}{:0>2}'.format(time_now.hour, timeformat,
                                            time_now.minute, timeformat,
                                            time_now.second)
    if options == 'day':
        return day
    elif options == 'time':
        return clock
    elif options == 'daytime':
        return '{}--{}'.format(day, clock)


def time_diff(start_time, end_time=None, choice='millis'):
    """Returns time difference from starting time"""
    if end_time is None:
        end_time = datetime.now()
    timediff = (end_time - start_time)
    if choice == 'millis':
        return timediff.seconds * 1000 + int(timediff.microseconds) / 1000
    elif choice == 'micros':
        return timediff.seconds * 1000 + float(timediff.microseconds) / 1000


def lim_str_len(string, length, end='...'):
    """Limit a given string to a specified length"""
    if len(string) <= length:
        return string
    else:
        return '{}{}'.format(string[:length - len(end)], end)


def deepcopy_lists(outer, inner, populate=None):
    """Returns a list of lists with unique
    Python IDs for each outer list, populated with desired variable
    or callable object

    would have been easier with numpy arrays but i'm in too deep now
    """
    hold = []
    for i in range(outer):
        if callable(populate):
            hold.append([])
            for n in range(inner):
                hold[i].append(populate())
        elif not callable(populate):
            hold.append(deepcopy([populate] * inner))
    if outer == 1:
        hold = hold[0]
    return hold


def dict_flatten(*args):
    """flattens the given dictionary into a list"""
    hold = []
    for a in args:
        hold.append([i for s in a.values() for i in s])
    return hold


def check_binary(num, register):
    """Given a number and arduino register
    Return all corresponding arduino pins"""
    dicts = {'binary': 'pin_num'}
    if register == 'D':
        dicts = {1: 0, 2: 1, 4: 2, 8: 3,
                 16: 4, 32: 5, 64: 6, 128: 7}
    elif register == 'B':
        dicts = {1: 8, 2: 9, 4: 10,
                 8: 11, 16: 12, 32: 13}
    store = []
    for i in dicts:
        if num & i > 0:
            store.append(dicts[i])
    return store
