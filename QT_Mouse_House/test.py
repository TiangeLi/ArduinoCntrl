#!/usr/bin/env python

import multiprocessing as mp
import random
import sys

import numpy as np
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class GUI_CameraDisplay(QWidget):
    """Displays Camera Feed"""
    def __init__(self):
        QWidget.__init__(self)
        self.readyQ = mp.Queue()
        array_dim = (240, 320)
        num_cmr = 2
        # We make tuples of (mp.Array, np.Array) that ref. the same underlying buffers

        m_arrays = (mp.Array('I', int(np.prod(array_dim)),
                             lock=mp.Lock()) for _ in range(num_cmr))
        self.arrays = [(m, np.frombuffer(m.get_obj(), dtype='I').reshape(array_dim))
                       for m in m_arrays]
        self.images = [QImage(n.data, n.shape[1],
                                    n.shape[0], QImage.Format_RGB32)
                       for m, n in self.arrays]
        self.labels = [QLabel(self) for _ in self.arrays]

        self.procs = [mp.Process(target=self.frame_stream, args=(i, m, n))
                      for i, (m, n) in enumerate(self.arrays)]
        for pr in self.procs:
            pr.daemon = True

        columns = np.ceil(len(self.arrays) ** 0.5)
        vbox = QGridLayout(self)
        for i, label in enumerate(self.labels):
            vbox.addWidget(label, i / columns, i % columns)
        timer = QTimer(self)
        timer.timeout.connect(self.update)
        timer.start()

    def update(self):
        """Updates image pixel map"""
        i = self.readyQ.get()
        m, n = self.arrays[i]
        self.labels[i].setPixmap(QPixmap.fromImage(self.images[i]))
        m.release()

    def frame_stream(self, array_ind, mp_array, np_array):
        """Stream Image Frames to Camera"""
        while True:
            mp_array.acquire()
            # Image Acquisition Method Below
            if array_ind % 2:
                for i, y in enumerate(np_array):
                    if i % 2:
                        y.fill(random.randrange(0x7f7f7f))
            else:
                for y in np_array:
                    y.fill(random.randrange(0xffffff))
            # Image Acquisition Ends
            self.readyQ.put(array_ind)

    def begin(self):
        [proc.start() for proc in self.procs]

if __name__ == '__main__':
    mp.freeze_support()

    app = QApplication(sys.argv)
    main_window = QWidget()
    grid = QGridLayout()


    cmr = GUI_CameraDisplay()
    grid.addWidget(cmr, 0, 0)
    main_window.setLayout(grid)
    main_window.show()
    cmr.begin()

    app.exec_()

