# coding=utf-8

from __future__ import print_function

"""All Point Grey Firefly Classes and Functions"""


import time
import scipy.misc
import numpy as np
import pyximea as xi
import flycapture2a as fc
from copy import deepcopy
from Misc_Classes import StoppableProcess


class Camera(StoppableProcess):
    """Fire Fly Camera"""
    def __init__(self, dirs, stream_ind, mp_array, image_size, sync_event, cmr_type, cmr_id):
        super(Camera, self).__init__(callable_fn=None, args=None)
        # Provided Parameters
        self.dirs = dirs
        self.stream_ind = stream_ind
        self.mp_array = mp_array
        self.image_size = image_size
        self.sync_event = sync_event
        self.cmr_type = cmr_type
        self.cmr_id = cmr_id
        # Operation Parameters
        self.connected = False
        self.recording = False
        self.hard_stopped = False
        self.save_file_name = ''

    def initialize(self):
        """Checks for camera availability and initializes"""
        if self.cmr_type == 'ff':
            self.init_firefly_camera()
        elif self.cmr_type == 'mm':
            self.init_mini_microscope()

    def init_firefly_camera(self):
        """Initializes a PT Grey Firefly Camera"""
        try:
            self.context = fc.Context()
            self.context.connect(*self.context.get_camera_from_index(self.cmr_id))
            self.context.set_video_mode_and_frame_rate(fc.VIDEOMODE_640x480Y8, fc.FRAMERATE_30)
            self.context.set_property(**self.context.get_property(fc.FRAME_RATE))
            self.context.start_capture()
            # self.status_queue.put_nowait('<cmr>Connected to Camera!')
            self.connected = True
        except fc.ApiError:
            # self.status_queue.put_nowait('<cmr>** Camera is disconnected or occupied by another program. '
            #                              'Please disconnect and try again.')
            self.connected = False

    def init_mini_microscope(self):
        """Initializes a mini microscope"""
        try:
            self.camera = xi.Xi_Camera(DevID=self.cmr_id)
            self.camera.set_param('exposure', 30000.0)
            self.camera.set_binning(4, skipping=False)
            self.connected = True
        except ValueError:
            self.connected = False

    def run(self):
        """Starts the Camera Process"""
        self.initialize()
        self.run_camera()

    def run_camera(self):
        """Starts camera acquisition"""
        while self.connected:
            time.sleep(5.0/1000.0)
            if not self.sync_event.is_set():
                np_array = np.frombuffer(self.mp_array.get_obj(), dtype='I').reshape(self.image_size)
                if self.cmr_type == 'ff':
                    data = self.context.tempImgGet()
                    data = scipy.misc.imresize(data, self.image_size)
                    np_array[:, :] = data
                elif self.cmr_type == 'mm':
                    data = self.camera.get_image()
                    data = scipy.misc.imresize(data, self.image_size)
                    np_array[:, :] = data
                self.sync_event.set()
