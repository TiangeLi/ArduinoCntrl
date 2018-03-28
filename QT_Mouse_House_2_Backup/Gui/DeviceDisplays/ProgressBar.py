# coding=utf-8

"""Progress Bar to monitor experiment and arduino on/off status"""


import PyQt4.QtGui as qg
from Gui.MiscWidgets import GuiSimpleGroup, GuiArdBar, GuiTextWithAnim, GuiLineWithAnim
from Misc.CustomFunctions import format_secs

from QT_Mouse_House_2_Backup.Misc.Variables import *


class ProgressBar(qg.QGraphicsView):
    """Progress Bar Object"""
    def __init__(self, parent):
        super(ProgressBar, self).__init__()
        # Externally Coupled Objects
        self.dirs = DIRS
        self.parent = parent
        # Underlying Background Handler
        self.scene = qg.QGraphicsScene(self)
        self.scene.selectionChanged.connect(self.highlight_selection)
        # Render graphics and objects
        self.render_static_bg()
        self.init_dynamic_bg()
        self.init_anim_gfx_obj()
        self.render_dynamic_bg()
        # Animation Timer
        self.exp_start_time = qc.QTime()
        # Render scene and finish
        self.setScene(self.scene)
        self.setRenderHint(qg.QPainter.Antialiasing)
        self.setMinimumSize(1056, 288)
        self.setMaximumSize(1056, 288)

    # Graphics and Objects
    def render_static_bg(self):
        """Sets up the static backdrop graphics"""
        bg_group = GuiSimpleGroup()
        # Main Background Shapes
        bg_group.add(qg.QGraphicsRectItem(0, 0, 1052, 284), brush=qBlack)
        bg_group.add(qg.QGraphicsLineItem(0, 20, 1052, 20), pen=qWhite)
        bg_group.add(qg.QGraphicsLineItem(0, 40, 1052, 40), pen=qWhite)
        bg_group.add(qg.QGraphicsLineItem(0, 160, 1052, 160), pen=qWhite)
        bg_group.add(qg.QGraphicsLineItem(0, 260, 1052, 260), pen=qWhite)
        # Row Label - Backdrops
        bg_group.add(qg.QGraphicsRectItem(1000, 20, 15, 20), brush=qWhite)
        bg_group.add(qg.QGraphicsRectItem(1000, 40, 15, 120), brush=qWhite)
        bg_group.add(qg.QGraphicsRectItem(1000, 160, 15, 100), brush=qWhite)
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
        bg_group.add(qg.QGraphicsTextItem('PIN #'), color=qWhite, pos_x=1011, pos_y=1)
        bg_group.add(qg.QGraphicsTextItem('10'), color=qWhite, pos_x=1021, pos_y=21)
        bg_group.add(qg.QGraphicsTextItem('02'), color=qWhite, pos_x=1021, pos_y=41)
        bg_group.add(qg.QGraphicsTextItem('03'), color=qWhite, pos_x=1021, pos_y=61)
        bg_group.add(qg.QGraphicsTextItem('04'), color=qWhite, pos_x=1021, pos_y=81)
        bg_group.add(qg.QGraphicsTextItem('05'), color=qWhite, pos_x=1021, pos_y=101)
        bg_group.add(qg.QGraphicsTextItem('06'), color=qWhite, pos_x=1021, pos_y=121)
        bg_group.add(qg.QGraphicsTextItem('07'), color=qWhite, pos_x=1021, pos_y=141)
        bg_group.add(qg.QGraphicsTextItem('08'), color=qWhite, pos_x=1021, pos_y=161)
        bg_group.add(qg.QGraphicsTextItem('09'), color=qWhite, pos_x=1021, pos_y=181)
        bg_group.add(qg.QGraphicsTextItem('11'), color=qWhite, pos_x=1021, pos_y=201)
        bg_group.add(qg.QGraphicsTextItem('12'), color=qWhite, pos_x=1021, pos_y=221)
        bg_group.add(qg.QGraphicsTextItem('13'), color=qWhite, pos_x=1021, pos_y=241)
        # Add Background to Progress Bar Scene
        self.scene.addItem(bg_group)

    def init_dynamic_bg(self):
        """Sets up dynamic background object groups, to hold object items later on"""
        self.v_bars = GuiSimpleGroup()
        self.bar_times = GuiSimpleGroup()
        self.dynamic_bg_groups = [self.v_bars, self.bar_times]
        for group in self.dynamic_bg_groups:
            self.scene.addItem(group)

    def render_dynamic_bg(self):
        """Generates the background using setting configs from DIRS.settings.last_ard"""
        # First we check if we need to update total time depending on any new progbars added
        ttl_time = max([self.dirs.settings.ttl_time] + [cfg.time_off_ms for cfg in self.dirs.settings.last_ard.configs])
        self.dirs.settings.ttl_time = ttl_time
        #
        # todo: need to display new ttl_time in time_config_widget.text_entry.
        # Finally we set the background and update animation timers
        self.reset_dynamic_bg()
        self.set_vert_spacers()
        self.set_ard_bars()
        self.reset_timers_anims()

    def reset_dynamic_bg(self):
        """Resets old background elements before populating with new ones"""
        # Remove dynamic backdrop objects
        for group in self.dynamic_bg_groups:
            for item in group.childItems():
                group.removeFromGroup(item)
        # We also remove selectable arduino bar objects
        for item in self.ard_stim_bars():
            self.scene.removeItem(item)

    def set_vert_spacers(self):
        """Sets up dynamic vertical spacers; number and spacing depends on total time configured"""
        ms_time = self.dirs.settings.ttl_time
        gap_size = 5 + 5 * int(ms_time / 300000)
        num_spacers_float = float(ms_time / 1000) / gap_size
        num_spacers_int = int(round(num_spacers_float))
        pos_raw = 1000.0 / num_spacers_float
        # Generate Spacers
        for i in range(num_spacers_int):
            i += 1
            # Generic Object Pointers
            tiny_line = qg.QGraphicsLineItem(i * pos_raw, 260, i * pos_raw, 265)
            short_line = qg.QGraphicsLineItem(i * pos_raw, 20, i * pos_raw, 260)
            long_line = qg.QGraphicsLineItem(I * pos_raw, 20, i * pos_raw, 265)
            time_text = qg.QGraphicsTextItem(format_secs(gap_size * i))
            # Creation Parameters
            odd_spacer = (i % 2 != 0)
            even_spacer = (i % 2 == 0)
            final_spacer = (i == num_spacers_int)
            undershoot = (i * pos_raw < 1000)
            at_end_of_bar = (i * pos_raw == 1000)
            # Create Spacers based on Creation Parameters
            if odd_spacer:
                if (not final_spacer) or (final_spacer and undershoot):
                    self.v_bars.add(short_line, pen=qWhite)
                elif final_spacer and at_end_of_bar:
                    self.v_bars.add(tiny_line, pen=qWhite)
            elif even_spacer:
                if (not final_spacer) or (final_spacer and undershoot):
                    self.v_bars.add(long_line, pen=qWhite)
                    self.bar_times.add(time_text, pos_x=i * pos_raw - 20, pos_y=262, color=qWhite)
                elif final_spacer and at_end_of_bar:
                    self.v_bars.add(tiny_line, pen=qWhite)
                    self.bar_times.add(time_text, pos_x=i * pos_raw - 20, pos_y=262, color=qWhite)

    def set_ard_bars(self):
        """Creates graphics for arduino stimuli segments"""
        ms_time = self.dirs.settings.ttl_time
        cfg_src = self.dirs.settings.last_ard.configs
        # Create Bars
        for cfg in cfg_src:
            self.create_bar_from_ard_configs(cfg, ms_time)

    def create_bar_from_ard_configs(self, cfg, ms_time):
        """Reads arduino configs and creates into selectable GUI progbar objects"""
        # Physical dimensions
        start_pt = (float(cfg.time_on_ms) / ms_time) * 1000.0
        on_duration = (float(cfg.time_off_ms) / ms_time) * 1000.0 - start_pt
        # Tooltips
        tltp_start_time = format_secs(cfg.time_on_ms / 1000)
        tltp_off_time = format_secs(cfg.time_off_ms / 1000)
        tooltip = '{} - {}\n'.format(tltp_start_time, tltp_off_time)
        # Type specific settings
        if cfg.types == tone:
            y_pos = 20
            tooltip += '{} Hz'.format(cfg.freq)
        elif cfg.types == outp:
            y_pos = 40 + (pins(outp).index(cfg.pin)) * 20
            tooltip += 'Pin {}'.format(cfg.pin)
        elif cfg.types == pwm:
            freq = cfg.freq
            dc = cfg.duty_cycle
            ps = cfg.phase_shift
            y_pos = 160 + (pins(pwm).index(cfg.pin)) * 20
            tooltip += 'Pin {}\nFreq: {}Hz\nDuty Cycle: {}%\nPhase Shift: {}{}' \
                       ''.format(cfg.pin, freq, dc, ps, u'\u00b0')
        # Generate Bars and add to Graphics Scene
        bar = GuiArdBar(start_pt, y_pos, on_duration, 20, tooltip, config=cfg)
        self.scene.addItem(bar)

    # Animation
    def init_anim_gfx_obj(self):
        """Sets up graphics objects for timer and movable bar"""
        # Create Graphical Objects
        self.time_gfx = GuiTextWithAnim('00:00.000', color=qWhite, z_stack=1)
        self.bar_gfx = GuiLineWithAnim((0, 22, 0, 258), color=qRed, z_stack=1)
        self.scene.addItem(self.time_gfx)
        self.scene.addItem(self.bar_gfx)

    def reset_timers_anims(self):
        """Refreshes timers and animations with new parameters"""
        self.duration = self.dirs.settings.ttl_time
        self.time_gfx.reset_timers_anims(self.duration)
        self.bar_gfx.reset_timers_anims(self.duration)
        # Render new frames
        self.bar_gfx.timer.frameChanged[int].connect(self.advance_increment)
        for i in range(1000):
            self.time_gfx.anim.setPosAt(i / 1000.0, qc.QPointF(i, 0))
            self.bar_gfx.anim.setPosAt(i / 1000.0, qc.QPointF(i, 0))

    def advance_increment(self):
        """Called by self.bar_gfx.timer every time timer goes up by 1"""
        # Update Time
        ms_elapsed = self.exp_start_time.elapsed() / 1000.0
        ms_elapsed = format_secs(ms_elapsed, 'with_ms')
        self.time_gfx.setPlainText(ms_elapsed)
        # Make sure Progress bar booleans are correct
        if not self.bar_gfx.running:  # Bar runs entire duration (not text), so use as running marker
            self.bar_gfx.running = True
        if abs(self.bar_gfx.timer.currentFrame()) >= self.duration * 1000:
            self.bar_gfx.running = False
        # Move the Time Indicator by 1 increment
        if not self.time_gfx.running \
            and abs(self.bar_gfx.timer.currentFrame()) > self.duration * 31 \
                and not abs(self.bar_gfx.timer.currentFrame()) >= self.duration * 934:
            self.time_gfx.running = True
            self.time_gfx.timer.start()
        if abs(self.time_gfx.timer.currentFrame()) >= self.duration * 940:
            self.time_gfx.running = False
            self.time_gfx.timer.stop()

    # Selectable Objects and Operations
    def ard_stim_bars(self):
        """Returns list of selectable arduino segments"""
        return [item for item in self.scene.items() if isinstance(item, GuiArdBar)]

    def highlight_selection(self):
        """Highlight the selected object on our base scene"""
        # Reset any previous highlights
        for item in self.ard_stim_bars():
            item.setBrush(qYellow)
        # Highlight currently selected items
        [item.setBrush(qBlue) for item in self.scene.selectedItems()]
        # Set arduino config widget entries
        # todo: implement this

    def keyPressEvent(self, e):
        """Adds actions to certain keypresses"""
        # the DELETE or BACKSPACE keys will delete a arduino segment from both graphics and internal configs
        if e.key() in (qKey_del, qKey_backspace):
            self.delete_selected()

    def delete_selected(self):
        """Checks if delete request can be processed, and deletes item(s)"""
        # We only visually remove an item from the GUI scene if we can als remove its associated internal configs
        for item in self.scene.selectedItems():
            if item.config in self.dirs.settings.last_ard.configs:
                self.dirs.settings.last_ard.configs.remove(item.config)  # first remove configs associated with GUI item
        self.render_dynamic_bg()  # then reset the graphic items using the newly updated configs
        # This way, we are certain a visual deletion corresponds with a backend config deletion
        # Because the new GUI objects are built from scratch from the backend configs
        # We can therefore be certain we don't have orphaned/hidden configs still sending instructions to the arduino

    def set_ard_bars_selectable(self, selectable):
        """Sets bars to be selectable or not. Use during experiments (so configs aren't disturbed)"""
        for bar in self.ard_stim_bars():
            if selectable:
                bar.setFlag(qSelectable, enabled=True)
            elif not selectable:
                bar.setFlag(qSelectable, enabled=False)

    def reset_selection(self):
        """Resets selected abrs to be unselected"""
        self.set_ard_bars_selectable(selectable=False)
        self.set_ard_bars_selectable(selectable=True)

    # Turn on and off
    def start(self):
        """Starts the progress bar"""
        self.time_gfx.setPos(0, 0)
        self.bar_gfx.timer.start()
        self.exp_start_time.start()

    def stop(self):
        """Stops the progress bar"""
        self.time_gfx.timer.stop()
        self.bar_gfx.timer.stop()
        self.time_gfx.running = False
        self.bar_gfx.running = False
