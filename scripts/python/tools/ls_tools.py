from tools import ls_batch_importer
from tools import ls_split_geo
from tools import ls_tex_to_mtlx
from pipeline import ls_create_project
# from tools import ls_project_manager
# from tools import ls_create_folders

''' This module is used to gather all tools of the folder and serve as a "distributing" script.
    The idea is to avoid calling functions that have the same name as the modules they are in
'''

def batch_import():
    ls_batch_importer.batch_import()

def split_geo():
    ls_split_geo.split_geo()

def create_project():
    win = ls_create_project.CreateProject()
    win.show()

def material_maker():
    win = ls_tex_to_mtlx.TxToMtlx()
    win.show()