# coding=utf-8

"""Useful Custom Classes"""


import threading as tr
import multiprocessing as mp


class StoppableThread(tr.Thread):
    """Thread class with stop() method"""
    def __init__(self, callable_fn, args):
        super(StoppableThread, self).__init__()
        self.daemon = True
        # Thread periodically checks the self._stop flag
        self._stop = tr.Event()
        # Callable function and arguments
        self.callable_fn = callable_fn
        self.args = args

    def stop(self):
        """Sets the stop flag to True"""
        self._stop.set()

    def stopped(self):
        """Checks if the thread is stopped and should terminate"""
        return self._stop.is_set()

    def run(self):
        """Overrides default run(). Call using start() for new thread"""
        while not self.stopped():
            self.callable_fn(self.args)


class StoppableProcess(mp.Process):
    """Process class with stop() method"""
    def __init__(self, callable_fn, args):
        super(StoppableProcess, self).__init__()
        self.daemon = True
        # Process periodically checks the self._stop flag
        self._stop = mp.Event()
        # Callable Function and Arguments
        self.callable_fn = callable_fn
        self.args = args

    def stop(self):
        """Sets the stop flag to True"""
        self._stop.set()

    def stopped(self):
        """Checks if process is stopped and should terminate"""
        return self._stop.is_set()

    def run(self):
        """Overrides default run(). Call using start() for new process"""
        while not self.stopped():
            self.callable_fn(self.args)
