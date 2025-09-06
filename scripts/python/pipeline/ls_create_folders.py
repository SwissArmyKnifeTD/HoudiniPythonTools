import hou
import os
import json

from PySide2 import QtCore, QtUiTools, QtWidgets

class CreateFolders(QtWidgets.QMainWindow):

    scene_created = QtCore.Signal()

    # Class Constants
    CONFIG_DIR = "$LSTools/config"
    CONFIG_FILE = "projects_config.json"
    UI_FILE = "$LSTools/ui/createScene.ui"

    def __init__(self, project_name):
        super().__init__()

        self.project_name = project_name
        
        # DECLARE DATA VARIABLE FOR PROJECTS CONFIG FILE
        self.projects_data = []
        self.json_path = os.path.join(hou.text.expandString(self.CONFIG_DIR), self.CONFIG_FILE).replace(os.sep,"/")

        # INITIALIZE UI
        self._init_ui()
        self._setup_connections()
        
    def _init_ui(self):
        """
        Initialize the UI components
        """

        scriptpath = hou.text.expandString(self.UI_FILE)
        self.ui = QtUiTools.QUiLoader().load(scriptpath, parentWidget = self)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle("LS Create Scene Tool 1.0")
        self.setMaximumSize(250,610)

        # SET CONNECTIONS
        # Title
        self.tool_label = self.ui.findChild(QtWidgets.QLabel, "lbl_title")

        # Scene Naming        
        self.scene_name_label = self.ui.findChild(QtWidgets.QLabel, "lbl_scene_name")
        self.scene_name = self.ui.findChild(QtWidgets.QLineEdit, "led_scene_name")
        self.console = self.ui.findChild(QtWidgets.QLineEdit, "led_console")
                
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
        self.plte_custom_folders = self.ui.findChild(QtWidgets.QPlainTextEdit, "plte_custom_folders")
        
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
                             "custom_Folders":{"chkb":self.chkb_custom_folders, "led":self.plte_custom_folders}
                             }
        
        # Create Folders
        self.create_folders_button = self.ui.findChild(QtWidgets.QPushButton, "btn_create_folders")

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
                                self.plte_custom_folders,
                                self.create_folders_button
                                ]

        # SET VALUES
        self.tool_label.setText(f"Create Scene for : {self.project_name}")

        for input in self.folder_input:
            input.setEnabled(False)
        
    def _setup_connections(self):
        """
        Setup the signal connections
        """

        self.scene_name.textChanged.connect(self.check_name_state)
        self.create_folders_button.clicked.connect(self.create_scene_folder)

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
        self.plte_custom_folders.textChanged.connect(self.checkbox_state)

    def checkbox_state(self):
        """
        Enables the corresponding Line Edit if the user checks its checkbox and create a list of all the requested folder to create
        """
        global new_folder_list
        new_folder_list = []

        for key in self.folders_dict.values() :
            chkb = key.get("chkb")
            led = key.get("led")
            if chkb.isChecked() :
                led.setEnabled(True)
                try: 
                    new_folder_list.extend(led.text().split(","))
                except :
                    new_folder_list.extend(led.toPlainText().split(","))
            else :
                led.setEnabled(False)

        new_folder_list = [item.strip() for item in new_folder_list]

    def get_existing_scenes(self):
        """
        Get existing scenes for the selected project or display error
        Returns:
            list : [project_scenes] or (None) if no exisitng scenes in the projects
        """

        with open(self.json_path, "r") as file :
                self.projects_data = json.load(file)

        project_name = self.project_name
        project_data= None
        
        for project in self.projects_data:
                if project_name in project:
                    project_data = project[project_name]
                    break
        project_scenes = project_data["PROJECT_FOLDERS_SEQ"]  

        return project_scenes
    
    def check_name_state(self):
        """
        Enables the folders checkboxes if the user filled a scene name that is not used yet
        """
        project_scenes = self.get_existing_scenes()

        if self.scene_name.text().strip() :
            self.checkbox_state()
            self.console.setText(f"{self.scene_name.text()} is available")
            self.scene_name_label.setStyleSheet("color: rgb(0, 255, 0);")

            for input in self.folder_input:
                input.setEnabled(True)
                self.checkbox_state()

            for scene in project_scenes:
                scene_check = scene
                if scene_check == self.scene_name.text():
                    self.scene_name_label.setStyleSheet("color: rgb(255, 0, 0);")
                    self.console.setText(f"{self.scene_name.text()} already exists")

                    for input in self.folder_input:
                        input.setEnabled(False)
        else : 
            self.console.setText("Specify a name for the scene")
            self.scene_name_label.setStyleSheet(";")

            for input in self.folder_input:
                        input.setEnabled(False)

    def create_scene_folder(self):

        # Update the PROJECT_FOLDERS_SEQ list in the json file
        if os.path.exists(self.json_path) :
            with open(self.json_path, "r") as file :
                try:
                    data = json.load(file)
                except json.JSONDecodeError :
                    data = []
        else :
            data = []
        global seq_path
        for project in data:
            if self.project_name in project:
                project[self.project_name]["PROJECT_FOLDERS_SEQ"].append(self.scene_name.text())
                seq_path = os.path.join(project[self.project_name]["PROJECT_PATH"], "seq").replace(os.sep,"/")
        with open(self.json_path, "w") as file :
            json.dump(data, file, sort_keys=True, indent=4)
        print(f"{self.json_path} successfully updated with scene {self.scene_name}")

        # Create Project folder and subfolders
        scene_root = os.path.join(seq_path, self.scene_name.text())
        os.makedirs(scene_root, exist_ok = True)

        for folder in new_folder_list :
            folder_path = os.path.join(scene_root, folder)
            os.makedirs(folder_path, exist_ok = True)

        print(f"Project folder and subfolders successfully created at {scene_root}")

        self.scene_created.emit()
        self.scene_name.clear()

        self.close()