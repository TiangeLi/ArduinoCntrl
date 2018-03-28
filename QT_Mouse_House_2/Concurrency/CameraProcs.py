# coding=utf-8

"""Each Process instance handles one external camera device"""

import sys
import time
import imageio
import numpy as np
import threading as thr
import flycapture2a as fc
import pyximea as xi
import scipy.misc
from Misc.Names import *
from Misc.CustomClasses import *
if sys.version[0] == '2':
    import Queue as Queue
else:
    import queue as Queue


class CameraDevice(object):
    """Container for specific camera hardware attributes"""
    def __init__(self, cmr_type, cmr_id):
        self.cmr_type = cmr_type
        self.cmr_id = cmr_id
        self.connected = False
        self.initialize()

    def check_connection(self):
        """Reports connetion status of camera"""
        try:
            self.get_img_method()
        except self.camera_error:
            return False
        else:
            return True

    def initialize(self):
        """Sets up camera based on type"""
        if self.cmr_type == FIREFLY_CAMERA:
            self.file_fmt = '.avi'
            self.camera_error = fc.ApiError
            self.init_ff_camera()
            self.get_img_method = self.fc_context.tempImgGet
            self.record_vid_method = self.fc_context.appendAVI
        elif self.cmr_type == MINIMIC_CAMERA:
            self.file_fmt = '.mkv'
            self.camera_error = xi.ximea.XI_Error, xi.XI_Error
            self.init_mm_camera()
            self.get_img_method = self.xi_camera.get_image
            self.record_vid_method = self.mini_mic_rec_to_file

    def init_ff_camera(self):
        """Initializes a PT Grey FireFly"""
        try:
            self.fc_context = fc.Context()
            self.fc_context.connect(*self.fc_context.get_camera_from_index(self.cmr_id))
            self.fc_context.set_video_mode_and_frame_rate(fc.VIDEOMODE_640x480Y8, fc.FRAMERATE_30)
            self.fc_context.set_property(**self.fc_context.get_property(fc.FRAME_RATE))
            self.fc_context.start_capture()
        except self.camera_error:
            self.connected = False
        else:
            self.connected = True

    def init_mm_camera(self):
        """Initializes a Ximea camera (mini microscope)"""
        try:
            self.xi_camera = xi.Xi_Camera(DevID=self.cmr_id)
            self.xi_camera.set_param('exposure', 33333.33)
            self.xi_camera.set_binning(4, skipping=False)
            self.xi_camera.set_debug_level('Error')
        except self.camera_error:
            self.connected = False
        else:
            self.connected = True

    def setup_recording_params(self, save_name):
        """Initializes recording parameters for camera"""
        if self.cmr_type == FIREFLY_CAMERA:
            save_name = save_name.encode()
            self.fc_context.openAVI(save_name, 30, 1000000)
            self.fc_context.set_strobe_mode(3, True, 1, 0, 10)
        elif self.cmr_type == MINIMIC_CAMERA:
            self.mini_mic_video_writer = imageio.get_writer(save_name, mode='I', fps=30, codex='ffv1', quality=10,
                                                            pixelformat='yuv420p', macro_block_size=None,
                                                            ffmpeg_log_level='error')

    def reset_recording_params(self):
        """Resets recording parameters"""
        if self.cmr_type == FIREFLY_CAMERA:
            self.fc_context.closeAVI()
            try:
                self.fc_context.set_strobe_mode(3, False, 1, 0, 10)
            except self.camera_error:
                pass
        elif self.cmr_type == MINIMIC_CAMERA:
            self.mini_mic_video_writer.close()

    def mini_mic_rec_to_file(self):
        """Video Recording Method for MiniMicroscope (Ximea Camera)"""
        data = self.xi_camera.get_image()
        self.mini_mic_video_writer.append_data(data)
        return data

    def close_camera(self):
        """Closes Device and Exits"""
        try:
            if self.cmr_type == FIREFLY_CAMERA:
                self.fc_context.stop_capture()
                self.fc_context.disconnect()
            elif self.cmr_type == MINIMIC_CAMERA:
                self.xi_camera.close()
        except self.camera_error:
            pass


class CameraHandler(StoppableProcess):
    """Single Camera Process, handles incoming messages from GUI/Proc Handler, and sends to external hardware"""
    def __init__(self, dirs, stream_index, mp_array, img_size, sync_event, cmr_pipe_end, cmr_type, cmr_id):
        super(CameraHandler, self).__init__()
        # Supplied Params
        self.dirs = dirs
        self.stream_index = stream_index
        self.mp_array = mp_array
        self.img_size = img_size
        self.cmr_type = cmr_type
        self.cmr_id = cmr_id
        # Synchronization
        self.img_to_gui_sync_event = sync_event  # Sync with GUI for image sending
        self.exp_start_event = EXP_START_EVENT  # Sync with proc_handler for experiment start
        self.cmr_pipe = cmr_pipe_end  # Comms with proc_handler for messages PH explicitly waiting for
        self.proc_handler_queue = PROC_HANDLER_QUEUE  # Comms with proc_handler for general messages
        # We create a frame_buffer to keep new frames for sending to GUI on separate thread
        # This way cameras can continuously acquire images without delay
        self.frame_buffer = None
        # Operation Parameters
        self.save_dir = self.dirs.settings.last_save_dir
        self.ttl_time = self.dirs.settings.ttl_time
        self.curr_frame = 0
        self.ttl_num_frames = 0
        self.hardstopped_rec = False
        self.recording_vid = False

    def setup_message_parser(self):
        """Generates a dictionary of {Message:Actions} for message parsing"""
        self.message_parser = {
            CMD_CHECK_CONN: lambda value: self.cmr_pipe.send(self.camera.check_connection()),
            CMD_START: lambda value: self.start_record(save_file_name=value),
            CMD_STOP: lambda value: self.hardstop_record(),
            CMD_SET_DIRS: lambda value: self.set_rec_params(save_dir=value),
            CMD_SET_TIME: lambda value: self.set_rec_params(ttl_time=value),
            CMD_EXIT: lambda value: self.stop()
        }

    def msg_polling(self):
        """Run on separate thread. Listen to cmr_pipe for messages from Proc_Handler"""
        while self.camera.connected:
            msg = None  # Reset message so we don't perform the same instructions multiple times
            time.sleep(1.0 / 1000.0)
            # we poll the pipe so as to not block this thread indefinitely if no messages
            # especially if self.camera.connected = False and we have exited other parts of the program
            if self.cmr_pipe.poll(1.0):
                msg = ReadMessage(self.cmr_pipe.recv())
            # Follow Message Instructions
            if msg:
                self.process_queued_message(msg)

    def submit_frames(self):
        """Run on separate thread. Sends new frames to shared mp_array of GUI from internal buffer"""
        self.frame_buffer = Queue.Queue()
        temp_array = np.empty(self.img_size, dtype=np.uint32)
        while self.camera.connected:
            try:
                data = self.frame_buffer.get_nowait()
            except Queue.Empty:
                time.sleep(1.0 / 1000.0)
            else:
                self.update_shared_array(data, temp_array)
                self.img_to_gui_sync_event.set()

    def update_shared_array(self, data, array):
        """Updates the shared mp array between camera and GUI with a new image"""
        data = scipy.misc.imresize(data, self.img_size)
        array[:, :] = data
        array[:, :] = (array << 8) + data  # Blue + Green Channel
        array[:, :] = (array << 8) + data  # Blue/Green + Red Channel
        self.np_array[:, :] = array

    def run(self):
        """Starts the Camera Process"""
        self.setup_message_parser()
        # Create camera device
        self.camera = CameraDevice(cmr_type=self.cmr_type, cmr_id=self.cmr_id)
        self.np_array = np.frombuffer(self.mp_array.get_obj(), dtype='I').reshape(self.img_size)
        # Threading
        SEND_FRAMES, POLLING = 'send_frames', 'polling'
        thr_send_frames = thr.Thread(target=self.submit_frames, name=SEND_FRAMES, daemon=True)
        thr_msg_polling = thr.Thread(target=self.msg_polling, name=POLLING, daemon=True)
        thr_send_frames.start()
        thr_msg_polling.start()
        # Main Camera Loop
        k = qc.QTime()
        k.start()
        while self.camera.connected:
            # We must acquire images regardless of GUI responsiveness; loss of frames if locked to GUI
            k.restart()
            self.get_frames()
            #print(k.elapsed())
            # If exiting, we must first close devices and threads, then inform proc_handler
            if self.stopped():
                self.camera.connected = False
                self.camera.close_camera()
                while True:
                    time.sleep(5.0 / 1000.0)
                    threads = (thread.name for thread in thr.enumerate())
                    if SEND_FRAMES not in threads and POLLING not in threads:
                        break  # we only exit process if threads have been killed
                self.cmr_pipe.send(MSG_RECEIVED)

    def process_queued_message(self, msg):
        """Follows instructions in message"""
        self.message_parser[msg.command](msg.value)

    def get_frames(self):
        """Acquires 1 Image per Call"""
        # -- Gets 1 frame. No recording to video file -- #
        # since we are not recording, it is ok to lock img acquisition to GUI sync
        # Even if GUI is unresponsive, it is not an issue since we aren't recording to file
        #print(self.img_to_gui_sync_event.is_set())

        if not self.recording_vid and not self.img_to_gui_sync_event.is_set():
            try:
                data = self.camera.get_img_method()
            except self.camera.camera_error:
                self.report_camera_error()
            else:
                self.frame_buffer.put_nowait(data)
                time.sleep(5.0/1000.0)
        # -- Gets 1 frame. Also records frame to video file -- #
        # since we are now recording, we cannot lock image acquisition to GUI
        # If GUI locks up, we will miss frames
        # We acquire frames and append to file regardless of GUI sync
        # But we will still send new frames to GUI if requested
        elif self.recording_vid:
            if self.curr_frame <= self.ttl_num_frames:
                try:
                    data = self.camera.record_vid_method()
                except self.camera.camera_error:
                    self.report_camera_error()
                else:
                    self.curr_frame += 1
                    if not self.img_to_gui_sync_event.is_set():
                        self.frame_buffer.put_nowait(data)
                        time.sleep(5.0 / 1000.0)
            elif self.curr_frame > self.ttl_num_frames:
                self.finish_record()

    def start_record(self, save_file_name):
        """Initializes recording parameters for camera and waits for start event to begin recording"""
        save_name = '{}\\{}_[{}#{}]{}'.format(self.save_dir, save_file_name,
                                              self.cmr_type, self.cmr_id, self.camera.file_fmt)
        self.camera.setup_recording_params(save_name=save_name)
        # Ready to Record Video
        self.ttl_num_frames = int(self.ttl_time * 30) // 1000
        self.cmr_pipe.send(MSG_RECEIVED)  # no need to package this message. PH only needs to pass the recv() block
        self.exp_start_event.wait()
        self.recording_vid = True  # We are ready to record. Main thread loop will enter recording status

    def report_camera_error(self):
        """If the camera produces an error, we notify proc handler such that it no longer attempts to reach camera"""
        # Inform Proc Handler that Camera at Stream Index had an Error
        msg = NewMessage(dev=CAMERAS, cmd=MSG_ERROR, val=self.stream_index)
        self.proc_handler_queue.put_nowait(msg)
        # Make sure any ongoing recordings have been closed
        if self.recording_vid:
            self.finish_record()
        # Stop this camera process
        self.stop()

    def finish_record(self):
        """Finishes recording current video, and resets recording parameters"""
        self.recording_vid = False
        self.curr_frame = 0
        self.camera.reset_recording_params()
        # Notify Proc_handler hat we are done recording
        if self.hardstopped_rec:
            self.cmr_pipe.send(MSG_RECEIVED)
            self.hardstopped_rec = False
        else:
            msg = NewMessage(dev=CAMERAS, cmd=MSG_FINISHED, val=self.stream_index)
            self.proc_handler_queue.put_nowait(msg)

    def hardstop_record(self):
        """Forces recording loop to exit"""
        self.curr_frame = self.ttl_num_frames + 1
        self.hardstopped_rec = True
        # This forces the get_frames() loop to exit recording, and also report hardstop to proc_handler

    def set_rec_params(self, save_dir=None, ttl_time=None):
        """Sets recording parameters"""
        if ttl_time:
            self.ttl_time = ttl_time
        if save_dir:
            self.save_dir = save_dir
        self.cmr_pipe.send(MSG_RECEIVED)
