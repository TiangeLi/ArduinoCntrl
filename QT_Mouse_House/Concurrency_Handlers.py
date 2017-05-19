# coding=utf-8

"""Manages instructions and data between main GUI process and child processes"""


import sys
import time
from Names import *
from Misc_Classes import *
import multiprocessing as mp
if sys.version[0] == '2':
    import Queue as Queue
else:
    import queue as Queue


class ProcessHandler(StoppableProcess):
    """Handles Communication between Main GUI and Devices"""
    def __init__(self, dirs, cameras, main_pipe_ends):
        super(ProcessHandler, self).__init__(callable_fn=None, args=None)
        self.dirs = dirs
        self.name = 'Process Handler'
        # Message Handling
        self.master_dump_queue = MASTER_DUMP_QUEUE
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        # Process Synchronization
        self.exp_start_event = EXP_START_EVENT
        # Device Comms
        self.cameras = cameras
        self.camera_pipes = main_pipe_ends
        self.labjack_pipes = None
        self.arduino_pipes = None
        # Use this device?
        self.use_cameras = {}
        for index, cam in enumerate(self.cameras):
            self.use_cameras[index] = True
        self.use_labjack = True
        self.use_arduino = True
        # Device is running?
        self.cameras_running = {}
        for index, cam in enumerate(self.cameras):
            self.cameras_running[index] = False
        self.labjack_running = False
        self.arduino_running = False
        # Handler Parameters
        self.running = True
        self.exp_running = False
        self.hardstop_exp = False
        self.save_file_name = ''

    def run(self):
        """Periodically checks and processes instructions from Main Process"""
        while self.running:
            time.sleep(5.0/1000.0)
            try:
                msg = self.proc_handler_queue.get_nowait()
            except Queue.Empty:
                pass
            else:
                if msg.startswith(RUN_EXP_HEADER):
                    self.run_experiment(msg)
                elif msg == HARDSTOP_HEADER:
                    self.hardstop()
                elif msg == EXIT_HEADER:
                    self.close_devices()
                elif msg.startswith(CMR_REC_FALSE):
                    cmr_ind = int(msg.replace(CMR_REC_FALSE, '', 1))
                    self.cameras_running[cmr_ind] = False
                elif msg.startswith(CMR_ERROR_EXIT):
                    cmr_ind = int(msg.replace(CMR_ERROR_EXIT, '', 1))
                    self.cameras_running[cmr_ind] = False
                    self.use_cameras[cmr_ind] = False
                elif msg.startswith(TTL_TIME_HEADER) or msg.startswith(DIR_TO_USE_HEADER):
                    self.set_device_params(msg)
            if self.exp_running:
                devices_to_check = [self.cameras_running[cmr] for cmr in self.use_cameras if self.use_cameras[cmr]]
                if not any(devices_to_check):
                    self.exp_start_event.clear()
                    self.exp_running = False
                    self.master_dump_queue.put_nowait(EXP_END_HEADER)

    def set_device_params(self, msg):
        """Sets the total run time in device processes"""
        for index, cmr_pipe in enumerate(self.camera_pipes):
            if self.use_cameras[index]:
                cmr_pipe.send(msg)

    def run_experiment(self, msg):
        """Checks device availability; Sends run command to in-use devices"""
        self.save_file_name = msg.replace(RUN_EXP_HEADER, '', 1)
        # If no devices are enabled, there's no point in starting an exp so we exit
        devices_to_use = [self.use_cameras[cmr] for cmr in self.use_cameras if self.use_cameras[cmr]]
        if len(devices_to_use) == 0:
            return
        # Devices should have been created in Main GUI; we just need to check connections
        if self.check_connections():
            for index, cmr_pipe in enumerate(self.camera_pipes):
                if self.use_cameras[index]:
                    cmr_pipe.send('{}{}'.format(RUN_EXP_HEADER, self.save_file_name))
                    cmr_pipe.recv()  # Just so we don't begin until everyone is ready
                    self.cameras_running[index] = True
            # Release the start event seen by all processes to begin experiment
            self.exp_start_event.set()
            self.exp_running = True
            self.master_dump_queue.put_nowait(EXP_STARTED_HEADER)
        else:
            self.master_dump_queue.put_nowait('{}*** Failed to initialize the '
                                              'selected devices.'.format(FAILED_INIT_HEADER))

    def check_connections(self):
        """Check if indicated devices are connected and responsive"""
        any_nonresponsive_devices = False
        for index, cmr_pipe in enumerate(self.camera_pipes):
            if self.use_cameras[index]:
                cmr_pipe.send(DEVICE_CHECK_CONN)
                if cmr_pipe.poll(3):
                    if not cmr_pipe.recv():
                        any_nonresponsive_devices = True
                else:
                    any_nonresponsive_devices = True
        return not any_nonresponsive_devices

    def hardstop(self):
        """Forces a premature exit from experiment"""
        for index, cmr_pipe in enumerate(self.camera_pipes):
            if self.use_cameras[index]:
                cmr_pipe.send(HARDSTOP_HEADER)
                cmr_pipe.recv()
                self.cameras_running[index] = False
        self.exp_start_event.clear()
        self.exp_running = False
        self.master_dump_queue.put_nowait(EXP_END_HEADER)

    def close_devices(self):
        """Safely closes device connections and processes"""
        for index, cmr_pipe in enumerate(self.camera_pipes):
            if self.use_cameras[index]:
                cmr_pipe.send(EXIT_HEADER)
                cmr_pipe.recv()
        self.master_dump_queue.put_nowait(EXIT_HEADER)
