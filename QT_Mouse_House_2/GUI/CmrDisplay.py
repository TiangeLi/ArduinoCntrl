# coding=utf-8

"""Displays Video Feeds from any number of connected cameras"""

import os
import sys
import math
import numpy as np
from Misc.Names import *
import multiprocessing as mp
from Concurrency.CameraProcs import CameraHandler
from Misc.Names import FIREFLY_CAMERA, MINIMIC_CAMERA
import pyximea as xi
import flycapture2a as fc
from GUI.MiscWidgets import qw
import PyQt4.QtGui as qg
import PyQt4.QtCore as qc


# Size of one camera stream display
CMR_IMG_SIZE = (240, 320)


class SingleCameraWidget(qw):
    """A single qPixMap that streams video feed from a single connected camera process"""
    def __init__(self, dirs, stream_index, cmr_type, cmr_id):
        super(SingleCameraWidget, self).__init__()
        self.dirs = dirs
        self.stream_index = stream_index
        self.type = cmr_type
        self.id = cmr_id
        # Image Data Holders
        self.array = None
        self.image = None
        self.label = None
        self.proc = None
        # Sync with camera process
        self.sync_event = mp.Event()
        self.sync_event.clear()
        self.cmr_pipe_main, self.cmr_pipe_end = mp.Pipe()
        # Initialize
        self.create_data_container()
        self.create_process()

    def create_data_container(self):
        """Generate shared data buffers and containers for image display"""
        # We generate a tuple of (mpArray, npArray) that reference the same underlying buffers
        # mpArray can be sent between processes; npArray is a readable format
        m_array = mp.Array('I', int(np.prod(CMR_IMG_SIZE)), lock=mp.Lock())
        self.array = (m_array, np.frombuffer(m_array.get_obj(), dtype='I').reshape(CMR_IMG_SIZE))
        # self.image containes image data; self.label displays it
        n_array = self.array[1]
        self.image = qg.QImage(n_array.data, n_array.shape[1], n_array.shape[0], qg.QImage.Format_RGB32)
        self.label = qg.QLabel(self)

    def create_process(self):
        """Generates a connected camera process"""
        self.proc = CameraHandler(self.dirs, self.stream_index, self.array[0], CMR_IMG_SIZE, self.sync_event,
                                  self.cmr_pipe_end, self.type, self.id)
        self.proc.name = 'cmr_stream_proc_#{} - [type {} id {}]'.format(self.stream_index, self.type,
                                                                        self.id)

    def update_display(self):
        """Updates the image pixel map label"""
        if self.sync_event.is_set():
            self.label.setPixmap(qg.QPixmap.fromImage(self.image))
            self.sync_event.clear()


class CameraDisplay(qw):
    """Creates a variable array of SingleCameraWidget to display any number of camera streams"""
    def __init__(self, dirs):
        super(CameraDisplay, self).__init__()
        self.dirs = dirs
        # Display Configs
        self.num_cmrs = 0
        # GUI Organization
        self.cameras = {}
        self.groupboxes = {}
        # Setup Displays
        self.setMinimumWidth(366)
        self.initialize()

    def initialize(self):
        """Clean up old cameras, setup new cameras"""
        self.cleanup()
        self.detect_cameras()
        self.setup_groupboxes()
        self.set_update_timer()
        self.start_cmr_procs()

    def cleanup(self):
        """Terminate any old processes"""
        if len(self.cameras) > 0:
            for _, camera in self.cameras.items():
                camera.proc.stop()
                camera.proc.join()
        for index in reversed(range(self.grid.count())):
            self.grid.itemAt(index).widget().setParent(None)
        self.cameras = {}
        self.groupboxes = {}

    def detect_cameras(self):
        """Detects number of cameras of each type"""
        num_attempts = 10  # We look for up to 10 TOTAL cameras (all types combined)
        cameras = []
        # -- Detect PTGrey Fireflies -- #
        temp_ff_context = fc.Context()
        for cmr_id in range(num_attempts):
            try:
                temp_ff_context.get_camera_from_index(cmr_id)
            except fc.ApiError:
                pass
            else:
                cameras.append((FIREFLY_CAMERA, cmr_id))
                num_attempts -= 1
        temp_ff_context.disconnect()
        # -- Detect Ximea Cameras -- #
        # Disable erroneous error messages
        devnull = open(os.devnull, 'w')
        stderr = sys.stderr
        sys.stderr = devnull
        # Check for ximea cameras
        for cmr_id in range(num_attempts):
            try:
                cam = xi.Xi_Camera(DevID=cmr_id)
                cam.get_image()
                cam.close()
            except (xi.XI_Error, xi.ximea.XI_Error):
                pass
            else:
                cameras.append((MINIMIC_CAMERA, cmr_id))
                num_attempts -= 1
        # Re-enable error messages
        sys.stderr = stderr
        devnull.close()
        # Finalize total num cameras
        self.num_cmrs = len(cameras)
        # Create Cameras
        for stream_index, (cmr_type, cmr_id) in enumerate(cameras):
            self.cameras[stream_index] = SingleCameraWidget(self.dirs, stream_index, cmr_type, cmr_id)

    def setup_groupboxes(self):
        """Creates individually labelled boxes for each camera"""
        max_per_col = 3
        num_cols = max(int(math.ceil(float(self.num_cmrs) / max_per_col)), 1)
        self.groupboxes = {}
        for stream_index in range(num_cols * max_per_col):
            self.groupboxes[stream_index] = qg.QGroupBox()
            col = num_cols - stream_index // max_per_col
            row = stream_index - (stream_index // max_per_col) * max_per_col
            try:
                camera = self.cameras[stream_index]
            except KeyError:
                self.groupboxes[stream_index].setTitle('No Camera Available')
            else:
                grid = qg.QGridLayout()
                grid.addWidget(camera.label)
                self.groupboxes[stream_index].setTitle('{} - {} #{}'.format(stream_index, camera.type, camera.id))
                self.groupboxes[stream_index].setLayout(grid)
            self.grid.addWidget(self.groupboxes[stream_index], row, col)

    def start_cmr_procs(self):
        """Starts camera processses"""
        [camera.proc.start() for _, camera in self.cameras.items()]

    def display_error_notif(self, stream_index):
        """Shows an error if the camera at stream_index is unresponsive"""
        self.cameras[stream_index].label.setText('Camera Closed due to API Error')
        self.cameras[stream_index].label.setAlignment(qAlignCenter)
        self.cameras[stream_index].label.setFrameStyle(qStyleSunken | qStylePanel)

    def set_update_timer(self):
        """Creates a timer that periodically updates camera streams"""
        update_timer = qc.QTimer(self)
        update_timer.timeout.connect(self.refresh_camera_frames)
        update_timer.start(5)

    def refresh_camera_frames(self):
        """Get a new frame from camera"""
        for _, camera in self.cameras.items():
            camera.update_display()
