# coding=utf-8

"""Commonly used variables and names from various modules in easier to understand names"""

import os
import PyQt4.QtGui as qg
import PyQt4.QtCore as qc
import multiprocessing as mp


# Forbidden Chars that cannot be used in file naming
FORBIDDEN_CHARS = ['<', '>', '*', '|', '?', '"', '/', ':', '\\']

# Var names for Misc. Functions
DAY = 'day'
TIME = 'time'
HOUR = 'Hour'
MINS = 'Mins'
SECS = 'Secs'

# Devices
ARDUINO = 'arduino'
CAMERAS = 'cameras'
FIREFLY_CAMERA = 'PTGrey FireFly'
MINIMIC_CAMERA = 'Mini Microscope'


# Arduino Related
FREQ = 'freq'
CHANNEL = 'channel'
TONE = 'tone'
OUTP = 'output'
PWM = 'pwm'
TONE_PIN = 10
OUTP_PIN = list(range(2, 8))
PWM_PINS = list(range(8, 14))
PWM_PINS.remove(10)

# Directories and Saving
HOME_DIR = os.path.expanduser('~')

# Concurrency
# Multiprocessing
MASTER_DUMP_QUEUE = mp.Queue()
PROC_HANDLER_QUEUE = mp.Queue()
EXP_START_EVENT = mp.Event()
# Queue Commands
CMD_START = 'cmd_start'
CMD_STOP = 'cmd_stop'
CMD_EXIT = 'cmd_exit'
CMD_SET_TIME = 'cmd_set_time'
CMD_SET_DIRS = 'cmd_set_dirs'
CMD_CHECK_CONN = 'cmd_check_connection'
# Queue Messages
MSG_RECEIVED = 'msg_received'
MSG_STARTED = 'msg_started'
MSG_FINISHED = 'msg_finished'
MSG_ERROR = 'msg_error'

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
# Background Colors
qBgRed = 'background-color: rgb(255, 0, 0)'
qBgWhite = 'background-color: rgb(255, 255, 255)'
qBgCyan = 'background-color: cyan'
qBgOrange = 'background-color: orange'
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
# Buttons
qBtnNo = qg.QMessageBox.No
qBtnYes = qg.QMessageBox.Yes
qBtnClose = qg.QMessageBox.Close
