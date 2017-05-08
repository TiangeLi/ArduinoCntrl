# coding=utf-8

"""Names for commonly used variables"""


import PyQt4.QtGui as qg
import multiprocessing as mp


# Synchronization Message Headers
# General Start/Stop Headers
RUN_EXP_HEADER = '<run>'
EXP_END_HEADER = '<end>'
HARDSTOP_HEADER = '<hardstop>'
EXIT_HEADER = '<exit>'
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

# Camera Related Items
cmr_error_img = r'support_files/cam_error_exit.bmp'

# Arduino Names
packet = 'packet'

# GUI Pointers
# Exp. Configs
hh = 'hh'
mm = 'mm'
ss = 'ss'

# Synchronization Items
MASTER_DUMP_QUEUE = mp.Queue()
PROC_HANDLER_QUEUE = mp.Queue()
EXP_START_EVENT = mp.Event()

# Quick pointers to Qt specific objects
# Colors
black = qg.QColor(0, 0, 0)
white = qg.QColor(255, 255, 255)
yellow = qg.QColor(255, 255, 0)
blue = qg.QColor(0, 0, 255)
red = qg.QColor(255, 0, 0)
