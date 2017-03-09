# coding=utf-8

"""PyQt4 Version of Mouse House"""


from Dirs_Settings import *
from Custom_Qt_Widgets import *
import multiprocessing as mp
from PyQt4 import QtGui


class GUI_Master(QtGui.QMainWindow):
    """Main GUI Window"""

    def __init__(self, parent=None):
        super(GUI_Master, self).__init__(parent)
        self.setWindowTitle('Mouse House')
        # Setup Main Widget Windows
        self.setMinimumWidth(1280)
        self.setMinimumHeight(700)
        self.exp_tab = GUI_RunExperiment(self)
        self.config_tab = GUI_ConfigSettings(self)
        # Setup Main Tabbed Widget
        self.gui_tabs = QtGui.QTabWidget(self)
        self.gui_tabs.addTab(self.exp_tab, 'Run Experiment')
        self.gui_tabs.addTab(self.config_tab, 'Configuration')
        # Finish and Show
        self.setCentralWidget(self.gui_tabs)
        self.show()

    def closeEvent(self, QCloseEvent):
        """Reimplements self.closeEvent: exits program if experiment not running"""
        if not self.exp_tab.exp_widget.main_prog_gfx.bar_gfx_running:
            super(GUI_Master, self).closeEvent(QCloseEvent)
        else:
            QCloseEvent.ignore()
            GUI_Message(msg='Cannot exit while experiment is running!')


class GUI_RunExperiment(QtGui.QWidget):
    """GUI Page for running and monitoring experiment progress"""

    def __init__(self, parent):
        super(GUI_RunExperiment, self).__init__(parent)
        # Grid Layout
        self.grid = QtGui.QGridLayout()
        # Render Widgets
        self.progbar_render()
        self.camera_render()
        # Finalize
        self.add_to_grid()
        self.setLayout(self.grid)

    def progbar_render(self):
        """Renders the experiment progress bar"""
        self.exp_widget = GUI_ExperimentWidget(dirs)

    def camera_render(self):
        """Sets up camera queues and processes"""
        self.cmr_widget = GUI_CameraDisplay()
        [p.start() for p in self.cmr_widget.procs]

    def add_to_grid(self):
        """Adds all widgets to layout grid"""
        self.grid.addWidget(self.exp_widget, 0, 0, 1, 2)
        self.grid.addWidget(self.cmr_widget, 2, 0)


# noinspection PyAttributeOutsideInit
class GUI_ConfigSettings(QtGui.QWidget):
    """GUI Page for configuring experiment settings"""

    def __init__(self, parent):
        super(GUI_ConfigSettings, self).__init__(parent)
        self.grid = QtGui.QGridLayout()
        self.grid.setSpacing(10)
        self.initialize()
        self.setLayout(self.grid)

    def initialize(self):
        """Sets up GUI elements"""
        # Render Individual Elements
        self.setup_grid()
        self.setup_signals()
        # Finalize window parameters
        self.setWindowTitle('Mouse House')

    def setup_grid(self):
        """Creates and adds widgets to grid"""
        # Generate widgets
        self.settings_overview = GUI_SettingsOverview(dirs)
        self.fp_widget = GUI_PhotometryConfig(dirs)
        self.lj_widget = GUI_LabJackConfig(dirs)
        # Grid widgets
        self.grid.addWidget(self.settings_overview, 0, 0)
        self.grid.addWidget(self.fp_widget, 1, 0)
        self.grid.addWidget(self.lj_widget, 1, 1)

    def setup_signals(self):
        """Connect all signals with their slots"""
        # Update Photometry Labels
        self.fp_widget.signal.signal.connect(self.settings_overview.update_label)
        self.fp_widget.clicked.connect(lambda:
                                       self.settings_overview.update_label(
                                           self.fp_widget.isChecked()))
        # Update LabJack Labels
        self.lj_widget.signal.signal.connect(lambda:
                                             self.settings_overview.update_label(
                                                 self.fp_widget.isChecked()))


if __name__ == '__main__':  # Always run Main_Module.py as primary script
    # Add Freeze Support for Executable Files
    mp.freeze_support()

    # Set up Directories and Save FIles
    dirs = Directories()
    dirs.load()

    # Start App
    app = QtGui.QApplication(sys.argv)  # Indicates to Python we're opening a GUI instance
    window = GUI_Master()  # Opens our main GUI
    app.exec_()  # Execute event loop; code stays here until GUI exit

    # Saves settings
    if dirs.save_on_exit:
        dirs.save()

    # Safely exit program
    sys.exit()
