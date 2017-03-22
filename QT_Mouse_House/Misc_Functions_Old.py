# coding=utf-8

"""Miscellaneous Functions"""


from operator import itemgetter


def format_secs(time_in_secs, report_ms=False, option=None):
    """Turns Seconds into MM:SS"""
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
    or callable object"""
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


def ard_decode_data(dirs, name, data_source):
    """Read packed up Arduino Data and puts it in proper format"""
    time_seg = float(dirs.settings.ard_last_used['packet'][3]) / 1000
    if name == 'tone':
        start, on = 1, 2
    elif name == 'pwm':
        start, on = 2, 3
    elif name == 'output':
        indiv_trigs, indiv_times, trig_times, final_intv = [], [], {}, []
        start, on, = 1, 2
        for i in data_source:
            triggers = check_binary(i[2], 'D')
            for n in triggers:
                indiv_trigs.append(n)
                indiv_times.append(i[1])
        for i in range(len(indiv_trigs)):
            n = indiv_trigs[i]
            try:
                trig_times[n].append(indiv_times[i])
            except KeyError:
                trig_times[n] = [indiv_times[i]]
        for i in trig_times:
            for n in range(len(trig_times[i])):
                if n % 2 == 0:
                    final_intv.append([i,
                                       trig_times[i][n],
                                       trig_times[i][n + 1]])
        final_intv = sorted(final_intv,
                            key=itemgetter(1))
        data_source = final_intv
    ard_data = []
    for i in data_source:
        start_space = (float(i[start]) / time_seg)
        on_space = float(i[on]) / time_seg - start_space
        if on_space == 0:
            start_space -= 1
            on_space = 1
        off_space = 1000 - on_space - start_space
        if name == 'tone':
            ard_data.append([start_space,
                             on_space,
                             off_space,
                             i[3],
                             i[start],
                             i[on]])
        elif name == 'pwm':
            ard_data.append([start_space,
                             on_space,
                             off_space,
                             check_binary(i[5], 'B')[0],
                             i[4],
                             i[7],
                             i[6],
                             i[start],
                             i[on]])
        elif name == 'output':
            ard_data.append([start_space,
                             on_space,
                             off_space,
                             i[0],
                             i[start],
                             i[on]])
    return ard_data


def time_convert(ms=None, hh=None, mm=None, ss=None):
    """Converts ms to hhmmss, or hhmmss to ms"""
    if ms:
        ms = int(ms)
        ms //= 1000
        hh = ms // 3600
        mm = (ms - hh * 3600) // 60
        ss = (ms - hh * 3600 - mm * 60)
        return hh, mm, ss
    else:
        hh, mm, ss = int(hh), int(mm), int(ss)
        ms = ss + mm * 60 + hh * 3600
        ms *= 1000
        return ms


def pin_to_int(pin):
    """Returns the integer representation of any given arduino pin"""
    if pin < 8:
        return int('1' + '0' * int(pin), 2)
    if 8 <= pin <= 13:
        return int('1' + '0' * (int(pin) - 8), 2)
