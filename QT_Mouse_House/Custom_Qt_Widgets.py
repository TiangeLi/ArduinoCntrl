# coding=utf-8

"""Qt Widget Blocks for implementation into a QMainWindow"""

import os
import sys
import math
from Names import *
from operator import itemgetter
from Misc_Classes import *
from Misc_Functions import *
from Custom_Qt_Tools import *
import Camera_Procs as cp
import flycapture2a as fc
import pyximea as xi
import PyQt4.QtGui as qg
import PyQt4.QtCore as qc


class GUI_ProgressBar(qg.QGraphicsView):
    """Progress Bar to Monitor Experiment and Arduino Status"""
    def __init__(self, dirs):
        qg.QGraphicsView.__init__(self)
        self.dirs = dirs
        self.exp_start_time = qc.QTime()
        self.scene = qg.QGraphicsScene(self)
        # Initialize Objects
        self.init_static_background()
        self.init_dynamic_background()
        self.init_anim_gfx_objects()
        self.set_dynamic_background()
        # Experiment Running Booleans
        self.bar_gfx_running = False
        self.time_gfx_running = False
        # Setup Graphics Scene
        self.setScene(self.scene)
        self.setRenderHint(qg.QPainter.Antialiasing)
        self.setMinimumSize(1056, 288)
        self.setMaximumSize(1056, 288)

    # -- Static Background -- #
    def init_static_background(self):
        """Sets up the static backdrop"""
        bg_group = GUI_SimpleGroup()
        # Main Background Shapes
        bg_group.add(qg.QGraphicsRectItem(0, 0, 1052, 284), brush=black)
        bg_group.add(qg.QGraphicsLineItem(0, 20, 1052, 20), pen=white)
        bg_group.add(qg.QGraphicsLineItem(0, 40, 1052, 40), pen=white)
        bg_group.add(qg.QGraphicsLineItem(0, 160, 1052, 160), pen=white)
        bg_group.add(qg.QGraphicsLineItem(0, 260, 1052, 260), pen=white)
        # Row Label - Backdrops
        bg_group.add(qg.QGraphicsRectItem(1000, 20, 15, 20), brush=white)
        bg_group.add(qg.QGraphicsRectItem(1000, 40, 15, 120), brush=white)
        bg_group.add(qg.QGraphicsRectItem(1000, 160, 15, 100), brush=white)
        # Row Label - Names
        bg_group.add(qg.QGraphicsTextItem(u'\u266b'), pos_x=997, pos_y=13)
        bg_group.add(qg.QGraphicsTextItem('S'), pos_x=999, pos_y=41)
        bg_group.add(qg.QGraphicsTextItem('I'), pos_x=1002, pos_y=61)
        bg_group.add(qg.QGraphicsTextItem('M'), pos_x=998, pos_y=81)
        bg_group.add(qg.QGraphicsTextItem('P'), pos_x=999, pos_y=101)
        bg_group.add(qg.QGraphicsTextItem('L'), pos_x=1000, pos_y=121)
        bg_group.add(qg.QGraphicsTextItem('E'), pos_x=999, pos_y=141)
        bg_group.add(qg.QGraphicsTextItem('P'), pos_x=999, pos_y=181)
        bg_group.add(qg.QGraphicsTextItem('W'), pos_x=997, pos_y=201)
        bg_group.add(qg.QGraphicsTextItem('M'), pos_x=998, pos_y=221)
        # Arduino Label - Pins
        bg_group.add(qg.QGraphicsTextItem('PIN #'), color=white, pos_x=1011, pos_y=1)
        bg_group.add(qg.QGraphicsTextItem('10'), color=white, pos_x=1021, pos_y=21)
        bg_group.add(qg.QGraphicsTextItem('02'), color=white, pos_x=1021, pos_y=41)
        bg_group.add(qg.QGraphicsTextItem('03'), color=white, pos_x=1021, pos_y=61)
        bg_group.add(qg.QGraphicsTextItem('04'), color=white, pos_x=1021, pos_y=81)
        bg_group.add(qg.QGraphicsTextItem('05'), color=white, pos_x=1021, pos_y=101)
        bg_group.add(qg.QGraphicsTextItem('06'), color=white, pos_x=1021, pos_y=121)
        bg_group.add(qg.QGraphicsTextItem('07'), color=white, pos_x=1021, pos_y=141)
        bg_group.add(qg.QGraphicsTextItem('08'), color=white, pos_x=1021, pos_y=161)
        bg_group.add(qg.QGraphicsTextItem('09'), color=white, pos_x=1021, pos_y=181)
        bg_group.add(qg.QGraphicsTextItem('11'), color=white, pos_x=1021, pos_y=201)
        bg_group.add(qg.QGraphicsTextItem('12'), color=white, pos_x=1021, pos_y=221)
        bg_group.add(qg.QGraphicsTextItem('13'), color=white, pos_x=1021, pos_y=241)
        # Add Background to Progress Bar Scene
        self.scene.addItem(bg_group)

    # -- Dynamic Background -- #
    def init_dynamic_background(self):
        """Sets up dynamic background objects when called"""
        # Each type of dynamic object is grouped together
        self.v_bars = GUI_SimpleGroup()
        self.bar_times = GUI_SimpleGroup()
        self.tone_bars = GUI_SimpleGroup()
        self.out_bars = GUI_SimpleGroup()
        self.pwm_bars = GUI_SimpleGroup()
        self.dynamic_bg_groups = [self.v_bars, self.bar_times,
                                  self.tone_bars, self.out_bars,
                                  self.pwm_bars]
        # Add objects/groups to scene
        for group in self.dynamic_bg_groups:
            self.scene.addItem(group)

    def set_dynamic_background(self):
        """
        Sets dynamic background using data from settings.ard_last_used
        Any changes to ard settings should be done to settings.ard_last_used before calling this!
        """
        data_source = self.dirs.settings.ard_last_used
        self.reset_dynamic_background()
        self.set_vert_spacers(ms_time=data_source['packet'][3])
        self.set_ard_bars(data_source=data_source)
        # We also update animation timers to correspond with new background
        self.set_timers_and_anims()

    def reset_dynamic_background(self):
        """Resets the dynamic background before creating new ones"""
        for group in self.dynamic_bg_groups:
            for item in group.childItems():
                group.removeFromGroup(item)

    def set_vert_spacers(self, ms_time):
        """Sets up dynamic vertical spacers for Progress Bar"""
        gap_size = 5 + 5 * int(ms_time / 300000)  # Factors into size of gaps between spacers
        num_spacers = float(ms_time / 1000) / gap_size  # Number of spacers to implement
        pos_raw = 1000.0 / num_spacers  # Position of 1st Spacer and True inter-spacer gap size.
        # Generating Spacers
        for i in range(int(round(num_spacers))):
            i += 1  # Such that i is in [1, ..., num_spacers] instead of [0, ..., num_spacers - 1]
            # -- Generic Object Pointers -- #
            tiny_line = qg.QGraphicsLineItem(i * pos_raw, 260, i * pos_raw, 265)
            short_line = qg.QGraphicsLineItem(i * pos_raw, 20, i * pos_raw, 260)
            long_line = qg.QGraphicsLineItem(i * pos_raw, 20, i * pos_raw, 265)
            time_text = qg.QGraphicsTextItem(format_secs(gap_size * i))
            # -- Creation Parameters -- #
            odd_spacer = (i % 2 != 0)
            even_spacer = (i % 2 == 0)
            final_spacer = (i == int(round(num_spacers)))
            undershoot = (i * pos_raw < 1000)
            at_end_of_bar = (i * pos_raw == 1000)
            # -- Create Spacers based on Creation Parameters -- #
            if odd_spacer:
                if (not final_spacer) or (final_spacer and undershoot):
                    self.v_bars.add(short_line, pen=white)
                elif final_spacer and at_end_of_bar:
                    self.v_bars.add(tiny_line, pen=white)
            elif even_spacer:
                if (not final_spacer) or (final_spacer and undershoot):
                    self.v_bars.add(long_line, pen=white)
                    self.bar_times.add(time_text, pos_x=i * pos_raw - 20, pos_y=262, color=white)
                elif final_spacer and at_end_of_bar:
                    self.v_bars.add(tiny_line, pen=white)
                    self.bar_times.add(time_text, pos_x=i * pos_raw - 20, pos_y=262, color=white)

    def set_ard_bars(self, data_source):
        """Creates Visual Indicators for Arduino Stimuli based on config data"""
        ms_time = data_source['packet'][3]
        # -- Create bars for Tone if exist -- #
        if len(data_source['tone_pack']) != 0:
            self.create_bar_from_ard_data('tone', data_source['tone_pack'], ms_time)
        if len(data_source['out_pack']) != 0:
            self.create_bar_from_ard_data('output', data_source['out_pack'], ms_time)
        if len(data_source['pwm_pack']) != 0:
            self.create_bar_from_ard_data('pwm', data_source['pwm_pack'], ms_time)

    def create_bar_from_ard_data(self, data_type, data, ms_time):
        """Reads packed arduino commands and turns into progress bar elements"""
        # -- Indicate where to get time data -- #
        if data_type == 'tone':
            start_index, off_index = 1, 2
        elif data_type == 'pwm':
            start_index, off_index = 2, 3
        elif data_type == 'output':
            start_index, off_index = 1, 2
            # -- Simple Output requires combining packed instructions -- #
            # Lists to save processed data
            indiv_trigs, indiv_times = [], []  # corresponding lists of every time a pin is triggered
            pins_and_times = {}  # {pin: [list_of_trigger_times]}
            final_intv = []  # List of lists of final data
            # Create mirror lists of each time a pin is triggered and the time of trigger
            for instruction in data:
                time, pins = instruction[1], instruction[2]
                triggers = check_binary(pins, 'D')
                for trigger in triggers:
                    indiv_trigs.append(trigger)
                    indiv_times.append(time)
            # Create a dictionary of {pin: [list of trigger times]}
            for trig_index in range(len(indiv_trigs)):
                pin = indiv_trigs[trig_index]
                try:
                    pins_and_times[pin].append(indiv_times[trig_index])
                except KeyError:
                    pins_and_times[pin] = [indiv_times[trig_index]]
            # Create list of lists containing [pin, on time, off time]
            for pin in pins_and_times:
                for time_index in range(len(pins_and_times[pin])):
                    if time_index % 2 == 0:
                        final_intv.append([pin,
                                           pins_and_times[pin][time_index],
                                           pins_and_times[pin][time_index + 1]])
            final_intv = sorted(final_intv, key=itemgetter(1))
            data = final_intv
        # -- Return arduino data in readable list -- #
        for instruction in data:
            start_point = (float(instruction[start_index]) / ms_time) * 1000.0
            on_duration = (float(instruction[off_index]) / ms_time) * 1000.0 - start_point
            # Export Data
            start_time = format_secs(instruction[start_index] / 1000)
            off_time = format_secs(instruction[off_index] / 1000)
            # -- Create TONE Bars -- #
            if data_type == 'tone':
                tone_freq = instruction[3]
                self.tone_bars.add(qg.QGraphicsRectItem(start_point, 20, on_duration, 20), brush=yellow, pen=blue,
                                   tooltip='{} - {}\n{} Hz'.format(start_time, off_time, tone_freq))
            # -- Create PWM Bars -- #
            elif data_type == 'pwm':
                pin = check_binary(instruction[5], 'B')[0]
                freq = instruction[4]
                duty_cycle = instruction[7]
                phase_shift = instruction[6]
                pin_ids = range(8, 14)
                pin_ids.remove(10)
                y_pos = 160 + (pin_ids.index(pin)) * 20
                self.pwm_bars.add(qg.QGraphicsRectItem(start_point, y_pos, on_duration, 20), brush=yellow, pen=blue,
                                  tooltip='{} - {}\nPin {}\nFreq: {}Hz\nDuty Cycle: {}%\nPhase Shift:{}'
                                          '' + u'\u00b0'.format(start_time, off_time,
                                                                pin, freq, duty_cycle, phase_shift))
            # -- Create OUTPUT Bars -- #
            elif data_type == 'output':
                pin = instruction[0]
                pin_ids = range(2, 8)
                y_pos = 40 + (pin_ids.index(pin)) * 20
                self.out_bars.add(qg.QGraphicsRectItem(start_point, y_pos, on_duration, 20), brush=yellow, pen=blue,
                                  tooltip='{} - {}\nPin {}'.format(start_time, off_time, pin))

    # -- Animation Objects, Timers, Functions -- #
    def init_anim_gfx_objects(self):
        """Sets up progress bar and timer"""
        # Graphics objects
        self.time_gfx = qg.QGraphicsTextItem('00:00.000')
        self.time_gfx.setDefaultTextColor(white)
        self.bar_gfx = qg.QGraphicsLineItem(0, 22, 0, 258)
        self.bar_gfx.setPen(red)
        # Add objects to scene
        self.scene.addItem(self.time_gfx)
        self.scene.addItem(self.bar_gfx)

    def set_timers_and_anims(self):
        """Sets duration and frames of progress bar animation"""
        self.duration = self.dirs.settings.ard_last_used['packet'][3]
        # Timer objects
        self.time_gfx_timer = qc.QTimeLine(self.duration)
        self.bar_gfx_timer = qc.QTimeLine(self.duration)
        self.time_gfx_timer.setCurveShape(qc.QTimeLine.LinearCurve)
        self.bar_gfx_timer.setCurveShape(qc.QTimeLine.LinearCurve)
        self.time_gfx_timer.setFrameRange(0, self.duration * 1000)
        self.bar_gfx_timer.setFrameRange(0, self.duration * 1000)
        # Animation Objects
        self.time_gfx_anim = qg.QGraphicsItemAnimation()
        self.bar_gfx_anim = qg.QGraphicsItemAnimation()
        self.time_gfx_anim.setItem(self.time_gfx)
        self.bar_gfx_anim.setItem(self.bar_gfx)
        self.time_gfx_anim.setTimeLine(self.time_gfx_timer)
        self.bar_gfx_anim.setTimeLine(self.bar_gfx_timer)
        # Animation Frames
        self.bar_gfx_timer.frameChanged[int].connect(self.advance_increment)
        for i in range(1000):
            self.time_gfx_anim.setPosAt(i / 1000.0, qc.QPointF(i, 0))
            self.bar_gfx_anim.setPosAt(i / 1000.0, qc.QPointF(i, 0))

    def advance_increment(self):
        """Called by bar_gfx_timer; runs this every time timer goes up by 1"""
        # -- Animations for Time Indicator -- #
        # Update Time
        ms_elapsed = self.exp_start_time.elapsed() / 1000.0
        ms_elapsed = format_secs(ms_elapsed, 'with_ms')
        self.time_gfx.setPlainText(ms_elapsed)
        # Make sure Progress Bar booleans are set correctly
        if not self.bar_gfx_running:  # Bar runs entire duration, so use as running marker
            self.bar_gfx_running = True
        if abs(self.bar_gfx_timer.currentFrame()) >= self.duration * 1000:
            self.bar_gfx_running = False
        # Move the Time Indicator by 1 increment
        if not self.time_gfx_running \
            and abs(self.bar_gfx_timer.currentFrame()) > self.duration * 31 \
                and not abs(self.bar_gfx_timer.currentFrame()) >= self.duration * 934:
            self.time_gfx_running = True
            self.time_gfx_timer.start()
        if abs(self.time_gfx_timer.currentFrame()) >= self.duration * 940:
            self.time_gfx_running = False
            self.time_gfx_timer.stop()

    # -- Progress Bar On/Off -- #
    def start_bar(self):
        """Starts Progress Bar"""
        self.time_gfx.setPos(0, 0)
        self.bar_gfx_timer.start()
        self.exp_start_time.start()

    def stop_bar(self):
        """Stops Progress Bar"""
        self.time_gfx_timer.stop()
        self.bar_gfx_timer.stop()
        self.bar_gfx_running = False
        self.time_gfx_running = False


class GUI_ExpControls(qg.QWidget):
    """Settings and Buttons for Configuring the Experiment"""
    def __init__(self, dirs, gui_progbar):
        qg.QWidget.__init__(self)
        self.dirs = dirs
        self.exp_start_event = EXP_START_EVENT
        self.proc_handler_queue = PROC_HANDLER_QUEUE
        self.gui_progbar = gui_progbar
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        self.init_start_stop_buttons()
        self.init_time_entries()
        self.add_to_grid()

    def init_start_stop_buttons(self):
        """Creates and Connects Start Stop Buttons"""
        self.start_btn = qg.QPushButton('START')
        self.start_btn.setStyleSheet('background-color: cyan')
        self.stop_btn = qg.QPushButton('STOP')
        self.stop_btn.setStyleSheet('background-color: orange')
        self.start_btn.clicked.connect(self.start_exp)
        self.stop_btn.clicked.connect(self.stop_exp)

    def init_time_entries(self):
        """Creates and Connects time config entries"""
        text_metrics = qg.QFontMetrics(qg.QApplication.font())
        self.entries = []
        entry_types = [hh, mm, ss]
        hhmmss = time_convert(ms=self.dirs.settings.ard_last_used[packet][3])
        # Entries and Buttons (Signal Emitters)
        for index, entry_type in enumerate(entry_types):
            self.entries.append(qg.QLineEdit())
            self.entries[index].setMaximumWidth(text_metrics.width('00000'))
            self.entries[index].setText(str(hhmmss[index]))
        self.ttl_time_confirm_btn = qg.QPushButton('\nConfirm\n')
        # Static Labels
        static_labels = ['Hour', 'Min', 'Sec', ':', ':']
        for index, name in enumerate(static_labels):
            static_labels[index] = qg.QLabel(name)
            static_labels[index].setAlignment(qc.Qt.AlignCenter)
        # Keep time entries contained in its own frame
        self.time_entry_frame = qg.QGroupBox()
        self.time_entry_frame.setTitle('Total Experiment Time:')
        self.time_entry_frame.setMaximumWidth(320)
        grid = qg.QGridLayout()
        self.time_entry_frame.setLayout(grid)
        # Add components to frame
        grid.addWidget(self.ttl_time_confirm_btn, 0, 5, 2, 1)
        for index, entry in enumerate(self.entries):
            grid.addWidget(static_labels[index], 0, index * 2)
            grid.addWidget(entry, 1, index * 2)
            if index < 2:
                grid.addWidget(static_labels[index + 3], 1, index * 2 + 1)

    def start_exp(self):
        """Starts the experiment"""
        print(mp.active_children())
        self.proc_handler_queue.put_nowait('{}{}'.format(RUN_EXP_HEADER, 'simple_name'))
        # Wait until proc_handler sends the synchronized signal
        self.exp_start_event.wait()
        self.gui_progbar.start_bar()

    def stop_exp(self):
        """Stops the experiment"""
        self.proc_handler_queue.put_nowait(HARDSTOP_HEADER)
        self.gui_progbar.stop_bar()

    # -- Finalize -- #
    def add_to_grid(self):
        """Add buttons to GUI grid"""
        self.grid.addWidget(self.start_btn, 0, 0)
        self.grid.addWidget(self.stop_btn, 0, 1)
        self.grid.addWidget(self.time_entry_frame, 1, 0, 1, 2)


class GUI_CameraDisplay(qg.QWidget):
    """Displays Video feeds from Cameras"""
    def __init__(self, dirs):
        qg.QWidget.__init__(self)
        self.dirs = dirs
        self.grid = qg.QGridLayout()
        self.setLayout(self.grid)
        # Display Configs
        self.image_size = (240, 320)
        self.num_cmrs = 0
        # Image data holders
        self.arrays, self.images, self.labels, self.camera_procs = [], [], [], []
        # GUI Organization parameters
        self.groupboxes = []
        # Sync w/ Camera Processes
        self.cameras = []
        self.sync_events = []
        self.msg_pipes = []
        # Setup Displays
        self.initialize()

    def initialize(self):
        """Cleans up old processes and sets up cameras"""
        self.clean_up()
        self.detect_cameras()
        self.create_data_containers()
        self.create_processes()
        self.setup_groupboxes()
        self.set_update_timer()
        self.start_procs()

    def clean_up(self):
        """Terminates old processes"""
        if len(self.camera_procs) > 0:
            for proc in self.camera_procs:
                proc.stop()
                proc.join()
        for index in reversed(range(self.grid.count())):
            self.grid.itemAt(index).widget().setParent(None)

    def detect_cameras(self):
        """Detects number of cameras of each type"""
        num_attempts = 10  # We'll try to detect up to 10 cameras
        # -- Try to detect PT Grey Firefly Cameras -- #
        temp_ff_context = fc.Context()
        for i in range(num_attempts):
            try:
                temp_ff_context.get_camera_from_index(i)
                self.cameras.append((FireFly_Camera, i))
                num_attempts -= 1
            except fc.ApiError:
                pass
        temp_ff_context.disconnect()
        # -- Try to detect Mini Microscopes -- #
        # Disable extraneous error messages
        devnull = open(os.devnull, 'w')
        stderr = sys.stderr
        sys.stderr = devnull
        # Check for mini microscopes
        for i in range(num_attempts):
            try:
                cam = xi.Xi_Camera(DevID=i)
                cam.get_image()
                cam.close()
                self.cameras.append((Mini_Microscope, i))
                num_attempts -= 1
            except xi.ximea.XI_Error:
                pass
        # Reinstate Error Messages
        sys.stderr = stderr
        devnull.close()
        # Finalize number of cameras across processes
        self.dirs.settings.num_cmrs = len(self.cameras)
        self.num_cmrs = self.dirs.settings.num_cmrs

    def create_data_containers(self):
        """Generates shared data buffers and containers for image display"""
        # -- mp.Array can be shared across processes; np.Array is a readable format -- #
        # -- We make tuples of (mp.Array, np.Array) that ref. the same underlying data buffers -- #
        m_arrays = (mp.Array('I', int(np.prod(self.image_size)), lock=mp.Lock()) for _ in range(self.num_cmrs))
        self.arrays = [(m_array, np.frombuffer(m_array.get_obj(), dtype='I').reshape(self.image_size))
                       for m_array in m_arrays]
        # -- self.images contains image data to be displayed on self.labels -- #
        self.images = [qg.QImage(n.data, n.shape[1], n.shape[0], qg.QImage.Format_RGB32) for m, n in self.arrays]
        self.labels = [qg.QLabel(self) for _ in self.arrays]

    def create_processes(self):
        """Generates separate processes for each camera stream"""
        for index, (m_array, n) in enumerate(self.arrays):
            self.msg_pipes.append(mp.Pipe())
            self.sync_events.append(mp.Event())
            cmr_type, cmr_id = self.cameras[index][0], self.cameras[index][1]
            main_pipe_end, cmr_pipe_end = self.msg_pipes[index]
            self.camera_procs.append(cp.Camera(self.dirs, index, m_array, self.image_size, self.sync_events[index],
                                               cmr_pipe_end, cmr_type, cmr_id))
            self.camera_procs[index].name = 'cmr_stream_proc_#{} - [type {} id {}]'.format(index,
                                                                                           self.cameras[index][0],
                                                                                           self.cameras[index][1])

    def setup_groupboxes(self):
        """Creates individual labeled boxes for each camera display"""
        max_per_col = 3  # Max number of cameras we'll render per column
        num_columns = max(int(math.ceil(float(self.num_cmrs) / max_per_col)), 1)
        num_empty = num_columns * max_per_col - self.num_cmrs
        self.groupboxes = []
        for i in range(num_columns * max_per_col):
            self.groupboxes.append(qg.QGroupBox())
        for cmr_index, cmr in enumerate(self.cameras):
            grid = qg.QGridLayout()
            grid.addWidget(self.labels[cmr_index])
            self.groupboxes[cmr_index].setTitle('{} - {} #{}'.format(cmr_index, cmr[0], cmr[1]))
            self.groupboxes[cmr_index].setLayout(grid)
            col = num_columns - cmr_index // max_per_col
            row = cmr_index - (cmr_index // max_per_col) * max_per_col
            self.grid.addWidget(self.groupboxes[cmr_index], row, col)
        for empty in range(num_empty):
            empty += self.num_cmrs
            self.groupboxes[empty].setTitle('No Camera Available')
            col = num_columns - empty // max_per_col
            row = empty - (empty // max_per_col) * max_per_col
            self.grid.addWidget(self.groupboxes[empty], row, col)

    def set_update_timer(self):
        """Creates a timer that periodically updates the camera displays"""
        update_timer = qc.QTimer(self)
        update_timer.timeout.connect(self.update_displays)
        update_timer.start(5)

    def start_procs(self):
        """Starts camera processes"""
        [proc.start() for proc in self.camera_procs]

    def update_displays(self):
        """Updates Image Pixel Map"""
        for index in range(self.num_cmrs):
            if self.sync_events[index].is_set():
                self.labels[index].setPixmap(qg.QPixmap.fromImage(self.images[index]))
                self.sync_events[index].clear()
