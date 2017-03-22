# coding=utf-8

"""Custom PyQt Widgets"""

import sys
import math
from Misc_Functions import *
from datetime import datetime
from copy import deepcopy
from PyQt4 import QtGui, QtCore

# Temp Imports
import numpy as np
import multiprocessing as mp
import random
import time


# Quick pointers to QT specific objects
black = QtGui.QColor(0, 0, 0)
white = QtGui.QColor(255, 255, 255)
yellow = QtGui.QColor(255, 255, 0)
blue = QtGui.QColor(0, 0, 255)


# Useful Tools
class GUI_SimpleGroup(QtGui.QGraphicsItemGroup):
    """Simplifies adding unnamed Qt Items to a group"""
    def __init__(self):
        QtGui.QGraphicsItemGroup.__init__(self)

    def newItem(self, item, pos_x=None, pos_y=None, pen=None, brush=None, color=None, tooltip=None):
        """Adds a new item with attributes"""
        self.addToGroup(item)
        if pos_x and pos_y: item.setPos(pos_x, pos_y)
        if pen: item.setPen(pen)
        if brush: item.setBrush(brush)
        if color: item.setDefaultTextColor(color)
        if tooltip: item.setToolTip(tooltip)


class GUI_NamedComboBox(QtGui.QComboBox):
    """ComboBox with __name__ attr."""
    def __init__(self, name):
        QtGui.QComboBox.__init__(self)
        self.__name__ = name


class GUI_CustomSignal(QtCore.QObject):
    """Creates a custom signal"""
    signal = QtCore.pyqtSignal()


class GUI_Message(QtGui.QMessageBox):
    """A quick popup message with buttons"""
    def __init__(self, title='Warning!', msg='', callable_fn=None,
                 icon=QtGui.QMessageBox.Warning, btns=QtGui.QMessageBox.Close):
        QtGui.QMessageBox.__init__(self)
        self.setIcon(icon)
        self.setWindowTitle(title)
        self.setText(msg)
        self.setStandardButtons(btns)
        self.exec_()
        if callable_fn:
            callable_fn()


# Actual Widgets
class GUI_ProgressBar(QtGui.QGraphicsView):
    """Progress Bar for Monitoring Experiment and Arduino Statuses"""

    def __init__(self, dirs):
        QtGui.QGraphicsView.__init__(self)
        self.init_static_background()
        self.dirs = dirs
        self.grid = QtGui.QGridLayout()
        # Flow Control Booleans
        self.bar_gfx_running = False
        self.time_gfx_running = False
        # Animated Graphics
        self.time_gfx = QtGui.QGraphicsTextItem('00:00.000')
        self.time_gfx.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        self.bar_gfx = QtGui.QGraphicsLineItem(0, 22, 0, 258)
        self.bar_gfx.setPen(QtGui.QColor(255, 0, 0))
        # Timers and Animation Objects
        self.set_timers_anim(self.dirs.settings.ard_last_used['packet'][3])
        # Dynamic Place Markers
        self.v_bars = GUI_SimpleGroup()
        self.bar_times = GUI_SimpleGroup()
        self.tone_bars = GUI_SimpleGroup()
        self.out_bars = GUI_SimpleGroup()
        self.pwm_bars = GUI_SimpleGroup()
        self.dynamic_item_groups = [self.v_bars, self.bar_times,
                                    self.tone_bars, self.out_bars,
                                    self.pwm_bars]
        self.ard_grab_data()
        # Finish Setup
        self.scene = QtGui.QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, 1250, 280)
        self.scene.addItem(self.bg_group)
        for group in self.dynamic_item_groups:
            self.scene.addItem(group)
        self.scene.addItem(self.time_gfx)
        self.scene.addItem(self.bar_gfx)
        self.setScene(self.scene)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setMinimumWidth(1252)
        self.setMaximumHeight(282)

    def init_static_background(self):
        """Sets up the Static Backdrop"""
        self.bg_group = GUI_SimpleGroup()
        # Main Background Shapes
        self.bg_group.newItem(QtGui.QGraphicsRectItem(0, 0, 1252, 280), brush=black)
        self.bg_group.newItem(QtGui.QGraphicsLineItem(0, 20, 1252, 20), pen=white)
        self.bg_group.newItem(QtGui.QGraphicsLineItem(0, 40, 1252, 40), pen=white)
        self.bg_group.newItem(QtGui.QGraphicsLineItem(0, 160, 1252, 160), pen=white)
        self.bg_group.newItem(QtGui.QGraphicsLineItem(0, 260, 1252, 260), pen=white)
        # Row Label White Backdrops
        self.bg_group.newItem(QtGui.QGraphicsRectItem(1200, 20, 15, 20), brush=white)
        self.bg_group.newItem(QtGui.QGraphicsRectItem(1200, 40, 15, 120), brush=white)
        self.bg_group.newItem(QtGui.QGraphicsRectItem(1200, 160, 15, 100), brush=white)
        # Row Name Labels
        self.bg_group.newItem(QtGui.QGraphicsTextItem(u'\u266b'), pos_x=1197, pos_y=13)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('S'), pos_x=1199, pos_y=41)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('I'), pos_x=1202, pos_y=61)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('M'), pos_x=1198, pos_y=81)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('P'), pos_x=1199, pos_y=101)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('L'), pos_x=1200, pos_y=121)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('E'), pos_x=1199, pos_y=141)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('P'), pos_x=1199, pos_y=181)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('W'), pos_x=1197, pos_y=201)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('M'), pos_x=1198, pos_y=221)
        # Arduino Pin Labels
        self.bg_group.newItem(QtGui.QGraphicsTextItem('PIN #'), color=white, pos_x=1211, pos_y=1)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('10'), color=white, pos_x=1221, pos_y=21)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('02'), color=white, pos_x=1221, pos_y=41)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('03'), color=white, pos_x=1221, pos_y=61)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('04'), color=white, pos_x=1221, pos_y=81)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('05'), color=white, pos_x=1221, pos_y=101)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('06'), color=white, pos_x=1221, pos_y=121)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('07'), color=white, pos_x=1221, pos_y=141)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('08'), color=white, pos_x=1221, pos_y=161)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('09'), color=white, pos_x=1221, pos_y=181)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('11'), color=white, pos_x=1221, pos_y=201)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('12'), color=white, pos_x=1221, pos_y=221)
        self.bg_group.newItem(QtGui.QGraphicsTextItem('13'), color=white, pos_x=1221, pos_y=241)

    def ard_grab_data(self, destroy=False, load=None):
        """Obtain Arduino Preset from Saves"""
        if load:
            self.dirs.settings.ard_last_used = deepcopy(self.dirs.settings.ard_presets[load])
        if destroy:
            for group in self.dynamic_item_groups:
                for item in group.childItems():
                    group.removeFromGroup(item)
        self.setup_spacers(self.dirs.settings.ard_last_used['packet'][3])
        self.setup_ard_bars()
        self.set_timers_anim(self.dirs.settings.ard_last_used['packet'][3])

    def setup_ard_bars(self):
        """Sets up on/off indicators of arduino stimuli"""
        if len(self.dirs.settings.ard_last_used['tone_pack']) != 0:
            self.tone_data = ard_decode_data(self.dirs, 'tone', self.dirs.settings.ard_last_used['tone_pack'])
            for i in range(len(self.tone_data)):
                self.tone_bars.newItem(QtGui.QGraphicsRectItem(self.tone_data[i][0] * 1.2,
                                                               20, self.tone_data[i][1] * 1.2,
                                                               20), brush=yellow, pen=blue,
                                       tooltip='{} - {}\n{} Hz'.format(format_secs(self.tone_data[i][4] / 1000),
                                                                       format_secs(self.tone_data[i][5] / 1000),
                                                                       self.tone_data[i][3]))
        if len(self.dirs.settings.ard_last_used['out_pack']) != 0:
            pin_ids = range(2, 8)
            self.out_data = ard_decode_data(self.dirs, 'output', self.dirs.settings.ard_last_used['out_pack'])
            for i in range(len(self.out_data)):
                y_pos = 40 + (pin_ids.index(self.out_data[i][3])) * 20
                self.out_bars.newItem(QtGui.QGraphicsRectItem(self.out_data[i][0] * 1.2,
                                                              y_pos, self.out_data[i][1] * 1.2,
                                                              20), brush=yellow, pen=blue,
                                      tooltip='{} - {}\nPin {}'.format(format_secs(self.out_data[i][4] / 1000),
                                                                       format_secs(self.out_data[i][5] / 1000),
                                                                       self.out_data[i][3]))
        if len(self.dirs.settings.ard_last_used['pwm_pack']) != 0:
            pin_ids = range(8, 14)
            pin_ids.remove(10)
            self.pwm_data = ard_decode_data(self.dirs, 'pwm', self.dirs.settings.ard_last_used['pwm_pack'])
            for i in range(len(self.pwm_data)):
                y_pos = 160 + (pin_ids.index(self.pwm_data[i][3])) * 20
                self.pwm_bars.newItem(QtGui.QGraphicsRectItem(self.pwm_data[i][0] * 1.2,
                                                              y_pos, self.pwm_data[i][1] * 1.2,
                                                              20), brush=yellow, pen=blue,
                                      tooltip=('{} - {}\nPin {}\nFreq: {}Hz\nDuty Cycle: {}%\nPhase Shift: {}'
                                               '' + u'\u00b0').format(format_secs(self.pwm_data[i][7] / 1000),
                                                                      format_secs(self.pwm_data[i][8] / 1000),
                                                                      self.pwm_data[i][3], self.pwm_data[i][4],
                                                                      self.pwm_data[i][5], self.pwm_data[i][6]))

    def setup_spacers(self, ms_time):
        """Sets up dynamic vertical spacer bars"""
        divisor = 5 + 5 * int(ms_time / 300000)
        segment = float(ms_time / 1000) / divisor
        pos_raw = 1200.0 / segment
        for i in range(int(round(segment))):
            if i > 0:
                if i % 2 != 0:
                    self.v_bars.newItem(QtGui.QGraphicsLineItem(i * pos_raw, 20, i * pos_raw, 260), pen=white)
                if i % 2 == 0:
                    self.v_bars.newItem(QtGui.QGraphicsLineItem(i * pos_raw, 20, i * pos_raw, 265), pen=white)
                    self.bar_times.newItem(QtGui.QGraphicsTextItem(format_secs(divisor * i)),
                                           pos_x=i * pos_raw - 20, pos_y=262, color=white)
                if i == int(round(segment)) - 1 and (i + 1) % 2 == 0 and (i + 1) * pos_raw <= 1201:
                    if round((i + 1) * pos_raw) != 1200.0:
                        self.v_bars.newItem(QtGui.QGraphicsLineItem((i + 1) * pos_raw, 20, (i + 1) * pos_raw, 265),
                                            pen=white)
                    elif round((i + 1) * pos_raw) == 1200.0:
                        self.v_bars.newItem(QtGui.QGraphicsLineItem((i + 1) * pos_raw, 260, (i + 1) * pos_raw, 265),
                                            pen=white)
                    self.bar_times.newItem(QtGui.QGraphicsTextItem(format_secs(divisor * (i + 1))),
                                           pos_x=(i + 1) * pos_raw - 20, pos_y=262, color=white)
                if i == int(round(segment)) - 1 and (i + 1) % 2 != 0 and (i + 1) * (1000.0 / segment) <= 1001:
                    if round((i + 1) * pos_raw) != 1200.0:
                        self.v_bars.newItem(QtGui.QGraphicsLineItem((i + 1) * pos_raw, 20, (i + 1) * pos_raw, 265),
                                            pen=white)
                    elif round((i + 1) * pos_raw) == 1200.0:
                        self.v_bars.newItem(QtGui.QGraphicsLineItem((i + 1) * pos_raw, 260, (i + 1) * pos_raw, 265),
                                            pen=white)

    def set_timers_anim(self, ms_time):
        """Call this to set the duration of the progress bar"""
        self.duration = ms_time
        # Timers
        self.time_gfx_timer = QtCore.QTimeLine(ms_time)
        self.bar_gfx_timer = QtCore.QTimeLine(ms_time)
        self.time_gfx_timer.setCurveShape(QtCore.QTimeLine.LinearCurve)
        self.bar_gfx_timer.setCurveShape(QtCore.QTimeLine.LinearCurve)
        self.time_gfx_timer.setFrameRange(0, self.duration * 1200)
        self.bar_gfx_timer.setFrameRange(0, self.duration * 1200)
        # Animation Objects
        self.time_gfx_anim = QtGui.QGraphicsItemAnimation()
        self.bar_gfx_anim = QtGui.QGraphicsItemAnimation()
        self.time_gfx_anim.setItem(self.time_gfx)
        self.bar_gfx_anim.setItem(self.bar_gfx)
        self.time_gfx_anim.setTimeLine(self.time_gfx_timer)
        self.bar_gfx_anim.setTimeLine(self.bar_gfx_timer)
        # Animation Proper
        self.bar_gfx_timer.frameChanged[int].connect(self.advance_increment)
        for i in range(1200):
            self.time_gfx_anim.setPosAt(i / 1200.0, QtCore.QPointF(i, 0))
            self.bar_gfx_anim.setPosAt(i / 1200.0, QtCore.QPointF(i, 0))

    def advance_increment(self):
        """Called by bar_gfx_timer; runs this every time the timer advances by 1"""
        now = datetime.now()
        last_time = (now - self.start_time).seconds + float((now - self.start_time).microseconds) / 1000000
        self.time_gfx.setPlainText(format_secs(last_time, report_ms=True))
        # Animations for Progress Bar
        if not self.bar_gfx_running:  # Bar runs entire duration, so use as running marker
            self.bar_gfx_running = True
        if abs(self.bar_gfx_timer.currentFrame()) >= self.duration * 1200:
            self.bar_gfx_running = False
        # Animations for Time Indicator
        if not self.time_gfx_running \
                and abs(self.bar_gfx_timer.currentFrame()) > self.duration * 32\
                and not abs(self.bar_gfx_timer.currentFrame()) >= self.duration * 1134:
            # At this point, we can start the time indicator; but don't run again for this cycle
            self.time_gfx_running = True
            self.time_gfx_timer.start()
        if abs(self.time_gfx_timer.currentFrame()) >= self.duration * 1134:
            self.time_gfx_running = False
            self.time_gfx_timer.stop()

    def start_bar(self):
        """Starts Progress Bar"""
        self.time_gfx.setPos(0, 0)
        self.bar_gfx_timer.start()
        self.start_time = datetime.now()

    def stop_bar(self):
        """Stops Progress Bar"""
        self.time_gfx_timer.stop()
        self.bar_gfx_timer.stop()
        self.bar_gfx_running = False
        self.time_gfx_running = False


class GUI_ArduinoSettings(QtGui.QWidget):
    """Popup windows for configuring arduino stimuli settings"""
    def __init__(self, dirs, parent=None):
        super(GUI_ArduinoSettings, self).__init__(parent)
        self.dirs = dirs
        self.types = ''
        self.num_entries = 0
        # Variables
        self.output_ids, self.pwm_ids = (range(2, 8), range(8, 14))
        self.pwm_ids.remove(10)
        self.entries = None
        self.closebutton = None
        # Default entry validation does not end in closing the GUI
        self.close_gui = False
        # Pull last used settings
        [self.packet, self.tone_pack,
         self.out_pack, self.pwm_pack] = self.dirs.settings.quick_ard()
        self.max_time = 0
        self.data = {'starts': {}, 'middles': {}, 'ends': {}, 'hold': {}}
        self.return_data = []
        self.fields_validated = {}

    def tone_setup(self):
        """Tone GUI"""
        self.setWindowTitle('Tone Configuration')
        self.types = 'tone'
        num_pins, self.num_entries = 1, 15
        # Main GUI Layout
        main_grid = QtGui.QGridLayout()
        # Scroll Area Layout
        scroll_container = QtGui.QWidget()
        scroll_area = QtGui.QScrollArea()
        scroll_grid = QtGui.QGridLayout()
        # Setup Toggle Button
        pin_toggle_name = 'Enable Tone\n(Arduino Pin 10)'
        self.pin_toggle = QtGui.QCheckBox(pin_toggle_name)
        self.pin_toggle.clicked.connect(lambda: self.btn_toggle('tone'))
        # Setup Confirm Button
        confirm_btn = QtGui.QPushButton('CONFIRM')
        confirm_btn.clicked.connect(self.pre_close)
        # Add Items to Main Layout
        main_grid.addWidget(self.pin_toggle, 0, 0)
        main_grid.addWidget(QtGui.QLabel('\nTime On(s), '
                                         'Time until Off(s), '
                                         'Freq (Hz)'), 1, 0)
        main_grid.addWidget(scroll_area, 2, 0)
        main_grid.addWidget(confirm_btn, 3, 0)
        self.setLayout(main_grid)
        # Add Items to Scroll Layout
        self.entries = [None] * self.num_entries
        for row in range(self.num_entries):
            scroll_grid.addWidget(QtGui.QLabel('{:0>2}'.format(row + 1)),
                                  row + 1, 0)
            self.entries[row] = QtGui.QLineEdit()
            scroll_grid.addWidget(self.entries[row], row + 1, 1)
            self.entries[row].setDisabled(True)
            self.entries[row].editingFinished.connect(lambda rows=row:
                                                      self.entry_validate(False, rows))
        scroll_container.setLayout(scroll_grid)
        # Finish Setup
        scroll_area.setWidget(scroll_container)
        self.setMinimumHeight(200)
        self.setMinimumWidth(200)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMinimumWidth(200)
        self.show()

    def btn_toggle(self, types):
        """Toggles the selected pin checkbox"""
        if types == 'tone':
            if self.pin_toggle.isChecked():
                for row in range(self.num_entries):
                    self.entries[row].setDisabled(False)
            elif not self.pin_toggle.isChecked():
                for row in range(self.num_entries):
                    self.entries[row].setDisabled(True)

    def pre_close(self):
        pass

    def entry_validate(self, pins=False, rows=None):
        """Checks inputs are valid"""
        entry, err_place_msg, arg_types = None, '', []
        row = int(rows)
        pin = None
        if pins:
            pin = int(pins)
        # If we request a close via confirm button, we do a final check
        close_gui = self.close_gui
        if self.close_gui:
            # set to False so if check fails we don't get stuck in a loop
            self.close_gui = False
        pin_ids = 0
        ##################################################################
        if self.types == 'tone':
            pin_ids = 10
            entry = self.entries[row]
            arg_types = ['Time On (s)', 'Time until Off (s)', 'Frequency (Hz)']
            err_place_msg = 'row [{:0>2}]'.format(row + 1)
        ##################################################################
        # Grab comma separated user inputs as a list
        inputs = str(entry.text()).strip().split(',')
        for i in range(len(inputs)):
            inputs[i] = inputs[i].strip()
        ##################################################################
        # Begin to check entry validity
        # 1. Check commas don't occur at ends or there exist any double commas:
        while True:
            time.sleep(0.0001)
            if '' in inputs:
                inputs.pop(inputs.index(''))
            else:
                break
        # 2. Check we have correct number of input arguments
        num_args = len(arg_types)
        error_str = ''
        for i in range(num_args):
            if i == 3:
                error_str += '\n'
            error_str += str(arg_types[i])
            if i < num_args - 1:
                error_str += ', '
        # 2a. More than 0 but not num_args
        if len(inputs) != num_args and len(inputs) > 0:
            GUI_Message(msg='Error in {}:\n'
                            'Setup requires [{}] arguments for each line.\n\n'
                            'Comma separated in this order:\n\n'
                            '[{}]'.format(err_place_msg, num_args, error_str))
            entry.setFocus(True)
            return False
        # 2b. Exactly 0: we don't need to process an empty field
        if len(inputs) == 0:
            if close_gui:
                self.close()
            return False
        # 3. Check input contents are valid
        try:
            on, off = int(inputs[0]), int(inputs[1])
            on_ms, off_ms = on * 1000, off * 1000
            refr, freq, phase, duty_cycle = None, 0, 0, 0
            if self.types == 'tone':
                freq = int(inputs[2])
                refr = freq
            # 3a. Store max time configured; at close, if max_time > dirs.settings max time,
            #     we changed the max time for this procedure
            if (on_ms + off_ms) > self.max_time and off_ms != 0:
                self.max_time = on_ms + off_ms
            # 3b. Time interval for each entry must be > 0
            if off == 0:
                GUI_Message(msg='Error in {}:\n\n'
                                'Time Interval (i.e. '
                                'Time until Off) '
                                'cannot be 0s!'.format(err_place_msg))
                entry.setFocus(True)
                return False
            # 3c. Type specific checks
            if self.types == 'tone':
                if freq < 50:
                    GUI_Message(msg='Error in {}:\n\n'
                                    'The TONE function works '
                                    'best for high frequencies.\n\n'
                                    'Use the PWM function '
                                    'instead for low Hz '
                                    'frequency modulation'.format(err_place_msg))
                    entry.setFocus()
                    return False
        except ValueError:
            GUI_Message(msg='Error in {}:\n\n'
                            'Input arguments '
                            'must be comma '
                            'separated integers'.format(err_place_msg))
            entry.setFocus()
            return False
        ##################################################################
        # 4. Check if any time intervals overlap
        #       Rules:
        #       - Time intervals cannot overlap for the same pin
        #       - Time intervals next to each other
        #         at the same [refr] will be joined into a single segment
        #         to save storage on arduino
        #       Therefore:
        #       - OUTPUT pins can always overlap. We just need to combine time inputs
        #       - PWM Pins can overlap iff same [refr]; else raise error
        #       - TONE is one pin only. Only allow overlap if same [refr]
        #       (to date only implemented joining adjacent segments;
        #           no overlap management available)
        ##################################################################
        # PWM Needs some extra steps before we begin
        starts_l, middles_l, ends_l, hold_l = {}, {}, {}, {}
        if self.types == 'pwm':
            pin_int = pin_to_int(pin_ids)
            # temp hold in starts_l so we can use self.data in the same way
            # for pwm and output/tone in the following
            (starts_l, middles_l, ends_l, hold_l) = (self.data['starts'],
                                                     self.data['middles'],
                                                     self.data['ends'],
                                                     self.data['hold'])
            try:
                starts_l[pin_ids], middles_l[pin_ids], ends_l[pin_ids], hold_l[pin_ids]
            except KeyError:
                (starts_l[pin_ids], middles_l[pin_ids],
                 ends_l[pin_ids], hold_l[pin_int]) = {}, {}, {}, {}
            (self.data['starts'], self.data['middles'],
             self.data['ends'], self.data['hold']) = (starts_l[pin_ids], middles_l[pin_ids],
                                                      ends_l[pin_ids], hold_l[pin_int])
        # 4a.
        # Before we validate entries further:
        # If the validation is performed on a field already validated
        # e.g. because user misclicked or needs to edit
        # we will need to remove its previous set of data first to prevent clashing

    def time_remove(self, rows, pins, refr):
        """Removes the indicated time segment"""
        field = {}


class GUI_ExperimentWidget(QtGui.QWidget):
    """Main Experiment Monitoring and Stimuli Config Widget"""
    def __init__(self, dirs):
        QtGui.QWidget.__init__(self)
        self.dirs = dirs
        self.grid = QtGui.QGridLayout()
        self.initialize()

    def initialize(self):
        """Sets up progress bar gfx and buttons/entries"""
        self.main_prog_gfx = GUI_ProgressBar(self.dirs)
        self.ard_config_widget = GUI_ArduinoSettings(self.dirs)
        self.render_buttons()
        self.render_time_entries()
        self.load_ard_preset_list()
        self.connect_buttons()
        self.add_to_grid()
        self.setLayout(self.grid)

    def ard_config_open(self, types):
        """Based on 'type' input, select config window to open up"""
        if types == 'tone':
            self.ard_config_widget.tone_setup()
        elif types == 'pwm':
            self.ard_config_widget.pwm_setup()
        elif types == 'output':
            self.ard_config_widget.output_setup()

    def render_buttons(self):
        """Renders button graphics"""
        # Create Grid Container
        self.setup_btns = QtGui.QFrame()
        grid = QtGui.QGridLayout()
        # -- Start and Stop Buttons -- #
        self.start_btn = QtGui.QPushButton('START')
        self.start_btn.setStyleSheet('background-color: cyan')
        self.stop_btn = QtGui.QPushButton('STOP')
        self.stop_btn.setStyleSheet('background-color: orange')
        # -- Experiment Stimuli Setup Buttons -- #
        #    Buttons
        self.tone_btn = QtGui.QPushButton('Tone Setup')
        self.tone_btn.clicked.connect(lambda: self.ard_config_open('tone'))
        self.output_btn = QtGui.QPushButton('Simple Outputs')
        self.output_btn.clicked.connect(lambda: self.ard_config_open('tone'))
        self.pwm_btn = QtGui.QPushButton('PWM Setup')
        self.pwm_btn.clicked.connect(lambda: self.ard_config_open('tone'))
        #    Button Container
        grid.addWidget(self.tone_btn, 0, 0)
        grid.addWidget(self.output_btn, 0, 1)
        grid.addWidget(self.pwm_btn, 0, 2)
        # -- Buttons for Presets -- #
        #    Buttons
        self.preset_entry = QtGui.QLineEdit()
        self.preset_list = QtGui.QComboBox()
        self.preset_btn = QtGui.QPushButton('Save as Preset')
        #    Title
        preset_title = QtGui.QLabel('Presets')
        preset_title.setAlignment(QtCore.Qt.AlignCenter)
        grid.addWidget(preset_title, 1, 0, 1, 3)
        #    Button Container
        grid.addWidget(self.preset_list, 2, 0)
        grid.addWidget(self.preset_entry, 2, 1)
        grid.addWidget(self.preset_btn, 2, 2)
        #    Resize Entry
        self.preset_entry.setMaximumWidth(200)
        # -- FINALIZE -- #
        self.setup_btns.setLayout(grid)

    def render_time_entries(self):
        """Renders entry boxes for editing total time"""
        text_metrics = QtGui.QFontMetrics(QtGui.QApplication.font())
        # -- Experiment Time Entries -- #
        #    Entries
        self.hh_entry = QtGui.QLineEdit()
        self.mm_entry = QtGui.QLineEdit()
        self.ss_entry = QtGui.QLineEdit()
        #    Text Labels
        ttl_time_label = QtGui.QLabel('Total Experiment Time:')
        ttl_time_label.setAlignment(QtCore.Qt.AlignCenter)
        colon1 = QtGui.QLabel(':')
        colon2 = QtGui.QLabel(':')
        colon1.setAlignment(QtCore.Qt.AlignCenter)
        colon2.setAlignment(QtCore.Qt.AlignCenter)
        hh_text = QtGui.QLabel('Hour')
        mm_text = QtGui.QLabel('Min')
        ss_text = QtGui.QLabel('Sec')
        hh_text.setAlignment(QtCore.Qt.AlignCenter)
        mm_text.setAlignment(QtCore.Qt.AlignCenter)
        ss_text.setAlignment(QtCore.Qt.AlignCenter)
        #    Confirm Button
        self.ttl_time_confirm_btn = QtGui.QPushButton('Confirm')
        #    Adjust Size
        time_entry_size = text_metrics.width('00000')
        self.hh_entry.setMaximumWidth(time_entry_size)
        self.mm_entry.setMaximumWidth(time_entry_size)
        self.ss_entry.setMaximumWidth(time_entry_size)
        hh, mm, ss = time_convert(ms=self.dirs.settings.ard_last_used['packet'][3])
        self.hh_entry.setText(str(hh))
        self.mm_entry.setText(str(mm))
        self.ss_entry.setText(str(ss))
        #    Add to Frame
        self.time_entries = QtGui.QFrame()
        self.time_entries.setMaximumWidth(320)
        grid = QtGui.QGridLayout()
        #       Grid Formatting
        grid.addWidget(ttl_time_label, 0, 0, 1, 6)
        grid.addWidget(self.ttl_time_confirm_btn, 2, 5, 2, 1)
        grid.addWidget(hh_text, 2, 0)
        grid.addWidget(mm_text, 2, 2)
        grid.addWidget(ss_text, 2, 4)
        grid.addWidget(self.hh_entry, 3, 0)
        grid.addWidget(colon1, 3, 1)
        grid.addWidget(self.mm_entry, 3, 2)
        grid.addWidget(colon2, 3, 3)
        grid.addWidget(self.ss_entry, 3, 4)
        self.time_entries.setLayout(grid)

    def connect_buttons(self):
        """Connects buttons to functions"""
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.ttl_time_confirm_btn.clicked.connect(self.set_ttl_time)
        self.preset_btn.clicked.connect(self.save_ard_preset)

    def add_to_grid(self):
        """Adds buttons to widget"""
        self.grid.addWidget(self.main_prog_gfx, 0, 0, 1, 4)
        self.grid.addWidget(self.start_btn, 1, 0)
        self.grid.addWidget(self.stop_btn, 2, 0)
        self.grid.addWidget(self.setup_btns, 1, 2, 1, 2)
        self.grid.addWidget(self.time_entries, 1, 1, 2, 1)

    def set_ttl_time(self):
        """Sets the total experiment time"""
        hh = self.hh_entry.text()
        mm = self.mm_entry.text()
        ss = self.ss_entry.text()
        ms = time_convert(hh=hh, mm=mm, ss=ss)
        self.dirs.settings.ard_last_used['packet'][3] = ms
        self.main_prog_gfx.ard_grab_data(destroy=True)

    def start(self):
        """Starts experiment"""
        self.main_prog_gfx.start_bar()

    def stop(self):
        """Stops experiment"""
        self.main_prog_gfx.stop_bar()

    def load_ard_preset_list(self):
        """Loads list of arduino presets from save file"""
        [self.preset_list.addItem(str(i)) for i in self.dirs.settings.ard_presets]
        self.preset_list.activated[str].connect(lambda name:
                                                self.main_prog_gfx.ard_grab_data(True, str(name)))

    def save_ard_preset(self):
        """Saves arduino preset to save file"""
        preset_list = [i for i in self.dirs.settings.ard_presets]
        preset_name = str(self.preset_entry.text()).strip().lower()
        if len(preset_name) == 0:
            GUI_Message(msg='You must give your preset a name.')
            self.preset_entry.setFocus()
            self.preset_entry.selectAll()
        else:
            if preset_name not in preset_list:
                to_save = deepcopy(self.dirs.settings.ard_last_used)
                self.dirs.settings.ard_presets[preset_name] = to_save
                self.preset_list.clear()
                [self.preset_list.addItem(i) for i in self.dirs.settings.ard_presets]
                GUI_Message(title='Saved!', icon=QtGui.QMessageBox.Information,
                            msg='Preset saved as [{}]'.format(preset_name))
            else:
                reply = QtGui.QMessageBox.question(self, 'Overwrite?',
                                                   '[{}] already exists as a preset. '
                                                   'Overwrite it anyway?'.format(preset_name),
                                                   QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                if reply == QtGui.QMessageBox.Yes:
                    to_save = deepcopy(self.dirs.settings.ard_last_used)
                    self.dirs.settings.ard_presets[preset_name] = to_save
                    self.preset_list.clear()
                    [self.preset_list.addItem(i) for i in self.dirs.settings.ard_presets]
                    GUI_Message(title='Saved!', icon=QtGui.QMessageBox.Information,
                                msg='Preset saved as [{}]'.format(preset_name))


class GUI_SettingsOverview(QtGui.QGroupBox):
    """Summary of settings selected"""
    def __init__(self, dirs):
        QtGui.QGroupBox.__init__(self)
        # Basic Structure
        self.setTitle('Summary of Settings')
        grid = QtGui.QGridLayout()
        # Variables
        self.dirs = dirs
        self.label = QtGui.QLabel('')
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        # Setup Layout
        grid.addWidget(self.label)
        self.setLayout(grid)
        # Load Settings for first time
        self.update_label(fp=False)

    def update_label(self, fp=True):
        """Gets information from dirs.settings and updates label"""
        # Photometry Labels
        if fp:
            fp_ch_num, fp_main_freq, fp_isos_freq = self.dirs.settings.quick_fp()
            fp_string = 'Photometry Channels: {}\n' \
                        'Main Stim Freq: [{} Hz]\n' \
                        'Isos Stim Freq: [{} Hz]'.format(fp_ch_num, fp_main_freq, fp_isos_freq)
        else:
            fp_string = '\n[Photometry DISABLED]\n'
        # LabJack Labels
        lj_ch_num, lj_scan_freq = self.dirs.settings.quick_lj()
        lj_string = 'LabJack Channels: {}\n' \
                    'Scan Frequency: [{} Hz]'. format(lj_ch_num, lj_scan_freq)
        if self.dirs.settings.save_dir != '':
            sv_settings = self.dirs.settings.save_dir
        else:
            sv_settings = '[N/A]'
        div = '-' * 100
        state = '{}\n\n{}\n{}\n{}\n\n{}'.format(fp_string, div, lj_string, div, sv_settings)
        self.label.setText(state)


class GUI_PhotometryConfig(QtGui.QGroupBox):
    """GUI for Configuring Photometry Options"""
    def __init__(self, dirs):
        QtGui.QWidget.__init__(self)
        # Housekeeping
        self.setTitle('Photometry')
        self.dirs = dirs  # Mesh into dirs.settings from main_module
        self.signal = GUI_CustomSignal()  # emit if change any states
        self.grid = QtGui.QGridLayout()
        # Render Widget
        self.render_widget()
        # Set Layout
        self.setLayout(self.grid)

    def render_widget(self):
        """Creates the Photometry Widget"""
        self.menus = {'data': {'pos': 0, 'menu': GUI_NamedComboBox('data'),
                               'label': QtGui.QLabel('Photometry Data Channel')},
                      'main': {'pos': 1, 'menu': GUI_NamedComboBox('main'),
                               'label': QtGui.QLabel('Main Reference Channel')},
                      'isos': {'pos': 2, 'menu': GUI_NamedComboBox('isos'),
                               'label': QtGui.QLabel('Isosbestic Reference Channel')}}
        for name in self.menus:
            # Assign
            pos = self.menus[name]['pos']
            menu = self.menus[name]['menu']
            label = self.menus[name]['label']
            # Configure
            label.setAlignment(QtCore.Qt.AlignCenter)
            menu.addItems(['LabJack AIN {}'.format(str(i)) for i in range(14)])
            menu.setCurrentIndex(self.dirs.settings.fp_last_used['ch_num'][pos])
            menu.activated.connect(lambda selection, menu_name=menu.__name__:
                                   self.select_menu_item(selection, menu_name))
            self.grid.addWidget(label, pos * 2, 0)
            self.grid.addWidget(menu, pos * 2 + 1, 0)
        self.setCheckable(True)
        self.setChecked(False)

    def select_menu_item(self, selection, menu_name):
        """Changes config options based on dropdown menu selection"""
        self.dirs.settings.fp_last_used['ch_num'][self.menus[menu_name]['pos']] = selection
        self.signal.signal.emit()


class GUI_LabJackConfig(QtGui.QGroupBox):
    """Configure LabJack Channels and Frequencies"""
    def __init__(self, dirs):
        QtGui.QGroupBox.__init__(self)
        self.setTitle('LabJack')
        self.dirs = dirs
        self.grid = QtGui.QGridLayout()
        # Signals
        self.signal = GUI_CustomSignal()
        # Setup
        self.setup_buttons()
        self.update_btn_states()
        self.setLayout(self.grid)

    def setup_buttons(self):
        """Sets up check buttons for channel selection"""
        self.buttons = []
        for ch_num in range(14):
            row = ch_num // 5
            col = ch_num - (ch_num // 5) * 5
            name = 'AIN {}'.format(ch_num)
            btn = QtGui.QCheckBox(name)
            btn.clicked.connect(self.click_btn)
            self.grid.addWidget(btn, row, col)
            self.buttons.append(btn)

    def update_btn_states(self):
        """Updates entire array of buttons as indicated in self.dirs.settings"""
        checked = self.dirs.settings.quick_lj()[0]
        checked.sort()
        for btn in self.buttons: btn.setChecked(False)
        for btn in self.buttons:
            if self.buttons.index(btn) in checked:
                btn.setChecked(True)

    def click_btn(self):
        """Called when a button is toggled on or off"""
        checked = []
        for btn in self.buttons:
            if btn.isChecked():
                checked.append(self.buttons.index(btn))
        if len(checked) > 8:
            GUI_Message(msg='Cannot exceed 8 LabJack channels simultaneously!')
        else:
            self.dirs.settings.lj_last_used['ch_num'] = checked
            self.signal.signal.emit()
        self.update_btn_states()


class GUI_CameraDisplay(QtGui.QWidget):
    """Displays Camera Feed"""
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.readyQ = mp.Queue()
        array_dim = (240, 320)
        num_cmr = 2
        # We make tuples of (mp.Array, np.Array) that ref. the same underlying buffers

        m_arrays = (mp.Array('I', int(np.prod(array_dim)),
                             lock=mp.Lock()) for _ in range(num_cmr))
        self.arrays = [(m, np.frombuffer(m.get_obj(), dtype='I').reshape(array_dim))
                       for m in m_arrays]
        self.images = [QtGui.QImage(n.data, n.shape[1],
                                    n.shape[0], QtGui.QImage.Format_RGB32)
                       for m, n in self.arrays]
        self.labels = [QtGui.QLabel(self) for _ in self.arrays]

        self.procs = [mp.Process(target=self.frame_stream, args=(i, m, n))
                      for i, (m, n) in enumerate(self.arrays)]
        for p in self.procs:
            p.daemon = True

        columns = np.ceil(len(self.arrays) ** 0.5)
        vbox = QtGui.QGridLayout(self)
        for i, label in enumerate(self.labels):
            vbox.addWidget(label, i / columns, i % columns)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update)
        timer.start()

    def update(self):
        """Updates image pixel map"""
        i = self.readyQ.get()
        m, n = self.arrays[i]
        self.labels[i].setPixmap(QtGui.QPixmap.fromImage(self.images[i]))
        m.release()

    def frame_stream(self, array_ind, mp_array, np_array):
        """Stream Image Frames to Camera"""
        while True:
            mp_array.acquire()
            # Image Acquisition Method Below
            if array_ind % 2:
                for i, y in enumerate(np_array):
                    if i % 2:
                        y.fill(random.randrange(0x7f7f7f))
            else:
                for y in np_array:
                    y.fill(random.randrange(0xffffff))
            # Image Acquisition Ends
            self.readyQ.put(array_ind)
