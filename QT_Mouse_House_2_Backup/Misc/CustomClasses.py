# coding=utf-8

"""Useful Custom Classes"""


import multiprocessing as mp


class StoppableProcess(mp.Process):
    """Multiprocessing Process with a Stop() method"""
    def __init__(self, name):
        super(StoppableProcess, self).__init__()
        self.name = name
        self.daemon = True
        # We use the self._stop flag to help us stop the process when needed
        self._stop = mp.Event()

    def stop(self):
        """Sets the stop flag to True"""
        self._stop.set()

    def stopped(self):
        """For external use: checks if process has _stop flag and should terminate"""
        return self._stop.is_set()
