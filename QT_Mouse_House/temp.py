# coding=utf-8
"""for testing"""

from Misc_Functions_Old import ard_decode_data
from Dirs_Settings import *

dirs = Directories()
dirs.load()
print ard_decode_data(dirs, 'output', dirs.settings.ard_presets['example']['out_pack'])
