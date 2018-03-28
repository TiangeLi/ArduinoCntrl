# coding=utf-8

"""Commonly used variables and objects across multiple modules"""

import multiprocessing as mp
import os

import PyQt4.QtCore as qc
import PyQt4.QtGui as qg

from DirsSettings.Directories import Directories

# Shared Device Variables
home_dir = 555
ljk_device = '<ljk_dev>'
ard_device = '<ard_dev>'
cmr_device = '<cmr_dev>'

# Arduino Related
tone = 'tone'
outp = 'output'
pwm = 'pwm'


def pins(types):
    """Return a list of arduino pins depending on type of pin requested"""
    if types == tone:
        return 10
    if types == outp:
        return list(range(2, 8))
    if types == pwm:
        output = list(range(8, 14))
        output.remove(10)
        return output


# LabJack Related


# Camera Related


# Concurrency Handling Related
MASTER_DUMP_QUEUE = mp.Queue()
PROC_HANDLER_QUEUE = mp.Queue()

# Var names for Misc. Functions
day = 'day'
time = 'time'
mins = 'min'
secs = 'sec'

# Directories and Saving
home_dir = os.path.expanduser('~')
DIRS = Directories()

# PyQt
# Layout
qAlignCenter = qc.Qt.AlignCenter
qStyleSunken = qg.QFrame.Sunken
qStylePanel = qg.QFrame.StyledPanel
# Colors
qBlack = qg.QColor(0, 0, 0)
qWhite = qg.QColor(255, 255, 255)
qYellow = qg.QColor(255, 255, 0)
qBlue = qg.QColor(0, 0, 255)
qRed = qg.QColor(255, 0, 0)
# Keypresses
qKey_k = qc.Qt.Key_K
qKey_del = qc.Qt.Key_Delete
qKey_backspace = qc.Qt.Key_Backspace
# Key Modifiers
qMod_shift = qc.Qt.ShiftModifier
qMod_cntrl = qc.Qt.ControlModifier
qMod_alt = qc.Qt.AltModifier
# Booleans
qSelectable = qg.QGraphicsItem.ItemIsSelectable
