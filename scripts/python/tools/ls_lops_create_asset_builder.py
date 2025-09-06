import hou
import os

from PySide2 import QtCore, QtUiTools, QtWidgets
from tools import ls_lops_asset_builder as lab
from tools import ls_lops_light_rig as llr
from tools import ls_lops_create_lookdev_camera as llc

class CreateAssetBuilder(QtWidgets.QMainWindow):

    UI_FILE = "$LSTools/ui/asset_builder.ui"

    def __init__(self):
        super().__init__()   

        self.selected_directory = None
        self.hdr = None
        self.light_options = []
        self.asset_name = None

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
        self.setWindowTitle("LS Create Asset Builder 1.0")
        self.setMaximumSize(360,430)

        # SET CONNECTIONS
        # Asset
        self.btn_asset = self.ui.findChild(QtWidgets.QToolButton, "btn_asset")
        self.led_asset = self.ui.findChild(QtWidgets.QLineEdit, "led_asset")

        # Light Rig   
        self.chkb_create_light_rig = self.ui.findChild(QtWidgets.QCheckBox, "chkb_create_light_rig")
        self.chkb_three_points = self.ui.findChild(QtWidgets.QCheckBox, "chkb_three_points")
        self.chkb_three_points.setChecked(True)
        self.chkb_dome = self.ui.findChild(QtWidgets.QCheckBox, "chkb_dome")

        self.grp_hdr = self.ui.findChild(QtWidgets.QGroupBox, "grp_hdr")
        self.btn_hdr = self.ui.findChild(QtWidgets.QToolButton, "btn_hdr")
        self.led_hdr = self.ui.findChild(QtWidgets.QLineEdit, "led_hdr")
                
        # Camera Rig
        self.chkb_create_camera_rig = self.ui.findChild(QtWidgets.QCheckBox, "chkb_create_camera_rig")
        self.chkb_include_spheres = self.ui.findChild(QtWidgets.QCheckBox, "chkb_include_spheres")
        self.chkb_include_checker = self.ui.findChild(QtWidgets.QCheckBox, "chkb_include_palette")

        # Create Asset
        self.btn_create_asset = self.ui.findChild(QtWidgets.QPushButton, "btn_create_asset")

        # CREATE INPUT LIST
        self.user_input = [
            self.led_asset,
            self.chkb_create_light_rig, 
            self.chkb_three_points,
            self.chkb_dome,
            self.grp_hdr,
            self.chkb_create_camera_rig,
            self.chkb_include_spheres,
            self.chkb_include_checker,
            self.btn_create_asset
        ]

        # CREATE LIGHT OPTIONS LIST
        self.light_options = [self.chkb_three_points.checkState(), self.chkb_dome.checkState()]
        self.camera_options = [self.chkb_include_spheres.checkState(), self.chkb_include_checker.checkState()]

        for input in self.user_input:
            input.setEnabled(False)
        
    def _setup_connections(self):
        """
        Setup the signal connections
        """

        # Asset Button
        self.btn_asset.clicked.connect(self.select_asset)

        # Main options
        self.chkb_create_light_rig.stateChanged.connect(self._light_rig_options)
        self.chkb_create_camera_rig.stateChanged.connect(self._camera_rig_options)

        # Light Options
        self.chkb_three_points.stateChanged.connect(self._light_rig_status)
        self.chkb_dome.stateChanged.connect(self._light_rig_status)
        self.chkb_dome.stateChanged.connect(self._dome_options)
        self.btn_hdr.clicked.connect(self.select_hdr)
        self.chkb_include_spheres.stateChanged.connect(self._camera_rig_status)
        self.chkb_include_checker.stateChanged.connect(self._camera_rig_status)

        # Create Asset Button
        self.btn_create_asset.clicked.connect(lambda : self.create_asset(self.asset_name, self.selected_directory, self.light_options, self.hdr, self.camera_options))

    def select_asset(self):
        """
        Prompt the user to select an asset to process.
        Unlock the UI if the asset is valid.
        """

        # Get the file
        selected_directory = hou.ui.selectFile(title = "Select the file to import",
                                                file_type = hou.fileType.Geometry,
                                                multiple_select = False
                                                )
            
        self.selected_directory = hou.text.expandString(selected_directory)

        valid_extensions = ["fbx", "abc", "obj", "bgeo", "bgeo.sc"]

        path, filename = os.path.split(self.selected_directory)
        self.asset_name = filename.split(".")[0]
        asset_extension = filename.split(".")[-1]

        if filename and asset_extension in valid_extensions:
            self.led_asset.setEnabled(True)
            self.led_asset.setText(filename)
            self.chkb_create_light_rig.setEnabled(True)
            self.chkb_create_camera_rig.setEnabled(True)  
            self.btn_create_asset.setEnabled(True)

        else:
            self.led_asset.setEnabled(False)
            self.led_asset.setText("")
            self.chkb_create_light_rig.setEnabled(False)
            self.chkb_create_camera_rig.setEnabled(False)  
            self.btn_create_asset.setEnabled(False)

            hou.ui.displayMessage("Please select a Geometry asset", severity = hou.severityType.Message) 

    def select_hdr(self):
        """
        Prompt the user to select an asset to process.
        Unlock the UI if the asset is valid.
        """

        # Get the file
        selected_hdr = hou.ui.selectFile(title = "Select the HDR file to use",
                                                file_type = hou.fileType.Image,
                                                multiple_select = False
                                                )
            
        self.hdr = hou.text.expandString(selected_hdr)

        valid_extensions = ["exr", "png", "jpg", "jpeg", "hdr", "pic"]

        path, filename = os.path.split(self.hdr)
        asset_extension = filename.split(".")[-1]

        if filename and asset_extension in valid_extensions:
            self.led_hdr.setText(filename)

        else:
            self.led_hdr.setText("")

            hou.ui.displayMessage("Please select a HDR asset", severity = hou.severityType.Message)    
            
    def _light_rig_options(self, state):
        """
        Updates the UI when enabling the create light rig option.
        """

        # Enable bot checkboard options
        self.chkb_three_points.setEnabled(state)
        self.chkb_dome.setEnabled(state)

        # Enables the HDR input if the corresponding checkbox is enabled as well
        if self.chkb_dome.checkState():
            self.grp_hdr.setEnabled(state)
        else:
            self.grp_hdr.setEnabled(False)

        # Refresh the list of checkbox state
        self.light_options = [self.chkb_three_points.checkState(), self.chkb_dome.checkState()]

        # Enables the Three Points Light Rig checkbox if all options are disabled
        if not self.light_options[0] and not self.light_options[1] and self.chkb_create_light_rig.checkState():
            self.chkb_three_points.setChecked(True)

    def _light_rig_status(self):
        """
        Updates the UI when both light rig options are disabled.
        """

        # Refresh the list of checkbox state
        self.light_options = [self.chkb_three_points.checkState(), self.chkb_dome.checkState()]

        # Disables the Create Light rig checkbox if both options are disabled
        if not self.light_options[0] and not self.light_options[1]:
            self.chkb_create_light_rig.setChecked(False)

    def _dome_options(self, state):
        """
        Enables the HDR Input if requested.
        """

        self.grp_hdr.setEnabled(state)

    def _camera_rig_options(self, state):
        """
        Updates the UI for camera rig otions
        """ 
        
        self.chkb_include_spheres.setEnabled(state)
        self.chkb_include_checker.setEnabled(state)

    def _camera_rig_status(self):
        """
        Updates the UI when both light rig options are disabled.
        """

        # Refresh the list of checkbox state
        self.camera_options = [self.chkb_include_spheres.checkState(), self.chkb_include_checker.checkState()]

    def create_asset(self, asset_name, selected_directory, light_options, hdr, camera_options):
        """
        Create the asset builder depending on the user selections
        """

        if selected_directory:
            lab.create_component_builder(selected_directory)

            if self.chkb_create_camera_rig.checkState():
                sphere_bool = camera_options[0]
                checker_bool = camera_options[1]

                llc.create_lookdev_camera_node(asset_name, sphere_bool, checker_bool)

            if self.chkb_create_light_rig.checkState():

                three_points_bool = light_options[0]
                dome_bool = light_options[1]

                llr.create_light_rig(asset_name, three_points_bool, dome_bool, hdr)

            
