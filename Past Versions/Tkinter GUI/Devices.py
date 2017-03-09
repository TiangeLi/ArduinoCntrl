# coding=utf-8
"""
Device Classes. Communicates with hardware and perform actual hardware tasks
Non-GUI classes
"""


import u6
import sys
import time
import math
import glob
import Queue
import serial
import calendar
import numpy as np
import multiprocessing
from struct import pack
import flycapture2a as fc2
from LabJackPython import LowlevelErrorException, LabJackException

from MiscFunctions import *


class LabJackU6(u6.U6):
    """
    Connects to and records from labjack. 2 separate methods for streaming and writing
    to be used in concurrent threads within one process
    """

    def __init__(self, ard_ready_lock, cmr_ready_lock,
                 lj_read_ready_lock, lj_exp_ready_lock,
                 master_dump_queue, master_graph_queue):
        u6.U6.__init__(self)
        self.running = False
        self.hard_stopped = False
        self.connected = False
        self.time_start_read = datetime.now()
        ##########################################################
        # note on concurrency controls:
        # since the LJ is created AFTER creating the separate process,
        # it won't have access to main process globals;
        # the locks and queues must be passed from the process handler,
        # which would have had access at time of process forking
        ##########################################################
        # Concurrency Controls
        # Locks to wait on:
        self.ard_ready_lock = ard_ready_lock
        self.cmr_ready_lock = cmr_ready_lock
        # Locks to control:
        self.lj_read_ready_lock = lj_read_ready_lock
        self.lj_exp_ready_lock = lj_exp_ready_lock
        # Queues for own use
        self.data_queue = Queue.Queue()  # data from stream to write
        self.stream_pipe, self.writer_pipe = multiprocessing.Pipe()
        # dumps small reports (post-exp and missed values) to master gui
        self.master_gui_dump_queue = master_dump_queue
        self.master_gui_graph_queue = master_graph_queue
        ##########################################################
        # Hardware Parameters
        self.settings = None
        self.ch_num = [0]
        self.scan_freq = 1
        self.n_ch = 1
        self.streamSamplesPerPacket = 25
        self.packetsPerRequest = 48
        self.streamChannelNumbers = self.ch_num
        self.streamChannelOptions = [0] * self.n_ch

    def check_connection(self):
        """Checks if LabJack is ready to be connected to"""
        self.master_gui_dump_queue.put_nowait('<lj>Connecting to LabJack...')
        try:
            self.close()
            self.open()
            self.master_gui_dump_queue.put('<lj>Connected to LabJack!')
            self.connected = True
            return
        except LabJackException:
            try:
                self.streamStop()
                self.close()
                self.open()
                self.master_gui_dump_queue.put('<lj>Connected to LabJack!')
                self.connected = True
                return
            except (LabJackException, LowlevelErrorException):
                try:
                    self.master_gui_dump_queue.put('<lj>Failed. Attempting a Hard Reset...')
                    self.hardReset()
                    time.sleep(2.5)
                    self.open()
                    self.master_gui_dump_queue.put('<lj>Connected to LabJack!')
                    self.connected = True
                    return
                except LabJackException:
                    self.master_gui_dump_queue.put('<lj>** LabJack cannot be reached! '
                                                   'Please reconnect the device.')
                    self.connected = False
                    return

    def reinitialize_vars(self):
        """Reloads channel and freq information from settings
        in case they were changed. call this before any lj streaming"""
        self.ch_num = self.settings.lj_last_used['ch_num']
        self.scan_freq = self.settings.lj_last_used['scan_freq']
        self.n_ch = len(self.ch_num)

    @staticmethod
    def find_packets_per_req(scanFreq, nCh):
        """Returns optimal packets per request to use"""
        if nCh == 7:
            high = 42
        else:
            high = 48
        hold = []
        for i in range(scanFreq + 1):
            if i % 25 == 0 and i % nCh == 0:
                hold.append(i)
        hold = np.asarray(hold)
        hold = min(high, max(hold / 25))
        hold = max(1, hold)
        return hold

    @staticmethod
    def find_samples_per_pack(scanFreq, nCh):
        """Returns optimal samples per packet to use"""
        hold = []
        for i in range(scanFreq + 1):
            if i % nCh == 0:
                hold.append(i)
        return max(hold)

    # noinspection PyDefaultArgument
    def streamConfig(self, NumChannels=1, ResolutionIndex=0,
                     SamplesPerPacket=25, SettlingFactor=0,
                     InternalStreamClockFrequency=0, DivideClockBy256=False,
                     ScanInterval=1, ChannelNumbers=[0],
                     ChannelOptions=[0], ScanFrequency=None,
                     SampleFrequency=None):
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
                    SamplesPerPacket = self.find_samples_per_pack(ScanFrequency, NumChannels)
                DivideClockBy256 = True
                ScanInterval = 15625 / ScanFrequency
            else:
                DivideClockBy256 = False
                ScanInterval = 4000000 / ScanFrequency
        ScanInterval = min(ScanInterval, 65535)
        ScanInterval = int(ScanInterval)
        ScanInterval = max(ScanInterval, 1)
        SamplesPerPacket = max(SamplesPerPacket, 1)
        SamplesPerPacket = int(SamplesPerPacket)
        SamplesPerPacket = min(SamplesPerPacket, 25)
        command = [0] * (14 + NumChannels * 2)
        # command[0] = Checksum8
        command[1] = 0xF8
        command[2] = NumChannels + 4
        command[3] = 0x11
        # command[4] = Checksum16 (LSB)
        # command[5] = Checksum16 (MSB)
        command[6] = NumChannels
        command[7] = ResolutionIndex
        command[8] = SamplesPerPacket
        # command[9] = Reserved
        command[10] = SettlingFactor
        command[11] = (InternalStreamClockFrequency & 1) << 3
        if DivideClockBy256:
            command[11] |= 1 << 1
        t = pack("<H", ScanInterval)
        command[12] = ord(t[0])
        command[13] = ord(t[1])
        for i in range(NumChannels):
            command[14 + (i * 2)] = ChannelNumbers[i]
            command[15 + (i * 2)] = ChannelOptions[i]
        self._writeRead(command, 8, [0xF8, 0x01, 0x11])
        self.streamSamplesPerPacket = SamplesPerPacket
        self.streamChannelNumbers = ChannelNumbers
        self.streamChannelOptions = ChannelOptions
        self.streamConfiged = True
        # Only happens for ScanFreq < 25, in which case
        # this number is generated as described above
        if SamplesPerPacket < 25:
            self.packetsPerRequest = 1
        elif SamplesPerPacket == 25:  # For all ScanFreq > 25.
            self.packetsPerRequest = self.find_packets_per_req(ScanFrequency, NumChannels)
            # Such that PacketsPerRequest*SamplesPerPacket % NumChannels == 0,
            # where min P/R is 1 and max 48 for nCh 1-6,8
            # and max 42 for nCh 7.

    def read_with_counter(self, num_requests, datacount_hold):
        """Given a number of requests, pulls data from labjack
         and returns number of data points pulled"""
        reading = True
        datacount = 0
        while reading:
            if not self.running:
                break
            return_dict = self.streamData(convert=False).next()
            self.data_queue.put_nowait(deepcopy(return_dict))
            datacount += 1
            if datacount >= num_requests:
                reading = False
        datacount_hold.append(datacount)

    # noinspection PyUnboundLocalVariable
    def read_stream_data(self, settings):
        """Reads from stream and puts in queue"""
        # pulls lj config and sets up the stream
        self.settings = settings
        self.reinitialize_vars()
        self.getCalibrationData()
        self.streamConfig(NumChannels=self.n_ch, ChannelNumbers=self.ch_num,
                          ChannelOptions=[0] * self.n_ch, ScanFrequency=self.scan_freq)
        datacount_hold = []
        ttl_time = self.settings.ard_last_used['packet'][3]
        max_requests = int(math.ceil(
            (float(self.scan_freq * self.n_ch * ttl_time / 1000) / float(
                self.packetsPerRequest * self.streamSamplesPerPacket))))
        small_request = int(round(
            (float(self.scan_freq * self.n_ch * 0.5) / float(
                self.packetsPerRequest * self.streamSamplesPerPacket))))
        # We will read 3 segments: 0.5s before begin exp, during exp, and 0.5s after exp
        # 1. wait until arduino and camera are ready
        self.ard_ready_lock.wait()
        self.cmr_ready_lock.wait()
        # 2. notify master gui that we've begun
        self.master_gui_dump_queue.put_nowait('<lj>Started Streaming.')
        ####################################################################
        # STARTED STREAMING
        self.time_start_read = datetime.now()
        # begin the stream; this should happen as close to actual streaming as possible
        # to avoid dropping data
        try:
            self.streamStart()
        except LowlevelErrorException:
            self.streamStop()  # happens if a previous instance was not closed properly
            self.streamStart()
        self.lj_read_ready_lock.set()
        self.running = True
        while self.running:
            # at anytime, this can be disrupted by a hardstop from the main thread
            # 1. 0.5s before exp start; extra collected to avoid missing anything
            self.read_with_counter(small_request, datacount_hold)
            # 2. read for duration of time specified in self.settings.ard_last_used['packet'][3]
            self.master_gui_dump_queue.put_nowait('<ljst>')
            self.lj_exp_ready_lock.set()  # we also unblock arduino and camera threads
            time_start = datetime.now()
            self.read_with_counter(max_requests, datacount_hold)
            time_stop = datetime.now()
            # 3. read for another 0.5s after
            self.read_with_counter(small_request, datacount_hold)
            time_stop_read = datetime.now()
            self.running = False
        self.streamStop()
        self.running = False  # redundant but just in case
        if not self.hard_stopped:
            self.master_gui_dump_queue.put_nowait('<lj>Finished Successfully.')
        elif self.hard_stopped:
            self.master_gui_dump_queue.put_nowait('<lj>Terminated Stream.')
            self.hard_stopped = False
        self.lj_read_ready_lock.clear()
        self.lj_exp_ready_lock.clear()
        ####################################################################
        # now we do some reporting
        missed_list_msg = self.stream_pipe.recv()
        # samples taken for each interval:
        multiplier = self.packetsPerRequest * self.streamSamplesPerPacket
        datacount_hold = (np.asarray(datacount_hold)) * multiplier
        total_samples = sum(i for i in datacount_hold)
        # total run times for each interval
        before_run_time = time_diff(start_time=self.time_start_read, end_time=time_start, choice='micros')
        run_time = time_diff(start_time=time_start, end_time=time_stop, choice='micros')
        after_run_time = time_diff(start_time=time_stop, end_time=time_stop_read, choice='micros')
        total_run_time = time_diff(start_time=self.time_start_read, end_time=time_stop_read, choice='micros')
        # Reconstruct when and where missed values occured
        missed_before, missed_during, missed_after = 0, 0, 0
        if len(missed_list_msg) != 0:
            for i in missed_list_msg:
                if i[1] <= float(int(before_run_time)) / 1000:
                    missed_before += i[0]
                elif float(int(before_run_time)) / 1000 < i[1] <= (float(int(
                        before_run_time)) + float(int(run_time))) / 1000:
                    missed_during += i[0]
                elif (float(int(before_run_time)) + float(int(run_time))) / 1000 < i[1] <= (float(int(
                        before_run_time)) + float(int(run_time)) + float(int(after_run_time))) / 1000:
                    missed_after += i[0]
        missed_total = missed_before + missed_during + missed_after
        # actual sampling frequencies
        try:
            overall_smpl_freq = int(round(float(total_samples) * 1000) / total_run_time)
        except ZeroDivisionError:
            overall_smpl_freq = 0
        overall_scan_freq = overall_smpl_freq / self.n_ch
        try:
            exp_smpl_freq = int(round(float(datacount_hold[1]) * 1000) / run_time)
        except ZeroDivisionError:
            exp_smpl_freq = 0
        exp_scan_freq = exp_smpl_freq / self.n_ch
        # we'll send some information to the file write now
        post_exp_info = '{},{},{},{},{},{},{},{},{},{},{},{},n/a,{},n/a,{},n/a,{},n/a,{}' \
                        ''.format(float(before_run_time) / 1000,
                                  float(run_time) / 1000, float(after_run_time) / 1000,
                                  float(total_run_time) / 1000,
                                  datacount_hold[0], datacount_hold[1], datacount_hold[2],
                                  total_samples, missed_before, missed_during, missed_after,
                                  missed_total, exp_smpl_freq, overall_smpl_freq, exp_scan_freq,
                                  overall_scan_freq)
        self.stream_pipe.send(post_exp_info)
        self.master_gui_dump_queue.put('<ljr>' + post_exp_info)

    def data_write_plot(self, results_dir, fp_used, save_name):
        """Reads from data queue and writes to file/plots"""
        missed_total, missed_list = 0, []
        save_file_name = '[{}]--{}'.format(save_name, format_daytime(options='daytime'))
        with open(results_dir + save_file_name + '.csv', 'w') as save_file:
            for i in range(self.n_ch):
                save_file.write('AIN{},'.format(self.ch_num[i]))
            save_file.write('\n')
            self.lj_read_ready_lock.wait()  # wait for the go ahead from read_stream_data
            data_to_master_counter = 1
            while self.running:
                if not self.running:
                    self.data_queue.queue.clear()
                    break
                result = self.data_queue.get()
                if result['errors'] != 0:
                    missed_total += result['missed']
                    self.master_gui_dump_queue.put_nowait('<ljm>{}'.format(missed_total))
                    missed_time = datetime.now()
                    timediff = time_diff(start_time=self.time_start_read,
                                         end_time=missed_time)
                    missed_list.append([deepcopy(result['missed']),
                                        deepcopy(float(timediff) / 1000)])
                r = self.processStreamData(result['result'])
                for each in range(len(r['AIN{}'.format(self.ch_num[0])])):
                    for i in range(self.n_ch):
                        save_file.write(str(r['AIN{}'.format(self.ch_num[i])][each]) + ',')
                    save_file.write('\n')
                if time_diff(self.time_start_read) / data_to_master_counter >= 50:
                    to_send = []
                    for i in range(self.n_ch):
                        to_send.append((r['AIN{}'.format(self.ch_num[i])][0]) * (-27) / 5 + (27 + 27 * i))
                    self.master_gui_graph_queue.put_nowait(to_send)
                    data_to_master_counter += 1
                    if not self.running:
                        break
            self.writer_pipe.send(missed_list)
        # block until we hear back from streamer
        msg = self.writer_pipe.recv().split(',')
        for i in msg:
            if i == 'n/a':
                msg.remove(i)
        (before_run_time, run_time, after_run_time, total_run_time,
         smpls_before, smpls_during, smpls_after, total_samples,
         missed_before, missed_during, missed_after, missed_total,
         exp_smpl_freq, overall_smpl_freq, exp_scan_freq, overall_scan_freq) = msg
        if fp_used:
            ch_num = self.settings.fp_last_used['ch_num']
            main_freq = self.settings.fp_last_used['main_freq']
            isos_freq = self.settings.fp_last_used['isos_freq']
            top_line = ' , BEFORE EXP, DURING EXP, AFTER EXP, TOTAL, ' \
                       'DATA CH, MAIN REF CH, ISOS REF CH, ' \
                       'MAIN REF FREQ, ISOS REF FREQ,\n'
            time_line = 'TIME (s),{},{},{},{},{},{},{},{},{},\n'.format(before_run_time, run_time,
                                                                        after_run_time, total_run_time,
                                                                        ch_num[0], ch_num[1], ch_num[2],
                                                                        main_freq, isos_freq)
        else:
            top_line = ', BEFORE EXP, DURING EXP, AFTER EXP, TOTAL,\n'
            time_line = 'TIME (s),{},{},{},{},\n'.format(before_run_time, run_time,
                                                         after_run_time, total_run_time)
        samples_line = 'SAMPLES TAKEN, {},{},{},{},\n'.format(smpls_before, smpls_during, smpls_after,
                                                              total_samples)
        smpls_missed_line = 'SAMPLES MISSED,{},{},{},{},\n'.format(missed_before, missed_during,
                                                                   missed_after, missed_total)
        smpl_freq_line = 'SAMPLING FREQ (Hz), ,{}, ,{},\n'.format(exp_smpl_freq, overall_smpl_freq)
        scan_freq_line = 'SCAN FREQ (hz), ,{}, ,{},\n'.format(exp_scan_freq, overall_scan_freq)
        # now put it at the top of the file
        to_write = top_line + time_line + samples_line + smpls_missed_line + smpl_freq_line + scan_freq_line
        with file(results_dir + save_file_name + '.csv') as original:
            data = original.read()
        with file(results_dir + save_file_name + '.csv', 'w') as new:
            new.write(to_write + data)


class FireFly(object):
    """firefly camera"""

    def __init__(self, dirs, lj_exp_ready_lock, master_gui_queue, cmr_ready_lock, ard_ready_lock):
        # Hardware parameters
        self.context = None
        self.dirs = dirs
        # Threading controls
        self.lj_exp_ready_lock = lj_exp_ready_lock
        self.cmr_ready_lock = cmr_ready_lock
        self.ard_ready_lock = ard_ready_lock
        self.status_queue = master_gui_queue
        self.data_queue = Queue.Queue()
        ###############################################
        self.connected = False
        self.recording = False
        self.hard_stopped = False
        self.frame = None
        self.save_file_name = ''

    def initialize(self):
        """checks that camera is available"""
        try:
            self.context = fc2.Context()
            self.context.connect(*self.context.get_camera_from_index(0))
            self.context.set_video_mode_and_frame_rate(fc2.VIDEOMODE_640x480Y8,
                                                       fc2.FRAMERATE_30)
            self.context.set_property(**self.context.get_property(fc2.FRAME_RATE))
            self.context.start_capture()
            self.status_queue.put_nowait('<cmr>Connected to Camera!')
            self.connected = True
            return True
        except fc2.ApiError:
            self.status_queue.put_nowait('<cmr>** Camera is not connected or'
                                         ' is occupied by another program. '
                                         'Please disconnect and try again.')
            self.connected = False
            return False

    def camera_run(self):
        """Runs camera non-stop; switches image acquisition method
        from tempImageGet to appendAVI when need to record video"""
        while self.connected:
            if not self.recording:
                try:
                    self.data_queue.put_nowait(self.context.tempImgGet())
                except fc2.ApiError:
                    if self.dirs.settings.debug_console:
                        print 'Camera Closed. Code = IsoT'
                        return
            if self.recording:
                self.record_video()
            time.sleep(0.031)
            if not self.connected:
                # this means we stopped the experiment and are closing the GUI
                self.close()

    def record_video(self):
        """records video"""
        self.context.openAVI(self.dirs.results_dir + '[{}]--{}.avi'.format(self.save_file_name,
                                                                           format_daytime(options='daytime')),
                             30, 1000000)
        num_frames = int(self.dirs.settings.ard_last_used['packet'][3] * 30) / 1000
        self.ard_ready_lock.wait()
        self.cmr_ready_lock.set()
        self.data_queue.put_nowait(self.context.tempImgGet())
        self.lj_exp_ready_lock.wait()
        # started recording
        self.status_queue.put_nowait('<cmr>Started Recording.')
        self.status_queue.put_nowait('<cmrst>')
        self.context.set_strobe_mode(3, True, 1, 0, 10)
        for i in range(num_frames):
            if self.recording:
                self.data_queue.put_nowait(self.context.appendAVI())
            elif not self.recording:
                break
        self.recording = False
        self.context.set_strobe_mode(3, False, 1, 0, 10)
        self.context.closeAVI()
        self.cmr_ready_lock.clear()
        if not self.hard_stopped:
            self.status_queue.put_nowait('<cmr>Finished Successfully.')
        elif self.hard_stopped:
            self.status_queue.put_nowait('<cmr>Terminated Video Recording.')
            self.hard_stopped = False

    def close(self):
        """closes camera instance"""
        self.context.stop_capture()
        self.context.disconnect()


class ArduinoUno(object):
    """Handles serial communication with arduino"""

    def __init__(self, dirs, lj_exp_ready_lock, master_gui_queue, ard_ready_lock, cmr_ready_lock):
        # Thread controls
        self.dirs = dirs
        self.lj_exp_ready_lock = lj_exp_ready_lock
        self.ard_ready_lock = ard_ready_lock
        self.cmr_ready_lock = cmr_ready_lock
        self.status_queue = master_gui_queue
        self.connected = False
        self.running = False
        self.hard_stopped = False
        # Hardware parameters
        self.baudrate = 115200
        self.ser_port = self.dirs.settings.ser_port
        # Communication protocols
        # Markers are unicode chrs '<' and '>'
        self.start_marker, self.end_marker = 60, 62
        self.serial = None

    def send_to_ard(self, send_str):
        """Sends packed str to arduino"""
        self.serial.write(send_str)

    def get_from_ard(self):
        """Reads serial data from arduino"""
        ard_string = ''
        byte_hold = 'z'
        # We read and discard serial data until we hit '<'
        while ord(byte_hold) != self.start_marker:
            byte_hold = self.serial.read()
            time.sleep(0.00001)
        # Then we read and record serial data until we hit '>'
        while ord(byte_hold) != self.end_marker:
            if ord(byte_hold) != self.start_marker:
                ard_string += byte_hold
            byte_hold = self.serial.read()
        return ard_string

    def send_packets(self, *args):
        """Send experiment config to arduino"""
        for each in args:
            for i in range(len(each)):
                if len(each) > 0:
                    try:
                        get_str = self.get_from_ard()
                        if get_str == 'M':
                            self.send_to_ard(pack(*each[i]))
                    except TypeError:
                        raise serial.SerialException

    @staticmethod
    def list_serial_ports():
        """Finds and returns all available and usable serial ports"""
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')
        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def wait_for_ready(self):
        """Wait for ready message from arduino"""
        msg = ''
        start = datetime.now()
        while msg.find('ready') == -1:
            while self.serial.inWaiting() == 0:
                time.sleep(0.02)
                timediff = time_diff(start)
                if timediff > 3500:
                    return False
            msg = self.get_from_ard()
        if msg == 'ready':
            return True

    def try_serial(self, port):
        """Given a port, attempts to connect to it"""
        try:
            # can we use this port at all?
            self.serial = serial.Serial(port, self.baudrate)
            try:
                # are we able to get the ready message from arduino?
                success = self.wait_for_ready()
                if success:
                    self.dirs.threadsafe_edit(recipient='ser_port', donor=port)
                    return True
                else:
                    return False
            except IOError:
                return False
        except (serial.SerialException, IOError, OSError):
            try:
                self.serial.close()
                self.serial = serial.Serial(port, self.baudrate)
                try:
                    # are we able to get the ready message from arduino?
                    success = self.wait_for_ready()
                    if success:
                        self.dirs.threadsafe_edit(recipient='ser_port', donor=port)
                        return True
                    else:
                        return False
                except IOError:
                    return False
            except (serial.SerialException, IOError, OSError, AttributeError):
                return False

    def check_connection(self):
        """Tries every possible serial port"""
        # First we close any outstanding ports
        try:
            self.serial.close()
        except AttributeError:
            pass
        # then we attempt a new connection
        ports = self.list_serial_ports()
        self.status_queue.put('<ard>Connecting to Port '
                              '[{}]...'.format(self.ser_port))
        self.connected = self.try_serial(self.ser_port)
        if self.connected:
            self.status_queue.put('<ard>Success! Connected to Port '
                                  '[{}].'.format(self.ser_port))
            self.connected = True
            return
        elif not self.connected:
            for port in ports:
                if self.try_serial(port):
                    self.ser_port = port
                    self.dirs.threadsafe_edit(recipient='ser_port', donor=port)
                    self.status_queue.put('<ard>Success! Connected to Port '
                                          '[{}].'.format(self.ser_port))
                    self.connected = True
                    return
                else:
                    self.status_queue.put('<ard>** Failed to connect. '
                                          'Attempting next available Port...')
            self.status_queue.put('<ard>** Arduino cannot be reached! '
                                  'Please make sure the device '
                                  'is plugged in.')
            self.connected = False
            return

    def run_experiment(self):
        """sends data packets and runs experiment"""
        self.status_queue.put_nowait('<ard>Success! Connected to '
                                     'Port [{}]. '
                                     'Sending data '
                                     'packets...'.format(self.ser_port))
        time_offset = 3600 * 4  # EST = -4 hours
        system_time = ["<L", calendar.timegm(time.gmtime()) - time_offset]
        pwm_pack_send = []
        for i in self.dirs.settings.ard_last_used['pwm_pack']:
            period = (float(1000000) / float(i[4]))
            cycleTimeOn = long(round(period * (float(i[7]) / float(100))))
            cycleTimeOff = long(round(period * (float(1) - (float(i[7]) / float(100)))))
            timePhaseShift = long(round(period * (float(i[6]) / float(360))))
            pwm_pack_send.append(["<LLLLLBL", 0, i[2], i[3], cycleTimeOn, cycleTimeOff,
                                  i[5], timePhaseShift])
        self.send_packets([system_time],
                          [self.dirs.settings.ard_last_used['packet']],
                          self.dirs.settings.ard_last_used['tone_pack'],
                          self.dirs.settings.ard_last_used['out_pack'],
                          pwm_pack_send)
        self.status_queue.put_nowait('<ard>Success! Connected to '
                                     'Port [{}]. '
                                     'Data packets sent'.format(self.ser_port))
        # we're done the bulk of the processing, now we wait for thread stuff
        # this order is very specific! do not modify
        self.ard_ready_lock.set()
        self.cmr_ready_lock.wait()
        self.lj_exp_ready_lock.wait()
        self.send_to_ard(pack("<B", 1))
        start = datetime.now()
        self.status_queue.put_nowait('<ard>Started Procedure.')
        self.status_queue.put_nowait('<ardst>')
        total_time = self.dirs.settings.ard_last_used['packet'][3]
        self.running = True
        while self.running:
            if not self.running:
                break
            if time_diff(start) >= total_time:
                end_msg = self.get_from_ard()
                end_msg = end_msg.split(',')
                self.status_queue.put_nowait('<ard>Finished. Hardware report: '
                                             'procedure was exactly [{} ms], '
                                             'from [{}] to [{}]'
                                             ''.format(end_msg[0], end_msg[1], end_msg[2]))
                self.running = False
                break
            time.sleep(0.1)
        self.running = False
        if self.hard_stopped:
            self.status_queue.put_nowait('<ard>Terminated Procedure.')
            self.hard_stopped = False
        self.serial.close()
        self.serial.open()
        self.serial.close()
        self.ard_ready_lock.clear()
