# coding=utf-8
"""
Included:
- Device, GUI, Misc. Classes and functions (in separate .py files)
- Pmw.py, PmwBlt.py, PmwColor.py, setup.py (for building windows .exe)
"""
import ast
import Pmw
from pprint import pprint
from operator import itemgetter
from PIL.ImageTk import Image, PhotoImage

# Import own files
from Devices import *
from DeviceGUIs import *
from GUIElements import *
from DirsSettings import *
from MiscFunctions import *

################################################################
# To do list:
# - Arduino GUI Geometry fine tuning
# - Arduino optiboot.c loader: remove led flash on start?
#################################################################
# Concurrency Controls:
#   (global variables because otherwise we need to create these
#   under the child process and extract as attributes to avoid
#   pickling issues)
# Queues:
MASTER_DUMP_QUEUE = multiprocessing.Queue()
MASTER_GRAPH_QUEUE = multiprocessing.Queue()
THREAD_DUMP_QUEUE = multiprocessing.Queue()
PROCESS_DUMP_QUEUE = multiprocessing.Queue()
# Lock Controls
# not real locks but the names stuck. used for inter-device synchronization
LJ_READ_READY_LOCK = multiprocessing.Event()
LJ_EXP_READY_LOCK = multiprocessing.Event()
ARD_READY_LOCK = multiprocessing.Event()
CMR_READY_LOCK = multiprocessing.Event()
# forbidden characters (cannot include these in file names)
FORBIDDEN_CHARS = ['#', '<', '>', '$', '+', '%', '!', '`',
                   '&', '*', '\'', '|', '{', '}', '?', '"',
                   '=', '/', ':', '\\', '@']
# Enable this if making an executable via cx_freeze
EXECUTABLE = False
###################################################################


class MasterGUI(GUI):
    """Main GUI.
    NOTE: Perform all GUI functions here, and here only!
    Tasks that take >1s to perform can be done in a thread,
    but interactions must be strictly through queues.
    Note on queues: do NOT process GUI objects in separate threads
    (e.g. PhotoImages, Canvas items, etc) even if they can be sent through queues.
        this WILL cause crashes under load or unexpected circumstances."""

    def __init__(self, master):
        GUI.__init__(self, master, topmost=False, dirs=None)
        self.master = self.root
        self.master.title('Mouse House')
        # Fonts
        self.time_label_font = tkFont.Font(family='Arial', size=6)
        self.label_font = tkFont.Font(family='Arial', size=10)
        self.label_font_symbol = tkFont.Font(family='Arial', size=9)
        self.small_label_font = tkFont.Font(family='Arial', size=7)
        self.main_button_font = tkFont.Font(family='Arial', size=10, weight='bold')
        # Widget Configs
        self.single_widget_dim = 100
        # noinspection PyUnresolvedReferences
        self.balloon = Pmw.Balloon(master)
        ###################################################################
        # Note on Threading Control:
        # All queues initiated by child thread that puts data IN
        # All locks initiated by child thread that CONTROLS its set and clear
        ###################################################################
        # Concurrency Controls
        self.master_dump_queue = MASTER_DUMP_QUEUE
        self.master_graph_queue = MASTER_GRAPH_QUEUE
        self.thread_dump_queue = THREAD_DUMP_QUEUE
        self.process_dump_queue = PROCESS_DUMP_QUEUE
        ###########################
        # Save variables
        # directories
        self.save_dir_name_used = []
        self.results_dir_used = {}
        # file name
        self.data_save_count = 0
        # Arduino config variables
        self.ttl_time = dirs.settings.ard_last_used['packet'][3]
        ###########################
        # GUI setup
        self.render_photometry()
        self.render_saves()
        self.render_lj()
        self.render_arduino()
        self.render_camera()
        self.progbar_started = False
        ###########################
        # Finalize GUI window and launch
        self.process_dump_queue.put_nowait(dirs.settings)
        self.lj_proc_handler = LJProcessHandler()
        self.thread_handler = GUIThreadHandler()
        self.lj_proc_handler.start()
        self.thread_handler.start()
        self.master.after(10, self.gui_event_loop)
        self.master.after(10, self.video_stream)
        self.master.after(10, self.lj_graph_stream)
        self.clear_lj_plot = False
        self.center()

    #####################################################################
    # GUI Setup
    #####################################################################
    # noinspection PyAttributeOutsideInit
    def render_photometry(self):
        """sets up photometry component"""
        frame = Tk.LabelFrame(self.master, text='Optional Photometry Config.',
                              width=self.single_widget_dim,
                              height=self.single_widget_dim)
        frame.grid(row=0, column=0, sticky=self.ALL)
        # Variables
        self.fp_toggle_var = Tk.IntVar()
        self.fp_toggle_var.set(0)
        self.fp_statustext_var = Tk.StringVar()
        self.fp_statustext_var.set('\n[N/A]\n')
        # Buttons
        self.fp_toggle_button = Tk.Checkbutton(frame, text='Toggle Photometry On/Off',
                                               variable=self.fp_toggle_var,
                                               onvalue=1, offvalue=0,
                                               command=self.fp_toggle)
        self.fp_toggle_button.pack()
        self.fp_config_button = Tk.Button(frame,
                                          text='CONFIG',
                                          command=self.fp_config)
        self.fp_config_button.pack()
        self.fp_config_button.config(state='disabled')
        Tk.Label(frame, textvariable=self.fp_statustext_var).pack()

    # noinspection PyAttributeOutsideInit
    def render_saves(self):
        """save gui setup"""
        self.save_grab_list()
        # 1. Primary Save Frame
        frame = Tk.LabelFrame(self.master,
                              text='Data Output Save Location',
                              width=self.single_widget_dim * 2,
                              height=self.single_widget_dim)
        frame.grid(row=1, column=0, sticky=self.ALL)
        # Display chosen save name / last used save name
        self.save_status_var = Tk.StringVar()
        save_file_label = Tk.Label(frame, textvariable=self.save_status_var,
                                   relief=Tk.RAISED)
        save_file_label.pack(side=Tk.TOP, expand='yes', fill='both')
        # 2a. Secondary Save Frame: Existing Saves
        existing_frame = Tk.LabelFrame(frame, text='Select a Save Name')
        existing_frame.pack(fill='both', expand='yes')
        self.chosen_dir_var = Tk.StringVar()
        self.save_status_var.set('Last Used Save Dir.:'
                                 '\n[{}]'.format(lim_str_len(dirs.settings.save_dir.upper(), 30)))
        self.chosen_dir_var.set('{: <30}'.format(dirs.settings.save_dir))
        if len(self.save_dir_list) == 0:
            self.save_dir_menu = Tk.OptionMenu(existing_frame,
                                               self.chosen_dir_var, ' ' * 15)
        else:
            self.save_dir_menu = Tk.OptionMenu(existing_frame,
                                               self.chosen_dir_var,
                                               *self.save_dir_list,
                                               command=lambda path:
                                               self.save_button_options(inputs=path))
        self.save_dir_menu.config(width=29)
        self.save_dir_menu.grid(sticky=self.ALL, columnspan=2)
        # 2b. Secondary Save Frame: New Saves
        new_frame = Tk.LabelFrame(frame, text='Create a New Save Location')
        new_frame.pack(fill='both', expand='yes')
        self.new_save_entry = Tk.Entry(new_frame)
        self.new_save_entry.pack(side=Tk.TOP, fill='both', expand='yes')
        self.new_save_button = Tk.Button(new_frame,
                                         text='Create New',
                                         command=lambda:
                                         self.save_button_options(new=True))
        self.new_save_button.pack(side=Tk.TOP)

    # noinspection PyAttributeOutsideInit
    def render_lj(self):
        """lj config gui"""
        # Frame
        frame = Tk.LabelFrame(self.master, text='LabJack Config.',
                              width=self.single_widget_dim * 2,
                              height=self.single_widget_dim)
        frame.grid(row=2, column=0, sticky=self.ALL)
        # Variables
        self.lj_status_var = Tk.StringVar()
        channels = dirs.settings.lj_last_used['ch_num']
        freq = dirs.settings.lj_last_used['scan_freq']
        self.lj_status_var.set('Channels:\n'
                               '{}\n\n'
                               'Scan Freq: '
                               '[{}Hz]'.format(channels, freq))
        # Current State Report
        Tk.Label(frame, textvariable=self.lj_status_var).pack(side=Tk.TOP)
        # Config Button
        self.lj_config_button = Tk.Button(frame, text='CONFIG',
                                          command=self.lj_config)
        self.lj_config_button.pack(side=Tk.BOTTOM, expand=True)
        # bottom frame containing live graph, report, and naming
        frame = Tk.Frame(self.master)
        frame.grid(row=3, column=1, sticky=self.ALL)
        # Post experiment LabJack report frame
        stream_frame = Tk.LabelFrame(frame, text='LabJack Stream (20 Hz Scanning)')
        stream_frame.grid(row=0, column=1, rowspan=2, sticky=self.ALL)
        table_frame = Tk.LabelFrame(frame, text='')
        table_frame.grid(row=1, column=0, sticky=Tk.S)
        name_trial_frame = Tk.LabelFrame(frame, text='Optional: Give the Next Trial a Name')
        name_trial_frame.grid(row=0, column=0, sticky=self.ALL)
        # naming
        self.name_entry = Tk.Entry(name_trial_frame, width=52)
        self.name_entry.grid(sticky=self.ALL)
        # report etc
        Tk.Label(table_frame, text='Post Experiment LabJack Report',
                 font=tkFont.Font(family='Arial', size='8')).grid(row=1, column=0, sticky=self.ALL)
        self.lj_table = SimpleTable(table_frame, 6, 5, highlight_column=2, highlight_color='#72ab97')
        self.lj_table.grid(row=2, column=0, sticky=self.ALL)
        self.lj_report_table_config()
        # labjack stream
        self.lj_graph = LiveGraph(dirs=dirs, parent=stream_frame)
        self.lj_graph.grid(sticky=self.ALL)

    # noinspection PyAttributeOutsideInit
    def render_arduino(self):
        """Sets up the main progress bar, arduino config buttons,
        and various status message bars"""
        # Frame
        self.ard_preset_list = []
        self.ard_bckgrd_height = 260
        ard_frame = Tk.LabelFrame(self.master, text='Arduino Stimuli Config.',
                                  width=self.single_widget_dim * 11,
                                  height=self.ard_bckgrd_height)
        ard_frame.grid(row=0, rowspan=3, column=1, sticky=self.ALL)
        Tk.Label(ard_frame,
                 text='Last used settings shown. '
                      'Rollover individual segments for '
                      'specific stimuli configuration info.',
                 font=self.small_label_font,
                 relief=Tk.RAISED).grid(row=0, columnspan=55, sticky=self.ALL)
        # Debug Buttons
        self.debug_button = Tk.Button(ard_frame, text='DEBUG', font=self.small_label_font,
                                      command=self.gui_debug)
        self.debug_button.grid(row=0, column=80, columnspan=10, sticky=self.ALL)
        self.clr_svs_button = Tk.Button(ard_frame, text='ClrSvs', font=self.small_label_font,
                                        command=self.clear_saves)
        self.clr_svs_button.grid(row=0, column=90, columnspan=10, sticky=self.ALL)
        self.clr_svs_button.config(state=Tk.DISABLED)
        self.debug_chk_var = Tk.IntVar()
        if dirs.settings.debug_console:
            self.debug_chk_var.set(1)
        elif not dirs.settings.debug_console:
            self.debug_chk_var.set(0)
        Tk.Checkbutton(ard_frame, text='', variable=self.debug_chk_var,
                       command=self.debug_printing, onvalue=1,
                       offvalue=0).grid(row=0, column=79, sticky=Tk.E)
        # Main Progress Canvas
        self.ard_canvas = Tk.Canvas(ard_frame, width=1050, height=self.ard_bckgrd_height + 10)
        self.ard_canvas.grid(row=1, column=0, columnspan=100)
        self.gui_canvas_initialize()
        # Progress Bar Control Buttons
        self.prog_on = Tk.Button(ard_frame, text='START', bg='#99ccff',
                                 font=self.main_button_font)
        self.prog_on.grid(row=5, column=2, columnspan=3, stick=self.ALL)
        self.prog_off = Tk.Button(ard_frame, text='STOP', bg='#ff9999',
                                  font=self.main_button_font)
        self.prog_off.grid(row=5, column=5, stick=self.ALL)
        self.prog_on.config(command=self.progbar_run)
        self.prog_off.config(state=Tk.DISABLED,
                             command=self.progbar_stop)
        # Grab Data and Generate Progress Bar
        self.ard_grab_data()
        # Arduino Presets
        self.ard_update_preset_list()
        self.ard_preset_chosen_var = Tk.StringVar()
        self.ard_preset_chosen_var.set('{: <20}'.format('(select a preset)'))
        self.ard_preset_menu = Tk.OptionMenu(ard_frame,
                                             self.ard_preset_chosen_var,
                                             *self.ard_preset_list,
                                             command=lambda file_in:
                                             self.ard_grab_data(True, file_in))
        self.ard_preset_menu.config(width=20)
        self.ard_preset_menu.grid(row=7, column=0, columnspan=2, sticky=self.ALL)
        self.preset_save_button = Tk.Button(ard_frame, text='Save as New Preset', command=self.save_new_preset)
        self.preset_save_button.grid(row=7, column=2, columnspan=4, sticky=self.ALL)
        self.preset_save_entry = Tk.Entry(ard_frame)
        self.preset_save_entry.grid(row=6, column=2, columnspan=4, sticky=self.ALL)
        # Manual Arduino Setup
        # Total Experiment Time Config
        Tk.Label(ard_frame, text='MM',
                 font=self.time_label_font).grid(row=3, column=2, sticky=self.ALL)
        Tk.Label(ard_frame, text='SS',
                 font=self.time_label_font).grid(row=3, column=4, sticky=self.ALL)
        Tk.Label(ard_frame,
                 text='Total Experiment Time:').grid(row=3 + 1, column=0, columnspan=2, sticky=self.ALL)
        # Minutes
        self.min_entry = Tk.Entry(ard_frame, width=2)
        self.min_entry.grid(row=3 + 1, column=2, sticky=self.ALL)
        self.min_entry.insert(Tk.END, '{}'.format(format_secs(self.ttl_time / 1000, option='min')))
        Tk.Label(ard_frame, text=':').grid(row=3 + 1, column=3, sticky=self.ALL)
        # Seconds
        self.sec_entry = Tk.Entry(ard_frame, width=2)
        self.sec_entry.grid(row=3 + 1, column=4, sticky=self.ALL)
        self.sec_entry.insert(Tk.END, '{}'.format(format_secs(self.ttl_time / 1000, option='sec')))
        self.ard_time_confirm_button = Tk.Button(ard_frame, text='Confirm',
                                                 command=self.ard_get_time)
        self.ard_time_confirm_button.grid(row=3 + 1, column=5, sticky=self.ALL)
        # Stimuli Config
        self.tone_setup_button = Tk.Button(ard_frame, text='Tone Setup',
                                           command=lambda types='tone':
                                           self.ard_config(types))
        self.tone_setup_button.grid(row=5, column=0, sticky=self.ALL)
        self.out_setup_button = Tk.Button(ard_frame, text='Simple\nOutputs',
                                          command=lambda types='output':
                                          self.ard_config(types))
        self.out_setup_button.grid(row=5, rowspan=2, column=1, columnspan=1, sticky=self.ALL)
        self.pwm_setup_button = Tk.Button(ard_frame, text='PWM Setup',
                                          command=lambda types='pwm':
                                          self.ard_config(types))
        self.pwm_setup_button.grid(row=6, column=0, sticky=self.ALL)
        # Status messages for devices
        Tk.Label(ard_frame, text='Enable:', relief=Tk.RAISED,
                 font=tkFont.Font(family='Arial', size='7')).grid(row=0, column=55,
                                                                  columnspan=15,
                                                                  sticky=self.ALL)
        # arduino
        self.ard_status_bar = Tk.StringVar()
        Tk.Label(ard_frame, anchor=Tk.E, text='Arduino:  ',
                 font=self.small_label_font).grid(row=4, column=10,
                                                  columnspan=20,
                                                  sticky=Tk.E)
        ard_status_display = Tk.Label(ard_frame, anchor=Tk.W, font=self.small_label_font,
                                      textvariable=self.ard_status_bar,
                                      relief=Tk.SUNKEN)
        ard_status_display.grid(row=4, column=30, columnspan=68, sticky=self.ALL)
        self.ard_status_bar.set('null')
        self.ard_toggle_var = Tk.IntVar()
        self.ard_toggle_var.set(1)
        self.ard_toggle_button = Tk.Checkbutton(ard_frame, variable=self.ard_toggle_var, text='Arduino',
                                                onvalue=1, offvalue=0, command=lambda:
                                                self.device_status_msg_toggle(self.ard_toggle_var,
                                                                              self.ard_status_bar,
                                                                              ard_status_display,
                                                                              name='ard'))
        self.ard_toggle_button.grid(row=0, column=70, sticky=Tk.E)
        # LabJack
        self.lj_status_bar = Tk.StringVar()
        Tk.Label(ard_frame, anchor=Tk.E, text='LabJack:  ', font=self.small_label_font).grid(row=5, column=10,
                                                                                             columnspan=20,
                                                                                             sticky=Tk.E)
        lj_status_display = Tk.Label(ard_frame, anchor=Tk.W, font=self.small_label_font,
                                     textvariable=self.lj_status_bar,
                                     relief=Tk.SUNKEN)
        lj_status_display.grid(row=5, column=30, columnspan=68, sticky=self.ALL)
        self.lj_status_bar.set('null')
        self.lj_toggle_var = Tk.IntVar()
        self.lj_toggle_var.set(1)
        self.lj_toggle_button = Tk.Checkbutton(ard_frame, variable=self.lj_toggle_var, text='LabJack',
                                               onvalue=1, offvalue=0, command=lambda:
                                               self.device_status_msg_toggle(self.lj_toggle_var,
                                                                             self.lj_status_bar,
                                                                             lj_status_display,
                                                                             name='lj'))
        self.lj_toggle_button.grid(row=0, column=72, sticky=Tk.E)
        # Camera
        self.cmr_status_bar = Tk.StringVar()
        Tk.Label(ard_frame, anchor=Tk.E, text='Camera:  ',
                 font=self.small_label_font).grid(row=6, column=10,
                                                  columnspan=20, sticky=Tk.E)
        cmr_status_display = Tk.Label(ard_frame, anchor=Tk.W, textvariable=self.cmr_status_bar,
                                      relief=Tk.SUNKEN, font=self.small_label_font)
        cmr_status_display.grid(row=6, column=30, columnspan=68, sticky=self.ALL)
        self.cmr_status_bar.set('null')
        self.cmr_toggle_var = Tk.IntVar()
        self.cmr_toggle_var.set(1)
        self.cmr_toggle_button = Tk.Checkbutton(ard_frame, variable=self.cmr_toggle_var, text='Camera',
                                                onvalue=1, offvalue=0, command=lambda:
                                                self.device_status_msg_toggle(self.cmr_toggle_var,
                                                                              self.cmr_status_bar,
                                                                              cmr_status_display,
                                                                              name='cmr'))
        self.cmr_toggle_button.grid(row=0, column=74, sticky=Tk.E)
        # Save Status
        self.save_status_bar = Tk.StringVar()
        Tk.Label(ard_frame, anchor=Tk.E, text='Saves:  ',
                 font=self.small_label_font).grid(row=7, column=10,
                                                  columnspan=20, sticky=Tk.E)
        save_status_display = Tk.Label(ard_frame, anchor=Tk.W, textvariable=self.save_status_bar,
                                       relief=Tk.SUNKEN, font=self.small_label_font)
        save_status_display.grid(row=7, column=30, columnspan=68, sticky=self.ALL)
        self.save_status_bar.set('null')

    def gui_canvas_initialize(self):
        """Setup Progress bar Canvas"""
        # Backdrop
        self.ard_canvas.create_rectangle(0, 0,
                                         1050, self.ard_bckgrd_height,
                                         fill='black', outline='black')
        self.ard_canvas.create_rectangle(0, 35 - 1,
                                         1050, 35 + 1,
                                         fill='white')
        self.ard_canvas.create_rectangle(0, 155 - 1,
                                         1050, 155 + 1,
                                         fill='white')
        self.ard_canvas.create_rectangle(0, 15 - 1,
                                         1050, 15 + 1,
                                         fill='white')
        self.ard_canvas.create_rectangle(0, self.ard_bckgrd_height - 5 - 1,
                                         1050, self.ard_bckgrd_height - 5 + 1,
                                         fill='white')
        self.ard_canvas.create_rectangle(0, 15,
                                         0, self.ard_bckgrd_height - 5,
                                         fill='white', outline='white')
        self.ard_canvas.create_rectangle(1000, 15,
                                         1013, self.ard_bckgrd_height - 5,
                                         fill='white', outline='white')
        # Type Labels
        self.ard_canvas.create_rectangle(1000, 0,
                                         1013, 15,
                                         fill='black')
        self.ard_canvas.create_text(1000 + 7, 15 + 10,
                                    text=u'\u266b', fill='black')
        self.ard_canvas.create_rectangle(1000, 35,
                                         1013, 35,
                                         fill='black')
        self.ard_canvas.create_text(1000 + 7, 35 + 10,
                                    text='S', fill='black')
        self.ard_canvas.create_text(1000 + 7, 55 + 10,
                                    text='I', fill='black')
        self.ard_canvas.create_text(1000 + 7, 75 + 10,
                                    text='M', fill='black')
        self.ard_canvas.create_text(1000 + 7, 95 + 10,
                                    text='P', fill='black')
        self.ard_canvas.create_text(1000 + 7, 115 + 10,
                                    text='L', fill='black')
        self.ard_canvas.create_text(1000 + 7, 135 + 10,
                                    text='E', fill='black')
        self.ard_canvas.create_rectangle(1000, 155,
                                         1013, 155,
                                         fill='black')
        self.ard_canvas.create_text(1000 + 7, 175 + 10,
                                    text='P', fill='black')
        self.ard_canvas.create_text(1000 + 7, 195 + 10,
                                    text='W', fill='black')
        self.ard_canvas.create_text(1000 + 7, 215 + 10,
                                    text='M', fill='black')
        self.ard_canvas.create_rectangle(1000, self.ard_bckgrd_height - 5,
                                         1013, self.ard_bckgrd_height,
                                         fill='black')
        # Arduino Pin Labels
        self.ard_canvas.create_text(1027 + 6, 9,
                                    text='PINS', fill='white')
        self.ard_canvas.create_text(1027 + 6, 15 + 10,
                                    text='10', fill='white')
        self.ard_canvas.create_text(1027 + 6, 35 + 10,
                                    text='02', fill='white')
        self.ard_canvas.create_text(1027 + 6, 55 + 10,
                                    text='03', fill='white')
        self.ard_canvas.create_text(1027 + 6, 75 + 10,
                                    text='04', fill='white')
        self.ard_canvas.create_text(1027 + 6, 95 + 10,
                                    text='05', fill='white')
        self.ard_canvas.create_text(1027 + 6, 115 + 10,
                                    text='06', fill='white')
        self.ard_canvas.create_text(1027 + 6, 135 + 10,
                                    text='07', fill='white')
        self.ard_canvas.create_text(1027 + 6, 155 + 10,
                                    text='08', fill='white')
        self.ard_canvas.create_text(1027 + 6, 175 + 10,
                                    text='09', fill='white')
        self.ard_canvas.create_text(1027 + 6, 195 + 10,
                                    text='11', fill='white')
        self.ard_canvas.create_text(1027 + 6, 215 + 10,
                                    text='12', fill='white')
        self.ard_canvas.create_text(1027 + 6, 235 + 10,
                                    text='13', fill='white')

    def lj_report_table_config(self):
        """sets up a simple table for reporting lj stats"""
        self.lj_table.set_var(0, 1, 'Before')
        self.lj_table.set_var(0, 2, 'During')
        self.lj_table.set_var(0, 3, 'After')
        self.lj_table.set_var(0, 4, 'Total')
        self.lj_table.set_var(1, 0, 'Time (s)')
        self.lj_table.set_var(2, 0, '# Samples')
        self.lj_table.set_var(3, 0, '# Missed')
        self.lj_table.set_var(4, 0, 'Sample Hz')
        self.lj_table.set_var(5, 0, 'Scan Hz')

    # noinspection PyAttributeOutsideInit
    def render_camera(self):
        """sets up camera feed"""
        frame = Tk.LabelFrame(self.master, text='Camera Feed')
        frame.grid(row=3, column=0)
        self.camera_panel = Tk.Label(frame)
        self.camera_panel.grid(row=0, column=0, sticky=self.ALL)
        self.video_stream()

    # Genera GUI Functions (INTERACTIONS WITH THREADHANDLER AND
    # PROCESS HANDLER ARE IN THIS BLOCK)
    #####################################################################
    def gui_event_loop(self):
        """Master GUI will call this periodically to check for
        thread queue items"""
        try:
            msg = self.master_dump_queue.get_nowait()
            if dirs.settings.debug_console:
                print 'MG -- ', msg
            if msg == '<ex_succ>':
                self.master.destroy()
                self.master.quit()
            elif msg.startswith('<ex_err>'):
                msg = msg[8:].split(',')
                devices = ''
                if 'lj' in msg:
                    devices += 'LabJack, '
                if 'cmr' in msg:
                    devices += 'Camera, '
                if 'ard' in msg:
                    devices += 'Arduino, '
                devices = devices[:-2]
                tkMb.showwarning('Warning!', 'The following devices '
                                             'did not close properly: \n\n'
                                             '[{}]\n\n'
                                             'This may cause issues on subsequent'
                                             ' runs. You may wish to perform a manual'
                                             ' Hard Reset.'.format(devices))
                self.master.destroy()
                self.master.quit()
            elif msg.startswith('<lj>'):
                msg = msg[4:]
                self.lj_status_bar.set(msg)
            elif msg.startswith('<ard>'):
                msg = msg[5:]
                self.ard_status_bar.set(msg)
            elif msg.startswith('<cmr>'):
                msg = msg[5:]
                self.cmr_status_bar.set(msg)
            elif msg.startswith('<exp_end>'):
                self.run_bulk_toggle(running=False)
                self.progbar_started = False
                msg = msg[9:]
                self.save_status_bar.set(msg)
            elif msg.startswith('<threads>'):
                msg = ast.literal_eval(msg[9:])
                self.gui_debug(request_threads=False, msg=msg)
            elif msg in ['<ljst>', '<ardst>', '<cmrst>']:
                if not self.progbar_started:
                    self.progbar.start()
                    self.progbar_started = True
                elif self.progbar_started:
                    pass
            elif msg.startswith('<ljr>'):
                msg = msg[5:].split(',')
                for row in range(5):
                    for column in range(4):
                        self.lj_table.set_var(row=row + 1, column=column + 1,
                                              value=msg[row * 4 + column])
                        time.sleep(0.001)
            elif msg.startswith('<ljm>'):
                msg = msg[5:]
                self.lj_table.set_var(row=3, column=4, value=msg)
        except Queue.Empty:
            pass
        self.master.after(50, self.gui_event_loop)

    # noinspection PyDefaultArgument
    def gui_debug(self, request_threads=True, msg=[]):
        """Under the hood stuff printed when press debug button"""
        if EXECUTABLE:
            tkMb.showinfo('Attn!', 'Please use the Debug Console version'
                                   ' of Mouse House for this feature.')
            return
        else:
            if request_threads:
                self.process_dump_queue.put_nowait('<thr>')
                return
            print '#' * 40 + '\nDEBUG\n' + '#' * 40
            print '\nSETTINGS'
            pprint(vars(dirs.settings))
            print '#' * 15
            print 'CAMERA QUEUE COUNT: {}'.format(self.thread_handler.cmr_device.data_queue.qsize())
            print '#' * 15
            print 'ACTIVE PROCESSES: {}'.format(len(multiprocessing.active_children()) + 1)
            #########################################################
            main_threads = threading.enumerate()
            main_threads_list = []
            main_threads_qfts = 0
            for i in main_threads:
                if i.name != 'QueueFeederThread':
                    main_threads_list.append(i.name)
                else:
                    main_threads_qfts += 1
            print ' - Main Process Threads ({}):'.format(threading.active_count())
            for i in range(len(main_threads_list)):
                print '   {} - {}'.format(i + 1, main_threads_list[i])
            print '     + [{}x] QueueFeederThreads'.format(main_threads_qfts)
            print ' - {} Threads ({}):'.format(multiprocessing.active_children()[0].name, len(msg))
            proc_threads_list = []
            proc_threads_qfts = 0
            for i in msg:
                if i[1] != 'QueueFeederThread':
                    proc_threads_list.append(i[1])
                else:
                    proc_threads_qfts += 1
            for i in range(len(proc_threads_list)):
                print '   {} - {}'.format(i + 1, proc_threads_list[i])
            print '     + [{}x] QueueFeederThreads'.format(proc_threads_qfts)

    def debug_printing(self):
        """more debug messages"""
        if EXECUTABLE:
            tkMb.showinfo('Attn!', 'Please use'
                                   ' the Debug Console version of Mouse'
                                   ' House for this feature.')
            return
        else:
            if self.debug_chk_var.get() == 1:
                dirs.settings.debug_console = True
                self.process_dump_queue.put_nowait('<dbon>')
            else:
                dirs.settings.debug_console = False
                self.process_dump_queue.put_nowait('<dboff>')

    def hard_exit(self, allow=True):
        """Handles devices before exiting for a clean close"""
        if allow:
            self.thread_dump_queue.put_nowait('<exit>')
            self.process_dump_queue.put_nowait('<exit>')
        else:
            tkMb.showwarning('Error!', 'Please STOP the experiment first.',
                             parent=self.master)

    def device_status_msg_toggle(self, var, status, display, name):
        """Hides or displays device statuses depending on
        toggle state
        var: TkInt variable that we check
        status: status msg of the device
        display: the status msg bar of the device
        """
        if var.get() == 0:
            status.set('disabled')
            display.config(state=Tk.DISABLED)
            self.thread_dump_queue.put_nowait('<{}off>'.format(name))
            if name == 'lj':
                self.process_dump_queue.put_nowait('<ljoff>')
        elif var.get() == 1:
            status.set('enabled')
            display.config(state=Tk.NORMAL)
            self.thread_dump_queue.put_nowait('<{}on>'.format(name))
            if name == 'lj':
                self.process_dump_queue.put_nowait('<ljon>')
        # experiment start button is only available if at least one device is enabled
        if self.ard_toggle_var.get() == 0 and self.lj_toggle_var.get() == 0 and self.cmr_toggle_var.get() == 0:
            self.prog_on.config(state=Tk.DISABLED)
        elif self.ard_toggle_var.get() == 1 or self.lj_toggle_var.get() == 1 or self.cmr_toggle_var.get() == 1:
            self.prog_on.config(state=Tk.NORMAL)

    def clear_saves(self):
        """Removes all settings and save directories"""
        if tkMb.askyesno('Warning!', 'This DELETES ALL settings, presets, '
                                     'and data saves!\n It should be '
                                     'used for debugging purposes only.\n\n'
                                     'Are you sure?',
                         default='no', parent=self.master):
            dirs.clear_saves()
            time.sleep(0.5)
            tkMb.showinfo('Finished', 'All settings and saves '
                                      'deleted. Program will now exit.',
                          parent=self.master)
            dirs.save_on_exit = False
            self.hard_exit()

    # Save GUI Methods
    #####################################################################
    # noinspection PyAttributeOutsideInit
    def save_grab_list(self):
        """Updates output save directories list"""
        self.save_dir_list = [d for d
                              in os.listdir(dirs.main_save_dir)
                              if os.path.isdir(dirs.main_save_dir + d)]

    # noinspection PyAttributeOutsideInit
    def save_button_options(self, inputs=None, new=False):
        """Determines whether to make a new save folder or not:"""
        self.save_grab_list()
        ready = 0
        if new:
            new_save_entry = self.new_save_entry.get().lower()
            for i in new_save_entry:
                if i in FORBIDDEN_CHARS:
                    new_save_entry = new_save_entry.replace(i, ' ')
            new_save_entry = new_save_entry.strip()
            if new_save_entry in self.save_dir_list or new_save_entry in self.save_dir_name_used:
                tkMb.showinfo('Error',
                              'You cannot use an existing '
                              'Save Entry Name; '
                              'select it from the top '
                              'dialogue instead.',
                              parent=self.master)
            elif len(new_save_entry) == 0:
                tkMb.showinfo('Error!',
                              'Please enter a name '
                              'for your save directory.',
                              parent=self.master)
            else:
                ready = 1
                menu = self.save_dir_menu.children['menu']
                if len(self.save_dir_list) == 0:
                    menu.delete(0, Tk.END)
                self.save_dir_to_use = str(new_save_entry)
                self.chosen_dir_var.set(self.save_dir_to_use)
                menu.add_command(label=self.save_dir_to_use,
                                 command=lambda path=self.save_dir_to_use:
                                 self.save_button_options(inputs=path))
                self.save_dir_name_used.append(self.save_dir_to_use)
        else:
            ready = 1
            self.chosen_dir_var.set(inputs)
            self.save_dir_to_use = str(self.chosen_dir_var.get())
        if ready == 1:
            self.preresults_dir = str(dirs.main_save_dir) + self.save_dir_to_use + '/'
            if self.preresults_dir not in self.results_dir_used:
                dirs.results_dir = self.preresults_dir + '{}/'.format(format_daytime('daytime'))
                self.make_save_dir = 1
            else:
                dirs.results_dir = self.results_dir_used[self.preresults_dir]
                self.make_save_dir = 0
            self.save_status_var.set(
                'Currently Selected:\n[{}]'.format(
                    lim_str_len(self.save_dir_to_use.upper(), 30)
                )
            )
            dirs.settings.save_dir = self.save_dir_to_use

    # Camera GUI Methods
    #####################################################################
    def video_stream(self):
        """live streams video feed from camera"""
        # try:
        #     print self.thread_handler.cmr_device.data_queue.qsize()
        # except AttributeError:
        #     pass
        try:
            img = self.thread_handler.cmr_device.data_queue.get_nowait()
        except (Queue.Empty, NameError, AttributeError):
            pass
        else:
            img = PhotoImage(Image.fromarray(img).resize((288, 216), Image.ANTIALIAS))
            self.camera_panel.configure(image=img)
            self.camera_panel.image = img
        self.master.after(15, self.video_stream)

    # LabJack GUI Methods
    #####################################################################
    def lj_config(self):
        """Opens LJ GUI for settings config"""
        config = Tk.Toplevel(self.master)
        config_run = LabJackGUI(config, dirs=dirs)
        config_run.run()
        channels, freq = dirs.settings.quick_lj()
        self.lj_status_var.set('Channels:\n{}\n'
                               '\nScan Freq: [{}Hz]'.format(channels, freq))
        self.lj_graph.update_labels(dirs)

    def lj_graph_stream(self):
        """streams data from labjack"""
        try:
            data = self.master_graph_queue.get_nowait()
            #  print self.master_graph_queue.qsize()
        except Queue.Empty:
            pass
        else:
            self.lj_graph.update_plot(data)
        if self.master_graph_queue.qsize() == 0 and self.clear_lj_plot:
            self.lj_graph.clear_plot()
            self.lj_graph.create_new_lines()
            self.clear_lj_plot = False
        self.master.after(15, self.lj_graph_stream)

    # Photometry GUI Functions
    #####################################################################
    def fp_toggle(self):
        """Toggles Photometry options On or Off"""
        if self.fp_toggle_var.get() == 1:
            self.process_dump_queue.put_nowait('<fpon>')
            self.fp_config_button.config(state=Tk.NORMAL)
            ch_num, main_freq, isos_freq = dirs.settings.quick_fp()
            state = 'LabJack Channels: {}\nMain Freq: {}Hz\nIsos Freq: {}Hz'.format(ch_num,
                                                                                    main_freq,
                                                                                    isos_freq)
            self.fp_statustext_var.set(state)
            self.fp_lj_sync()
        elif self.fp_toggle_var.get() == 0:
            self.process_dump_queue.put_nowait('<fpoff>')
            shared_ch = deepcopy([i for i in dirs.settings.fp_last_used['ch_num']
                                  if i in dirs.settings.lj_last_used['ch_num']])
            if len(shared_ch) == 3:
                for i in shared_ch:
                    dirs.settings.lj_last_used['ch_num'].remove(i)
            if len(dirs.settings.lj_last_used['ch_num']) == 0:
                dirs.settings.lj_last_used['ch_num'].append(0)
            dirs.settings.lj_last_used['ch_num'].sort()
            self.lj_status_var.set('Channels:\n{}\n'
                                   '\nScan Freq: [{}Hz]'.format(dirs.settings.lj_last_used['ch_num'],
                                                                dirs.settings.lj_last_used['scan_freq']))
            self.fp_config_button.config(state=Tk.DISABLED)
            self.fp_statustext_var.set('\n[N/A]\n')

    def fp_config(self):
        """Configures photometry options"""
        fp_ch_num_old = deepcopy(dirs.settings.fp_last_used['ch_num'])
        config = Tk.Toplevel(self.master)
        config_run = PhotometryGUI(config, dirs=dirs)
        config_run.run()
        state = 'LabJack Channels: {}\nMain Freq: ' \
                '{}Hz\nIsos Freq: {}Hz'.format(config_run.ch_num,
                                               config_run.stim_freq['main'],
                                               config_run.stim_freq['isos'])
        if len([i for i in fp_ch_num_old if i in dirs.settings.lj_last_used['ch_num']]) == 3:
            for i in fp_ch_num_old:
                dirs.settings.lj_last_used['ch_num'].remove(i)
        self.fp_lj_sync()
        self.fp_statustext_var.set(state)

    def fp_lj_sync(self):
        """synchronizes fp and lj channels used"""
        ch_num = deepcopy(dirs.settings.fp_last_used['ch_num'])
        lj_ch_num = deepcopy(dirs.settings.lj_last_used['ch_num'])
        for i in ch_num:
            if i not in lj_ch_num:
                lj_ch_num.append(i)
        lj_n_ch = len(lj_ch_num)
        if lj_n_ch <= 8:
            dirs.settings.lj_last_used['ch_num'] = lj_ch_num
            dirs.settings.lj_last_used['ch_num'].sort()
            dirs.settings.lj_last_used['scan_freq'] = min(dirs.settings.lj_last_used['scan_freq'],
                                                          int(50000 / lj_n_ch))
            self.lj_status_var.set('Channels:\n{}\n'
                                   '\nScan Freq: [{}Hz]'.format(lj_ch_num, dirs.settings.lj_last_used['scan_freq']))
        elif lj_n_ch > 8:
            tkMb.showinfo('Warning!', 'Enabling photometry has increased the number of LabJack channels '
                                      'in use to {}; the maximum is 8. \n\n'
                                      'Please reconfigure LabJack settings.'.format(lj_n_ch))
            dirs.settings.lj_last_used['ch_num'] = ch_num
            self.lj_config()

    # Arduino GUI Functions
    #####################################################################
    def save_new_preset(self):
        """Saves current settings in a new preset"""
        preset_list = [d for d in dirs.settings.ard_presets]
        preset_name = self.preset_save_entry.get().strip().lower()
        if len(preset_name) == 0:
            tkMb.showerror('Error!', 'You must give your preset a name.',
                           parent=self.master)
            self.preset_save_entry.focus()
        else:
            if preset_name not in preset_list:
                to_save = deepcopy(dirs.settings.ard_last_used)
                dirs.threadsafe_edit(recipient='ard_presets', donor=to_save,
                                     name=preset_name)
                menu = self.ard_preset_menu.children['menu']
                menu.add_command(label=preset_name, command=lambda name=preset_name:
                                 self.ard_grab_data(True, name))
                self.ard_preset_chosen_var.set(preset_name)
                tkMb.showinfo('Saved!', 'Preset saved as '
                                        '[{}]'.format(preset_name),
                              parent=self.master)
            elif preset_name in preset_list:
                if tkMb.askyesno('Overwrite?', '[{}] already exists as '
                                               'a preset. Overwrite it '
                                               'anyway?'.format(preset_name),
                                 parent=self.master):
                    to_save = deepcopy(dirs.settings.ard_last_used)
                    dirs.threadsafe_edit(recipient='ard_presets', donor=to_save,
                                         name=preset_name)
                    tkMb.showinfo('Saved!', 'Preset saved as '
                                            '[{}]'.format(preset_name),
                                  parent=self.master)

    def ard_config(self, types):
        """Presents the requested Arduino GUI"""
        config = Tk.Toplevel(self.master)
        config_run = ArduinoGUI(config, dirs=dirs)
        if types == 'tone':
            config_run.tone_setup()
        elif types == 'output':
            config_run.output_setup()
        elif types == 'pwm':
            config_run.pwm_setup()
        config_run.run()
        # Now we load these settings
        # back into settings.ard_last_used
        if not config_run.hard_closed:
            data = config_run.return_data
            if config_run.types == 'tone':
                dirs.settings.ard_last_used['packet'][4] = len(data)
                dirs.settings.ard_last_used['tone_pack'] = []
                for i in data:
                    dirs.settings.ard_last_used['tone_pack'].append(["<LLH"] + i)
                dirs.settings.ard_last_used['tone_pack'] = sorted(dirs.settings.ard_last_used['tone_pack'],
                                                                  key=itemgetter(1))
            if config_run.types == 'output':
                dirs.settings.ard_last_used['packet'][5] = len(data)
                dirs.settings.ard_last_used['out_pack'] = []
                for i in data:
                    dirs.settings.ard_last_used['out_pack'].append(["<LB", i, data[i]])
                dirs.settings.ard_last_used['out_pack'] = sorted(dirs.settings.ard_last_used['out_pack'],
                                                                 key=itemgetter(1))
            if config_run.types == 'pwm':
                dirs.settings.ard_last_used['packet'][6] = len(data)
                dirs.settings.ard_last_used['pwm_pack'] = []
                for i in data:
                    dirs.settings.ard_last_used['pwm_pack'].append(["<LLLfBBf"] + i)
                dirs.settings.ard_last_used['pwm_pack'] = sorted(dirs.settings.ard_last_used['pwm_pack'],
                                                                 key=itemgetter(2))
            self.ard_grab_data(destroy=True)

    def ard_get_time(self):
        """Gets total exp time from GUI input and uses it if if is >= max time
        of all stimuli components"""
        max_stim_time = []
        for i in dirs.settings.ard_last_used['tone_pack']:
            max_stim_time.append(i[2])
        for i in dirs.settings.ard_last_used['out_pack']:
            max_stim_time.append(i[1])
        for i in dirs.settings.ard_last_used['pwm_pack']:
            max_stim_time.append(i[3])
        try:
            max_stim_time = max(max_stim_time)
        except ValueError:
            max_stim_time = 0
        try:
            # Grab Inputs
            mins = int(self.min_entry.get().strip())
            secs = int(self.sec_entry.get().strip())
            mins += secs // 60
            secs %= 60
            # Update Fields if improper format entered
            self.min_entry.delete(0, Tk.END)
            self.min_entry.insert(Tk.END, '{:0>2}'.format(mins))
            self.sec_entry.delete(0, Tk.END)
            self.sec_entry.insert(Tk.END, '{:0>2}'.format(secs))
            # Update Vairbales
            self.ttl_time = (mins * 60 + secs) * 1000
            if self.ttl_time < max_stim_time:
                self.ttl_time = deepcopy(max_stim_time)
                max_stim_time /= 1000
                mins = max_stim_time // 60
                secs = max_stim_time % 60
                tkMb.showinfo('Error!', 'Total time cannot be less than '
                                        '[{}:{}] because one of the stimuli segments'
                                        ' exceeds this value. \n\n'
                                        'Reconfigure your stimuli if you wish to'
                                        ' reduce total '
                                        'time further.'.format(mins, secs))
                self.min_entry.delete(0, Tk.END)
                self.min_entry.insert(Tk.END, '{:0>2}'.format(mins))
                self.sec_entry.delete(0, Tk.END)
                self.sec_entry.insert(Tk.END, '{:0>2}'.format(secs))
            dirs.settings.ard_last_used['packet'][3] = self.ttl_time
            self.ard_grab_data(destroy=True)
        except ValueError:
            tkMb.showinfo('Error!',
                          'Time must be entered as integers',
                          parent=self.master)

    # noinspection PyAttributeOutsideInit
    def ard_update_preset_list(self):
        """List of all Arduino Presets"""
        self.ard_preset_list = [i for i in dirs.settings.ard_presets]

    # noinspection PyAttributeOutsideInit
    def ard_grab_data(self, destroy=False, load=False):
        """Obtain arduino data from saves"""
        # If load is false, then we load from settings.mshs
        if load is not False:
            # Then load must be a preset name.
            dirs.settings.ard_last_used = deepcopy(dirs.settings.ard_presets[load])
            # Update Total Time Fields
            last_used_time = dirs.settings.ard_last_used['packet'][3] / 1000
            self.min_entry.delete(0, Tk.END)
            self.sec_entry.delete(0, Tk.END)
            self.min_entry.insert(Tk.END, '{}'.format(format_secs(last_used_time,
                                                                  option='min')))
            self.sec_entry.insert(Tk.END, '{}'.format(format_secs(last_used_time,
                                                                  option='sec')))
            self.ard_preset_chosen_var.set(load)
        if destroy:
            self.ard_canvas.delete(self.progress_shape)
            self.ard_canvas.delete(self.progress_text)
            for i in self.v_bars:
                self.ard_canvas.delete(i)
            for i in self.bar_times:
                self.ard_canvas.delete(i)
            for i in self.tone_bars:
                self.balloon.tagunbind(self.ard_canvas, i)
                self.ard_canvas.delete(i)
            for i in self.out_bars:
                self.balloon.tagunbind(self.ard_canvas, i)
                self.ard_canvas.delete(i)
            for i in self.pwm_bars:
                self.balloon.tagunbind(self.ard_canvas, i)
                self.ard_canvas.delete(i)
        divisor = 5 + 5 * int(dirs.settings.ard_last_used['packet'][3] / 300000)
        segment = float(dirs.settings.ard_last_used['packet'][3] / 1000) / divisor
        self.v_bars = [[]] * (1 + int(round(segment)))
        self.bar_times = [[]] * (1 + int(round(segment)))
        for i in range(int(round(segment))):
            if i > 0:
                if i % 2 != 0:
                    self.v_bars[i] = self.ard_canvas.create_rectangle(i * (1000.0 / segment) - 1,
                                                                      15,
                                                                      i * (1000.0 / segment) + 1,
                                                                      self.ard_bckgrd_height - 5,
                                                                      fill='white')
                if i % 2 == 0:
                    self.v_bars[i] = self.ard_canvas.create_rectangle(i * (1000.0 / segment) - 1,
                                                                      15,
                                                                      i * (1000.0 / segment) + 1,
                                                                      self.ard_bckgrd_height,
                                                                      fill='white')
                    self.bar_times[i] = self.ard_canvas.create_text(i * (1000.0 / segment),
                                                                    self.ard_bckgrd_height + 8,
                                                                    text=format_secs(divisor * i),
                                                                    fill='black',
                                                                    font=self.time_label_font)
                if i == int(round(segment)) - 1 and (i + 1) % 2 == 0 and (i + 1) * (1000.0 / segment) <= 1001:
                    if round((i + 1) * (1000.0 / segment)) != 1000.0:
                        self.v_bars[i + 1] = self.ard_canvas.create_rectangle((i + 1) * (1000.0 / segment) - 1,
                                                                              15,
                                                                              (i + 1) * (1000.0 / segment) + 1,
                                                                              self.ard_bckgrd_height,
                                                                              fill='white')
                    elif round((i + 1) * (1000.0 / segment)) == 1000:
                        self.v_bars[i + 1] = self.ard_canvas.create_rectangle((i + 1) * (1000.0 / segment) - 1,
                                                                              self.ard_bckgrd_height - 5,
                                                                              (i + 1) * (1000.0 / segment) + 1,
                                                                              self.ard_bckgrd_height,
                                                                              fill='white')
                    self.bar_times[i + 1] = self.ard_canvas.create_text((i + 1) * (1000.0 / segment),
                                                                        self.ard_bckgrd_height + 8,
                                                                        text=format_secs(divisor * (i + 1)),
                                                                        fill='black',
                                                                        font=self.time_label_font)
                if i == int(round(segment)) - 1 and (i + 1) % 2 != 0 and (i + 1) * (1000.0 / segment) <= 1001:
                    if round((i + 1) * (1000.0 / segment)) != 1000.0:
                        self.v_bars[i + 1] = self.ard_canvas.create_rectangle((i + 1) * (1000.0 / segment) - 1,
                                                                              15,
                                                                              (i + 1) * (1000.0 / segment) + 1,
                                                                              self.ard_bckgrd_height,
                                                                              fill='white')
                    elif round((i + 1) * (1000.0 / segment)) == 1000:
                        self.v_bars[i + 1] = self.ard_canvas.create_rectangle((i + 1) * (1000.0 / segment) - 1,
                                                                              self.ard_bckgrd_height - 5,
                                                                              (i + 1) * (1000.0 / segment) + 1,
                                                                              self.ard_bckgrd_height,
                                                                              fill='white')
        self.tone_data, self.out_data, self.pwm_data = -1, -1, -1
        self.tone_bars = []
        if len(dirs.settings.ard_last_used['tone_pack']) != 0:
            self.tone_data = self.ard_decode_data('tone', dirs.settings.ard_last_used['tone_pack'])
            self.tone_bars = [[]] * len(self.tone_data)
            for i in range(len(self.tone_data)):
                self.tone_bars[i] = self.ard_canvas.create_rectangle(self.tone_data[i][0],
                                                                     0 + 15,
                                                                     self.tone_data[i][1] + self.tone_data[i][0],
                                                                     35, fill='yellow', outline='blue')
                self.balloon.tagbind(self.ard_canvas,
                                     self.tone_bars[i],
                                     '{} - {}\n{} Hz'.format(
                                         format_secs(
                                             self.tone_data[i][4] / 1000),
                                         format_secs(
                                             self.tone_data[i][5] / 1000),
                                         self.tone_data[i][3]))
        self.out_bars = []
        if len(dirs.settings.ard_last_used['out_pack']) != 0:
            pin_ids = range(2, 8)
            self.out_data = self.ard_decode_data('output',
                                                 dirs.settings.ard_last_used['out_pack'])
            self.out_bars = [[]] * len(self.out_data)
            for i in range(len(self.out_data)):
                y_pos = 35 + (pin_ids.index(self.out_data[i][3])) * 20
                self.out_bars[i] = self.ard_canvas.create_rectangle(self.out_data[i][0],
                                                                    y_pos,
                                                                    self.out_data[i][1] + self.out_data[i][0],
                                                                    y_pos + 20,
                                                                    fill='yellow', outline='blue')
                self.balloon.tagbind(self.ard_canvas,
                                     self.out_bars[i],
                                     '{} - {}\nPin {}'.format(
                                         format_secs(
                                             self.out_data[i][4] / 1000),
                                         format_secs(
                                             self.out_data[i][5] / 1000),
                                         self.out_data[i][3]))
        self.pwm_bars = []
        if len(dirs.settings.ard_last_used['pwm_pack']) != 0:
            pin_ids = range(8, 14)
            pin_ids.remove(10)
            self.pwm_data = self.ard_decode_data('pwm', dirs.settings.ard_last_used['pwm_pack'])
            self.pwm_bars = [[]] * len(self.pwm_data)
            for i in range(len(self.pwm_data)):
                y_pos = 155 + (pin_ids.index(self.pwm_data[i][3])) * 20
                self.pwm_bars[i] = self.ard_canvas.create_rectangle(self.pwm_data[i][0],
                                                                    y_pos,
                                                                    self.pwm_data[i][1] + self.pwm_data[i][0],
                                                                    y_pos + 20,
                                                                    fill='yellow', outline='blue')
                self.balloon.tagbind(self.ard_canvas,
                                     self.pwm_bars[i],
                                     ('{} - {}\n'
                                      'Pin {}\n'
                                      'Freq: {}Hz\n'
                                      'Duty Cycle: {}%\n'
                                      'Phase Shift: {}' + u'\u00b0').format(
                                         format_secs(self.pwm_data[i][7] / 1000),
                                         format_secs(self.pwm_data[i][8] / 1000),
                                         self.pwm_data[i][3],
                                         self.pwm_data[i][4],
                                         self.pwm_data[i][5],
                                         self.pwm_data[i][6]))
        self.progress_shape = self.ard_canvas.create_rectangle(-1, 0,
                                                               1, self.ard_bckgrd_height,
                                                               fill='red')
        self.progress_text = self.ard_canvas.create_text(35, 0,
                                                         fill='white',
                                                         anchor=Tk.N,
                                                         font=self.small_label_font)
        self.progbar = ProgressBar(self.master,
                                   self.ard_canvas,
                                   self.progress_shape,
                                   self.progress_text,
                                   dirs.settings.ard_last_used['packet'][3])

    @staticmethod
    def ard_decode_data(name, data_source):
        """Read packed up Arduino Data and puts it in proper format"""
        time_seg = float(dirs.settings.ard_last_used['packet'][3]) / 1000
        if name == 'tone':
            start, on = 1, 2
        elif name == 'pwm':
            start, on = 2, 3
        elif name == 'output':
            indiv_trigs, indiv_times, trig_times, final_intv = [], [], {}, []
            start, on, = 1, 2
            for i in data_source:
                triggers = check_binary(i[2], 'D')
                for n in triggers:
                    indiv_trigs.append(n)
                    indiv_times.append(i[1])
            for i in range(len(indiv_trigs)):
                n = indiv_trigs[i]
                try:
                    trig_times[n].append(indiv_times[i])
                except KeyError:
                    trig_times[n] = [indiv_times[i]]
            for i in trig_times:
                for n in range(len(trig_times[i])):
                    if n % 2 == 0:
                        final_intv.append([i,
                                           trig_times[i][n],
                                           trig_times[i][n + 1]])
            final_intv = sorted(final_intv,
                                key=itemgetter(1))
            data_source = final_intv
        ard_data = []
        for i in data_source:
            start_space = (float(i[start]) / time_seg)
            on_space = float(i[on]) / time_seg - start_space
            if on_space == 0:
                start_space -= 1
                on_space = 1
            off_space = 1000 - on_space - start_space
            if name == 'tone':
                ard_data.append([start_space,
                                 on_space,
                                 off_space,
                                 i[3],
                                 i[start],
                                 i[on]])
            elif name == 'pwm':
                ard_data.append([start_space,
                                 on_space,
                                 off_space,
                                 check_binary(i[5], 'B')[0],
                                 i[4],
                                 i[7],
                                 i[6],
                                 i[start],
                                 i[on]])
            elif name == 'output':
                ard_data.append([start_space,
                                 on_space,
                                 off_space,
                                 i[0],
                                 i[start],
                                 i[on]])
        return ard_data

    # THESE FUNCTIONS INTERACT WITH THREAD HANDLER THROUGH QUEUES
    #####################################################################
    # Running the Experiment
    #####################################################################
    # noinspection PyAttributeOutsideInit
    def progbar_run(self):
        """Check if valid settings, make directories, and start progress bar"""
        # Check folders are available
        self.clear_lj_plot = True
        self.lj_table.clear()
        if len(self.save_dir_list) == 0 and len(self.results_dir_used) == 0 and dirs.settings.save_dir == '':
            tkMb.showinfo('Error!',
                          'You must first create a directory to save data output.',
                          parent=self.master)
            return
        # save file naming
        file_name = self.name_entry.get().strip()
        for i in file_name:
            if i in FORBIDDEN_CHARS:
                file_name = file_name.replace(i, ' ')
        if file_name == '':
            file_name = 'no_name'
        file_name = file_name.strip()
        file_name_to_send = '{}-{}'.format(self.data_save_count, file_name)
        self.data_save_count += 1
        # Make sure we actually have a place to save files:
        if len(self.results_dir_used) == 0:
            self.preresults_dir = str(dirs.main_save_dir) + dirs.settings.save_dir + '/'
            dirs.results_dir = self.preresults_dir + '{}/'.format(format_daytime('daytime'))
            self.make_save_dir = 1
            self.save_status_var.set('Currently Selected:\n[{}]'.format(
                lim_str_len(dirs.settings.save_dir.upper(), 30)))
        if self.make_save_dir == 1 or not os.path.isdir(dirs.results_dir):
            os.makedirs(dirs.results_dir)
            self.results_dir_used[self.preresults_dir] = dirs.results_dir
            self.make_save_dir = 0
            self.save_grab_list()
        # Run
        run_msg = '<run>'
        self.thread_dump_queue.put_nowait('<sfn>{}'.format(file_name_to_send))
        self.thread_dump_queue.put_nowait(run_msg)
        self.process_dump_queue.put_nowait(run_msg)
        self.process_dump_queue.put_nowait(dirs.settings)
        self.process_dump_queue.put_nowait(dirs.results_dir)
        self.process_dump_queue.put_nowait(file_name_to_send)
        self.save_status_bar.set('Started.')
        self.run_bulk_toggle(running=True)

    def progbar_stop(self):
        """performs a hard stop on the experiment"""
        self.thread_dump_queue.put_nowait('<hardstop>')
        self.process_dump_queue.put_nowait('<hardstop>')
        self.progbar.stop()

    def run_bulk_toggle(self, running):
        """Toggles all non-essential buttons to active
        or disabled based on running state"""
        if running:
            self.master.protocol('WM_DELETE_WINDOW',
                                 lambda: self.hard_exit(allow=False))
            self.prog_off.config(state=Tk.NORMAL)
            self.prog_on.config(state=Tk.DISABLED)
            self.fp_toggle_button.config(state=Tk.DISABLED)
            self.fp_config_button.config(state=Tk.DISABLED)
            self.save_dir_menu.config(state=Tk.DISABLED)
            self.new_save_entry.config(state=Tk.DISABLED)
            self.new_save_button.config(state=Tk.DISABLED)
            self.lj_config_button.config(state=Tk.DISABLED)
            # self.debug_button.config(state=Tk.DISABLED)
            # self.clr_svs_button.config(state=Tk.DISABLED)
            self.ard_preset_menu.config(state=Tk.DISABLED)
            self.min_entry.config(state=Tk.DISABLED)
            self.sec_entry.config(state=Tk.DISABLED)
            self.ard_time_confirm_button.config(state=Tk.DISABLED)
            self.tone_setup_button.config(state=Tk.DISABLED)
            self.out_setup_button.config(state=Tk.DISABLED)
            self.pwm_setup_button.config(state=Tk.DISABLED)
            self.ard_toggle_button.config(state=Tk.DISABLED)
            self.lj_toggle_button.config(state=Tk.DISABLED)
            self.cmr_toggle_button.config(state=Tk.DISABLED)
            self.preset_save_button.config(state=Tk.DISABLED)
            self.preset_save_entry.config(state=Tk.DISABLED)
        if not running:
            self.master.protocol('WM_DELETE_WINDOW', self.hard_exit)
            self.prog_off.config(state=Tk.DISABLED)
            self.prog_on.config(state=Tk.NORMAL)
            self.fp_toggle_button.config(state=Tk.NORMAL)
            if self.fp_toggle_var.get() == 1:
                self.fp_config_button.config(state=Tk.NORMAL)
            self.save_dir_menu.config(state=Tk.NORMAL)
            self.new_save_entry.config(state=Tk.NORMAL)
            self.new_save_button.config(state=Tk.NORMAL)
            self.lj_config_button.config(state=Tk.NORMAL)
            # self.debug_button.config(state=Tk.NORMAL)
            # self.clr_svs_button.config(state=Tk.NORMAL)
            self.ard_preset_menu.config(state=Tk.NORMAL)
            self.min_entry.config(state=Tk.NORMAL)
            self.sec_entry.config(state=Tk.NORMAL)
            self.ard_time_confirm_button.config(state=Tk.NORMAL)
            self.tone_setup_button.config(state=Tk.NORMAL)
            self.out_setup_button.config(state=Tk.NORMAL)
            self.pwm_setup_button.config(state=Tk.NORMAL)
            self.ard_toggle_button.config(state=Tk.NORMAL)
            self.lj_toggle_button.config(state=Tk.NORMAL)
            self.cmr_toggle_button.config(state=Tk.NORMAL)
            self.preset_save_button.config(state=Tk.NORMAL)
            self.preset_save_entry.config(state=Tk.NORMAL)


#################################################################
# Concurrency Processors
class GUIThreadHandler(threading.Thread):
    """Handles all non-gui processing and communicates
    with GUI via queue polling"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.name = 'Subthread Handler'
        # Thread handling
        # Queues
        self.master_dump_queue = MASTER_DUMP_QUEUE
        self.thread_dump_queue = THREAD_DUMP_QUEUE
        self.process_dump_queue = PROCESS_DUMP_QUEUE
        #####
        self.lj_read_ready_lock = LJ_READ_READY_LOCK
        self.lj_exp_ready_lock = LJ_EXP_READY_LOCK
        self.ard_ready_lock = ARD_READY_LOCK
        self.cmr_ready_lock = CMR_READY_LOCK
        # Devices
        self.lj_connected = False
        self.lj_running = False
        self.cmr_device = None
        self.ard_device = None
        # Use this device?
        self.lj_use = True
        self.ard_use = True
        self.cmr_use = True
        self.lj_created = False
        self.ard_created = False
        self.cmr_created = False
        self.devices_created = False
        # main handler loop
        self.hard_stop_experiment = False
        self.exp_is_running = False
        self.running = True
        # file name handling
        self.save_file_name = ''

    def run(self):
        """Periodically processes queue instructions from
        master gui; (starts the thread)"""
        # because the camera needs to immediately start streaming,
        # we set it up now if possible
        self.cmr_device = FireFly(lj_exp_ready_lock=self.lj_exp_ready_lock,
                                  cmr_ready_lock=self.cmr_ready_lock,
                                  ard_ready_lock=self.ard_ready_lock,
                                  master_gui_queue=self.master_dump_queue,
                                  dirs=dirs)
        if self.cmr_device.initialize():
            camera_thread = threading.Thread(target=self.cmr_device.camera_run,
                                             name='Camera Stream')
            camera_thread.daemon = True
            camera_thread.start()
            self.cmr_created = True
        # loops until we exit the program
        while self.running:
            time.sleep(0.01)
            try:
                msg = self.thread_dump_queue.get_nowait()
            except Queue.Empty:
                pass
            else:
                if msg == '<run>':
                    if not self.devices_created:
                        if all(self.create_devices()):
                            self.devices_created = True
                        else:
                            self.master_dump_queue.put_nowait('<exp_end>*** Failed to Initiate '
                                                              'one of the selected devices.')
                    if self.devices_created and all(self.check_connections()):
                        # devices needed are connected. start exp
                        if self.cmr_use:
                            self.cmr_device.save_file_name = self.save_file_name
                            self.cmr_device.recording = True
                        if self.lj_use:
                            self.lj_running = True
                        if self.ard_use:
                            ard_thread = threading.Thread(target=self.ard_device.run_experiment,
                                                          name='Arduino Control')
                            ard_thread.daemon = True
                            ard_thread.start()
                            self.ard_device.running = True
                        self.exp_is_running = True
                    else:
                        self.master_dump_queue.put_nowait('<exp_end>*** Failed to Initiate '
                                                          'one of the selected devices.')
                elif msg.startswith('<sfn>'):
                    self.save_file_name = msg[5:]
                elif msg == '<hardstop>':
                    self.hard_stop_experiment = True
                    try:
                        self.ard_device.hard_stopped = True
                        self.ard_device.running = False
                    except AttributeError:
                        pass
                    try:
                        self.cmr_device.hard_stopped = True
                        self.cmr_device.recording = False
                    except AttributeError:
                        pass
                elif msg == '<ljoff>':
                    self.lj_use = False
                elif msg == '<ardoff>':
                    self.ard_use = False
                    self.ard_ready_lock.set()
                elif msg == '<cmroff>':
                    self.cmr_use = False
                    self.cmr_ready_lock.set()
                elif msg == '<ljon>':
                    self.lj_use = True
                    self.devices_created = False
                elif msg == '<ardon>':
                    self.ard_use = True
                    self.ard_ready_lock.clear()
                    self.devices_created = False
                elif msg == '<cmron>':
                    self.cmr_use = True
                    self.cmr_ready_lock.clear()
                    self.devices_created = False
                elif msg == '<lj_run_false>':
                    self.lj_running = False
                elif msg == '<exit>':
                    self.close_devices()
                if dirs.settings.debug_console:
                    print 'TH -- ', msg
            if self.devices_created and self.exp_is_running:
                devices_to_check = []
                if self.cmr_use:
                    devices_to_check.append(self.cmr_device.recording)
                if self.lj_use:
                    devices_to_check.append(self.lj_running)
                if self.ard_use:
                    devices_to_check.append(self.ard_device.running)
                if not any(devices_to_check):
                    msg_with_save_status = '<exp_end>'
                    if self.hard_stop_experiment:
                        msg_with_save_status += 'Terminated.'
                        self.hard_stop_experiment = False
                    elif not self.hard_stop_experiment:
                        msg_with_save_status += "Data saved in '{}'".format(dirs.results_dir)
                    self.master_dump_queue.put_nowait(msg_with_save_status)
                    self.exp_is_running = False

    def check_connections(self):
        """Checks that user enabled devices are ready to go"""
        devices_ready = []
        if self.lj_use:
            lj_conn_status = self.thread_dump_queue.get()
            if lj_conn_status == '<lj_connected>':
                self.lj_connected = True
            elif lj_conn_status == '<lj_conn_failed>':
                self.lj_connected = False
            devices_ready.append(self.lj_connected)
        if self.ard_use:
            self.ard_device.check_connection()
            devices_ready.append(self.ard_device.connected)
        if self.cmr_use:
            # we already checked connection in the cmr
            # initialize function.
            devices_ready.append(self.cmr_device.connected)
        return devices_ready

    def create_devices(self):
        """Creates device instances"""
        devices_ready = []
        # Labjack
        if self.lj_use and not self.lj_created:
            lj_status = self.thread_dump_queue.get()
            if dirs.settings.debug_console:
                print 'TH -- ', lj_status
            if lj_status == '<lj_created>':
                self.lj_created = True
            elif lj_status == '<lj_create_failed>':
                self.lj_created = False
            devices_ready.append(self.lj_created)
        # camera
        if self.cmr_use and not self.cmr_created:
            if self.cmr_device.initialize():
                camera_thread = threading.Thread(target=self.cmr_device.camera_run,
                                                 name='CameraStreamThread')
                camera_thread.daemon = True
                camera_thread.start()
                self.cmr_created = True
                devices_ready.append(self.cmr_created)
        # arduino
        if self.ard_use and not self.ard_created:
            self.ard_device = ArduinoUno(lj_exp_ready_lock=self.lj_exp_ready_lock,
                                         ard_ready_lock=self.ard_ready_lock,
                                         cmr_ready_lock=self.cmr_ready_lock,
                                         master_gui_queue=self.master_dump_queue,
                                         dirs=dirs)
            self.master_dump_queue.put_nowait('<ard>Arduino initialized! Waiting for'
                                              ' other selected devices to begin...')
            self.ard_created = True
            devices_ready.append(self.ard_created)
        return devices_ready

    def close_devices(self):
        """attempts to close hardware properly, and reports
        close status to GUI"""
        cmr_error, ard_error = False, False
        lj_error = self.thread_dump_queue.get()
        if lj_error == '<lj_ex_err>':
            lj_error = True
        elif lj_error == '<lj_ex_succ>':
            lj_error = False
        # camera
        try:
            self.cmr_device.close()
            if dirs.settings.debug_console:
                print 'Camera Closed Successfully.'
        except fc2.ApiError:
            cmr_error = True
        except AttributeError:
            pass
        # ... and arduino
        try:
            self.ard_device.serial.close()
            if dirs.settings.debug_console:
                print 'Arduino Closed Successfully.'
        except serial.SerialException:
            ard_error = True
        except AttributeError:
            pass
        if any((lj_error, cmr_error, ard_error)):
            error_msg = '<ex_err>'
            if lj_error:
                error_msg += 'lj,'
            if cmr_error:
                error_msg += 'cmr,'
            if ard_error:
                error_msg += 'ard,'
            error_msg = error_msg[:-1]
            self.master_dump_queue.put_nowait(error_msg)
        else:
            self.master_dump_queue.put_nowait('<ex_succ>')
        self.running = False


class LJProcessHandler(multiprocessing.Process):
    """Handles all labjack instructions on a separate process
    for maximum labjack stream rates"""

    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self.name = 'LabJack Process Handler'
        # Concurrency Controls
        self.master_dump_queue = MASTER_DUMP_QUEUE
        self.master_graph_queue = MASTER_GRAPH_QUEUE
        self.thread_dump_queue = THREAD_DUMP_QUEUE
        self.process_dump_queue = PROCESS_DUMP_QUEUE
        #####
        self.lj_read_ready_lock = LJ_READ_READY_LOCK
        self.lj_exp_ready_lock = LJ_EXP_READY_LOCK
        self.ard_ready_lock = ARD_READY_LOCK
        self.cmr_ready_lock = CMR_READY_LOCK
        # LJ parameters
        self.lj_device = None
        # Use this device?
        self.lj_use = True
        self.lj_created = False
        # main handler loop
        self.hard_stop_experiment = False
        self.exp_is_running = False
        self.running = True
        # Grab settings from main process
        self.settings = None
        self.results_dir = None
        # fp settings for save purposes
        self.fp_used = False
        # save file name
        self.file_name = ''

    def run(self):
        """periodically checks for instructions from
        self.process_dump_queue and performs them"""
        self.settings = self.process_dump_queue.get()
        while self.running:
            time.sleep(0.01)
            try:
                msg = self.process_dump_queue.get_nowait()
            except Queue.Empty:
                pass
            else:
                if msg == '<run>':
                    # grab dirs.settings from main process
                    self.settings = self.process_dump_queue.get()
                    self.results_dir = self.process_dump_queue.get()
                    self.file_name = self.process_dump_queue.get()
                    self.create_lj()
                    if self.lj_created and self.check_lj_connected():
                        if self.lj_use:
                            lj_stream_thread = threading.Thread(target=self.lj_device.read_stream_data,
                                                                args=(self.settings,),
                                                                name='LabJack Stream')
                            lj_stream_thread.daemon = True
                            lj_write_thread = threading.Thread(target=self.lj_device.data_write_plot,
                                                               args=(self.results_dir, self.fp_used, self.file_name),
                                                               name='LabJack Data Write')
                            lj_write_thread.daemon = True
                            lj_write_thread.start()
                            lj_stream_thread.start()
                            self.lj_device.running = True
                            self.exp_is_running = True
                elif msg == '<hardstop>':
                    self.hard_stop_experiment = True
                    try:
                        self.lj_device.hard_stopped = True
                        self.lj_device.running = False
                    except AttributeError:
                        pass
                elif msg == '<ljoff>':
                    self.lj_use = False
                    self.lj_read_ready_lock.set()
                    self.lj_exp_ready_lock.set()
                elif msg == '<ljon>':
                    self.lj_use = True
                    self.lj_read_ready_lock.clear()
                    self.lj_exp_ready_lock.clear()
                elif msg == '<dbon>':
                    self.settings.debug_console = True
                elif msg == '<dboff>':
                    self.settings.debug_console = False
                elif msg == '<exit>':
                    self.close_lj()
                elif msg == '<fpon>':
                    self.fp_used = True
                elif msg == '<fpoff>':
                    self.fp_used = False
                elif msg == '<thr>':
                    threads = threading.enumerate()
                    thread_list = []
                    for i in range(len(threads)):
                        thread_list.append([i, threads[i].name])
                    self.master_dump_queue.put_nowait('<threads>{}'.format(thread_list))
                if self.settings.debug_console:
                    print 'CP -- ', msg
            if self.lj_created and not self.lj_device.running and self.exp_is_running:
                self.thread_dump_queue.put_nowait('<lj_run_false>')
                self.exp_is_running = False
                self.hard_stop_experiment = False

    def create_lj(self):
        """creates new LJ object"""
        if self.lj_use and not self.lj_created:
            try:
                self.master_dump_queue.put_nowait('<lj>Creating LabJack Instance...')
                self.lj_device = LabJackU6(ard_ready_lock=self.ard_ready_lock,
                                           cmr_ready_lock=self.cmr_ready_lock,
                                           lj_read_ready_lock=self.lj_read_ready_lock,
                                           lj_exp_ready_lock=self.lj_exp_ready_lock,
                                           master_dump_queue=self.master_dump_queue,
                                           master_graph_queue=self.master_graph_queue)
                self.lj_created = True
                self.thread_dump_queue.put_nowait('<lj_created>')
            except (LabJackException, LowlevelErrorException):
                self.master_dump_queue.put_nowait('<lj>** LabJack could not be initialized! '
                                                  'Please perform a manual hard reset (disconnect'
                                                  '/reconnect)')
                self.lj_created = False
                self.thread_dump_queue.put_nowait('<lj_create_failed>')

    def check_lj_connected(self):
        """checks that the labjack is connected if requested"""
        if self.lj_use:
            self.lj_device.check_connection()
            if self.lj_device.connected:
                self.thread_dump_queue.put_nowait('<lj_connected>')
            elif not self.lj_device.connected:
                self.thread_dump_queue.put_nowait('<lj_conn_failed>')
            return self.lj_device.connected

    def close_lj(self):
        """closes the labjack"""
        lj_error = False
        try:
            self.lj_device.streamStop()
            self.lj_device.close()
            if self.settings.debug_console:
                print 'LabJack Closed Successfully [SC]'
        except (LabJackException, LowlevelErrorException):
            try:
                self.lj_device.close()
                self.lj_device.streamStop()
                if self.settings.debug_console:
                    print 'LabJack Closed Successfully [CS]'
            except (LabJackException, LowlevelErrorException):
                try:
                    self.lj_device.close()
                    if self.settings.debug_console:
                        print 'LabJack Closed Successfully [N]'
                except LabJackException:
                    if self.settings.debug_console:
                        print 'LabJack Close Unsuccessful.'
                    lj_error = True
        except AttributeError:
            pass
        if lj_error:
            self.thread_dump_queue.put_nowait('<lj_ex_err>')
        elif not lj_error:
            self.thread_dump_queue.put_nowait('<lj_ex_succ>')
        self.running = False


#################################################################
#################################################################
if __name__ == '__main__':

    # Add freeze support for windows executables
    multiprocessing.freeze_support()

    # Open Tkinter instance
    tcl_main_root = Tk.Tk()

    # Setup all Directories
    dirs = Directories()
    # Load last used settings
    dirs.load(EXECUTABLE=EXECUTABLE)

    # Run Main Loop
    main = MasterGUI(tcl_main_root)
    main.master.mainloop()

    # Save Settings for Next Run
    if dirs.save_on_exit:
        dirs.save()
#################################################################
