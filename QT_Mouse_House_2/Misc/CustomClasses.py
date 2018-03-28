# coding=utf-8

"""Usefl reimplementations of many classes"""

import multiprocessing as mp


class HHMMSS(object):
    """Container for Time in Hour:Min:Sec format"""
    def __init__(self, ms_equiv=None, hh=None, mm=None, ss=None):
        self.ms = int(ms_equiv)
        self.hh = int(hh)
        self.mm = int(mm)
        self.ss = int(ss)
        self.convert()

    def convert(self):
        """Converts HHMMSS to millis, or millis to HHMMSS"""
        if all([self.hh, self.mm, self.ss]):
            secs = self.ss + self.mm * 60 + self.hh * 3600
            self.ms = secs * 1000
        elif self.ms:
            secs = self.ms // 1000
            self.hh = secs // 3600
            self.mm = (secs - self.hh * 3600) // 60
            self.ss = (secs - self.hh * 3600 - self.mm * 60)


class StoppableProcess(mp.Process):
    """Multiprocessing Process with stop() method"""
    def __init__(self):
        super(StoppableProcess, self).__init__()
        self.daemon = True
        # We can check the self._stop flag to determine if running or not
        self._stop = mp.Event()

    def stop(self):
        """Sets the STOP flag"""
        self._stop.set()

    def stopped(self):
        """Checks status of STOP flag"""
        return self._stop.is_set()


class ProcessMessage(object):
    """A Message Container"""
    def __init__(self, device, command, value):
        self.device = device
        self.command = command
        self.value = value


def NewMessage(dev=None, cmd=None, val=None):
    """Returns a Packaged ProcessMessage Tuple"""
    msg = ProcessMessage(device=dev, command=cmd, value=val)
    return msg.device, msg.command, msg.value


def ReadMessage(process_message_tuple):
    """Converts a packaged ProcessMessage tuple into a ProcessMessage object"""
    return ProcessMessage(*process_message_tuple)
