# coding=utf-8

"""All Point Grey Firefly Classes and Functions"""

from __future__ import print_function
import sys
import time
import imageio
import scipy.misc
import numpy as np
from Names import *
import pyximea as xi
import flycapture2a as fc
from copy import deepcopy
from Misc_Functions import *
import threading as tr
from Misc_Classes import StoppableProcess
if sys.version[0] == '2':
    import Queue as Queue
else:
    import queue as Queue


class Camera(StoppableProcess):
    """Fire Fly Camera"""
    def __init__(self, dirs, stream_ind, mp_array, image_size, sync_event, cmr_pipe_end, cmr_type, cmr_id):
        super(Camera, self).__init__(callable_fn=None, args=None)
        # Provided Parameters
        self.dirs = dirs
        self.stream_ind = stream_ind
        self.mp_array = mp_array
        self.image_size = image_size
        self.cmr_type = cmr_type
        self.cmr_id = cmr_id
        # Synchronization
        self.img_to_gui_sync_event = sync_event  # Sync with GUI for image sending
        self.exp_start_event = EXP_START_EVENT  # Sync with proc_handler for exp start
        self.cmr_pipe = cmr_pipe_end  # Comms with proc handler for msgs PH is explicitly waiting for
        self.proc_handler_queue = PROC_HANDLER_QUEUE  # Comms with proc handler for general messages
        # Mini Microscope specific objects
        self.mini_mic_video_writer = None  # Writes frames from Mini Microscope to video file
        # Camera Operation objects (diff. depending on cmr type)
        self.get_img_method = None
        self.record_vid_method = None
        self.camera_error = None
        # We create a frame_buffer to keep new frames for sending to GUI on separate thread
        # This way cameras can continuously get frames without delay
        self.frame_buffer = None
        # Operation Parameters
        self.curr_frame = 0
        self.ttl_num_frames = 0
        self.ready_to_record = False
        self.recording = False
        self.connected = False
        self.save_file_name = ''

    def initialize(self):
        """Checks for camera availability and initializes"""
        if self.cmr_type == FireFly_Camera:
            self.init_firefly_camera()
            self.get_img_method = self.fc_context.tempImgGet
            self.record_vid_method = self.fc_context.appendAVI
            self.camera_error = fc.ApiError
        elif self.cmr_type == Mini_Microscope:
            self.init_mini_microscope()
            self.get_img_method = self.xi_camera.get_image
            self.record_vid_method = self.mini_mic_rec_to_file
            self.camera_error = xi.ximea.XI_Error

    def init_firefly_camera(self):
        """Initializes a PT Grey Firefly Camera"""
        try:
            self.fc_context = fc.Context()
            self.fc_context.connect(*self.fc_context.get_camera_from_index(self.cmr_id))
            self.fc_context.set_video_mode_and_frame_rate(fc.VIDEOMODE_640x480Y8, fc.FRAMERATE_30)
            self.fc_context.set_property(**self.fc_context.get_property(fc.FRAME_RATE))
            self.fc_context.start_capture()
            # self.status_queue.put_nowait('<cmr>Connected to Camera!')
            self.connected = True
        except self.camera_error:
            # self.status_queue.put_nowait('<cmr>** Camera is disconnected or occupied by another program. '
            #                              'Please disconnect and try again.')
            self.connected = False

    def init_mini_microscope(self):
        """Initializes a mini microscope"""
        try:
            self.xi_camera = xi.Xi_Camera(DevID=self.cmr_id)
            self.xi_camera.set_param('exposure', 33333.33)
            self.xi_camera.set_binning(4, skipping=False)
            self.xi_camera.set_debug_level('Error')
            self.connected = True
        except self.camera_error:
            self.connected = False

    def msg_polling(self):
        """Run on separate thread. Polls pipe for messages"""
        while self.connected:
            msg = ''  # Reset msg so we don't perform instructions multiple times
            time.sleep(1.0/1000.0)
            # We don't want the thread to block indefinitely if no messages come from the pipe.
            if self.cmr_pipe.poll(2):
                msg = self.cmr_pipe.recv()
            # Message actions
            if msg == DEVICE_CHECK_CONN:
                self.cmr_pipe.send(self.check_connection())
            elif msg.startswith(RUN_EXP_HEADER):
                self.save_file_name = msg.replace(RUN_EXP_HEADER, '', 1)
                self.recording = True
                self.cmr_pipe.send(CAMERA_READY)
            elif msg == HARDSTOP_HEADER:
                self.curr_frame = self.ttl_num_frames + 1

    def submit_frames(self):
        """Run on Separate thread. Sends new frames to shared mp_array of GUI from internal buffer"""
        self.frame_buffer = Queue.Queue()
        temp_array = np.empty(self.image_size, dtype=np.uint32)
        while self.connected:
            try:
                data = self.frame_buffer.get_nowait()
            except Queue.Empty:
                time.sleep(1.0/1000.0)
            else:
                self.update_shared_array(data, temp_array)

    def update_shared_array(self, data, temp_array):
        """Updates the shared array between camera and GUI with a new image"""
        data = scipy.misc.imresize(data, self.image_size)
        temp_array[:, :] = data
        temp_array[:, :] = (temp_array << 8) + data  # Blue Channel + Green Channel
        temp_array[:, :] = (temp_array << 8) + data  # Blue/Green Channels + Red Channel
        self.np_array[:, :] = temp_array

    def check_connection(self):
        """Checks whether device is connected and responsive"""
        try:
            self.get_img_method()
            return True
        except self.camera_error:
            return False

    def run(self):
        """Starts the Camera Process"""
        self.initialize()
        self.np_array = np.frombuffer(self.mp_array.get_obj(), dtype='I').reshape(self.image_size)
        send_frames = tr.Thread(target=self.submit_frames)
        polling = tr.Thread(target=self.msg_polling)
        send_frames.start()
        polling.start()
        while self.connected:
            if not self.img_to_gui_sync_event.is_set():
                self.get_frame()
                self.img_to_gui_sync_event.set()
            time.sleep(1.0/1000.0)
            if self.stopped():
                self.connected = False
                self.close()

    def get_frame(self):
        """Acquires 1 Image per call."""
        # Get a Single Frame
        if not self.recording:
            try:
                data = self.get_img_method()
                self.frame_buffer.put_nowait(data)
            except self.camera_error:
                self.report_cmr_error()
        # Gets a Single Frame and Appends to a Video File
        elif self.recording:
            if not self.ready_to_record:
                self.setup_for_record()
                # Since this is the first time through the recording loop, we wait to begin.
                self.exp_start_event.wait()
            if self.curr_frame <= self.ttl_num_frames:
                try:
                    data = self.record_vid_method()
                    self.frame_buffer.put_nowait(data)
                    self.curr_frame += 1
                except self.camera_error:
                    self.report_cmr_error()
            else:
                self.finish_record()

    def report_cmr_error(self):
        """If the camera produces an error, notify proc handler such that it no longer attempts communication"""
        print('Camera [{} #{}] Closed due to API Error'.format(self.cmr_type, self.cmr_id))
        # We display a prominent error msg in the image display field
        # We don't do this in the send_frames thread in case that thread exits before displaying this image
        error_img = imageio.imread(cmr_error_img)
        temp_array = np.empty(self.image_size, dtype=np.uint32)
        self.update_shared_array(error_img, temp_array)
        # We also need to let proc_handler know this camera is kaput
        self.proc_handler_queue.put_nowait('{}{}'.format(CMR_ERROR_EXIT, self.stream_ind))
        # Make sure any recordings in progress are properly closed first
        if self.recording:
            self.finish_record()
        # Stop the camera process
        self.stop()

    def setup_for_record(self):
        """Initializes recording parameters for cameras"""
        if self.cmr_type == FireFly_Camera:
            file_fmt = '.avi'
        elif self.cmr_type == Mini_Microscope:
            file_fmt = '.mkv'
        save_name = '{}[{}]--{}-[{}#{}]{}'.format(self.dirs.main_save_dir, self.save_file_name,
                                                  format_daytime(option='daytime', use_as_save=True),
                                                  self.cmr_type, self.cmr_id, file_fmt)
        self.ttl_num_frames = int(self.dirs.settings.ard_last_used['packet'][3] * 30) // 1000
        if self.cmr_type == FireFly_Camera:
            save_name = save_name.encode()
            self.fc_context.openAVI(save_name, 30, 1000000)
            self.fc_context.set_strobe_mode(3, True, 1, 0, 10)
        elif self.cmr_type == Mini_Microscope:
            self.mini_mic_video_writer = imageio.get_writer(save_name, mode='I', fps=30, codec='ffv1', quality=10,
                                                            pixelformat='yuv420p', macro_block_size=None,
                                                            ffmpeg_log_level='error')
        self.ready_to_record = True

    def finish_record(self):
        """Finishes recording and resets recording parameters"""
        self.recording = False
        self.ready_to_record = False
        self.curr_frame = 0
        if self.cmr_type == FireFly_Camera:
            self.fc_context.closeAVI()
            try:
                self.fc_context.set_strobe_mode(3, False, 1, 0, 10)
            except self.camera_error:
                pass
        elif self.cmr_type == Mini_Microscope:
            self.mini_mic_video_writer.close()
        self.proc_handler_queue.put_nowait('{}{}'.format(CMR_REC_FALSE, self.stream_ind))

    def mini_mic_rec_to_file(self):
        """Writes frames from Mini Microscope to a Video File"""
        data = self.xi_camera.get_image()
        self.mini_mic_video_writer.append_data(data)
        return data

    def close(self):
        """Closes camera instances and exits"""
        try:
            if self.cmr_type == FireFly_Camera:
                self.fc_context.stop_capture()
                self.fc_context.disconnect()
            elif self.cmr_type == Mini_Microscope:
                self.xi_camera.close()
        except self.camera_error:
            pass
