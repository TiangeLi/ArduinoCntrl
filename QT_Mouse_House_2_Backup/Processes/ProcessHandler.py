# coding=utf-8

"""Manages Instructions and Data between Main GUI and Child Processes"""

from Misc.CustomClasses import StoppableProcess

from QT_Mouse_House_2_Backup.Misc.Variables import *


class NewProcHandlerMsg(object):
    """Object and Method for easily sending instructions to Process Handler"""
    def __init__(self, device=None, msg_type=None, parameter=None):
        super(NewProcHandlerMsg, self).__init__()
        self.dev = device
        self.type = msg_type
        self.param = parameter

    def submit(self):
        """Sends our message to proc handler"""
        PROC_HANDLER_QUEUE.put_nowait(self)


class ProcessHandler(StoppableProcess):
    """Main gateway between MasterGUI and Child Processes"""
    def __init__(self):
        super(ProcessHandler, self).__init__(name='Process Handler')
        self.dirs = DIRS
        self.master_dump_queue = MASTER_DUMP_QUEUE
        self.proc_handler_queue = PROC_HANDLER_QUEUE

    def run(self):
        """Periodically checks for and processes instructions between processes"""
        while self.running
