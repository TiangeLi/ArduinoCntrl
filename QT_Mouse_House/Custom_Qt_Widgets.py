# coding=utf-8

"""Qt Widget Blocks for implementation into a QMainWindow"""

from copy import deepcopy
from Misc_Functions import *
from Custom_Qt_Tools import *


class GUI_ProgressBar(qg.QGraphicsView):
    """Progress Bar to Monitor Experiment and Arduino Status"""
    def __init__(self, dirs):
        qg.QGraphicsView.__init__(self)
        self.dirs = dirs
        self.start_time = qc.QTime()
        self.scene = qg.QGraphicsScene(self)
        # Initialize Objects
        self.init_static_background()
        self.init_dynamic_background()
        self.init_anim_gfx_objects()
        self.set_timers_and_anims()
        self.set_dynamic_background()
        # Experiment Running Booleans
        self.bar_gfx_running = False
        self.time_gfx_running = False
        # Setup Graphics Scene
        self.setScene(self.scene)
        self.setRenderHint(qg.QPainter.Antialiasing)
        self.setMaximumWidth(1054)
        self.setMaximumHeight(284)

    # -- Static Background -- #
    def init_static_background(self):
        """Sets up the static backdrop"""
        bg_group = GUI_SimpleGroup()
        # Main Background Shapes
        bg_group.add(qg.QGraphicsRectItem(0, 0, 1052, 280), brush=black)
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
        """Sets dynamic background to new data"""
        self.get_ard_data()
        self.set_vert_spacers()
        self.set_ard_bars()
        self.set_timers_and_anims()

    def get_ard_data(self, destroy=False, load=None):
        """Obtain Arduino Data from Saves"""
        if load:
            load = self.dirs.settings.ard_presets[load]
            self.dirs.settings.ard_last_used = deepcopy(load)
        if destroy:
            for group in self.dynamic_bg_groups:
                for item in group.childItems():
                    group.removeFromGroup(item)

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
        ms_elapsed = self.start_time.elapsed() / 1000.0
        ms_elapsed = format_secs(ms_elapsed, 'with_ms')
        self.time_gfx.setPlainText(ms_elapsed)
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
    def run_bar(self):
        """Starts Progress Bar"""
        self.time_gfx.setPos(0, 0)
        self.bar_gfx_timer.start()
        self.start_time.start()
