# coding=utf-8

"""Names for commonly used variables"""


import PyQt4.QtGui as qg
import PyQt4.QtCore as qc
import multiprocessing as mp


# Synchronization Message Headers
# General Start/Stop Headers
RUN_EXP_HEADER = '<run>'
EXP_STARTED_HEADER = '<started>'
EXP_END_HEADER = '<end>'
HARDSTOP_HEADER = '<hardstop>'
EXIT_HEADER = '<exit>'
# Operation Headers
DIR_TO_USE_HEADER = '<dir_to_use>'
TTL_TIME_HEADER = '<ttl_time>'
# General Device Headers
DEVICE_CHECK_CONN = '<chk_conn>'
FAILED_INIT_HEADER = '<fail_init>'


# Camera Headers
CAMERA_READY = '<cmr_rdy>'
CMR_REC_FALSE = '<cmr_rec_f>'
CMR_ERROR_EXIT = '<cmr_err_exit>'
# Camera Types
FireFly_Camera = 'FireFly Camera'
Mini_Microscope = 'Mini Microscope'


# General Device Names
camera = 'CAMERA'
arduino = 'ARDUINO'
labjack = 'LABJACK'
# Message Headers
LJMSG = '<lj_msg>'
ARDMSG = '<ard_msg>'
CMRMSG = '<cmr_msg>'


# Arduino Parameters
tone = 'Tone'
output = 'Output'
pwm = 'PWM'
# Pins
tone_pin = 10
output_pins = list(range(2, 8))
pwm_pins = list(range(8, 14))
pwm_pins.remove(10)
# Headers
ard_systime_hdr = '<L'
ard_setup_hdr = '<BBLHHH'
ard_tone_hdr = '<LLH'
ard_output_hdr = '<LB'
ard_pwm_hdr = '<LLLfBBf'
# Defaults
default_phaseshift = 0
default_dutycycle = 50


# LabJack Headers
LJ_ERROR_EXIT = '<lj_err_exit>'
LJ_READY = '<lj_ready>'
LJ_REC_FALSE = '<lj_rec_false>'
LJ_CONFIG = '<lj_config>'
# Other settings
lj_color_scheme = [(51, 204, 153), (51, 179, 204),
                   (153, 51, 204), (216, 100, 239),
                   (179, 204, 51), (204, 153, 51),
                   (204, 77, 51), (102, 204, 51)]


# GUI Pointers
# Exp. Configs
hh = 'hh'
mm = 'mm'
ss = 'ss'

# Forbidden Characters (Cannot include in file names)
FORBIDDEN_CHARS = ['<', '>', '*', '|', '?', '"', '/', ':', '\\']

# Synchronization Items
MASTER_DUMP_QUEUE = mp.Queue()
PROC_HANDLER_QUEUE = mp.Queue()
EXP_START_EVENT = mp.Event()
# Pipe names
LJ_PIPE_MAIN_NAME = '<lj_pipe_main_name>'

# Quick pointers to Qt specific objects
# Key Sequences
nuke_keys = qg.QKeySequence(qc.Qt.CTRL + qc.Qt.SHIFT + qc.Qt.Key_K)
# Colors
black = qg.QColor(0, 0, 0)
white = qg.QColor(255, 255, 255)
yellow = qg.QColor(255, 255, 0)
blue = qg.QColor(0, 0, 255)
red = qg.QColor(255, 0, 0)
# Text Metrics
qt_text_metrics = qg.QFontMetrics(qg.QApplication.font())

# Misc. Names
CONVERTED = '<cnvrt>'
