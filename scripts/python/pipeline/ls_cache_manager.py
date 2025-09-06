import hou
import os
import shutil
import platform

from datetime import datetime
from PySide2 import QtWidgets, QtCore, QtUiTools

class CacheManager(QtWidgets.QWidget):

    # Class Constant
    UI_FILE = "$LSTools/ui/cacheManager.ui"

    KB = 1024
    MB = KB*1024
    GB = MB*1024

    CACHE_NODES = {
        "rop_alembic" : "filename",
        "rop_geometry" : "sopoutput",
        "rop_fbx" : "sopoutput",
        "rop_dop" : "dopoutput",
        }

    def __init__(self):
        super().__init__()
        
        scriptpath = hou.text.expandString(self.UI_FILE)
        self.ui = QtUiTools.QUiLoader().load(scriptpath, parentWidget = self)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle("LS Cache Manager Tool 1.0")
        self.setMaximumSize(1210,500)

        self._init_UI()
        self._setup_connections()

        self.cache_data = []
        self.current_tree_item = 0

    def _init_UI(self):
        """
        Initialize the UI
        """

        self.cache_tree = self.ui.findChild(QtWidgets.QTreeWidget, "tw_scene_cache_nodes")

        self.info_base_name = self.ui.findChild(QtWidgets.QLineEdit, "led_base_name")
        self.info_base_folder = self.ui.findChild(QtWidgets.QLineEdit, "led_base_folder")

        self.info_framerange_label = self.ui.findChild(QtWidgets.QLabel, "label_start_end")
        self.info_start = self.ui.findChild(QtWidgets.QLineEdit, "led_start")
        self.info_end = self.ui.findChild(QtWidgets.QLineEdit, "led_end")
        self.info_inc = self.ui.findChild(QtWidgets.QLineEdit, "led_inc")
        self.info_substeps = self.ui.findChild(QtWidgets.QLineEdit, "led_substeps")
        self.info_clamp_first = self.ui.findChild(QtWidgets.QLineEdit, "led_clamp_first")
        self.info_clamp_last = self.ui.findChild(QtWidgets.QLineEdit, "led_clamp_last")

        self.enable_button = self.ui.findChild(QtWidgets.QPushButton, "btn_enable")
        self.write_button = self.ui.findChild(QtWidgets.QPushButton, "btn_write")
        self.version_up_button = self.ui.findChild(QtWidgets.QPushButton, "btn_version_up")
        self.reload_button = self.ui.findChild(QtWidgets.QPushButton, "btn_reload")

        self.scan_button = self.ui.findChild(QtWidgets.QPushButton, "btn_scan")
        self.reveal_button = self.ui.findChild(QtWidgets.QPushButton, "btn_reveal")
        self.clean_button = self.ui.findChild(QtWidgets.QPushButton, "btn_clean")

        self.total_cache_nodes_label = self.ui.findChild(QtWidgets.QLabel, "lbl_total_cache_nodes")
        self.total_cache_size_label = self.ui.findChild(QtWidgets.QLabel, "lbl_total_cache_size")
        self.unused_versions_label = self.ui.findChild(QtWidgets.QLabel, "lbl_unused_versions")

        # Enable alphabetical order
        self.cache_tree.setSortingEnabled(True)

        # Enable Right click context menu
        self.cache_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.cache_tree.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_connections(self):
        """
        Setup signal connections
        """

        self.scan_button.clicked.connect(self.scan_scene)
        self.cache_tree.itemDoubleClicked.connect(self._select_node)
        self.cache_tree.itemClicked.connect(self._update_cache_details)
        self.reveal_button.clicked.connect(self._reveal_in_explorer)
        self.enable_button.clicked.connect(self._enable_cache)
        self.write_button.clicked.connect(self._write_cache)
        self.version_up_button.clicked.connect(self._write_version_up)
        self.reload_button.clicked.connect(self._reload_geometry)
        self.clean_button.clicked.connect(self._cleanup_old_version)

    def get_current_item(self):
        """
        Return the node, node_path, cache_path and node_type of the current item in the tree
        """
        current = self.cache_tree.currentItem()
        
        if not current:
            hou.ui.displayMessage("Please select a cache first", severity = hou.severityType.Error)
            return

        node_path = current.text(1)
        node = hou.node(node_path)
        node_type = node.type().name()
        cache_path = current.text(3)
        
        return node, node_path, cache_path, node_type

    def scan_scene(self):
        """
        Scan the entire project for nodes doing cache
        """

        try:
            self.cache_tree.clear()
            self.cache_data = []

            # Fecth all the nodes in the scene. store the node and the output parm
            for node_type, parm_name in self.CACHE_NODES.items():
                # Find the nodes of cache category among all the nodes in the scene (cfr CACHE_NODES dict)
                for category in [hou.sopNodeTypeCategory(), hou.dopNodeTypeCategory(), hou.ropNodeTypeCategory()]:
                    # store the sop node that are cache node in the variable node_type_sop for further process
                    node_type_sop = hou.nodeType(category, node_type)
                    # make sure there is something to process
                    if node_type_sop:
                        # get all the instances of that node cache type
                        cache_nodes = node_type_sop.instances()

                        # check the cache_nodes list and fetch the output parm
                        for node in cache_nodes:

                            cache_path = node.parm(parm_name).eval()                            
                            
                            # check the env vars and shortens the cache path if the path is inside the env vars
                            env_var = hou.text.expandString("$JOB")
                            if cache_path.startswith(env_var):
                                cache_path = cache_path.replace(env_var, "$JOB")
                            
                            # Check path validity
                            if not cache_path:
                                continue
                            # trigger the right methods to fetch the expected information 
                            
                            node_name, node_path, node_type_name = self._get_node_details(node)
                            current_version = self._get_current_version(node_path)
                            node_state = self._get_cache_state(node_path)

                            node_data = {
                                "node_name" : node_name,
                                "node_path" : node_path,
                                "node_type" : node_type_name,
                                "node_cache_path" : cache_path,
                                "node_current_version" : current_version,
                                "node_other_version" : self._get_other_version(current_version, cache_path),
                                "node_last_modified" : self._get_last_modified(cache_path),
                                "node_total_size" : self._get_total_size(cache_path, node_path)[0],
                                "unit" : self._get_total_size(cache_path, node_path)[1],
                                "node_state" : node_state
                            }

                            self._add_to_tree(node_data)
                            self.cache_data.append(node_data) 

            self._update_statistics()


            current = self.cache_tree.topLevelItem(self.current_tree_item)
            if current :
                self.cache_tree.setCurrentItem(current)
                self._update_cache_details(current)

            # Change the scan button text if any cache exists in the scene
            if len(self.cache_data) == 0 :
                self.scan_button.setText("Scan Scene")
            else:
                self.scan_button.setText("Refresh Scene")

        except Exception as e:
            hou.ui.displayMessage(f"Error scanning the scene : {str(e)}", severity = hou.severityType.Error)

    def _add_to_tree(self, node_data):
        """
        Add the node data to the tree widget
        """
        item = QtWidgets.QTreeWidgetItem(self.cache_tree)
        item.setText(0, node_data["node_name"])
        item.setText(1, node_data["node_path"])
        item.setText(2, node_data["node_type"])
        item.setText(3, node_data["node_cache_path"])
        item.setText(4, str(node_data["node_current_version"]))
        item.setText(5, str(node_data["node_other_version"]))
        item.setText(6, node_data["node_last_modified"])
        item.setText(7, str(node_data["node_total_size"]) + " " + node_data["unit"])
        item.setText(8, node_data["node_state"])

    def _get_node_details(self, node):
        """
        Get the node details (name, path, file)
        Args:
            node - the node currently checked
        Return:
            tuple with the 3 values
        """

        node_name = node.name()
        node_path = node.path()
        node_type = node.type().name()

        check_parent = node.parent()
        
        if node_name == "render" and check_parent.name() == "filecache":
            node_name = node.parent().parent().name()
            node_path = node.parent().parent().path()
            node_type = node.parent().parent().type().name()
        
        if node_name == "render" and check_parent.name() == "output":
            node_name = node.parent().parent().name()
            node_path = node.parent().path()
            node_type = node.parent().type().name()

        if node_name == "render":
            node_name = node.parent().name()
            node_path = node.parent().path()
            node_type = node.parent().type().name()    

        return node_name, node_path, node_type
    
    def _get_current_version(self, node_path):
        """
        Get the current cache version - ignores if the node has no versionning implemented
        """

        node = hou.node(node_path)
        try:
            version = node.parm("version").eval()
            return version if version else "n/a"

        except AttributeError:
            return "n/a"

    def _get_other_version(self, current_version, cache_path):
        """
        Get a list of version folders in the cache directory
        """

        try:
            if current_version != "n/a":
                
                # Get the directory that contains the caches
                cache_dir = os.path.dirname(os.path.split(cache_path)[0])
                
                #find all the version folder by checking which begins with the letter V
                version =  []

                for item in os.listdir(cache_dir):
                    if os.path.isdir(os.path.join(cache_dir, item)) and item.startswith("v"):
                        try:
                            version_number = int(item[1:])
                            version.append(version_number)
                        except ValueError:
                            continue
                if len(version) == 0:
                    other_version = 0
                    self.clean_button.setEnabled(False)

                else:
                    other_version = len(version) - 1
                    self.clean_button.setEnabled(True)                  

                return other_version

            else:
                return "--"

        except OSError:
                return "not found"
                
    def _get_last_modified(self, cache_path):
        """
        Get the last modified fate of the cache file
        """

        try:
            timestamp = os.path.getmtime(cache_path)
            return datetime.fromtimestamp(timestamp).strftime("%d-%m-%Y - %H:%M")

        except(OSError, ValueError):
            return("--")

    def _select_node(self, item):
        """
        Select and focus to the selected node when clicked
        """

        node_path = item.text(1)
        node = hou.node(node_path)

        if node:
            # Select the node if not None
            node.setSelected(True)

            # Find the closest network editor pane available
            for pane in hou.ui.paneTabs():
                if isinstance(pane, hou.NetworkEditor):
                    network_pane = pane
                    break
            if network_pane:
                # get the parent network in focus
                network_pane.cd(node.parent().path())

                # Frame the node
                network_pane.frameSelection()
        else :
            node_delete = item.text(0)
            hou.ui.displayMessage(
                f"The node selected : '{node_delete}' is not in the scene. Please refresh the scene cache manager",
                severity= hou. severityType.Error)

    def _reveal_in_explorer(self):
        """
        Open the folder containing the selected cache
        """
        selected_item = self.cache_tree.selectedItems()

        if not selected_item:
            hou.ui.displayMessage("Please select a cache first", severity = hou.severityType.Error)
            return
        
        cache_path = selected_item[0].text(3)
        dir_path = os.path.dirname(cache_path)
        if os.path.exists(dir_path):
            if platform.system() == "Windows":
                os.startfile(dir_path)

            elif platform.system() == "Darwin":
                os.system(f"open '{dir_path}")
            
            else:
                os.system(f"xfg-open '{dir_path}")
        else:
            hou.ui.displayMessage(f"Directory not found : {dir_path}", severity = hou.severityType.Error)

    def _cleanup_old_version(self):
        """
        Clean old version of selected cache
        """
        node, node_path, cache_path, node_type = self.get_current_item()
        current_version = self._get_current_version(node_path)
        other_versions = self._get_other_version(current_version, cache_path)

        try:
            if current_version != "n/a":
                
                # Get the directory that contains the caches
                cache_dir = os.path.dirname(os.path.split(cache_path)[0])
                
                #find allt he version folder by checking which begins with the letter V
                folders_delete =  []

                for item in os.listdir(cache_dir):
                    if os.path.isdir(os.path.join(cache_dir, item)) and item.startswith("v"):
                        try:

                            version_number = int(item[1:])
                            if version_number != current_version:
                                folder = os.path.join(cache_dir, item)
                                folders_delete.append(folder)
                        except ValueError:
                            continue
                
                if len(folders_delete) > 0:
                    confirm_delete = hou.ui.displayMessage(
                        f"!!! WARNING!!!\n"
                        f"This action is definitive. All cache version except v{current_version} will be deleted\n"
                        f"Are you sure you want to proceed?",
                        buttons=("Yes", "No"),
                        default_choice = 1,
                        severity= hou.severityType.Warning)
            
                    if confirm_delete == 1:
                        return
                else:
                    hou.ui.displayMessage("No other cache found", severity = hou.severityType.Message)
                    return
                
                for folder_delete in folders_delete:
                    if os.path.exists(folder_delete):
                        try:
                            shutil.rmtree(folder_delete)
 
                        except Exception as e:
                            error_msg = f"Error deleting cache directory : {str(e)}"
                            hou.ui.displayMessage(error_msg, severity = hou.severityType.Error)

                hou.ui.displayMessage("All previous cache has been deleted", severity = hou.severityType.Message)

                self.scan_scene()
        except OSError as e:
            hou.ui.displayMessage(f"Error during cache deletion : {str(e)}", severity = hou.severityType.Error)

    def _show_context_menu(self, position):
        """
        Show context menu for  right click
        """
        
        menu = QtWidgets.QMenu()
        selected_items = self.cache_tree.selectedItems()

        if selected_items:
            reveal_action = menu.addAction("Show Folder")
            reveal_action.triggered.connect(self._reveal_in_explorer)

            cleanup_action = menu.addAction("Clean Old Versions")
            cleanup_action.triggered.connect(self._cleanup_old_version)

        menu.exec_(self.cache_tree.viewport().mapToGlobal(position))

    def _update_statistics(self):
        """
        update the cache statistics labels
        """

        total_nodes = len(self.cache_data)
        self.total_cache_nodes_label.setText(f"Total Cache Nodes = {total_nodes}")

        unused_versions = sum(data["node_other_version"] for data in self.cache_data
                              if isinstance(data["node_other_version"], int))
        
        self.unused_versions_label.setText(f" Unused Versions : {unused_versions}")

        total_bytes, size = self._get_cache_size()
        self.total_cache_size_label.setText(f"Total Cache Size : {total_bytes} {size}")

    def _update_cache_details(self, current):
        """
        Fetch nodes data to populate Cache Infos
        """

        # CACHE NAME, FOLDER
        #====================

        # Store the current item in Class variables to avoid list jumping at refresh
        self.current_tree_item = self.cache_tree.indexOfTopLevelItem(current)

        if not current:
            hou.ui.displayMessage("Please select a cache first", severity = hou.severityType.Error)
            return
        
        cache_path = current.text(3)

        env_var = hou.text.expandString("$HIP")
        if cache_path.startswith(env_var):
            cache_path = cache_path.replace(env_var, "$HIP")
            
        cache_file_info = os.path.split(cache_path)
        self.info_base_name.setText(cache_file_info[1])
        self.info_base_folder.setText(cache_file_info[0])

        node_path = current.text(1)
        node = hou.node(node_path)
        node_type = node.type().name()

        # CACHE FRAMERANGE
        #=================

        # Store the framerange dropwdown menu and populate cache infos accordingly
        valid_frame_range = node.parm("trange")

        if valid_frame_range:

            self.info_start.setText(str(int(node.parm("f1").eval())))
            self.info_end.setText(str(int(node.parm("f2").eval())))
            self.info_inc.setText(str(int(node.parm("f3").eval())))


            if valid_frame_range.eval() == 0 :
                self.info_start.setEnabled(False)
                self.info_end.setEnabled(False)
                self.info_inc.setEnabled(False)
                self.info_framerange_label.setText("Start/End/Inc : Render Current Frame")
            else:
                self.info_start.setEnabled(True)
                self.info_end.setEnabled(True)
                self.info_inc.setEnabled(True)
                self.info_framerange_label.setText("Start/End/Inc : Render Frame Range")
       
        # Special attention to characterio which change the name of the frame range
        elif node_type == "kinefx::characterio::2.0":

            valid_clip_range = node.parm("animatedpose_motionclipcliprangemode").eval()
            self.info_start.setText(str(int(node.parm("animatedpose_motioncliprangex").eval())))
            self.info_end.setText(str(int(node.parm("animatedpose_motioncliprangey").eval())))
            self.info_inc.clear()

            if valid_clip_range == 0:
                self.info_start.setEnabled(False)
                self.info_end.setEnabled(False)
                self.info_inc.setEnabled(False)
                self.info_framerange_label.setText("Start/End/Inc : Use clipinfo Detail Attribute")
            else: 
                self.info_start.setEnabled(True)
                self.info_end.setEnabled(True)
                self.info_inc.setEnabled(False)
                self.info_framerange_label.setText("Start/End : Render Frame Range")

        # Special attention for dop network that doesn't have frame range dropdown
        elif node_type == "output": 
            self.info_start.setEnabled(True)
            self.info_end.setEnabled(True)
            self.info_inc.setEnabled(True)
            self.info_start.setText(str(int(node.parm("f1").eval())))
            self.info_end.setText(str(int(node.parm("f2").eval())))
            self.info_inc.setText(str(int(node.parm("f3").eval())))
            self.info_framerange_label.setText("Start/End : Simulate Frame Range")

        # Finally, for any other node without frame range settings
        else:
            self.info_start.setEnabled(False)
            self.info_end.setEnabled(False)
            self.info_inc.setEnabled(False)
            self.info_framerange_label.setText("Start/End/Inc : n/a")


        # CACHE SUBSTEPS
        # ==============

        valid_substeps = node.parm("substeps")

        if valid_substeps:
           self.info_substeps.setEnabled(True)
           self.info_substeps.setText(str(valid_substeps.eval()))

        # Special attention for dop network which have different name and location for substep
        elif node_type == "output":
            valid_substeps = node.parent().parm("substep")
            self.info_substeps.setText(str(valid_substeps.eval()))

        else:
            self.info_substeps.setEnabled(False)
            self.info_substeps.setText("n/a")

        # CLAMP FRAMES
        #=============

        clamp_first = node.parm("clampfirst")
        clamp_last = node.parm("clamplast")

        if clamp_first and clamp_last:
            clamp_first = str(int(node.parm("clampfirst").eval()))
            clamp_last = str(int(node.parm("clamplast").eval()))

            chk_first = node.parm("doclampfirst").eval()
            chk_last = node.parm("doclamplast").eval()
            
            self.info_clamp_first.setText(clamp_first)
            self.info_clamp_last.setText(clamp_last)
            if chk_first:
                self.info_clamp_first.setEnabled(True)
            else:
                self.info_clamp_first.setEnabled(False)
            if chk_last:
                self.info_clamp_last.setEnabled(True)
            else:
                self.info_clamp_last.setEnabled(False)

        else:
            self.info_clamp_first.setEnabled(False)
            self.info_clamp_last.setEnabled(False)

            self.info_clamp_first.setText("n/a")
            self.info_clamp_last.setText("n/a")

        # ENABLE/DISABLE
        #===============

        #Enable/Disable the Load from Disk feature of cache nodes and Enable/Disable UI unused buttons

        load_from_disk = node.parm("loadfromdisk") 

        if load_from_disk:
            self.enable_button.setEnabled(True)
            self.reload_button.setEnabled(True)
            self.write_button.setEnabled(True)
            self.version_up_button.setEnabled(True)
            load_from_disk = load_from_disk.eval()
            if load_from_disk:
                self.enable_button.setText("Disable")
                self.reload_button.setEnabled(True)
                self.write_button.setEnabled(True)
                self.version_up_button.setEnabled(True)
            else:
                self.enable_button.setText("Enable")
                self.reload_button.setEnabled(False)
        else:
            self.enable_button.setText("Enable")
            self.enable_button.setEnabled(False)
            self.reload_button.setEnabled(False)
            self.write_button.setEnabled(False)
            self.version_up_button.setEnabled(False)

        # CLEAN BUTTON
        #=============

        other_version = current.text(5)

        if other_version == "0" or other_version == "--" or other_version == "not found":
            self.clean_button.setEnabled(False)
        else:
            self.clean_button.setEnabled(True)

        # WRITE+ BUTTON
        #==============

        if other_version == "not found" or other_version == "--":
            self.version_up_button.setEnabled(False)
        else:
            self.version_up_button.setEnabled(True)
        
    def _enable_cache(self):
        """
        Enable/Disable the Load from Disk checkerbox of cache nodes
        """

        node, node_path, cache_path, node_type = self.get_current_item()

        load_from_disk = node.parm("loadfromdisk") 
        
        if load_from_disk:
            chk = load_from_disk.eval()
            if chk:
                load_from_disk.set(False)
            else:
                load_from_disk.set(True)

        self.scan_scene()
    
    def _get_cache_state(self, node_path):
        """
        Get the state of the checbox load from disk
        """

        node = hou.node(node_path)

        current_state = node.parm("loadfromdisk")

        if current_state:
            current_state = node.parm("loadfromdisk").eval()
            if current_state:
                return "Enabled"
            else:
                return "Disabled"
        else:
            return "--"

    def _write_cache(self):
        """
        Write/Rewrite the current cache version
        """

        node, node_path, cache_path, node_type = self.get_current_item()

        node.parm("execute").pressButton()

        self.scan_scene()

    def _write_version_up(self):
        """
        Write a new cache using the highest version numver and increment it by 1
        """

        node, node_path, cache_path, node_type = self.get_current_item()

        current_version = self._get_current_version(node_path)
        
        try:
            if current_version != "n/a":
                # Get the directory that conatins the cache
                cache_dir = os.path.dirname(os.path.split(cache_path)[0])


                #find all the version folder by checking which begins with the letter V
                version =  []
                if os.listdir(cache_dir):

                    for item in os.listdir(cache_dir):
                        if os.path.isdir(os.path.join(cache_dir, item)) and item.startswith("v"):
                            try:
                                version_number = int(item[1:])
                                version.append(version_number)
                    
                            except ValueError:
                                continue

                            last_version = max(version)
                            
                    node.parm("version").set(last_version + 1)
                    node.parm("execute").pressButton()
                    self.scan_scene()

                else:
                    hou.ui.displayMessage("No cache written yet. Please, write a first version")
        except Exception as e:
            hou.ui.displayMessage(f"Error writing the cache : {str(e)}", severity = hou.severityType.Error)

    def _reload_geometry(self):
        """
        Press the selected node Reload Geometry Button
        """

        node, node_path, cache_path, node_type = self.get_current_item()

        node.parm("reload").pressButton()

    def _get_total_size(self, cache_path, node_path):
        """
        Get the total size of all cache version for a specified cache node
        Args:
            path of the cache on disk and the path to the node in the network
        Return :
            tuple of two values : Size and Unit - e.g : 4.2, "MB"
        """

        try:
            node = hou.node(node_path)

            if not node:
                return 0, "B"
            
            node_type = node.type().name()
            frame_range = node.parm("trange")
            if frame_range:
                frame_range = node.parm("trange").eval()
            elif node_type == "kinefx::characterio::2.0":
                frame_range = node.parm("animatedpose_motionclipcliprangemode").eval()

            cache_folder = os.path.dirname(cache_path)

            if not os.path.exists(cache_folder):
                return 0, "B"
            
            # Check if the node handles a single file or a sequence
            if frame_range == 0:
                size = os.path.getsize(cache_path)
            else:
                # Check for all directories in the cache_path folder
                size = 0
                for root, dir, files in os.walk(cache_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        size += os.path.getsize(file_path)

            if size >= self.GB:
                return round(size/self.GB, 2), "GB"
            elif size >= self.MB:
                return round(size/self.MB, 2), "MB"
            elif size>= self.KB:
                return round(size/self.KB, 2), "KB"
            else:
                return size, "B"
            
        except Exception as e:
            hou.ui.displayMessage(f"Error calculating the cache size : {str(e)}", severity = hou.severityType.Error)
            return 0, "B"
        
    def _get_cache_size(self):
        """
        Get the total size of cache in the scene
        """
        multipliers = {
            "B" : 1,
            "KB" : 1024,
            "MB" : 1024**2,
            "GB" : 1024**3,
            "TB" : 1024**4
        }

        total_bytes = 0

        # Loop through each item in the self.cache_data
        if len(self.cache_data) > 0:
            for item_data in self.cache_data:
                size = float(item_data["node_total_size"])
                unit = item_data["unit"]

                # Convert to bytes
                bytes_to_convert = size * multipliers.get(unit, 1)
                total_bytes += bytes_to_convert

            for unit in ["B","KB","MB","GB","TB"]:
                if bytes_to_convert < 1024.0:
                    return total_bytes, unit
                bytes_to_convert = total_bytes / (1024.0**3)
                return f"{bytes_to_convert:.2f}", "GB"
        else:
            return f"0", "B"