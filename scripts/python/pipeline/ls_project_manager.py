import hou
import os
import json
import shutil

from pipeline.ls_create_folders import CreateFolders
from pipeline.ls_create_project import CreateProject
from pipeline.ls_save_tool import SaveCurrentFile

from PySide2 import QtCore, QtUiTools, QtWidgets

class ProjectManager(QtWidgets.QMainWindow):
    # Class Constants
    CONFIG_DIR = "$LSTools/config"
    CONFIG_FILE = "projects_config.json"
    UI_FILE = "$LSTools/ui/projectManager.ui"

    def __init__(self):
        super().__init__()

        # DECLARE DATA VARIABLE FOR PROJECTS CONFIG FILE
        self.projects_data = []
        self.json_path = os.path.join(hou.text.expandString(self.CONFIG_DIR), self.CONFIG_FILE).replace(os.sep,"/")
        self.selected_project = 0
        self.selected_scene = 0
        self.selected_file = 0
        self.create_project_window = None
        self.create_folders_window = None
        self.save_current_file = None

        # INITIALIZE UI
        self._init_ui()
        self._setup_connections()

        # POPULATE THE PROJECTS LIST AT RUNTIME
        self.load_projects()

    def _init_ui(self):
        """
        Initialize the UI components
        """

        scriptpath = hou.text.expandString(self.UI_FILE)
        self.ui = QtUiTools.QUiLoader().load(scriptpath, parentWidget = self)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle("LS Project Manager Tool 1.0")
        self.setMaximumSize(1070,610)

        # SET CONNECTIONS
        #Projects     
        self.projects_list = self.ui.findChild(QtWidgets.QListWidget, "wdgt_projects_list")
        self.create_project_button = self.ui.findChild(QtWidgets.QPushButton, "btn_create_project")
        self.enable_project_button = self.ui.findChild(QtWidgets.QPushButton, "btn_enable_project")
        self.disable_project_button = self.ui.findChild(QtWidgets.QPushButton, "btn_disable_project")
        self.delete_project_button = self.ui.findChild(QtWidgets.QPushButton, "btn_delete_project")
        self.project_name_info = self.ui.findChild(QtWidgets.QLineEdit, "led_project_name")
        self.project_code_info = self.ui.findChild(QtWidgets.QLineEdit, "led_project_code")
        self.project_framerate_info = self.ui.findChild(QtWidgets.QLineEdit, "led_project_framerate")
        self.project_path_info = self.ui.findChild(QtWidgets.QLineEdit, "led_project_path")
        self.project_active_info = self.ui.findChild(QtWidgets.QLineEdit, "led_project_active")

        # Scenes
        self.scenes_list = self.ui.findChild(QtWidgets.QListWidget, "wdgt_scenes_list")
        self.create_scene_button = self.ui.findChild(QtWidgets.QPushButton, "btn_create_scene")
        self.delete_scene_button = self.ui.findChild(QtWidgets.QPushButton, "btn_delete_scene")

        # Files
        self.files_list = self.ui.findChild(QtWidgets.QListWidget, "wdgt_files_list")
        self.open_file_button = self.ui.findChild(QtWidgets.QPushButton, "btn_open_file")
        self.save_file_button = self.ui.findChild(QtWidgets.QPushButton, "btn_save_file")

        # Status
        self.messages = self.ui.findChild(QtWidgets.QLineEdit, "led_messages")

    def _setup_connections(self):
        """
        Setup the signal connections
        """

        self.create_project_button.clicked.connect(self.open_create_project)
        self.enable_project_button.clicked.connect(lambda : self.toggle_project(True))
        self.disable_project_button.clicked.connect(lambda : self.toggle_project(False))
        self.delete_project_button.clicked.connect(self.project_delete)
        self.projects_list.currentItemChanged.connect(self.item_change)
        self.scenes_list.itemSelectionChanged.connect(self.load_hip_files)
        self.scenes_list.currentItemChanged.connect(self.scene_change)
        self.create_scene_button.clicked.connect(self.open_create_folders)
        self.delete_scene_button.clicked.connect(self.scene_delete)
        self.files_list.itemSelectionChanged.connect(self.store_file_index)
        self.open_file_button.clicked.connect(self.open_hip_file)
        self.save_file_button.clicked.connect(self.open_save_tool)

    def item_change(self, current, previous):
        """
        Only call load_scenes when there is a valid current item
        Args:
            current : The current QListWidgetItem
            previous : The previous QListWidgetItem
        """

        if current is not None:
            self.load_scenes()
            self.show_project_details()
            self.selected_project = self.projects_list.currentRow()

            # Update the save tool if it is opened
            self.update_save_current_file()

    def scene_change(self,current,previous):
        if current is not None:
            # Update the save tool if it is opened
            self.update_save_current_file()

    def store_file_index(self):
        """
        Store the current row index of the file list
        """
        self.selected_file = self.files_list.currentRow()

    def update_status(self, message, severity=None):
        """
        Update the status message and display message when needed
        Args:
            messsage (str) : Message to display
            severity (hou.severity, optionnal) : Severity for UI display
        """

        self.messages.setText(message)
        if severity is not None:
            hou.ui.displayMessage(message, severity=severity)
        
    def get_selected_project(self):
        """
        Get selected folder or display error
        Returns:
            tuple : (project_name, project_data) or (None, None) if no selection
        """

        if not self.projects_list.selectedItems():
            error_msg = "Please select a project first"
            self.update_status(error_msg, hou.severityType.Error)
            return None, None

        project_name = self.projects_list.currentItem().text()
        project_data= None
        
        for project in self.projects_data:
                if project_name in project:
                    project_data = project[project_name]
                    break
                
        return project_name, project_data

    def get_selected_scene(self):
        """
        Get selected scene or display error
        Returns:
            string : (scene_name) or (None) if no selection
        """

        if not self.scenes_list.selectedItems():
            error_msg = "Please select a scene first"
            self.update_status(error_msg, hou.severityType.Error)
            return None

        scene_name = self.scenes_list.currentItem().text()

        return scene_name

    def load_projects(self):
        """
        Load projects from JSON projects file and populate the projects list widget
        """

        # Empty the list before update
        self.projects_list.clear()
        try:

            with open(self.json_path, "r") as file :
                self.projects_data = json.load(file)
            
            project_names = []
            active_project_index = 0

            for index, project in enumerate(self.projects_data):
                project_name = list(project.keys())[0]
                project_names.append(project_name)

                # Check if the project is active
                if project[project_name].get("PROJECT_ACTIVE", False):
                    active_project_index= index
            
            project_names.sort()

            # Add the projects to the list
            for name in project_names:
                self.projects_list.addItem(name)

            self.messages.setText(f"{self.json_path} successfully loaded")

            # Always select last item
            if self.projects_list.count() > 0:
                # sorted_active_index = project_names.index(list(self.projects_data[active_project_index].keys())[0])
                # self.projects_list.setCurrentRow(sorted_active_index)
            
                if self.selected_project < self.projects_list.count()-1:
                    self.projects_list.setCurrentRow(self.selected_project)
                else:
                    self.projects_list.setCurrentRow(self.projects_list.count()-1)
            else :
                self.scenes_list.clear()
                self.files_list.clear()
        except Exception as error:
            self.messages.setText("No projects found in the Config File")

    def show_project_details(self):
        """
        Display the details for the selected project
        """

        project_name, project_data = self.get_selected_project()

        if not project_name :
            return
        if project_data:
            self.project_name_info.setText(f"{project_name}")
            self.project_code_info.setText(f"{project_data['PROJECT_CODE']}")
            self.project_framerate_info.setText(f"{project_data['PROJECT_FRAMERATE']}")
            self.project_path_info.setText(f"{project_data['PROJECT_PATH']}")
            if project_data['PROJECT_ACTIVE'] :
                self.project_active_info.setText("Enabled")
            else:
                self.project_active_info.setText("Disabled")
        else:
            message = f"Project {project_name} is not found"
            self.update_status(message)
    
    def toggle_project(self, status=True):
        """
        Toggle the environment variables for the selected project
        Args:
            status (bool) : True enables the project, false disable the project
        """

        project_name, project_data = self.get_selected_project()
        
        # Collect the project data
        env_vars = {"JOB":"", "CODE":"", "FPS":"", "PROJECT":""}

        if status:
            if project_data:
                # update json file with enabled Project Status- put all inactive except selected one
                for project in self.projects_data:
                    current_project_name = list(project.keys())[0]
                    project[current_project_name]["PROJECT_ACTIVE"] = (current_project_name == project_name)

                # write updated json file
                with open(self.json_path, "w") as file:
                    json.dump(self.projects_data, file, sort_keys=True, indent=4)

                #update env variables
                env_vars.update(
                    {
                        "JOB" : project_data["PROJECT_PATH"],
                        "CODE" : project_data["PROJECT_CODE"],
                        "FPS" : project_data["PROJECT_FRAMERATE"],
                        "PROJECT" : project_name
                    }
                )

            else:
                error_msg = f"Could not find data for project {project_name}"
                self.update_status(error_msg, hou.severityType.Error)
                return  
            status_message = f"Current active project is : {project_name}"
        else:
            # update json file with disabled Project Status
            for project in self.projects_data:
                if project_name in project:
                    project[project_name]["PROJECT_ACTIVE"] = False

            # write updated json file
            with open(self.json_path, "w") as file:
                json.dump(self.projects_data, file, sort_keys=True, indent=4)

            status_message = f"Project : {project_name} is disabled"

        # Update env variables
        for var, value in env_vars.items():
            hou.putenv(var, value)

        # Update status message
        self.messages.setText(status_message)
        hou.ui.displayMessage(status_message)

        self.load_projects()

    def project_delete(self):
        """
        Delete the project from the json file, the project list and delete all related folders
        """

        project_name, project_data = self.get_selected_project()

        # Warns the user of definitive nature of the action. Request confirmation.
        confirm_delete = hou.ui.displayMessage(
            f"!!! WARNING!!!\n"
            f"This action is definitive. All folders from {project_name} will be deleted\n"
            f"Are you sure you want to proceed?",
            buttons=("Yes", "No"),
            severity= hou.severityType.Warning)
        
        if confirm_delete == 1:
            return
        
        try:

            with open(self.json_path, "r") as file :
                self.projects_data = json.load(file)

            project_path_delete = None

            for project in self.projects_data:
                if project_name in project:
                    project_data = project[project_name]
                    project_path_delete = project_data["PROJECT_PATH"]
                    self.projects_data.remove(project)
                    break
            
            if project_path_delete:
                if os.path.exists(project_path_delete):
                    try:
                        shutil.rmtree(project_path_delete)
                    except Exception as e:
                        error_msg = f"Error deleting project directory : {str(e)}"
                        self.update_status(error_msg, hou.severityType.Error)

            with open(self.json_path, "w") as file :
                json.dump(self.projects_data, file, sort_keys=True, indent=4)

            if hou.getenv("PROJECT") == project_name:
                self.toggle_project(False)

            self.load_projects()

            success_msg = f"{project_name} has been deleted"
            self.update_status(success_msg, hou.severityType.Message)

        except Exception as e:
            error_msg = f"Error during project deletion: {str(e)}"
            self.update_status(error_msg, hou.severityType.Error)

    def load_scenes(self):
        """
        Refresh the Scenes Widget according to the selected project in the list
        """
        
        project_name, project_data = self.get_selected_project()

        if not project_name or not project_data:
            return
        
        try:
            self.scenes_list.clear()
            for project in self.projects_data:
                if project_name in project:
                    project_data = project[project_name]
                    seq_path = os.path.join(project_data["PROJECT_PATH"], "seq").replace(os.sep,"/")

                    if os.path.exists(seq_path):
                        
                        sequences = []

                        for dir in os.listdir(seq_path) :
                            if os.path.isdir(os.path.join(seq_path, dir)):
                                sequences.append(dir)
                        
                        sequences.sort()

                        for scene in sequences:
                            self.scenes_list.addItem(scene)
                    else:
                        error_msg = f"No Seq folder found in {project_name}"
                        self.update_status(error_msg)
                        break
            # Always select last item
            if self.scenes_list.count() > 0:
                if self.selected_scene < self.scenes_list.count()-1:
                    self.scenes_list.setCurrentRow(self.selected_scene)
                else:
                    self.scenes_list.setCurrentRow(self.scenes_list.count()-1)

        except Exception as e:
            error_msg = f"Error loading sequence: {str(e)}"
            self.update_status(error_msg, hou.severityType.Error)
    
    def open_create_project(self):
        """
        Open the tool to create projects
        """
        if not self.create_project_window:
            self.create_project_window = CreateProject()
            self.create_project_window.project_created.connect(self.load_projects)

        self.create_project_window.show()
        self.create_project_window.raise_()

    def open_create_folders(self):
        """
        Fetch the current project in the project list and send its name to the create_folders() tool
        """

        project_name, Project_data = self.get_selected_project()

        if not self.create_folders_window:
            self.create_folders_window = CreateFolders(project_name)
            self.create_folders_window.scene_created.connect(self.load_projects)

        else:
            self.create_folders_window.project_name = project_name

        
        self.create_folders_window.show()
        self.create_folders_window.raise_()

    def scene_delete(self):
        """
        Delete the scene from the json file, the project list and delete all related folders
        """
        project_name, project_data = self.get_selected_project()
        scene_name = self.get_selected_scene()
        
        if scene_name:

            # Warns the user of definitive nature of the action. Request confirmation.
            confirm_delete = hou.ui.displayMessage(
                f"!!! WARNING!!!\n"
                f"This action is definitive. All folders from {scene_name} will be deleted\n"
                f"Are you sure you want to proceed?",
                buttons=("Yes", "No"),
                severity= hou.severityType.Warning)
            
            if confirm_delete == 1:
                return
            
            try:

                with open(self.json_path, "r") as file :
                    self.projects_data = json.load(file)

                scene_path_delete = None

                for project in self.projects_data:
                    if project_name in project:
                        for key in project.values():
                            scene_path_delete = os.path.join(project_data["PROJECT_PATH"], f"seq/{scene_name}").replace(os.sep,"/")
                            key["PROJECT_FOLDERS_SEQ"].remove(scene_name)
                
                if scene_path_delete:
                    if os.path.exists(scene_path_delete):
                        try:
                            shutil.rmtree(scene_path_delete)
                        except Exception as e:
                            error_msg = f"Error deleting project directory : {str(e)}"
                            self.update_status(error_msg, hou.severityType.Error)

                with open(self.json_path, "w") as file :
                    json.dump(self.projects_data, file, sort_keys=True, indent=4)

                self.load_scenes()
                self.update_save_current_file()

                success_msg = f"{scene_name} has been deleted"
                self.update_status(success_msg, hou.severityType.Message)
                
            except Exception as e:
                error_msg = f"Error during project deletion: {str(e)}"
                self.update_status(error_msg, hou.severityType.Error)

    def load_hip_files(self):
        """
        Load all the existing houdini files in the specified scene
        """

        # Clear the list if no scene is selected
        if not self.scenes_list.selectedItems():
            self.files_list.clear()
            return
        
        # Get the project name and data
        project_name, project_data = self.get_selected_project()
        if not project_name :
            return
        
        # Get the scene name
        scene_name = self.scenes_list.currentItem().text()
        self.selected_scene = self.scenes_list.currentRow()

        try:
            # assemble scene folder path
            seq_path = os.path.join(project_data["PROJECT_PATH"], "seq").replace(os.sep,"/")
            scene_path = os.path.join(seq_path, scene_name).replace(os.sep, "/")

            # Clean current files list
            self.files_list.clear()

            # Fetch all the compatible hip files
            hip_files = []
            for root, dir, files in os.walk(scene_path):
                for file in files:
                    if file.endswith((".hip", ".hiplc", ".hipnc")):
                        relative_path = os.path.relpath(os.path.join(root, file), scene_path)
                        hip_files.append(relative_path)

            hip_files.sort()

            # Add hip list to the list
            for hip in hip_files:
                self.files_list.addItem(hip)
            
            # Always select last item
            if self.scenes_list.count() > 0:
                if self.selected_file < self.files_list.count()-1:
                    self.files_list.setCurrentRow(self.selected_file)
                else:
                    self.files_list.setCurrentRow(self.files_list.count()-1)

        except Exception as e:
                error_msg = f"Error during loading hip files: {str(e)}"
                self.update_status(error_msg, hou.severityType.Error)
            
    def open_hip_file(self):
        """
        Open the selected hip file
        """
        if not self.files_list.selectedItems():
            error_msg = f"Please select a file top open"
            self.update_status(error_msg)
            return
        
        project_name, project_data = self.get_selected_project()
        if not project_name:
            return
        
        # Get file details
        scene_name = self.get_selected_scene()
        file_name = self.files_list.currentItem().text()

        try:
            # assemble scene folder path
            seq_path = os.path.join(project_data["PROJECT_PATH"], "seq").replace(os.sep,"/")
            scene_path = os.path.join(seq_path, scene_name).replace(os.sep, "/")
            file_path = os.path.join(scene_path, file_name).replace(os.sep, "/")

            if hou.hipFile.hasUnsavedChanges():
                save_file = hou.ui.displayMessage(
                    "Current scene has unsaved changes. Do you want to save them?",
                    buttons = ("Yes","No","Cancel"), 
                    severity = hou.severityType.Warning
                )

                if save_file == 2 :
                    return
                elif save_file == 0:
                    hou.hipFile.save()

            hou.hipFile.load(file_path)
            self.update_status(f"Opened file : '{file_name}'", hou.severityType.Message)



        except Exception as e:
            error_msg = f"Error opening '{file_name}': {str(e)}"
            self.update_status(error_msg, hou.severityType.Error)

    def open_save_tool(self):
        """
        Open the save tool and transmit required data : project_name, project_data, scene_name
        """

        project_name, project_data = self.get_selected_project()
        if not project_name:
            return
        
        scene_name = None

        if self.scenes_list.selectedItems():
            scene_name = self.scenes_list.currentItem().text()
        
        if not self.save_current_file:
            self.save_current_file = SaveCurrentFile(project_data, scene_name, project_name)
            self.save_current_file.file_saved.connect(self.load_projects)
        
        else:
            self.save_current_file.project_data = project_data
            self.save_current_file.scene_name = scene_name
            self.save_current_file.project_name = project_name
            self.save_current_file.update_project_info()
            self.save_current_file.update_preview_path()

        self.save_current_file.show()
        self.save_current_file.raise_()
    
    def update_save_current_file(self):
        if not self.save_current_file:
            return
        
        project_name, project_data = self.get_selected_project()
        if not project_name:
            return
        
        scene_name = None
        if self.scenes_list.selectedItems():
            scene_name = self.scenes_list.currentItem().text()
        
        self.save_current_file.project_data = project_data
        self.save_current_file.scene_name = scene_name
        self.save_current_file.project_name = project_name
        self.save_current_file.update_project_info()
        self.save_current_file.update_preview_path()