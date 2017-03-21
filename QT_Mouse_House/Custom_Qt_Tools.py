# coding=utf-8

"""Re-implementations of certain Qt widgets to include custom functions"""


import PyQt4.QtGui as qg
import PyQt4.QtCore as qc


# Quick pointers to Qt specific objects
# Colors
black = qg.QColor(0, 0, 0)
white = qg.QColor(255, 255, 255)
yellow = qg.QColor(255, 255, 0)
blue = qg.QColor(0, 0, 255)
red = qg.QColor(255, 0, 0)


class GUI_SimpleGroup(qg.QGraphicsItemGroup):
    """Simplifies adding unnamed Qt Items to a group"""
    def __init__(self):
        qg.QGraphicsItemGroup.__init__(self)

    def add(self, item,
            pos_x=None, pos_y=None,
            pen=None, brush=None,
            color=None, tooltip=None):
        """Adds a new item with specified attributes"""
        self.addToGroup(item)
        if pos_x and pos_y: item.setPos(pos_x, pos_y)
        if pen: item.setPen(pen)
        if brush: item.setBrush(brush)
        if color: item.setDefaultTextColor(color)
        if tooltip: item.setToolTip(tooltip)
