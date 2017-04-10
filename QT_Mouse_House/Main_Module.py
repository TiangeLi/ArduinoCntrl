# coding=utf-8

"""PyQt4/Python2.7 Mouse House"""

from Dirs_Settings import *
from Custom_Qt_Widgets import *
import multiprocessing as mp


class GUI_Master(qg.QWidget):
    """Main GUI Window"""

    def __init__(self, parent=None):
        super(GUI_Master, self).__init__(parent)
        # Main Window Configs
        self.setWindowTitle('Mouse House')
        self.setMinimumWidth(1280)
        self.setMinimumHeight(700)
        # Add Module Components
        self.grid = qg.QGridLayout()
        self.render_widgets()
        # Finish and Show Window
        self.show()

    def render_widgets(self):
        """Adds all GUI Modules"""
        # Create Widget Objects
        self.progbar = GUI_ProgressBar(dirs)
        self.cameras = GUI_CameraDisplay(dirs)
        [proc.start() for proc in self.cameras.procs]
        self.exp_cntrls = GUI_ExpControls(dirs, self.progbar)
        # Add Widgets to Grid
        self.grid.addWidget(self.progbar, 0, 0)
        self.grid.addWidget(self.cameras, 1, 0)
        self.grid.addWidget(self.exp_cntrls, 1, 1)
        # Finish Layout
        self.setLayout(self.grid)

    def closeEvent(self, QCloseEvent):
        """Reimplements self.closeEvent to exit iff experiment not running"""
        pass


# Actual Program Runs Below #
if __name__ == '__main__':  # Always run Main_Module.py as primary script
    # -- Add Freeze Support for Windows .exe Files -- #
    mp.freeze_support()
    # -- Set up Directories and Save Files -- #
    dirs = Directories()
    dirs.load()
    # -- Start Application -- #
    app = qg.QApplication(sys.argv)  # Tells Python: we're opening a new GUI app
    window = GUI_Master()  # Opens our main GUI Window
    app.exec_()  # Execute GUI event loop; program stays here until we close GUI
    # -- Save settings to File -- #
    if dirs.save_on_exit:
        dirs.save()
    # -- Safely exit application and Python -- #
    sys.exit()
