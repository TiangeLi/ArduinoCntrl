# coding=utf-8

"""PyQt4/Python2.7 Mouse House"""

from Dirs_Settings import *
from Custom_Qt_Widgets import *


class GUI_Master(qg.QWidget):
    """Main GUI Window"""

    def __init__(self, parent=None):
        super(GUI_Master, self).__init__(parent)
        # Main Window Configs
        self.setWindowTitle('Mouse House')
        # Add Module Components
        self.grid = qg.QGridLayout()
        self.render_widgets()
        self.set_window_size()
        # Finish and Show Window
        self.show()

    def render_widgets(self):
        """Adds all GUI Modules"""
        # Create Widget Objects
        self.progbar = GUI_ProgressBar(dirs)
        self.cameras = GUI_CameraDisplay(dirs)
        self.exp_cntrls = GUI_ExpControls(dirs, self.progbar)
        # Add Widgets to Grid
        self.grid.addWidget(self.progbar, 0, 1)
        self.grid.addWidget(self.cameras, 0, 0, 4, 1)
        self.grid.addWidget(self.exp_cntrls, 1, 1)
        # Finish Layout
        self.setLayout(self.grid)

    def set_window_size(self):
        """Generates sizing parameters for main window"""
        # Window size is based on number of cameras we have
        max_per_col = 3
        num_cmrs = dirs.settings.num_cmrs
        num_columns = int(math.ceil(float(num_cmrs) / max_per_col))
        # -- Width -- #
        base_width = 1050  # This accounts for Progress Bar and Bordering
        if num_columns > 1:
            width = base_width + num_columns * 375
        else:
            width = base_width + num_columns * 400
        # -- Height -- #
        if num_cmrs < 3:
            height = 700
        else:
            height = 900
        # -- Set Window Size -- #
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)

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
