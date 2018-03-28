# coding=utf-8

"""Main Manager of Communication between GUI and Child Processes"""

import sys
import time
from Misc.Names import *
from Misc.CustomFunctions import format_daytime
from Misc.CustomClasses import *
if sys.version[0] == '2':
    import Queue as Queue
else:
    import queue as Queue


class Device(object):
    """Container for Device Parameters relevant to Process Handler"""
    def __init__(self, device_type, mp_pipe=None, index=None):
        self.device_type = device_type
        self.mp_pipe = mp_pipe
        self.index = index
        self.use_device = True
        self.running = False

    def send_message(self, msg):
        """Sends a message through our mp_pipe ending"""
        self.mp_pipe.send(msg)
        new_msg = self.mp_pipe.recv()


class ProcessHandler(StoppableProcess):
    """Handles Comms between GUI and Child Processes"""
    def __init__(self, cmr_pipe_mains):
        super(ProcessHandler, self).__init__()
        self.name = 'Proess Handler'
        # Concurrency
        self.master_dump_queue = MASTER_DUMP_QUEUE
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        self.exp_start_event = EXP_START_EVENT
        # Devices
        self.cameras = [Device(CAMERAS, pipe, index) for index, pipe in enumerate(cmr_pipe_mains)]
        # Handler Params
        self.hardstop_exp = False

    def setup_message_parser(self):
        """Creates Message Parsing Dictionaries"""
        self.message_parser = {
            CMD_START: lambda device, value: self.run_experiment(save_file_name=value),
            CMD_STOP: lambda device, value: self.hardstop_experiment(),
            CMD_EXIT: lambda device, value: self.close_devices(),
            CMD_SET_TIME: lambda device, value: self.set_device_params(param=CMD_SET_TIME, value=value),
            CMD_SET_DIRS: lambda device, value: self.set_device_params(param=CMD_SET_DIRS, value=value),
            MSG_FINISHED: lambda device, value: self.set_device_stopped(device_type=device, index=value, error=False),
            MSG_ERROR: lambda device, value: self.set_device_stopped(device_type=device, index=value, error=True)
        }

    def run(self):
        """Periodically Check and Process Instructions from Proc Handler Queue"""
        self.setup_message_parser()
        while not self.stopped():
            time.sleep(5.0 / 1000.0)
            try:
                msg = self.proc_handler_queue.get_nowait()
            except Queue.Empty:
                pass
            else:
                msg = ReadMessage(msg)
                self.process_queue_message(msg)
            self.check_exp_is_running()

    def process_queue_message(self, msg):
        """Processes Queued Message and follows instructions"""
        self.message_parser[msg.command](msg.device, msg.value)

    def check_exp_is_running(self):
        """Check for device status while experiment running, in order to know when to report experiment complete"""
        if self.exp_start_event.is_set():
            devices_to_check = [camera.running for camera in self.cameras if camera.use_device]
            if not any(devices_to_check):
                self.exp_start_event.clear()
                msg = NewMessage(cmd=MSG_FINISHED)
                self.master_dump_queue.put_nowait(msg)

    def set_device_stopped(self, device_type, index, error):
        """Sets device status to stopped; this is internal to proc_handler for managing active/inactive devices"""
        if device_type == CAMERAS:
            # Get Camera
            camera = [camera for camera in self.cameras if camera.index == index][0]
            # Stop Camera Running
            camera.running = False
            # Error shutdown Camera
            if error:
                msg = NewMessage(dev=CAMERAS, cmd=MSG_ERROR, val=index)
                self.master_dump_queue.put_nowait(msg)
                camera.use_device = False

    def set_device_params(self, param, value):
        """Change Device Parameters"""
        for camera in self.cameras:
            if camera.use_device:
                msg = NewMessage(cmd=param, val=value)
                camera.send_message(msg)

    def run_experiment(self, save_file_name):
        """Checks devices available, and sends run command to devices in-use"""
        save_file_name = '{}_[{}]'.format(format_daytime(option=TIME, use_as_save=True), save_file_name)
        # If we have not enabled any devices, there is no point in starting a run so we exit immediately
        devices_to_use = [camera.use_device for camera in self.cameras]
        if not any(devices_to_use):
            return
        # Check connections to devices
        msg = NewMessage(cmd=CMD_START, val=save_file_name)
        if self.devices_connected:
            for camera in self.cameras:
                if camera.use_device:
                    camera.send_message(msg)
                    camera.running = True
        # Now we can start the experiment by releasing the multiprocessing exp_start_event seen by all processes
            self.exp_start_event.set()
            msg = NewMessage(cmd=MSG_STARTED)
        else:
            msg = NewMessage(cmd=MSG_ERROR, val='Failed to Initialize Devices!')
        # We let Main GUI know if experiment was successfully started
        self.master_dump_queue.put_nowait(msg)

    @property
    def devices_connected(self):
        """Checks if the in-use devices are connected and responsive"""
        nonresponsive_devices = []
        msg = NewMessage(cmd=CMD_CHECK_CONN)
        for camera in self.cameras:
            if camera.use_device:
                camera.mp_pipe.send(msg)
                if camera.mp_pipe.poll(3):
                    if not camera.mp_pipe.recv():
                        nonresponsive_devices.append(True)
                else:
                    nonresponsive_devices.append(True)
        return not any(nonresponsive_devices)

    def hardstop_experiment(self):
        """Forces a premature exit from running experiment"""
        msg = NewMessage(cmd=CMD_STOP)
        for camera in self.cameras:
            if camera.use_device:
                camera.send_message(msg)
                camera.running = False
        self.exp_start_event.clear()
        msg = NewMessage(cmd=MSG_FINISHED)
        self.master_dump_queue.put_nowait(msg)

    def close_devices(self):
        """Safely close device connections and processes"""
        msg = NewMessage(cmd=CMD_EXIT)
        for camera in self.cameras:
            if camera.use_device:
                camera.send_message(msg)
        self.master_dump_queue.put_nowait(msg)
