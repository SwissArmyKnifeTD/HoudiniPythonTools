import hou
import glob
import os

from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Qt

class SaveCurrentFile(QtWidgets.QWidget):

    # Class constants
    STAGES = ["Main", "Dev","WIP"]
    DEPARTMENTS = ["Gen", "Anim","CFX","Env","FX","LRC","Rig","Layout"]
    LICENSE_TYPE = {
            "Commercial":"hip",
            "Indie":"hiplc",
            "Apprentice":"hipnc",
            "ApprenticeHD":"hipnc",
            "Education":"hipnc"
    }

    file_saved = QtCore.Signal()

    def __init__(self, project_data = None, scene_name = None, project_name = None):
        super().__init__()

        # Initialize variables for project manager arguments
        self.project_data = project_data
        self.scene_name = scene_name
        self.project_name = project_name

        # INITIALIZE UI
        self._init_ui()
        self._setup_connections()
        self.update_project_info()
        self.update_preview_path()

    def _init_ui(self):
        # Window setup
        self.setWindowTitle("LS Save Tool 1.0")
        self.resize(500, 175)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)

        # Create Labels
        self.project_info_label = QtWidgets.QLabel("**")
        self.project_info_label.setMaximumHeight(20)

        self.stage_label = QtWidgets.QLabel("Stage :")
        self.stage_label.setMaximumHeight(20)

        self.dept_label = QtWidgets.QLabel("Department :")
        self.dept_label.setMaximumHeight(20)

        self.file_label = QtWidgets.QLabel("File Name :")
        self.file_label.setMinimumWidth(65)
        self.file_label.setMaximumHeight(20)

        self.console_label = QtWidgets.QLabel("Path :")
        self.console_label.setMaximumHeight(20)

        self.console = QtWidgets.QLabel("")
        self.console.setMaximumHeight(20)

        # Create Combo Boxes
        self.stage_combo = QtWidgets.QComboBox()
        self.stage_combo.setMinimumHeight(25)
        self.stage_combo.setMaximumHeight(25)
        self.stage_combo.addItems(self.STAGES)

        self.dept_combo = QtWidgets.QComboBox()
        self.dept_combo.setMinimumHeight(25)
        self.dept_combo.setMaximumHeight(25)
        self.dept_combo.addItems(self.DEPARTMENTS)

        # Create Text Inputs
        self.file_name = QtWidgets.QLineEdit("")
        self.file_name.setMinimumHeight(30)

        # Create Save Button
        self.save_button = QtWidgets.QPushButton("Save File")
        self.save_button.setMinimumSize(450, 30)

        # Main Layout sections
        self.main_layout = QtWidgets.QVBoxLayout()
        self.label_layout = QtWidgets.QHBoxLayout()
        self.combo_layout = QtWidgets.QHBoxLayout()
        self.file_layout = QtWidgets.QHBoxLayout()
        self.console_layout = QtWidgets.QHBoxLayout()
        
        # Assign layouts to Main
        self.main_layout.addWidget(self.project_info_label)

        self.main_layout.addLayout(self.label_layout)
        self.main_layout.addLayout(self.combo_layout)
        self.main_layout.addLayout(self.file_layout)

        self.main_layout.addWidget(self.save_button)

        self.main_layout.addLayout(self.console_layout)
        self.setLayout(self.main_layout)

        # Build UI
        self.label_layout.addWidget(self.stage_label)
        self.label_layout.addWidget(self.dept_label)

        self.combo_layout.addWidget(self.stage_combo)
        self.combo_layout.addWidget(self.dept_combo)
        
        self.file_layout.addWidget(self.file_label)
        self.file_layout.addWidget(self.file_name)
        
        self.console_layout.addWidget(self.console_label)
        self.console_layout.addWidget(self.console)
    
    def _setup_connections(self):
        """
        Setup the signals connections
        """
        self.save_button.clicked.connect(self.save_current_file)
        self.stage_combo.currentTextChanged.connect(self.update_preview_path)
        self.dept_combo.currentTextChanged.connect(self.update_preview_path)
        self.file_name.textChanged.connect(self.update_preview_path)

    def update_project_info(self):
        """
        Update the project information label
        """
        if self.project_name and self.scene_name:
            info_text = f"Project : {self.project_name} || Scene : {self.scene_name}"
        else:
            info_text = "No Project or Scene selected"

        self.project_info_label.setText(info_text)

    def update_preview_path(self):
        """
        Update the tool console to display the file path
        """

        if not self. project_name or not self.scene_name:
            self.save_button.setEnabled(False)
            self.console.setText("")
            return
        else:
            self.save_button.setEnabled(True)
            
            # Get info from user inputs
            stage = self.stage_combo.currentText()
            dept = self.dept_combo.currentText()
            file_name = self.file_name.text().strip().replace(" ", "_") or "unnamed"

            # Get project path
            project_path = self.project_data["PROJECT_PATH"]

            # Get user infos
            get_user = hou.getenv("USER")
            get_license = hou.licenseCategory().name()
            extension = self.LICENSE_TYPE[get_license]

            # Create the File Path
            base_path = f"{project_path}/seq/{self.scene_name}/hip/{stage.lower()}_{dept.lower()}_{file_name.lower()}_{get_user.lower()}"
            next_version = self.get_next_version(base_path)

            save_path = f"{base_path}_v{next_version:03d}.{extension}"
            self.console.setText(save_path)

    def get_next_version(self, base_path):
        """
        Find the next available version number for the saved file
        Args:
            base_path (str): Base path without the version number and extension
        Return:
            int: Next available version number
        """
        get_license = hou.licenseCategory().name()
        extension = self.LICENSE_TYPE[get_license]

        # Look for existing versions
        pattern = f"{base_path}_v[0-9][0-9][0-9].{extension}"
        existing_files = glob.glob(pattern)

        if not existing_files:
            return 1
        
        versions = []

        for file in existing_files:
            try:
                # Extract the version number from the file name
                version_string = file.split("_v")[-1].split(".")[0]
                version_int = int(version_string)
                versions.append(version_int)

            except (ValueError, IndexError):
                continue

        if not versions:
            return 1
        return max(versions) + 1 

    def save_current_file(self):
        """
        Save the current opened Houdini file
        """

        if not self. project_name or not self.scene_name:
            self.save_button.setEnabled(False)
            return
        else:
            self.save_button.setEnabled(True)
        
        save_path = self.console.text()

        try:
            # Create the directory if it doesn't exist
            save_dir = os.path.dirname(save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            # Save the Houdini file
            hou.hipFile.save(save_path)
            hou.ui.displayMessage(f"File saved succeessfully : {save_path}", severity = hou.severityType.Message)

            self.update_preview_path()
        except PermissionError:
            hou.ui.displayMessage(f"Permissions denied. Cannot save to the specified location. Check with IT Department")
        except OSError as e:
            hou.ui.displayMessage(f"Error saving the file : {str(e)}", severity = hou.severityType.Error)
        except Exception as e:
            hou.ui.displayMessage(f"Unexpected error while saving the file : {str(e)}", severity = hou.severityType.Error)
        
        self.file_saved.emit()