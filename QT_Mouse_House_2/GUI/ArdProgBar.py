# coding=utf-8

"""Custom Widget for viewing and editing Arduino stimuli"""

from Misc.Names import *
from Misc.CustomFunctions import format_secs
from GUI.MiscWidgets import *


class GuiArdBar(qg.QGraphicsRectItem):
    """A Rectangle Item with custom implementation for deletable arduino segments"""
    def __init__(self, x, y, w, h, tooltip, data):
        super(GuiArdBar, self).__init__(x, y, w, h)
        self.setBrush(qYellow)
        self.setPen(qBlue)
        self.setToolTip(tooltip)
        self.setFlag(qSelectable, enabled=True)
        self.data = data
        self.visual_warning_stage = 0

    def visual_warning(self, times_to_flash=6):
        """Deploys a visual warning to indicate error to user"""
        # First we grab the correct base color depending if object is selected or not
        base_color = qBlue if self.isSelected() else qYellow
        # If we've reached the end of the sequence, return to base color and exit
        if self.visual_warning_stage == times_to_flash:
            self.setBrush(base_color)
            self.visual_warning_stage = 0
            return
        # Else we change colors depending on stage
        if self.visual_warning_stage % 2 == 0:
            self.setBrush(qRed)
        else:
            self.setBrush(base_color)
        # We then increment the stage and run the function again in 150ms
        self.visual_warning_stage += 1
        qc.QTimer.singleShot(150, lambda t=times_to_flash: self.visual_warning(t))


class GuiProgressBar(qg.QGraphicsView):
    """Main Progress Bar Widget for Monitoring Experiment and Arduino Status"""
    # Since we'll only have one instance of GuiProgressBar running, it's okay to make this signal a class variable
    # pyqtSignal for some reason does not work as an instance variable
    new_highlight_signal = qc.pyqtSignal(object, name='HighlightChangedSignal')
    ttl_time_updated_signal = qc.pyqtSignal(name='TotalTimeUpdatedSignal')

    def __init__(self, dirs, parent):
        super(GuiProgressBar, self).__init__()
        self.dirs = dirs
        self.parent = parent
        self.exp_start_time = qc.QTime()
        self.initialize()

    def initialize(self):
        """Sets up all required objects and containers"""
        self.init_scene()
        self.init_static_bg()
        self.init_dynamic_bg()
        self.init_anim_gfx_objects()
        self.set_progbar_scene()
        self.setScene(self.scene)
        self.setRenderHint(qg.QPainter.Antialiasing)
        self.setMinimumSize(1056, 288)
        self.setMaximumSize(1056, 288)

    # -- User Manipulatable Objects -- #
    @property
    def ard_stim_bars(self):
        """Returns a list of arduino stimulation prog bar segments currently on scene"""
        return (item for item in self.scene.items() if isinstance(item, GuiArdBar))

    def init_scene(self):
        """Sets up the Prog Bar Scene object"""
        def highlight_selected():
            """Highlights a selected ard_segment within the prog bar scene"""
            # Reset any previous highlights
            for item in self.ard_stim_bars:
                item.setBrush(qYellow)
            # Highlight any currently selected items
            selected = self.scene.selectedItems()
            for item in selected:
                item.setBrush(qBlue)
            # If we selected exactly 1 bar, we can emit a signal with the bar's attributes to other widgets
            if len(selected) == 1:
                self.new_highlight_signal.emit(selected[0].data)
            # If we selected any other number of bars, we need to reset the signal
            else:
                self.new_highlight_signal.emit(None)
        self.scene = qg.QGraphicsScene(self)
        self.scene.selectionChanged.connect(highlight_selected)

    def keyPressEvent(self, event):
        """Defines some keyboard commands for the progbar GUI"""
        # Delete or Backspace buttons will delete a selected progbar segment
        def delete_selection():
            """Checks if the selected items can be deleted, and deletes them"""
            configs = self.dirs.settings.last_ard.configs
            # We will visually remove an item from the GUI, ONLY IF we can remove its associated data first
            for item in self.scene.selectedItems():
                if item.data in configs:
                    configs.remove(item.data)  # Removes backend data associated with GUI object
            # We then use the updated configs to completely reset the progbar and its elements
            # This way, we ensure that what we show on the GUI is 100% representative of backend configurations
            self.set_progbar_scene()
        if event.key() in (qKey_del, qKey_backspace):
            delete_selection()

    def set_ard_bars_selectable(self, selectable):
        """Changes whether user is able to interact with arduino bars or not
        @selectable: boolean"""
        for bar in self.ard_stim_bars:
            bar.setFlag(qSelectable, enabled=selectable)

    def reset_selection(self):
        """Resets all selected objects to be unselected"""
        self.set_ard_bars_selectable(selectable=False)
        self.set_ard_bars_selectable(selectable=True)

    # -- Static Background -- #
    def init_static_bg(self):
        """Sets up the static backdrop"""
        group = GuiSimpleGroup()
        # Main background Shapes
        group.add(qg.QGraphicsRectItem(0, 0, 1052, 284), brush=qBlack)
        group.add(qg.QGraphicsLineItem(0, 20, 1052, 20), pen=qWhite)
        group.add(qg.QGraphicsLineItem(0, 40, 1052, 40), pen=qWhite)
        group.add(qg.QGraphicsLineItem(0, 160, 1052, 160), pen=qWhite)
        group.add(qg.QGraphicsLineItem(0, 260, 1052, 260), pen=qWhite)
        # Row Label - Backdrops
        group.add(qg.QGraphicsRectItem(1000, 20, 15, 20), brush=qWhite)
        group.add(qg.QGraphicsRectItem(1000, 40, 15, 120), brush=qWhite)
        group.add(qg.QGraphicsRectItem(1000, 160, 15, 100), brush=qWhite)
        # Row Label - Names
        group.add(qg.QGraphicsTextItem(u'\u266b'), pos_x=997, pos_y=13)
        group.add(qg.QGraphicsTextItem('S'), pos_x=999, pos_y=41)
        group.add(qg.QGraphicsTextItem('I'), pos_x=1002, pos_y=61)
        group.add(qg.QGraphicsTextItem('M'), pos_x=998, pos_y=81)
        group.add(qg.QGraphicsTextItem('P'), pos_x=999, pos_y=101)
        group.add(qg.QGraphicsTextItem('L'), pos_x=1000, pos_y=121)
        group.add(qg.QGraphicsTextItem('E'), pos_x=999, pos_y=141)
        group.add(qg.QGraphicsTextItem('P'), pos_x=999, pos_y=181)
        group.add(qg.QGraphicsTextItem('W'), pos_x=997, pos_y=201)
        group.add(qg.QGraphicsTextItem('M'), pos_x=998, pos_y=221)
        # Arduino Label - Pins
        group.add(qg.QGraphicsTextItem('PIN #'), color=qWhite, pos_x=1011, pos_y=1)
        group.add(qg.QGraphicsTextItem('10'), color=qWhite, pos_x=1021, pos_y=21)
        group.add(qg.QGraphicsTextItem('02'), color=qWhite, pos_x=1021, pos_y=41)
        group.add(qg.QGraphicsTextItem('03'), color=qWhite, pos_x=1021, pos_y=61)
        group.add(qg.QGraphicsTextItem('04'), color=qWhite, pos_x=1021, pos_y=81)
        group.add(qg.QGraphicsTextItem('05'), color=qWhite, pos_x=1021, pos_y=101)
        group.add(qg.QGraphicsTextItem('06'), color=qWhite, pos_x=1021, pos_y=121)
        group.add(qg.QGraphicsTextItem('07'), color=qWhite, pos_x=1021, pos_y=141)
        group.add(qg.QGraphicsTextItem('08'), color=qWhite, pos_x=1021, pos_y=161)
        group.add(qg.QGraphicsTextItem('09'), color=qWhite, pos_x=1021, pos_y=181)
        group.add(qg.QGraphicsTextItem('11'), color=qWhite, pos_x=1021, pos_y=201)
        group.add(qg.QGraphicsTextItem('12'), color=qWhite, pos_x=1021, pos_y=221)
        group.add(qg.QGraphicsTextItem('13'), color=qWhite, pos_x=1021, pos_y=241)
        # Add Background to Progress Bar Scene
        self.scene.addItem(group)

    # -- Dynamic Background -- #
    def init_dynamic_bg(self):
        """Sets up dynamic background objects"""
        self.vertical_spacers = GuiSimpleGroup()
        self.time_stamps = GuiSimpleGroup()
        self.dynamic_bg_groups = [self.vertical_spacers, self.time_stamps]
        for group in self.dynamic_bg_groups:
            self.scene.addItem(group)

    def set_dynamic_bg(self):
        """Renders dynamic background objects based on arduino settings"""
        ms_time = self.dirs.settings.ttl_time
        gap_size = 5 + 5 * int(ms_time / 300000)  # Factors into size of gaps between vertical spacers
        num_spacers = float(ms_time / 1000) / gap_size  # Number of vertical spacers
        raw_pos = 1000.0 / num_spacers  # Position of 1st spacer and real inter-spacer gap size
        # Generating Spacers
        # General Spacer Y1 and Y2 Params
        tiny_line = (260, 265)  # e.g. Line of length 5, y1=260, y2=265
        short_line = (20, 260)
        long_line = (20, 265)
        for i in range(int(round(num_spacers))):  # for each spacer i
            i += 1  # such that i is in [1, ..., num_spacers] instead of [0, ..., num_spacers - 1]
            # Reset Line Params and time stamp
            line_params = None
            time_stamp = None
            # -- Creation Rules -- #
            odd_spacer = (i % 2 != 0)
            even_spacer = (i % 2 == 0)
            final_spacer = (i == int(round(num_spacers)))
            undershoot = (i * raw_pos < 1000)
            at_end_of_bar = (i * raw_pos == 1000)
            # Get specific object parameters
            if odd_spacer:
                time_stamp = False
                if (not final_spacer) or (final_spacer and undershoot):
                    line_params = short_line
                elif final_spacer and at_end_of_bar:
                    line_params = tiny_line
            elif even_spacer:
                time_stamp = True
                if (not final_spacer) or (final_spacer and undershoot):
                    line_params = long_line
                elif final_spacer and at_end_of_bar:
                    line_params = tiny_line
            # Generate Dynamic Background based on creation params
            if line_params:
                vertical_spacer = qg.QGraphicsLineItem(i * raw_pos, line_params[0], i * raw_pos, line_params[1])
                self.vertical_spacers.add(vertical_spacer, pen=qWhite)
                if time_stamp:
                    time_text = qg.QGraphicsTextItem(format_secs(gap_size * i))
                    self.time_stamps.add(time_text, pos_x=(i * raw_pos - 20), pos_y=262, color=qWhite)

    # Interactable Arduino Stim Segments
    def set_ard_bars(self):
        """Creates visual indicators on progress bar for arduino stimuli"""
        ms_time = self.dirs.settings.ttl_time
        configs = self.dirs.settings.last_ard.configs
        def ard_bar(cfg, ms):
            """Reads one set of arduino instructions and generates a visual segment for progbar"""
            # Dimensions
            start_pt = (float(cfg.on_ms) / ms) * 1000.0
            on_duration = (float(cfg.off_ms) / ms) * 1000.0 - start_pt
            # Time Tooltips
            tltp_start_time = format_secs(cfg.on_ms / 1000)
            tltp_off_time = format_secs(cfg.off_ms / 1000)
            tooltip = '{} - {}\n'.format(tltp_start_time, tltp_off_time)
            # Type specific tooltips
            if cfg.types == TONE:
                y_pos = 20
                tooltip += '{} Hz'.format(cfg.freq)
            elif cfg.types == OUTP:
                y_pos = 40 + (OUTP_PIN.index(cfg.pin)) * 20
                tooltip += 'Pin {}'.format(cfg.pin)
            elif cfg.types == PWM:
                y_pos = 160 + (PWM_PINS.index(cfg.pin)) * 20
                tooltip += 'Pin {}\nFreq: {}Hz\nDuty Cycle: {}%\nPhase Shift: {}{}' \
                           ''.format(cfg.pin, cfg.freq, cfg.duty_cycle, cfg.phase_shift, u'\u00b0')
            return GuiArdBar(x=start_pt, y=y_pos, w=on_duration, h=20, tooltip=tooltip, data=cfg)
        # Generate Bars
        for config in configs:
            self.scene.addItem(ard_bar(cfg=config, ms=ms_time))

    # Animation Objects, Timers, Functions
    def init_anim_gfx_objects(self):
        """Sets up animated progress bar and timer text"""
        self.time_gfx = GuiTextWithAnim('00:00.000', qWhite, z_stack=1)
        self.bar_gfx = GuiLineWithAnim((0, 22, 0, 258), qRed, z_stack=1)
        self.scene.addItem(self.time_gfx)
        self.scene.addItem(self.bar_gfx)

    def set_timers_and_anims(self):
        """Sets duration and frames of progress bar animation"""
        self.duration = self.dirs.settings.ttl_time
        # Set up timers and animation objects
        self.time_gfx.reset_timers_anims(self.duration)
        self.bar_gfx.reset_timers_anims(self.duration)
        # Create animation frames
        self.bar_gfx.timer.frameChanged[int].connect(self.advance_frame)
        for i in range(1000):
            self.time_gfx.anim.setPosAt(i / 1000.0, qc.QPointF(i, 0))
            self.bar_gfx.anim.setPosAt(i / 1000.0, qc.QPointF(i, 0))

    def advance_frame(self):
        """Advances one frame of the animation each time the bar_gfx.timer increments"""
        # Update time
        ms_elapsed = self.exp_start_time.elapsed() / 1000.0
        ms_elapsed = format_secs(ms_elapsed, option='with_ms')
        self.time_gfx.setPlainText(ms_elapsed)
        # Make sure Progress Bar booleans are set correctly
        if not self.bar_gfx.running:  # Bar runs entire duration, text does not. use bar as running marker.
            self.bar_gfx.running = True
        if abs(self.bar_gfx.timer.currentFrame()) >= self.duration * 1000:
            self.bar_gfx.running = False
        # Animate by 1 frame
        if not self.time_gfx.running \
            and abs(self.bar_gfx.timer.currentFrame()) > self.duration * 31 \
                and not abs(self.bar_gfx.timer.currentFrame()) >= self.duration * 934:
            self.time_gfx.running = True
            self.time_gfx.timer.start()
        if abs(self.time_gfx.timer.currentFrame()) >= self.duration * 940:
            self.time_gfx.running = False
            self.time_gfx.timer.stop()

    def reset_progbar_scene(self):
        """Clears dynamic bg items and any remaining progbar segments"""
        # For non-selectable items, we can just clear out the groups they belong to
        for group in self.dynamic_bg_groups:
            for item in group.childItems():
                group.removeFromGroup(item)
        # Selectable items have individual identifiers, so we need to remove them one by one
        for item in self.ard_stim_bars:
            self.scene.removeItem(item)

    def set_progbar_scene(self):
        """Sets the background objects, arduino segments, and animations using arduino configs"""
        # First we check if we need to update the total time depending on new ard_bars added
        ttl_time = max([self.dirs.settings.ttl_time]
                       + [cfg.off_ms for cfg in self.dirs.settings.last_ard.configs])
        self.dirs.settings.ttl_time = ttl_time
        self.ttl_time_updated_signal.emit()  # We let other widgets know that we have updated total time
        # Then we set the scene
        self.reset_progbar_scene()
        self.set_dynamic_bg()
        self.set_ard_bars()
        self.set_timers_and_anims()

    # On/Off Operations
    def start(self):
        """Starts Progress Bar"""
        self.time_gfx.setPos(0, 0)
        self.bar_gfx.timer.start()
        self.exp_start_time.start()

    def stop(self):
        """Stops Progress Bar"""
        self.time_gfx.timer.stop()
        self.bar_gfx.timer.stop()
        self.bar_gfx.running = False
        self.time_gfx.running = False
