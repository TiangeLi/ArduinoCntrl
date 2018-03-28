# coding=utf-8


import cv2
import numpy as np
import PyQt4.QtCore as qc
import PyQt4.QtGui as qg

class Camera(object):
    """Source Video"""
    def __init__(self):
        vid = r"C:\Users\Tiange\Desktop\trial1_00.avi"
        self.vid = cv2.VideoCapture(vid)

    def iterator(self):
        """iterator"""
        _, f = self.vid.read()
        while f is not None:
            yield f.astype(float)[..., 1]
            _, f = self.vid.read()


class GUI(qg.QLabel):
    """sd"""
    def __init__(self):
        super(GUI, self).__init__()
        self.tracker = Tracker()
        coord, img = self.tracker.track()
        self.setMaximumHeight(img.shape[0])
        self.setMinimumHeight(img.shape[0])
        self.setMaximumWidth(img.shape[1])
        self.setMaximumWidth(img.shape[1])
        self.bounds = []
        self.set_bounds = False
        timer = qc.QTimer(self)
        timer.timeout.connect(self.new_frame)
        timer.start(33)

    def new_frame(self):
        coord, img = self.tracker.track()
        #print(coord)
        img = qg.QImage(img.data, img.shape[1], img.shape[0], qg.QImage.Format_RGB888)
        self.setPixmap(qg.QPixmap.fromImage(img))

    def create_bounds(self):
        self.set_bounds = True
        self.bounds = []
        self.tracker.bounding_coords = None, None

    def mousePressEvent(self, qevent):
        if self.set_bounds:
            print(len(self.bounds))
            if len(self.bounds) < 2:
                self.bounds.append((qevent.x(), qevent.y()))
            if len(self.bounds) == 2:
                self.tracker.bounding_coords = self.bounds
                self.set_bounds = False
        print(self.bounds)




class Tracker(object):
    def __init__(self):
        self.cam = Camera()
        self.get_bg()
        self.stim=False
        self.bounding_coords = None, None, None, None
        #self.guass = np.random.multivariate_normal([120, 120], [[1000, 0], [1, 1000]], 10)

    def get_bg(self, num=5, accum_fn=np.mean):
        bg = np.array([next(self.cam.iterator()) for i in range(num)])
        self.bg = accum_fn(bg, axis=0)

    def track(self, thresh=-50, targ=550.0, open_rad=4, debug=False):
        kernel = np.zeros((open_rad, open_rad))
        c = open_rad / 2.
        for i in range(open_rad):
            for j in range(open_rad):
                if (i - c) ** 2 + (j - c) ** 2 <= open_rad ** 2:
                    kernel[i, j] = 1

        # use next() for iteration instead of a for loop, since we only loop once per call on track() -> using return
        # todo: above ^^^
        for frame in self.cam.iterator():
            diff = frame - self.bg
            th = (diff < thresh).astype("uint8") * 255
            seg = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)
            seg = seg.astype("uint8")
            _, contours, hierarchy = cv2.findContours(seg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                disp_frame = frame.copy().astype("uint8")
                disp_frame = np.dstack([disp_frame, disp_frame, disp_frame])
                #for x, y in self.guass:
                 #   x = int(x)
                  #  y = int(y)
                   # cv2.circle(disp_frame, (x, y), 3, (255, 255, 255), thickness=-1)

                if all(self.bounding_coords):
                    for coords in self.bounding_coords:
                        cv2.circle(disp_frame, coords, 3, (255, 255, 255), thickness=-1)
                    cv2.rectangle(disp_frame, self.bounding_coords[0], self.bounding_coords[1], (255,255,255))
                    coord2 = (int(np.mean([self.bounding_coords[0][0], self.bounding_coords[1][0]])),
                              int(np.mean([self.bounding_coords[0][1], self.bounding_coords[1][1]])))
                    cv2.rectangle(disp_frame, self.bounding_coords[0], coord2, (255, 255, 255))



                return (0, 0), disp_frame

            # select contour
            contour_area = np.array([cv2.contourArea(c) for c in contours])
            contour_area = np.abs(contour_area - targ)
            select_contour = np.argmin(contour_area)

            moments = cv2.moments(contours[select_contour])
            cx = int(moments['m10'] / moments['m00'])
            cy = int(moments['m01'] / moments['m00'])

            disp_frame = frame.copy().astype("uint8")
            disp_frame = np.dstack([disp_frame, disp_frame, disp_frame])
            cv2.drawContours(disp_frame, contours, select_contour,
                             (0, 255, 0), 1)
            cv2.circle(disp_frame, (cx, cy), 3, (0, 0, 255), thickness=-1)
            cv2.rectangle(disp_frame, (20, 20), (200, 200), (0, 255, 0), thickness=2)
            if 20 < cx < 200 and 20 < cy < 200:
                self.stim=True
                cv2.putText(disp_frame, 'stim', org=(cx, cy), fontFace=cv2.FONT_HERSHEY_COMPLEX,
                            fontScale=0.5,
                            color=(0, 255, 0))
            else:
                self.stim=False
                cv2.putText(disp_frame, 'no stim', org=(cx, cy), fontFace=cv2.FONT_HERSHEY_COMPLEX, fontScale=0.5,
                        color=(255, 0, 0))
            if all(self.bounding_coords):
                for coords in self.bounding_coords:
                    cv2.circle(disp_frame, coords, 3, (255,255,255), thickness=-1)
                cv2.rectangle(disp_frame, self.bounding_coords[0], self.bounding_coords[1], (255, 255, 255))
                coord2 = (int(np.mean([self.bounding_coords[0][0], self.bounding_coords[1][0]])),
                          int(np.mean([self.bounding_coords[0][1], self.bounding_coords[1][1]])))
                cv2.rectangle(disp_frame, self.bounding_coords[0], coord2, (255, 255, 255))
           # for x, y in self.guass:
            #    x = int(x)
             #   y = int(y)
              #  cv2.circle(disp_frame, (x, y), 3, (255, 255, 255), thickness=-1)
            return (cx, cy), disp_frame


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


class ProgBar(qg.QGraphicsView):
    def __init__(self, tracker):
        super(ProgBar, self).__init__()
        self.tracker = tracker
        self.exp_start_time = qc.QTime()
        self.bar_gfx_running = False
        self.time_gfx_running = False
        self.scene = qg.QGraphicsScene(self)
        self.init_static_background()
        self.init_anim_gfx_objects()
        self.set_dynamic_background()
        self.setScene(self.scene)
        self.setRenderHint(qg.QPainter.Antialiasing)
        self.setMinimumSize(1056, 288)
        self.setMaximumSize(1056, 288)
        self.paint_group = GUI_SimpleGroup()
        self.scene.addItem(self.paint_group)


    def init_static_background(self):
        """Sets up the static backdrop"""
        bg_group = GUI_SimpleGroup()
        # Main Background Shapes
        bg_group.add(qg.QGraphicsRectItem(0, 0, 1052, 284), brush=qg.QColor(0, 0, 0))
        self.scene.addItem(bg_group)

    def init_anim_gfx_objects(self):
        """Sets up progress bar and timer"""
        # Graphics objects
        self.time_gfx = qg.QGraphicsTextItem('00:00.000')
        self.time_gfx.setDefaultTextColor(qg.QColor(255, 255, 255))
        self.bar_gfx = qg.QGraphicsLineItem(0, 22, 0, 258)
        self.bar_gfx.setPen(qg.QColor(255, 0, 0))
        # Stacking
        self.time_gfx.setZValue(1)  # So the animated objects are stacked on top of background objects
        self.bar_gfx.setZValue(1)  # Regardless of insertion order
        # Add objects to scene
        self.scene.addItem(self.time_gfx)
        self.scene.addItem(self.bar_gfx)

    def set_dynamic_background(self):
        """
        Sets dynamic background using data from settings.ard_last_used
        Any changes to ard settings should be done to settings.ard_last_used before calling this!
        """
        self.set_timers_and_anims()

    def set_timers_and_anims(self):
        """Sets duration and frames of progress bar animation"""
        self.duration = 2 * 1000 * 60
        # Timer objects
        self.time_gfx_timer = qc.QTimeLine(self.duration)
        self.bar_gfx_timer = qc.QTimeLine(self.duration)
        self.time_gfx_timer.setCurveShape(qc.QTimeLine.LinearCurve)
        self.bar_gfx_timer.setCurveShape(qc.QTimeLine.LinearCurve)
        self.time_gfx_timer.setFrameRange(0, self.duration * 1000)
        self.bar_gfx_timer.setFrameRange(0, self.duration * 1000)
        # Animation Objects
        self.time_gfx_anim = qg.QGraphicsItemAnimation()
        self.bar_gfx_anim = qg.QGraphicsItemAnimation()
        self.time_gfx_anim.setItem(self.time_gfx)
        self.bar_gfx_anim.setItem(self.bar_gfx)
        self.time_gfx_anim.setTimeLine(self.time_gfx_timer)
        self.bar_gfx_anim.setTimeLine(self.bar_gfx_timer)
        # Animation Frames
        self.bar_gfx_timer.frameChanged[int].connect(self.advance_increment)
        for i in range(1000):
            self.time_gfx_anim.setPosAt(i / 1000.0, qc.QPointF(i, 0))
            self.bar_gfx_anim.setPosAt(i / 1000.0, qc.QPointF(i, 0))

    def format_secs(self, time_in_secs, option='norm'):
        """
        Turns Seconds into various time formats
        @time_in_secs: integer seconds; decimal milliseconds
        @option: 'norm', 'with_ms', 'min', 'sec'
        """
        output = ''
        # Check option given is in correct list of options
        if option not in ['norm', 'with_ms', 'min', 'sec']:
            raise ValueError('[{}] is not a valid option!'.format(option))
        # -- Obtain mins, secs, millis -- #
        mins = int(time_in_secs) // 60
        secs = int(time_in_secs) % 60
        millis = int((time_in_secs - int(time_in_secs)) * 1000)
        # -- Report time in specific format specified -- #
        if option == 'norm':  # MM:SS
            output = '{:0>2}:{:0>2}'.format(mins, secs)
        elif option == 'with_ms':  # MM:SS.mss
            output = '{:0>2}:{:0>2}.{:0>3}'.format(mins, secs, millis)
        elif option == 'min':  # MM
            output = '{:0>2}'.format(mins)
        elif option == 'sec':  # SS
            output = '{:0>2}'.format(secs)
        # -- Finish -- #
        return output

    def advance_increment(self):
        """Called by bar_gfx_timer; runs this every time timer goes up by 1"""
        # -- Animations for Time Indicator -- #
        # Update Time
        ms_elapsed = self.exp_start_time.elapsed() / 1000.0
        ms_elapsed = self.format_secs(ms_elapsed, 'with_ms')
        self.time_gfx.setPlainText(ms_elapsed)
        # Make sure Progress Bar booleans are set correctly
        if not self.bar_gfx_running:  # Bar runs entire duration, so use as running marker
            self.bar_gfx_running = True
        if abs(self.bar_gfx_timer.currentFrame()) >= self.duration * 1000:
            self.bar_gfx_running = False
        # Move the Time Indicator by 1 increment
        if not self.time_gfx_running \
            and abs(self.bar_gfx_timer.currentFrame()) > self.duration * 31 \
                and not abs(self.bar_gfx_timer.currentFrame()) >= self.duration * 934:
            self.time_gfx_running = True
            self.time_gfx_timer.start()
        if abs(self.time_gfx_timer.currentFrame()) >= self.duration * 940:
            self.time_gfx_running = False
            self.time_gfx_timer.stop()
        if self.tracker.stim:
            x = self.bar_gfx.x()
            self.paint_group.add(qg.QGraphicsLineItem(x, 50, x, 200), pen=qg.QColor(255, 255, 0))

    def start_bar(self):
        """Starts Progress Bar"""
        self.time_gfx.setPos(0, 0)
        self.bar_gfx_timer.start()
        self.exp_start_time.start()


if __name__ == '__main__':
    app = qg.QApplication([])
    window = qg.QWidget()
    grid = qg.QGridLayout()
    window.setLayout(grid)
    gui = GUI()
    window.show()
    grid.addWidget(gui)
    btn = qg.QPushButton('push')
    grid.addWidget(btn)
    btn.clicked.connect(gui.create_bounds)
    progbar = ProgBar(gui.tracker)
    grid.addWidget(progbar)
    progbar.start_bar()
    app.exec_()
