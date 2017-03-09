# coding=utf-8
"""
Custom Widgets for TKinter

self.root or self.master denotes the Tkinter frame or canvas holding the widget
"""


import sys
import tkFont
import Tkinter as Tk
from copy import deepcopy
from datetime import datetime
from MiscFunctions import format_secs, deepcopy_lists


class ScrollFrame(object):
    """Produces a scrollable canvas object hooked to a vertical scroll bar"""

    def __init__(self, master, num_args, rows, bottom_padding=0):
        # frame root
        self.root = master
        # number of rows
        self.rows = rows
        # number of columns (e.g. num pins)
        self.num_args = num_args
        # a pixel value of padding below the input entry boxes (to bring bottommost rows into view)
        self.bottom_padding = bottom_padding

        # Top Frame
        self.top_frame = Tk.Frame(self.root)
        self.top_frame.grid(row=0, column=0,
                            columnspan=self.num_args,
                            sticky=Tk.N + Tk.S + Tk.E + Tk.W)

        # Scroll Bar
        v_bar = Tk.Scrollbar(self.root, orient=Tk.VERTICAL)
        self.canvas = Tk.Canvas(self.root, yscrollcommand=v_bar.set)
        v_bar['command'] = self.canvas.yview
        self.canvas.bind_all('<MouseWheel>', self.on_vertical)
        v_bar.grid(row=1, column=self.num_args, sticky=Tk.N + Tk.S)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        # Middle Frame
        self.middle_frame = Tk.Frame(self.canvas)
        # Bottom Frame
        self.bottom_frame = Tk.Frame(self.root)
        self.bottom_frame.grid(row=2, column=0, columnspan=self.num_args + 1)

    def on_vertical(self, event):
        """returns vertical position of scrollbar"""
        self.canvas.yview_scroll(-1 * event.delta, 'units')

    def finalize(self):
        """finishes initial setup before showing the screen"""
        self.canvas.create_window(0, 0, anchor=Tk.NW, window=self.middle_frame)
        self.canvas.grid(row=1, column=0,
                         columnspan=self.num_args, sticky=Tk.N + Tk.S + Tk.E + Tk.W)
        self.canvas.configure(scrollregion=(0, 0, 0, self.rows * 28 + self.bottom_padding))


class ProgressBar(object):
    """
    Not a true GUI widget by itself.

    we pass, as arguments, the desired shape (bar) and timestamp (time_gfx) when calling
    ProgressBar(). This object will, when start() is called, move the shape and timestamp as necessary
    Do not run in a separate thread! it will screw up the GUI
    """

    def __init__(self, master, canvas, bar, time_gfx, ms_total_time):
        self.master = master  # root master
        self.canvas = canvas  # canvas upon which to move the prog bar
        # the size of each prog bar advancement
        self.segment_size = (float(ms_total_time / 1000)) / 1000
        # total time in millis
        self.ms_total_time = ms_total_time
        # progress bar to be moved
        self.bar = bar
        # the timestamp to be moved
        self.time_gfx = time_gfx
        # if running, run prog bar
        self.running = False
        # starting time
        self.start_prog = None
        # number of times the prog bar and timestamp have been moved
        self.num_prog, self.num_time = 1, 1
        # time difference, used to decide when to shift the graphics forward by one self.segment_size
        self.time_diff = 0

    def start(self):
        """Starts the progress bar"""
        # first we check and move progress bar to starting position
        if self.num_prog != 1:
            self.canvas.move(self.bar, -self.num_prog + 1, 0)
            if (-self.num_prog + 1 + 35) < 0:
                text_move = max(-self.num_prog + 1 + 35, -929)
                self.canvas.move(self.time_gfx, text_move, 0)
            self.num_prog, self.num_time = 1, 1
        # get starting time
        self.start_prog = datetime.now()
        # run
        self.running = True
        self.advance()

    def advance(self):
        """Moves the progressbar one increment when necessary"""
        if self.running:
            # get current time to compare against start
            now = datetime.now()
            # get time difference since start
            self.time_diff = (now - self.start_prog).seconds + float(
                (now - self.start_prog).microseconds) / 1000000
            # we update the value in the timestamp every 5ms
            if self.time_diff / self.num_time >= 0.005:
                self.canvas.itemconfig(self.time_gfx,
                                       text='{}'.format(format_secs(self.time_diff, True)))
                self.num_time += 1
            # we move the timestamp and prog bar every self.segment_size
            if self.time_diff / self.num_prog >= self.segment_size:
                self.canvas.move(self.bar, 1, 0)
                # we only move the timestamp when the prog bar reaches the middle of the timestamp
                if (self.num_prog > 35) and (self.num_prog < 965):
                    self.canvas.move(self.time_gfx, 1, 0)
                self.num_prog += 1
            # update the canvase (redraw)
            self.canvas.update()
            # stop if reach end of bar or end of time
            if self.num_prog > 1000 or self.time_diff > float(self.ms_total_time / 1000):
                self.running = False
                return self.running
            # we check in smaller increments if the total time is small; otherwise bar becomes very inaccurate
            if self.ms_total_time < 120000:
                advance_by = 15
            else:
                advance_by = 30
            # place function back into master event loop
            self.master.after(advance_by, self.advance)

    def stop(self):
        """Stops the progress bar"""
        self.running = False


# noinspection PyClassicStyleClass
class LiveGraph(Tk.Frame):
    """
    Plots a live graph using data from a queue filled with labjack output
    """

    def __init__(self, dirs, parent):
        # noinspection PyTypeChecker,PyCallByClass
        Tk.Frame.__init__(self, parent)
        # line colors
        self.color_scheme = ['#FF7F00', '#003643', '#F10026', '#3BDA00',
                             '#6C3600', '#3EB7D3', '#F94461', '#195D00']
        # graph lines
        self.line_canvas = Tk.Canvas(self, background='#EFEFEF', height=216, width=610)
        self.line_canvas.grid(column=1, row=0, rowspan=8)
        self.line_canvas.grid_rowconfigure(0, weight=1, uniform='x')
        # line labels
        self.line_labels = deepcopy_lists(outer=1, inner=8, populate=Tk.StringVar)
        for i in range(8):
            label = Tk.Label(self, textvariable=self.line_labels[i], fg=self.color_scheme[i])
            label.grid(column=0, row=i)
            label.grid_rowconfigure(0, weight=1, uniform='x')
            self.line_labels[i].set('')
        # frame holder line (forces canvase to stay in frame even if some lines fall out of height range)
        self.line_canvas.create_line(50, 0, 50, 216, fill='#EFEFEF', width=2)
        # setup
        self.lines = []
        self.update_labels(dirs)
        self.create_new_lines()

    def create_new_lines(self):
        """creates 8 lines, corresponding to the 8 max channels usable at one time on labjack"""
        self.lines = []
        for i in range(8):
            self.lines.append(self.line_canvas.create_line(0, 27 + 27 * i, 0, 27 + 27 * i,
                                                           fill=self.color_scheme[i], width=1.3))

    def clear_plot(self):
        """clears existing lines on the graph"""
        for i in range(8):
            self.line_canvas.delete(self.lines[i])

    def update_labels(self, dirs):
        """updates lj channel labels"""
        lj_ch_num = deepcopy(dirs.settings.lj_last_used['ch_num'])
        for i in range(8):
            self.line_labels[i].set('')
        for i in range(len(lj_ch_num)):
            self.line_labels[i].set('{:0>2}'.format(lj_ch_num[i]))

    def update_plot(self, *args):
        """Updates data on the plot"""
        # grab data, add to line
        for i in range(len(args[0])):
            self.add_point(self.lines[i], args[0][i])
        # shift the line leftwards by 1.
        self.line_canvas.xview_moveto(1.0)

    def add_point(self, line, y):
        """adds new data to existing plot"""
        coords = self.line_canvas.coords(line)
        x = coords[-2] + 1
        coords.append(x)
        coords.append(y)
        coords = coords[-1500:]  # keep # of points to a manageable size
        self.line_canvas.coords(line, *coords)
        self.line_canvas.configure(scrollregion=self.line_canvas.bbox("all"))


# noinspection PyClassicStyleClass,PyTypeChecker
class SimpleTable(object, Tk.Frame):
    """Creates a table with defined rows and columns modifiable via a set command"""
    # noinspection PyCallByClass
    def __init__(self, master, rows, columns, highlight_column, highlight_color):
        Tk.Frame.__init__(self, master, background="black")
        self.text_var = deepcopy_lists(rows, columns, Tk.StringVar)
        for row in range(rows):
            for column in range(columns):
                # we can highlight a specific column if desired
                if column == highlight_column:
                    label = Tk.Label(self, textvariable=self.text_var[row][column],
                                     borderwidth=0, width=10, height=1,
                                     font=tkFont.Font(root=master, family='Arial', size=8),
                                     bg=highlight_color)
                else:
                    label = Tk.Label(self, textvariable=self.text_var[row][column],
                                     borderwidth=0, width=10, height=1,
                                     font=tkFont.Font(root=master, family='Helvetica', size=8))
                label.grid(row=row, column=column, sticky='nsew', padx=1, pady=1)
                self.text_var[row][column].set('')
        for column in range(columns):
            self.grid_columnconfigure(column, weight=1)

    def set_var(self, row, column, value):
        """sets a specific box to specified value"""
        item = self.text_var[row][column]
        item.set(value)

    def clear(self):
        """clears fields"""
        for row in range(len(self.text_var) - 1):
            for column in range(len(self.text_var[row]) - 1):
                self.text_var[row + 1][column + 1].set('')


class GUI(object):
    """Skeleton GUI"""

    def __init__(self, tcl_root, dirs, topmost=True):
        self.root = tcl_root
        self.dirs = dirs
        try:
            self.root.wm_iconbitmap('mouse_rec_icon.ico')
        except Tk.TclError:
            pass
        self.root.resizable(width=False, height=False)
        self.ALL = Tk.N + Tk.E + Tk.S + Tk.W
        # If exiting by close button (top right x), call self.hard_exit() to clean up processes etc first
        self.root.protocol('WM_DELETE_WINDOW', self.hard_exit)
        self.hard_closed = False
        # keep window permanently on top or not
        if topmost:
            self.root.wm_attributes("-topmost", True)
        self.root.focus_force()

    def hard_exit(self):
        """Destroy all instances of the window
        if close button is pressed
        Prevents ID errors and clashes. Re-implement to customize closing actions"""
        self.hard_closed = True
        self.root.destroy()
        self.root.quit()

    def center(self):
        """Centers GUI window"""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        [window_width, window_height] = list(
            int(i) for i in
            self.root.geometry().split('+')[0].split('x'))
        x_pos = screen_width / 2 - window_width / 2
        y_pos = screen_height / 2 - window_height / 2
        self.root.geometry('{}x{}+{}+{}'.format(
            window_width,
            window_height,
            x_pos, y_pos))

    def run(self):
        """Initiate GUI"""
        self.center()
        self.root.mainloop()

    def platform_geometry(self, windows, darwin):
        """Changes window dimensions based on platform"""
        if sys.platform.startswith('win'):
            self.root.geometry(windows)
        elif sys.platform.startswith('darwin'):
            self.root.geometry(darwin)
        else:
            pass
