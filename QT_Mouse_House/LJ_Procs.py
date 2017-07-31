# coding=utf-8

"""Separate Process for LabJack Operation"""

import ast
import sys
import math
import time
import u6 as u6
import numpy as np
from Names import *
import threading as tr
from struct import pack
import LabJackPython as lj
from itertools import zip_longest
from Misc_Classes import StoppableProcess, NamedObjectContainer
from datetime import datetime
if sys.version[0] == '2':
    import Queue as Queue
else:
    import queue as Queue


def find_packets_per_req(scan_freq, n_ch):
        """Returns optimal packets per request to use"""
        if n_ch == 7:
            high = 42
        else:
            high = 48
        hold = []
        for i in range(scan_freq + 1):
            if i % 25 == 0 and i % n_ch == 0:
                hold.append(i)
        hold = np.asarray(hold)
        hold = min(high, max(hold / 25))
        hold = max(1, int(hold))
        return hold


def find_samples_per_pack(scan_freq, n_ch):
        """Returns optimal samples per packet to use"""
        hold = []
        for i in range(scan_freq + 1):
            if i % n_ch == 0:
                hold.append(i)
        hold = max(hold)
        hold = max(hold, 1)
        hold = int(hold)
        hold = min(hold, 25)
        return hold


class LabJackU6(u6.U6):
    """LabJack Device"""
    def __init__(self):
        super(LabJackU6, self).__init__()

    def streamConfig(self, NumChannels=1, ResolutionIndex=0, SamplesPerPacket=25, SettlingFactor=0,
                     InternalStreamClockFrequency=0, DivideClockBy256=False, ScanInterval=1, ChannelNumbers=[0],
                     ChannelOptions=[0], ScanFrequency=None, SampleFrequency=None):
        """Sets up Streaming settings"""
        if NumChannels != len(ChannelNumbers) or NumChannels != len(ChannelOptions):
            raise LabJackException("NumChannels must match length "
                                   "of ChannelNumbers and ChannelOptions")
        if len(ChannelNumbers) != len(ChannelOptions):
            raise LabJackException("len(ChannelNumbers) doesn't "
                                   "match len(ChannelOptions)")
        if (ScanFrequency is not None) or (SampleFrequency is not None):
            if ScanFrequency is None:
                ScanFrequency = SampleFrequency
            if ScanFrequency < 1000:
                if ScanFrequency < 25:
                    # below 25 ScanFreq, S/P is some multiple of nCh less than SF.
                    SamplesPerPacket = find_samples_per_pack(ScanFrequency, NumChannels)
                DivideClockBy256 = True
                ScanInterval = 15625 / ScanFrequency
            else:
                DivideClockBy256 = False
                ScanInterval = 4000000 / ScanFrequency
        # Force ScanInterval and SamplersPerPacket into correct range
        ScanInterval = min(ScanInterval, 65535)
        ScanInterval = int(ScanInterval)
        ScanInterval = max(ScanInterval, 1)
        SamplesPerPacket = max(SamplesPerPacket, 1)
        SamplesPerPacket = int(SamplesPerPacket)
        SamplesPerPacket = min(SamplesPerPacket, 25)
        # Create config command to be streamed to LJ
        command = [0] * (14 + NumChannels * 2)
        command[1] = 0xF8
        command[2] = NumChannels + 4
        command[3] = 0x11
        command[6] = NumChannels
        command[7] = ResolutionIndex
        command[8] = SamplesPerPacket
        command[10] = SettlingFactor
        command[11] = (InternalStreamClockFrequency & 1) << 3
        if DivideClockBy256:
            command[11] |= 1 << 1
        t = pack("<H", ScanInterval)
        command[12] = t[0]
        command[13] = t[1]
        for i in range(NumChannels):
            command[14 + (i * 2)] = ChannelNumbers[i]
            command[15 + (i * 2)] = ChannelOptions[i]
        self._writeRead(command, 8, [0xF8, 0x01, 0x11])
        # Setup some variables for future use
        self.streamSamplesPerPacket = SamplesPerPacket
        self.streamChannelNumbers = ChannelNumbers
        self.streamChannelOptions = ChannelOptions
        self.streamConfiged = True
        # Only happens for ScanFreq < 25, in which case
        # this number is generated as described above
        if SamplesPerPacket < 25:
            self.packetsPerRequest = 1
        elif SamplesPerPacket == 25:  # For all ScanFreq > 25.
            self.packetsPerRequest = find_packets_per_req(ScanFrequency, NumChannels)
            # Such that PacketsPerRequest*SamplesPerPacket % NumChannels == 0,
            # where min P/R is 1 and max 48 for nCh 1-6,8
            # and max 42 for nCh 7.


class LabJackProcess(StoppableProcess):
    """Connects to and records from LabJack. Streams a low frequency output and writes high
    frequency data to a file. Communicates with proc_handler with a queue and main gui through a shared buffer"""
    def __init__(self, dirs, lj_pipe_lj, mp_array, sync_event, array_shape):
        super(LabJackProcess, self).__init__(callable_fn=None, args=None)
        # Provided Params
        self.dirs = dirs
        self.array_shape = array_shape
        self.mp_array = mp_array
        # Synchronization
        self.lj_pipe = lj_pipe_lj
        self.data_to_gui_sync_event = sync_event
        self.exp_start_event = EXP_START_EVENT
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        self.master_dumpp_queue = MASTER_DUMP_QUEUE
        # LabJack Operation Params
        self.lj = None
        self.lj_is_being_config = False
        self.ch_num = self.dirs.settings.lj_last_used.ch_num
        self.scan_freq = self.dirs.settings.lj_last_used.scan_freq
        self.lj_error = (lj.LabJackException, lj.LowlevelErrorException)
        # We create a data_buffer to keep new data for sending to GUI on a sep. thread;
        # This way we can continuously grab data from LabJack with minimal delay
        self.data_buffer = None
        # Process Operation Params
        self.save_dir = self.dirs.settings.last_used_save_dir
        self.ttl_time = self.dirs.settings.ttl_time()
        self.curr_request = 0
        self.ttl_num_requests = 0
        self.hard_stopped_rec = False
        self.recording = False
        self.connected = False
        self.save_file_name = ''

    # -- Device Operations -- #
    def initialize(self):
        """Setup the device and connects to it"""
        # todo: does this chain make sense?
        try:
            self.lj = LabJackU6()
            try:
                self.lj.close()
            except self.lj_error:
                try:
                    self.lj.streamStop()
                    self.lj.close()
                except self.lj_error:
                    try:
                        self.lj.hardReset()
                        time.sleep(3)
                        self.lj.close()
                    except self.lj_error:
                        self.connected = False
                        return
            self.lj.open()
            self.connected = True
            self.lj.streamConfig(NumChannels=len(self.ch_num), ChannelNumbers=self.ch_num,
                                 ChannelOptions=[0] * len(self.ch_num), ScanFrequency=self.scan_freq)
            try:
                self.lj.streamStart()
            except self.lj_error:
                self.lj.streamStop()
                self.lj.streamStart()
        except self.lj_error:
            self.report_lj_error()

    def check_connection(self):
        """Checks if LabJack is available and connected"""
        try:
            next(self.lj.streamData(convert=False))
            return True
        except self.lj_error:
            return False

    def close_device(self):
        """Closes LJ Process and Exits"""
        try:
            self.lj.streamStop()
            self.lj.close()
        except self.lj_error:
            # TODO implement error notifications
            print('LabJack did not close properly.')

    def report_lj_error(self):
        """If the LabJack produces the error, we notify proc_handler and exit"""
        print('LabJack Error; Closing Device...')
        # Notify Proc Handler
        self.proc_handler_queue.put_nowait(LJ_ERROR_EXIT)
        # Close any in progress recordings
        if self.recording:
            self.finish_record()
        # Stop the LJ Process
        self.stop()

    def setup_for_record(self):
        """Initializes recording parameters"""
        self.save_file_path = '{}\\{}.csv'.format(self.save_dir, self.save_file_name)
        # Get the number of packets we need
        smpls_per_req = self.lj.packetsPerRequest * self.lj.streamSamplesPerPacket
        ttl_smpls = self.scan_freq * len(self.ch_num) * self.ttl_time / 1000
        self.ttl_num_requests = int(math.ceil(ttl_smpls / smpls_per_req))  # Actual exp # packets
        half_sec_smpls = self.scan_freq * len(self.ch_num) * 0.5
        self.half_sec_requests = int(math.ceil(half_sec_smpls / smpls_per_req))  # we record for 0.5s before/after exp.
        # Generate the save file writer
        self.save_file_writer = open(self.save_file_path, 'w')
        for channel in self.ch_num:
            self.save_file_writer.write('AIN{},'.format(channel))
        self.save_file_writer.write('\n')
        # Ready to Record
        self.lj_pipe.send(LJ_READY)
        self.exp_start_event.wait()
        print(self.name, datetime.now())
        self.recording = True

    def finish_record(self):
        """Finishes recording and resets recording parameters"""
        self.recording = False
        self.curr_request = 0
        self.write_to_file_queue.put_nowait(LJ_REC_FALSE)
        if self.hard_stopped_rec:
            self.lj_pipe.send(LJ_REC_FALSE)
            self.hard_stopped_rec = False
        else:
            self.proc_handler_queue.put_nowait(LJ_REC_FALSE)

    # -- Concurrency Methods -- #
    def msg_polling(self):
        """Run on separate thread; polls lj_pipe for messages"""
        while self.connected:
            msg = ''  # Reset msg
            time.sleep(1.0/1000.0)
            # pipe.recv() blocks indefinitely and we don't want this, so we poll()
            if self.lj_pipe.poll(1.0):
                msg = self.lj_pipe.recv()
            # Message Actions
            if msg:
                if msg == DEVICE_CHECK_CONN:
                    self.lj_pipe.send(self.check_connection())
                elif msg.startswith(RUN_EXP_HEADER):
                    self.save_file_name = msg.replace(RUN_EXP_HEADER, '', 1)
                    self.setup_for_record()
                elif msg == HARDSTOP_HEADER:
                    self.curr_request = self.ttl_num_requests + 1
                    self.hard_stopped_rec = True
                elif msg.startswith(TTL_TIME_HEADER):
                    self.ttl_time = float(msg.replace(TTL_TIME_HEADER, '', 1))
                    self.lj_pipe.send(DIR_TO_USE_HEADER)
                elif msg.startswith(LJ_CONFIG):
                    self.lj_config(msg)
                    self.lj_pipe.send(LJ_CONFIG)
                elif msg.startswith(DIR_TO_USE_HEADER):
                    self.save_dir = msg.replace(DIR_TO_USE_HEADER, '', 1)
                    self.lj_pipe.send(DIR_TO_USE_HEADER)
                elif msg == EXIT_HEADER:
                    self.stop()

    def lj_config(self, msg):
        """From proc_handler message get settings to pass to labjack"""
        # Pause getting data
        self.lj_is_being_config = True
        # Parse Data
        msg = (msg.replace(LJ_CONFIG, '', 1)).split('|')
        self.ch_num = ast.literal_eval(msg[0])
        self.scan_freq = int(msg[1])
        # Reset LabJack
        try:
            self.lj.streamStop()
        except IndexError:
            self.report_lj_error()
            return
        self.lj = LabJackU6()
        self.lj.streamConfig(NumChannels=len(self.ch_num), ChannelNumbers=self.ch_num,
                             ChannelOptions=[0] * len(self.ch_num), ScanFrequency=self.scan_freq)
        self.lj.streamStart()
        # Unpause getting data
        self.num_channels = len(self.dirs.settings.lj_last_used.ch_num)
        self.lj_is_being_config = False

    def submit_to_gui_live_stream(self):
        """Run on separate thread; send data at a low frequency to GUI for live visualization"""
        self.data_buffer = mp.Queue()
        temp_array = np.empty(self.array_shape, dtype='f')
        temp_array[:] = None
        while self.connected:
            try:
                # Remember: LabJack data gets sent into the stream queue wrapped in a NamedObjectContainer
                # data.name indicates if it has already been CONVERTED to readable data or not.
                # data.obj is the raw or converted data.
                data = self.data_buffer.get_nowait()
                if data.name != CONVERTED:
                    data = self.lj.processStreamData(data.obj['result'])
                else:
                    data = data.obj
            except Queue.Empty:
                time.sleep(1.0/1000.0)
            else:
                self.update_shared_array(data, temp_array)
                self.data_to_gui_sync_event.set()

    def update_shared_array(self, data, temp_array):
        """Updates the shared mp_array between LJ and GUI with new data"""
        # data_set is the raw output from self.streamData(); we process it to give results
        # in a readable list format: {channel:[data]}
        temp_array[:] = None
        for i, ch in enumerate(self.ch_num):
            channel = 'AIN{}'.format(ch)
            if not len(data[channel]) == 0:
                temp_array[i][:len(data[channel])] = data[channel]
            else:
                temp_array[i] = 0
        self.np_array[:] = temp_array

    def run(self):
        """Starts the LabJack Process"""
        self.initialize()
        self.np_array = np.frombuffer(self.mp_array.get_obj(), dtype='f').reshape(self.array_shape)
        # Threading
        thread_names = 'data_sender', 'polling', 'writer'
        send_data = tr.Thread(target=self.submit_to_gui_live_stream, name=thread_names[0])
        polling = tr.Thread(target=self.msg_polling, name=thread_names[1])
        writer = tr.Thread(target=self.write_to_file, name=thread_names[2])
        send_data.start()
        polling.start()
        writer.start()
        # Main LabJack Loop
        while self.connected:
            # We run get_data() every loop regardless of GUI sync
            # to avoid missing data points due to GUI responsiveness.
            if not self.lj_is_being_config:
                self.get_data()
            # If we stop, we close device, threads, inform proc_handler
            # before we fully exit the process
            if self.stopped():
                self.connected = False
                self.close_device()
                while True:
                    time.sleep(5.0/1000.0)
                    threads = [thr.name for thr in tr.enumerate()]
                    if all([thread not in threads for thread in thread_names]):
                        break
                self.lj_pipe.send(EXIT_HEADER)

    # -- Reading Methods -- #
    def get_data(self):
        """Sends 1 request to LJ. numSamples = samplesPerPackt * packetsPerRequest"""
        # Get a single request without recording to file
        if not self.recording:  # and not self.data_to_gui_sync_event.is_set():
            try:
                data = next(self.lj.streamData(convert=False))
            except self.lj_error:
                self.report_lj_error()
            else:
                if not self.data_to_gui_sync_event.is_set():
                    self.data_buffer.put_nowait(NamedObjectContainer(obj=data, name=None))
        # Get a request with appending to file
        elif self.recording:
            if self.curr_request < self.ttl_num_requests:
                try:
                    data = next(self.lj.streamData(convert=False))
                except self.lj_error:
                    self.report_lj_error()
                else:
                    print('Missed: ', data['missed']) if data['missed'] != 0 else None
                    self.write_to_file_queue.put_nowait(data)
                    self.curr_request += 1
            else:
                self.finish_record()

    def write_to_file(self):
        """Run as seprate thread. Looks for data to write and writes a new line of data to file"""
        self.write_to_file_queue = Queue.Queue()
        while self.connected:
            try:
                msg = self.write_to_file_queue.get_nowait()
            except Queue.Empty:
                time.sleep(5.0 / 1000.0)
            else:
                if msg == LJ_REC_FALSE:
                    self.save_file_writer.close()
                else:
                    data = self.lj.processStreamData(msg['result'])
                    if not self.data_to_gui_sync_event.is_set():
                        self.data_buffer.put_nowait(NamedObjectContainer(obj=data, name=CONVERTED))
                    for row, _ in enumerate(data['AIN{}'.format(self.ch_num[0])]):
                        for channel in self.ch_num:
                            ch = 'AIN{}'.format(channel)
                            append = data[ch][row]
                            self.save_file_writer.write('{},'.format(append))
                        self.save_file_writer.write('\n')
