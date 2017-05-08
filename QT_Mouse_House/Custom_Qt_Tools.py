# coding=utf-8

"""Re-implementations of certain Qt widgets to include custom functions"""


from Names import *
import PyQt4.QtGui as qg
import PyQt4.QtCore as qc


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
