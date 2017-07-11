# coding=utf-8

"""Manages instructions and data between main GUI process and child processes"""


import sys
import time
from Names import *
from Misc_Classes import *
from Misc_Functions import *
import multiprocessing as mp
if sys.version[0] == '2':
    import Queue as Queue
else:
    import queue as Queue


class ProcessHandler(StoppableProcess):
    """Handles Communication between Main GUI and Devices"""
    def __init__(self, dirs, cmr_pipe_mains, lj_pipe_main):
        super(ProcessHandler, self).__init__(callable_fn=None, args=None)
        self.dirs = dirs
        self.name = 'Process Handler'
        # Message Handling
        self.master_dump_queue = MASTER_DUMP_QUEUE
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        # Process Synchronization
        self.exp_start_event = EXP_START_EVENT
        # Device Comms
        self.camera_pipes = cmr_pipe_mains
        self.labjack_pipe = lj_pipe_main
        self.arduino_pipe = None
        # Use this device?
        self.use_cameras = {index: True for index, _ in enumerate(self.camera_pipes)}
        self.use_labjack = True
        self.use_arduino = True
        # Device is running?
        self.cameras_running = {index: False for index, _ in enumerate(self.camera_pipes)}
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
                # New Object?
                if isinstance(msg, NamedObjectContainer):
                    if msg.name == LJ_PIPE_MAIN_NAME:
                        self.labjack_pipe = msg.obj
                        self.use_labjack = True
                        self.labjack_running = False
                # String Message?
                elif isinstance(msg, str):
                    # General Exp start/stop
                    if msg.startswith(RUN_EXP_HEADER):
                        self.run_experiment(msg)
                    elif msg == HARDSTOP_HEADER:
                        self.hardstop()
                    # Full Exit
                    elif msg == EXIT_HEADER:
                        self.close_devices()
                    # Device Operations
                    # -- Camera
                    elif msg.startswith(CMR_REC_FALSE):
                        cmr_ind = int(msg.replace(CMR_REC_FALSE, '', 1))
                        self.cameras_running[cmr_ind] = False
                    elif msg.startswith(CMR_ERROR_EXIT):
                        self.master_dump_queue.put_nowait(msg)
                        cmr_ind = int(msg.replace(CMR_ERROR_EXIT, '', 1))
                        self.cameras_running[cmr_ind] = False
                        self.use_cameras[cmr_ind] = False
                    # -- LabJack
                    elif msg == LJ_REC_FALSE:
                        self.labjack_running = False
                    elif msg == LJ_ERROR_EXIT:
                        self.master_dump_queue.put_nowait(msg)
                        self.labjack_running = False
                        self.use_labjack = False
                    elif msg.startswith(LJ_CONFIG):
                        self.set_device_params(msg, update_cmr=False, update_lj=True)
                        self.master_dump_queue.put_nowait(LJ_CONFIG)
                    # Exp Configuration
                    elif msg.startswith(TTL_TIME_HEADER) or msg.startswith(DIR_TO_USE_HEADER):
                        self.set_device_params(msg)
            if self.exp_running:
                devices_to_check = [self.cameras_running[cmr_ind]
                                    for cmr_ind in self.use_cameras
                                    if self.use_cameras[cmr_ind]]
                if self.use_labjack:
                    devices_to_check.append(self.labjack_running)
                if not any(devices_to_check):
                    self.exp_start_event.clear()
                    self.exp_running = False
                    self.master_dump_queue.put_nowait(EXP_END_HEADER)

    def pipe_message(self, device_name, pipe, msg):
        """Sends to pipe a message and listens for receipt notif"""
        # todo: replace send/recv methods with pipe_message
        # todo: implications of not blocking until message received though?
        pipe.send(msg)
        if not pipe.poll(3):
            print('[{}] is not responding'.format(device_name))
        else:
            pipe.recv()

    def set_device_params(self, msg, update_cmr=True, update_lj=True):
        """Sets the total run time in device processes"""
        for cmr_ind, cmr_pipe in enumerate(self.camera_pipes):
            if self.use_cameras[cmr_ind] and update_cmr:
                cmr_pipe.send(msg)
                cmr_pipe.recv()
        if self.use_labjack and update_lj:
            self.labjack_pipe.send(msg)
            self.labjack_pipe.recv()

    def run_experiment(self, msg):
        """Checks device availability; Sends run command to in-use devices"""
        self.save_file_name = msg.replace(RUN_EXP_HEADER, '', 1)
        self.save_file_name = '{}_[{}]'.format(format_daytime(option='time', use_as_save=True),
                                               self.save_file_name)
        # If no devices are enabled, there's no point in starting an exp so we exit
        devices_to_use = [self.use_cameras[cmr] for cmr in self.use_cameras if self.use_cameras[cmr]]
        if self.use_labjack:
            devices_to_use.append(self.use_labjack)
        if len(devices_to_use) == 0:
            return
        # Devices should have been created in Main GUI; we just need to check connections
        msg = '{}{}'.format(RUN_EXP_HEADER, self.save_file_name)
        if self.check_connections():
            for cmr_ind, cmr_pipe in enumerate(self.camera_pipes):
                if self.use_cameras[cmr_ind]:
                    cmr_pipe.send(msg)
                    cmr_pipe.recv()  # Just so we don't begin until everyone is ready
                    self.cameras_running[cmr_ind] = True
            if self.use_labjack:
                self.labjack_pipe.send(msg)
                self.labjack_pipe.recv()
                self.labjack_running = True
            # Release the start event seen by all processes to begin experiment
            self.exp_start_event.set()
            print(self.name, datetime.now())
            self.exp_running = True
            self.master_dump_queue.put_nowait(EXP_STARTED_HEADER)
        else:
            self.master_dump_queue.put_nowait('{}*** Failed to initialize the '
                                              'selected devices.'.format(FAILED_INIT_HEADER))

    def check_connections(self):
        """Check if indicated devices are connected and responsive"""
        nonresponsive_devices = []
        for cmr_ind, cmr_pipe in enumerate(self.camera_pipes):
            if self.use_cameras[cmr_ind]:
                cmr_pipe.send(DEVICE_CHECK_CONN)
                if cmr_pipe.poll(3):
                    if not cmr_pipe.recv():
                        nonresponsive_devices.append(True)
                else:
                    nonresponsive_devices.append(True)
        if self.use_labjack:
            self.labjack_pipe.send(DEVICE_CHECK_CONN)
            if self.labjack_pipe.poll(3):
                if not self.labjack_pipe.recv():
                    nonresponsive_devices.append(True)
            else:
                nonresponsive_devices.append(True)
        return not any(nonresponsive_devices)

    def hardstop(self):
        """Forces a premature exit from experiment"""
        for cmr_ind, cmr_pipe in enumerate(self.camera_pipes):
            if self.use_cameras[cmr_ind]:
                cmr_pipe.send(HARDSTOP_HEADER)
                cmr_pipe.recv()
                self.cameras_running[cmr_ind] = False
        if self.use_labjack:
            self.labjack_pipe.send(HARDSTOP_HEADER)
            self.labjack_pipe.recv()
            self.labjack_running = False
        self.exp_start_event.clear()
        self.exp_running = False
        self.master_dump_queue.put_nowait(EXP_END_HEADER)

    def close_devices(self):
        """Safely closes device connections and processes"""
        for cmr_ind, cmr_pipe in enumerate(self.camera_pipes):
            if self.use_cameras[cmr_ind]:
                cmr_pipe.send(EXIT_HEADER)
                cmr_pipe.recv()
        if self.use_labjack:
            self.labjack_pipe.send(EXIT_HEADER)
            self.labjack_pipe.recv()
        self.master_dump_queue.put_nowait(EXIT_HEADER)
