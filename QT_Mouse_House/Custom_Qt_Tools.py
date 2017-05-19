# coding=utf-8

"""Re-implementations of certain Qt widgets to include custom functions"""


from Names import *
import PyQt4.QtGui as qg
import PyQt4.QtCore as qc
import pyqtgraph as pg
import numpy as np


class GUI_SimpleGroup(qg.QGraphicsItemGroup):
    """Simplifies adding unnamed Qt Items to a group"""
    def __init__(self, selectable=False):
        qg.QGraphicsItemGroup.__init__(self)
        if selectable: self.setFlag(qg.QGraphicsItem.ItemIsSelectable, enabled=True)

    def add(self, item,
            pos_x=None, pos_y=None,
            pen=None, brush=None,
            color=None, tooltip=None,
            selectable=False):
        """Adds a new item with specified attributes"""
        self.addToGroup(item)
        if pos_x and pos_y: item.setPos(pos_x, pos_y)
        if pen: item.setPen(pen)
        if brush: item.setBrush(brush)
        if color: item.setDefaultTextColor(color)
        if tooltip: item.setToolTip(tooltip)
        if selectable: item.setFlag(qg.QGraphicsItem.ItemIsSelectable, enabled=True)


class GUI_ArdBar(qg.QGraphicsRectItem):
    """Creates a Rectangle Item with custom implementation for deletable arduino bars"""
    def __init__(self, x, y, w, h, tooltip, data):
        qg.QGraphicsRectItem.__init__(self, x, y, w, h)
        self.setBrush(yellow)
        self.setPen(blue)
        self.setToolTip(tooltip)
        self.setFlag(qg.QGraphicsItem.ItemIsSelectable, enabled=True)
        self.data = data


class GUI_Message(qg.QMessageBox):
    """Quick popup message with buttons"""
    def __init__(self, msg, title='Warning', icon=qg.QMessageBox.Warning,
                 btns=qg.QMessageBox.Close):
        qg.QMessageBox.__init__(self)
        self.setIcon(icon)
        self.setWindowTitle(title)
        self.setText(msg)
        self.setStandardButtons(btns)
        self.exec_()


class GUI_IntOnlyEntry(qg.QLineEdit):
    """An entry that takes only integers"""
    def __init__(self, max_digits=None, default_txt=''):
        qg.QLineEdit.__init__(self)
        self.max_digis = max_digits
        self.last_valid_data = default_txt
        self.visual_warning_stage = 0
        self.initialize()

    def initialize(self):
        """Sets up entry conditions and connects signal/slots"""
        if self.max_digis:
            self.setMaxLength(self.max_digis)
        self.textEdited.connect(self.check_text_edit)

    def check_text_edit(self):
        """Checks that entries are valid"""
        # Check if we entered a space before the text
        if self.text().startswith(' '):
            self.setText(self.last_valid_data)
            self.setCursorPosition(0)
        # Main check
        text = self.text().strip()
        if text == '':
            self.last_valid_data = ''
            pos = 0
        else:
            try:
                # did we input a valid integer?
                int(text)
            except ValueError:
                # if not, we revert to entry before it was invalid
                pos = self.cursorPosition() - 1
            else:
                # else we update the last valid data
                self.last_valid_data = text
                pos = self.cursorPosition()
        self.setText(self.last_valid_data)
        self.setCursorPosition(pos)

    def visual_warning(self, times_to_flash=3):
        """Flashes a visual warning indicating to users that entry is invalid"""
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


class GUI_EntryWithWarning(qg.QLineEdit):
    """An entry with a visual warning"""
    def __init__(self):
        qg.QLineEdit.__init__(self)
        self.visual_warning_stage = 0

    def visual_warning(self, times_to_flash=3):
        """Flashes a visual warning indicating to users that entry is invalid"""
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


class GUI_SinglePlot(pg.PlotWidget):
    """Plots a live scrolling graph updating using data from a provided source"""
    def __init__(self, color):
        pg.PlotWidget.__init__(self)
        self.color = color
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)
        self.showAxis('left', False)
        self.showAxis('bottom', False)
        self.setBackgroundBrush(white)
        self.init_plotter()

    def init_plotter(self):
        """Initialize the graphing object"""
        self.data = np.zeros(shape=500)
        self.curve = self.getPlotItem().plot(self.data, pen=self.color)
        self.update_timer = qc.QTimer(self)
        self.update_timer.timeout.connect(self.graph_update)
        self.update_timer.start(50)

    def graph_update(self):
        """Updates the graph once"""
        self.data[:-1] = self.data[1:]
        self.data[-1] = np.random.normal()
        self.curve.setData(self.data)
