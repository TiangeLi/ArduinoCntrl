# coding=utf-8

"""Custom implementations of some widgets to provide additional functionality"""

import PyQt4.QtCore as qc
import PyQt4.QtGui as qg
import numpy as np
import pyqtgraph as pg

from QT_Mouse_House_2_Backup.Misc.Variables import *


# General Reimplementations
class ql(qg.QLabel):
    """Reimplements QLabel to quickly setup a label with various parameters"""
    def __init__(self, text, align=None, style=None):
        super(ql, self).__init__(text)
        if align:
            self.setAlignment(align)
        if style:
            self.setFrameStyle(style)


class qw(qg.QWidget):
    """Reimplements QWidget to include some commonly used functions for convenience"""
    def __init__(self, parent=None):
        super(qw, self).__init__(parent)
        # Interfacing with other modules and objects
        self.dirs = DIRS
        # Basic Layout
        self.grid = qgridlayout()
        self.setLayout(self.grid)


# Organization
class GuiSimpleGroup(qg.QGraphicsItemGroup):
    """Simplifies adding unnamed Qt items to a shared group"""
    def __init__(self, selectable=False):
        super(GuiSimpleGroup, self).__init__()
        if selectable:
            self.setFlag(qg.QGraphicsItem.ItemIsSelectable, enabled=True)

    def add(self, item, pos_x=None, pos_y=None, pen=None, brush=None, color=None, tooltip=None, selectable=False):
        """Adds a new item with specifiable attributes"""
        self.addToGroup(item)
        if pos_x and pos_y: item.setPos(pos_x, pos_y)
        if pen: item.setPen(pen)
        if brush: item.setBrush(brush)
        if color: item.setDefaultTextColor(color)
        if tooltip: item.setToolTip(tooltip)
        if selectable: item.setFlag(qg.QGraphicsItemGroup.ItemIsSelectable, enabled=True)


# Custom Entry Types
class GuiEntryWithWarning(qg.QLineEdit):
    """A line entry with a triggerable visual warning"""
    def __init__(self, default_text=''):
        super(GuiEntryWithWarning, self).__init__()
        self.visual_warning_stage = 0
        if default_text:
            self.setText(default_text)

    def visual_warning(self, times_to_flash=3):
        """Triggers several flashes from white to red, num defined by times_to_flash"""
        r = 'background-color: rgb(255, 0, 0)'
        w = 'background-color: rgb(255, 255, 255)'
        if self.visual_warning_stage == times_to_flash:
            self.setStyleSheet(w)
            self.visual_warning_stage = 0
            return
        if self.visual_warning_stage % 2 == 0:
            self.setStyleSheet(r)
        else:
            self.setStyleSheet(w)
        self.visual_warning_stage += 1
        qc.QTimer.singleShot(150, lambda t=times_to_flash: self.visual_warning(t))


class GuiIntOnlyEntry(GuiEntryWithWarning):
    """An entry that takes only integers"""
    def __init__(self, max_digits=None, default_text=''):
        super(GuiIntOnlyEntry, self).__init__(default_text)
        self.max_digits = max_digits
        self.last_valid_entry = default_text
        self.min, self.max = None, None
        self.initialize()

    def initialize(self):
        """Sets up entry conditions and connects signals/slots"""
        if self.max_digits:
            self.setMaxLength(self.max_digits)
        self.textEdited.connect(self.check_text_edit)

    def check_text_edit(self):
        """Checks that entries are valid"""
        # Check if we entered a space before the text
        if self.text().startswith(' '):
            self.setText(self.last_valid_entry)
            self.setCursorPosition(0)
        # Main check
        text = self.text().strip()
        if not text:
            self.last_valid_entry = ''
            pos = 0
        else:
            try:
                # did we input a valid integer?
                int(text)
            except ValueError:
                # if not, we revert to entry before it was invalid
                pos = self.cursorPosition() - 1
            else:
                # if valid integer, we update the last valid data
                self.last_valid_entry = text
                pos = self.cursorPosition()
                # we check if our valid integer is beyond the min/max bounds we set
                if self.min and int(text) < self.min:
                    self.last_valid_entry = str(self.min)
                elif self.max and int(text) > self.max:
                    self.last_valid_entry = str(self.max)
        self.setText(self.last_valid_entry)
        self.setCursorPosition(pos)

    def set_min_max_value(self, minimum, maximum):
        """sets the min/max values of the entry"""
        self.min = minimum
        self.max = maximum


# Custom Layout Types
class qgriddedframe(qg.QFrame):
    """Adds a convenient grid to use as layout on Frames"""
    def __init__(self):
        super(qgriddedframe, self).__init__()
        self.grid = qgridlayout()
        self.setLayout(self.grid)


class qgriddedgroupbox(qg.QGroupBox):
    """Adds a convenient grid to use as layout on Group Boxes"""
    def __init__(self, name):
        super(qgriddedgroupbox, self).__init__(name)
        self.grid = qgridlayout()
        self.setLayout(self.grid)


class qgridlayout(qg.QGridLayout):
    """Reimplements QGroupBox to add some new layout methods"""
    def __init__(self):
        super(qgridlayout, self).__init__()

    def add_arrayed_layout(self, array):
        """Quickly add PyQt Widgets to a given grid
        in an array form instead of manually entering numbers
        Ex. Array Input:
        [
        ['', A, '', '', ''],
        ['', '', B, B, ''],
        ['', C, '', D, ''],
        ['', C, '', '', D]
        ]  --> we only need define the corner points (e.g. for widget 'D')
        Ex. Equivalent addWidget commands:
        grid.addWidget(A, 0, 1)
        grid.addWidget(B, 1, 2, 1, 2)
        grid.addWidget(C, 2, 1, 2, 1)
        grid.addWidget(D, 2, 3, 2, 2)
        """
        # First we generate a series of Widget:(coordinate) pairs
        widgets = {widget: [] for row in array for widget in row if widget}
        [widgets[widget].append((row, col)) for row, content in enumerate(array)
         for col, w in enumerate(content) for widget in widgets if w == widget]
        # For any widget with corner coordinates, we combine them into (row, col, row_len, col_len) form
        for widget in widgets:
            # We find the top left corner of each widget
            corner = min(widgets[widget])
            if len(widgets[widget]) > 1:
                # We find the widget length and width. np.add(1,1) compensates for 0-indexing when generating size.
                size = tuple(np.add(np.subtract(max(widgets[widget]), corner), (1, 1)))
                widgets[widget] = (widget, corner[0], corner[1], size[0], size[1])
            else:
                widgets[widget] = (widget, corner[0], corner[1])
            # Finally, we grid everything
            self.addWidget(*widgets[widget])


# Custom Graphics
class GuiArdBar(qg.QGraphicsRectItem):
    """Creates a Rectangle Item with attributes for selectable/deletable visual arduino segments"""
    def __init__(self, x, y, w, h, tooltip, config):
        super(GuiArdBar, self).__init__(x, y, w, h)
        self.setBrush(qYellow)
        self.setPen(qBlue)
        self.setToolTip(tooltip)
        self.setFlag(qg.QGraphicsItem.ItemIsSelectable, enabled=True)
        self.config = config
        self.visual_warning_stage = 0

    def visual_warning(self, times_to_flash=6):
        """Flashes a warning to indicate to user that an error exists"""
        if self.visual_warning_stage == times_to_flash:
            if self.isSelected():
                self.setBrush(qBlue)
            else:
                self.setBrush(qYellow)
            self.visual_warning_stage = 0
            return
        if self.visual_warning_stage % 2 == 0:
            self.setBrush(qRed)
        else:
            self.setBrush(qYellow)
        self.visual_warning_stage += 1
        qc.QTimer.singleShot(150, lambda t=times_to_flash: self.visual_warning(t))


class GuiMessage(qg.QMessageBox):
    """Popup Message with Buttons"""
    def __init__(self, msg, title='Warning', icon=qg.QMessageBox.Warning, btns=qg.QMessageBox.Close):
        super(GuiMessage, self).__init__()
        self.setText(msg)
        self.setWindowTitle(title)
        self.setIcon(icon)
        self.setStandardButtons(btns)
        self.exec_()


class GuiSinglePlot(pg.PlotWidget):
    """Plots a live scrolling graph, updates using data from provided source"""
    def __init__(self, color):
        super(GuiSinglePlot, self).__init__()
        self.color = color
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)
        self.showAxis('left', True)
        self.showAxis('bottom', False)
        self.setLimits(minYRange=2)
        self.setBackgroundBrush(qWhite)
        self.initialize()

    def initialize(self):
        """Sets up the Graphing Object"""
        self.data = np.zeros(shape=500)
        self.curve = self.getPlotItem().plot(self.data, pen=self.color)
        self.curve.setData(self.data)

    def graph_update(self, new_point):
        """Updates graph once"""
        self.data[:-1] = self.data[1:]
        self.data[-1] = new_point
        self.curve.setData(self.data)


class GuiObjectWithAnim(object):
    """Object with Qt Animation Properties"""
    def __init__(self, parent_obj):
        self.parent_obj = parent_obj
        # Animation Boolean
        self.running = False

    def reset_timers_anims(self, duration):
        """Resets timers and animations with new durations"""
        # Timer
        self.timer = qc.QTimeLine(duration)
        self.timer.setCurveShape(qc.QTimeLine.LinearCurve)
        self.timer.setFrameRange(0, duration * 1000)
        # Animation Object
        self.anim = qg.QGraphicsItemAnimation()
        self.anim.setItem(self.parent_obj)
        self.anim.setTimeLine(self.timer)


class GuiTextWithAnim(qg.QGraphicsTextItem, GuiObjectWithAnim):
    """Qt Text Object with Animation Properties"""
    def __init__(self, text, color, z_stack):
        qg.QGraphicsTextItem.__init__(self, text)
        GuiObjectWithAnim.__init__(self, parent_obj=self)
        self.setDefaultTextColor(color)
        self.setZValue(z_stack)


class GuiLineWithAnim(qg.QGraphicsLineItem, GuiObjectWithAnim):
    """Qt Line Object with Animation Properties"""
    def __init__(self, dimensions, color, z_stack):
        qg.QGraphicsLineItem.__init__(self, *dimensions)
        GuiObjectWithAnim.__init__(self, parent_obj=self)
        self.setPen(color)
        self.setZValue(z_stack)
