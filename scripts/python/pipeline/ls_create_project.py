import hou
import os
import json
import ls_utils

from PySide2 import QtCore, QtUiTools, QtWidgets, QtGui

class CreateProject(QtWidgets.QMainWindow):

    project_created = QtCore.Signal()

    # Class Constants
    CONFIG_DIR = "$LSTools/config"
    CONFIG_FILE = "projects_config.json"
    UI_FILE = "$LSTools/ui/createProject.ui"

    def __init__(self):
        super().__init__()
        
        global folder_list
        folder_list = []
        self.json_path = os.path.join(hou.text.expandString(self.CONFIG_DIR), self.CONFIG_FILE).replace(os.sep,"/")
        self.input_state = False
        
        scriptpath = hou.text.expandString(self.UI_FILE)
        self.ui = QtUiTools.QUiLoader().load(scriptpath, parentWidget = self)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle("LS Create Project Tool 1.0")
        self.setMaximumSize(250,700)

        # SET CONNECTIONS
        self.ui.int_validator = QtGui.QIntValidator()
        self.select_dir = self.ui.findChild(QtWidgets.QPushButton, "btn_project_directory")
        self.project_name = self.ui.findChild(QtWidgets.QLineEdit, "led_project_name")
        self.project_name_label = self.ui.findChild(QtWidgets.QLabel, "lbl_project_name")
        self.project_code = self.ui.findChild(QtWidgets.QLineEdit, "led_project_code")
        self.project_code_label = self.ui.findChild(QtWidgets.QLabel, "lbl_project_code")
        self.project_framerate = self.ui.findChild(QtWidgets.QLineEdit, "led_project_framerate")
        self.project_framerate_label = self.ui.findChild(QtWidgets.QLabel, "lbl_project_framerate")
        self.project_console = self.ui.findChild(QtWidgets.QLineEdit, "led_project_console")
        self.default_folders_label = self.ui.findChild(QtWidgets.QLabel, "lbl_default_folders")

        self.project_name.textChanged.connect(self.check_name_state)
        self.project_code.textChanged.connect(self.check_name_state)
        self.project_framerate.textChanged.connect(self.check_name_state)

        # Folders
        self.chkb_geo = self.ui.findChild(QtWidgets.QCheckBox, "chkb_geo")
        self.led_geo = self.ui.findChild(QtWidgets.QLineEdit, "led_geo")
        self.chkb_hda = self.ui.findChild(QtWidgets.QCheckBox, "chkb_hda")
        self.led_hda = self.ui.findChild(QtWidgets.QLineEdit, "led_hda")
        self.chkb_sim = self.ui.findChild(QtWidgets.QCheckBox, "chkb_sim")
        self.led_sim = self.ui.findChild(QtWidgets.QLineEdit, "led_sim")
        self.chkb_abc = self.ui.findChild(QtWidgets.QCheckBox, "chkb_abc")
        self.led_abc = self.ui.findChild(QtWidgets.QLineEdit, "led_abc")
        self.chkb_tex = self.ui.findChild(QtWidgets.QCheckBox, "chkb_tex")
        self.led_tex = self.ui.findChild(QtWidgets.QLineEdit, "led_tex")
        self.chkb_render = self.ui.findChild(QtWidgets.QCheckBox, "chkb_render")
        self.led_render = self.ui.findChild(QtWidgets.QLineEdit, "led_render")
        self.chkb_flip = self.ui.findChild(QtWidgets.QCheckBox, "chkb_flip")
        self.led_flip = self.ui.findChild(QtWidgets.QLineEdit, "led_flip")
        self.chkb_scripts = self.ui.findChild(QtWidgets.QCheckBox, "chkb_scripts")
        self.led_scripts = self.ui.findChild(QtWidgets.QLineEdit, "led_scripts")
        self.chkb_comp = self.ui.findChild(QtWidgets.QCheckBox, "chkb_comp")
        self.led_comp = self.ui.findChild(QtWidgets.QLineEdit, "led_comp")
        self.chkb_audio = self.ui.findChild(QtWidgets.QCheckBox, "chkb_audio")
        self.led_audio = self.ui.findChild(QtWidgets.QLineEdit, "led_audio")
        self.chkb_videos = self.ui.findChild(QtWidgets.QCheckBox, "chkb_videos")
        self.led_videos = self.ui.findChild(QtWidgets.QLineEdit, "led_videos")
        self.chkb_desk = self.ui.findChild(QtWidgets.QCheckBox, "chkb_desk")
        self.led_desk = self.ui.findChild(QtWidgets.QLineEdit, "led_desk")

        self.chkb_custom_folders = self.ui.findChild(QtWidgets.QCheckBox, "chkb_custom_folders")
        self.custom_folders = self.ui.findChild(QtWidgets.QPlainTextEdit, "plte_custom_folders")
        self.create_proj = self.ui.findChild(QtWidgets.QPushButton, "btn_create_project")

        # CREATE FOLDERS DICTIONNARY
        self.folders_dict = {"geo":{"chkb":self.chkb_geo, "led":self.led_geo},
                             "hda":{"chkb":self.chkb_hda, "led":self.led_hda},
                             "sim":{"chkb":self.chkb_sim, "led":self.led_sim},
                             "abc":{"chkb":self.chkb_abc, "led":self.led_abc},
                             "chkb":{"chkb":self.chkb_tex, "led":self.led_tex},
                             "render":{"chkb":self.chkb_render, "led":self.led_render},
                             "flip":{"chkb":self.chkb_flip, "led":self.led_flip},
                             "sccripts":{"chkb":self.chkb_scripts, "led":self.led_scripts},
                             "comp":{"chkb":self.chkb_comp, "led":self.led_comp},
                             "audio":{"chkb":self.chkb_audio, "led":self.led_audio},
                             "videos":{"chkb":self.chkb_videos, "led":self.led_videos},
                             "desk":{"chkb":self.chkb_desk, "led":self.led_desk},
                             "custom_Folders":{"chkb":self.chkb_custom_folders, "led":self.custom_folders}
                             }
        
        # CREATE FOLDERS LIST
        self.folder_input = [self.chkb_geo, 
                                self.led_geo,
                                self.chkb_hda,
                                self.led_hda,
                                self.chkb_sim,
                                self.led_sim,
                                self.chkb_abc,
                                self.led_abc,
                                self.chkb_tex,
                                self.led_tex,
                                self.chkb_render,
                                self.led_render,
                                self.chkb_flip,
                                self.led_flip,
                                self.chkb_scripts,
                                self.led_scripts,
                                self.chkb_comp,
                                self.led_comp,
                                self.chkb_audio,
                                self.led_audio,
                                self.chkb_videos,
                                self.led_videos,
                                self.chkb_desk,
                                self.led_desk,
                                self.chkb_custom_folders,
                                self.custom_folders,
                                self.create_proj
                                ]
        # SET VALUES
        self.project_name.setEnabled(False)
        self.project_name_label.setEnabled(False)
        self.project_code.setEnabled(False)
        self.project_code_label.setEnabled(False)
        self.project_framerate.setEnabled(False)
        self.project_framerate.setValidator(self.ui.int_validator)
        self.project_framerate_label.setEnabled(False)
        self.default_folders_label.setEnabled(False)

        for input_fields in [self.chkb_geo, self.led_geo, self.chkb_hda, self.led_hda, self.chkb_sim, self.led_sim, self.chkb_abc,
        self.led_abc, self.chkb_tex, self.led_tex, self.chkb_render, self.led_render, self.chkb_flip, self.led_flip,
        self.chkb_scripts, self.led_scripts, self.chkb_comp, self.led_comp, self.chkb_audio, self.led_audio,
        self.chkb_videos, self.led_videos, self.chkb_desk, self.led_desk, self.chkb_custom_folders,
        self.custom_folders, self.create_proj]:
            input_fields.setEnabled(False)
        
        # CONNECTIONS
        self.select_dir.clicked.connect(self.select_directory)
        self.create_proj.clicked.connect(self.create_project)

        self.chkb_geo.stateChanged.connect(self.checkbox_state)
        self.led_geo.textChanged.connect(self.checkbox_state)
        self.chkb_hda.stateChanged.connect(self.checkbox_state)
        self.led_hda.textChanged.connect(self.checkbox_state)
        self.chkb_sim.stateChanged.connect(self.checkbox_state)
        self.led_sim.textChanged.connect(self.checkbox_state)
        self.chkb_abc.stateChanged.connect(self.checkbox_state)
        self.led_abc.textChanged.connect(self.checkbox_state)
        self.chkb_tex.stateChanged.connect(self.checkbox_state)
        self.led_tex.textChanged.connect(self.checkbox_state)
        self.chkb_render.stateChanged.connect(self.checkbox_state)
        self.led_render.textChanged.connect(self.checkbox_state)
        self.chkb_flip.stateChanged.connect(self.checkbox_state)
        self.led_flip.textChanged.connect(self.checkbox_state)
        self.chkb_scripts.stateChanged.connect(self.checkbox_state)
        self.led_scripts.textChanged.connect(self.checkbox_state)
        self.chkb_comp.stateChanged.connect(self.checkbox_state)
        self.led_comp.textChanged.connect(self.checkbox_state)
        self.chkb_audio.stateChanged.connect(self.checkbox_state)
        self.led_audio.textChanged.connect(self.checkbox_state)
        self.chkb_videos.stateChanged.connect(self.checkbox_state)
        self.led_videos.textChanged.connect(self.checkbox_state)
        self.chkb_desk.stateChanged.connect(self.checkbox_state)
        self.led_desk.textChanged.connect(self.checkbox_state)
        self.chkb_custom_folders.stateChanged.connect(self.checkbox_state)
        self.custom_folders.textChanged.connect(self.checkbox_state)
        
    def select_directory(self):    
        """
        Prompt the user to select a directory in which saving the project folders
        """

        global directory
        start_directory = hou.text.expandString("$LSTools")
        directory = hou.ui.selectFile(
            start_directory = start_directory, 
            title = "Select project location", 
            file_type = hou.fileType.Directory)
        
        ls_utils.check_path_valid(directory)

        if directory :
            self.project_name.setEnabled(True)
            self.project_name_label.setEnabled(True)
            self.project_name.textChanged.connect(self.check_button_state)
            self.project_code.setEnabled(True)
            self.project_code_label.setEnabled(True)
            self.project_code.textChanged.connect(self.check_button_state)
            self.project_framerate.setEnabled(True)
            self.project_framerate_label.setEnabled(True)
            self.project_framerate.textChanged.connect(self.check_button_state)

            self.check_name_state()

    def get_existing_data(self):
        """
        Get selected folder or display error
        Returns:
            lists : (project_name, project_data) or (None, None) if no selection
        """

        project_names = []
        project_codes = []
        # Open the json and loop through names and codes to output two lists
        try:
            with open(self.json_path, "r") as file :
                self.projects_data = json.load(file)

            for project in self.projects_data:
                project_name = list(project.keys())[0]
                project_names.append(project_name)
                project_code = project[project_name]["PROJECT_CODE"]
                project_codes.append(project_code)
            
            project_names.sort()
            project_codes.sort()

        except Exception as error:
            self.project_console.setText("No projects found in the Config File")

        return project_names, project_codes
    
    def check_name_state(self):
        """
        Enables the folders checkboxes if the user filled correct Project name and code that is not used yet as well as a framerate value
        """
        # get project names and codes
        project_names, project_codes = self.get_existing_data()

        # Set both Project and Code validity booleans to none to be able to know when nothing is written by the user
        project_validity = None
        code_validity = None
        framerate_validity = None

        # Check the user input against json project names list
        if self.project_name.text().strip() :
            self.project_name_label.setStyleSheet("color: rgb(0, 255, 0);")
            project_validity = True

            for name in project_names :
                name_check = name
                if name_check == self.project_name.text():
                    self.project_name_label.setStyleSheet("color: rgb(255, 0, 0);")
                    project_validity = False
        else :
            self.project_name_label.setStyleSheet("")
            project_validity = None
            
         # Check the user input against json project codes list       
        if self.project_code.text().strip() :
            self.project_code_label.setStyleSheet("color: rgb(0, 255, 0);")
            code_validity = True

            for code in project_codes :
                code_check = code
                if code_check == self.project_code.text():
                    self.project_code_label.setStyleSheet("color: rgb(255, 0, 0);")
                    code_validity = False
        else :
            self.project_code_label.setStyleSheet("")
            code_validity = None

        # Check framerate has been set
        if self.project_framerate.text().strip() :
            self.project_framerate_label.setStyleSheet("color: rgb(0, 255, 0);")
            framerate_validity = True
        else:
            self.project_framerate_label.setStyleSheet("color: rgb(255, 0, 0);")
            framerate_validity = None
        
        # Check global validty to unlock folder inputs and project creation button
        if project_validity and code_validity and framerate_validity:
            self.input_state = True
            self.project_console.setText("Project and Code are available")
        else :
            if project_validity == False and code_validity == False:
                self.project_console.setText("Project and Code already exist")
            elif project_validity == False:
                self.project_console.setText("Project already exists")
                self.input_state = False
            elif code_validity == False:
                self.project_console.setText("Code already exists")
                self.input_state = False
            elif project_validity == None or code_validity == None:
                self.project_console.setText("")
                self.input_state = False
            elif not framerate_validity:
                self.project_console.setText("Framerate is empty")
                self.input_state = False

    def check_button_state(self):
        """
        Enables the Create Project button and the folders checkboxes if the user filled the Project Name, Code and Framerate correctly
        """

        if self.input_state:
            for input in self.folder_input:
                input.setEnabled(True)
                self.checkbox_state()

        else :
            for input in self.folder_input:
                input.setEnabled(False)

    def checkbox_state(self):
        """
        Enables the corresponding Line Edit if the user checks its checkbox
        """
        global folder_list
        folder_list = []

        for key in self.folders_dict.values() :
            chkb = key.get("chkb")
            led = key.get("led")
            if chkb.isChecked() :
                led.setEnabled(True)
                try: 
                    folder_list.extend(led.text().split(","))
                except :
                    folder_list.extend(led.toPlainText().split(","))
            else :
                led.setEnabled(False)

        folder_list = [item.strip() for item in folder_list]
        folder_list.append("seq")

    def create_project(self) :
        """
        This function creates a JSON file with the information provided by the user.
        Gather the name, code, framerate and selected folders name the user chose.
        """
        # Declare variables
        project_name = self.project_name.text().strip()
        project_code = self.project_code.text().strip()
        project_framerate = self.project_framerate.text().strip()

        project_path = directory + project_name

        # Create the project dictionnary
        project_dict = {
            project_name:{
                "PROJECT_CODE" : project_code,
                "PROJECT_PATH" : project_path,
                "PROJECT_FRAMERATE" : project_framerate,
                "PROJECT_FOLDERS" : folder_list,
                "PROJECT_FOLDERS_SEQ" : [],
                "PROJECT_ACTIVE" : False
                
            }
        }

        # JSON file path
        config_path = hou.text.expandString("$LSTools/config")
        json_file_path = os.path.join(config_path, "projects_config.json")

        if os.path.exists(json_file_path) :
            with open(json_file_path, "r") as file :
                try:
                    data = json.load(file)
                except json.JSONDecodeError :
                    data = []
        else :
            data = []

        # Check for duplicates project name or code in the json file
        for existing_project in data :
            project_name_check = list(existing_project.keys())[0]

            if (project_name_check == project_name 
                or existing_project[project_name_check]["PROJECT_CODE"] == project_code) :
                
                if (project_name_check == project_name 
                and existing_project[project_name_check]["PROJECT_CODE"] == project_code) :

                    hou.ui.displayMessage(
                    f"A project with same name or code alreasdy exists: \n \n"
                    f"Name : {project_name_check}\n"
                    f"Code :{project_code}\n"
                    f"Please use a different name or code", 
                    severity = hou.severityType.Error
                    )
                    return
                else:
                    if (project_name_check == project_name) : 

                        hou.ui.displayMessage(
                            f"A project with same name alreasdy exists: \n \n"
                            f"Name : {project_name_check}\n"
                            f"Please use a different name", 
                            severity = hou.severityType.Error
                        )
                        return
                    else :
                        hou.ui.displayMessage(
                            f"A project with same code alreasdy exists: \n \n"
                            f"Code :{project_code}\n"
                            f"Please use a different code", 
                            severity = hou.severityType.Error
                        )
                        return
        # Append new project data
        data.append(project_dict)

        # Save updated data back to the json file
        with open(json_file_path, "w") as file :
            json.dump(data, file, sort_keys=True, indent=4)
        print(f"Project data successfully saved to {json_file_path}")

        # Create Project folder and subfolders
        project_root = os.path.join(directory, project_name)
        os.makedirs(project_root, exist_ok = True)

        for folder in folder_list :
            folder_path = os.path.join(project_root, folder)
            os.makedirs(folder_path, exist_ok = True)

        print(f"Project folder and subfolders successfully created at {project_root}")

        # Emit signal to Project Manager
        self.project_created.emit()
        self.project_name.clear()
        self.project_code.clear()

        self.close()