import pyximea as xi
import os
import sys


dnull = open(os.devnull, 'w')
s = sys.stderr
sys.stderr = dnull


try:
    cam = xi.Xi_Camera(DevID=1)
    cam.get_image()
    cam.close()
    print('good')
except xi.ximea.XI_Error:
    print('bad')


sys.stderr = s
dnull.close()