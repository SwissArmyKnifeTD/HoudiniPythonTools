def reload_package(kwargs):

    ''' Base function to load/reload the packages and the associated functions.

        Args:
            kwargs : Check if the Alt modifier key is pressed. 
            If pressed, the function will only reload the package and the modules currently present in the memory.
            If not, any module found that is not loaded will be imported.
    '''
    #import modules
    import hou
    import importlib
    import os
    import sys

    #reload packages
    package_path = hou.text.expandString("$HOUDINI_USER_PREF_DIR/packages/") + "LS_Tools.json"
    hou.ui.reloadPackage(package_path)

    #reload python modules
    folder_path = hou.text.expandString("$LSTools/scripts/python")

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                module_path = os.path.join(root, file).replace(os.sep,"/")
                module_name = os.path.relpath(module_path, folder_path).replace(os.sep,".").replace(".py","")
                
                try:
                    if module_name in sys.modules:
                        if kwargs["altclick"] == True :
                            importlib.reload(sys.modules[module_name])
                            print(f"{module_name} has been updated")
                    else:
                        importlib.import_module(module_name)
                        print(f"{module_name} was discovered and imported")
                except Exception as error:
                        print(f"Failed to import or reload the module {module_name}: {error}")

    #reload the menus

    #reload the shelves
    shelves = hou.shelves.shelves()
    path_shelves = hou.text.expandString("$LSTools/toolbar")

    for root, dir, files in os.walk(path_shelves):
        for file in files :
            if file.endswith(".shelf"):
                shelf_path = os.path.join(root, file).replace(os.sep, "/")
                hou.shelves.loadFile(shelf_path)

def check_path_valid(path):
    """
    This unction checks if a path is valid to use
    Args:
        path : The path to check
    Returns :
        True if path is usable, False if not.
    """

    import hou
    import os

    # Fix the path if the given path is an environment variable (E.g: $HIP, $HOME,...)
    path = os.path.dirname(hou.text.expandString(path))
    # Check if the path exists, is a directory and is accessible
    if os.path.exists(path) and os.access(path, os.R_OK) :
        print(f"The path {path} is valid")
    else :
        print(f"The path {path} is not valid")
        hou.ui.displayMessage(f"The path {path} is not valid. Please select another location", title = "Error")