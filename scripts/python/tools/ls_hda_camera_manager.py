import hou

class MultiCameraManager:
    """
    Helps managing cameras in a Houdini Scene
    Allows to set cameras - set camera, set frame range
    Allow batch rename cameras
    Merge all camera into a single camera
    Render submission
    """

    def __init__(self):
        """
        Initialize variables and context location
        """

        self.cameras = {}
        self.start_frame = 1001
        self.cameras_to_render = {}
        self.obj = hou.node("/obj")
        self.node = hou.pwd()
        self.CAMERA_PARMS = [
            "tx", "ty", "tz", "rx", "ry" , "rz",
            "resx", "resy", "aspect",
            "focal", "aperture", "near", "far", "focus", "fstop"
        ]
        
    def scan_scene_cameras(self):
        """
        Scan the scene forr cameras nodes end stores info in self.cameras
        """

        try:
            # Find all the camera nodes
            self.cameras = {
                camera.name() : camera for camera in self.obj.recursiveGlob("*", filter = hou.nodeTypeFilter.ObjCamera)
            }

            if not self.cameras:
                hou.ui.displayMessage("No Cameras in the Scene", severity = hou.severityType.Error)
                return
                       
            self._update_ui_camera()

        except Exception as e:
            hou.ui.displayMessage(f"Error scanning the scene for cameras : {str(e)}", severity = hou.severityType.Error)

    def _update_ui_camera(self):
        """
        Build the UI menu parameter for found cameras
        """
        self.node = hou.pwd()
        cam_list = list(self.cameras.keys())
        node_ptg = self.node.parmTemplateGroup()
        camera_selection = node_ptg.find("camera_selector")

        new_menu = hou.MenuParmTemplate(
            name = "camera_selector",
            label = "Select Camera",
            menu_items = cam_list,
            menu_labels = cam_list
        )

        if not camera_selection:
            node_ptg.insertAfter("scan_scene", new_menu)
        else:
            node_ptg.replace(camera_selection, new_menu)

        self.node.setParmTemplateGroup(node_ptg)


        self.node.parm("set_visible").set(1)
        self.node.parm("camera_list").set(0)
        self.node.parm("enable_render_btn").set(0)

    def set_active_camera(self):
        """
        Set viewport with the selected camera in the list
        """

        # Get the current camera by name
        cam_name = self.node.parm("camera_selector").rawValue()
        camera = self.cameras[cam_name]

        # Get viewport
        viewport = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)

        if viewport:
            viewport.curViewport().setCamera(camera)

            first_frame = hou.playbar.playbackRange()[0]
            last_frame = hou.playbar.playbackRange()[1]

            keyframes = self._get_camera_frame_range(camera)

            if keyframes:
                first_frame = min(keyframes)
                last_frame = max(keyframes)
                
            hou.playbar.setPlaybackRange(first_frame, last_frame)
            set_global_frame_range = f"tset `({first_frame}-1)/$FPS` `{last_frame}/$FPS"
            hou.hscript(set_global_frame_range)
            hou.setFrame(first_frame)

    def _get_camera_frame_range(self, camera):
        """
        Get the frame range of the selected camera and set the playbar ranges
        Args:
            camera : camera to check
        """

        # Check if camera has keyframes
        try:
            if any(camera.parm(parms).isTimeDependent() for parms in self.CAMERA_PARMS):
                keyframes = []

                for parm in self.CAMERA_PARMS:
                    parm_keyframes = camera.parm(parm).keyframes()
                    if parm_keyframes:
                        keyframes.extend(value.frame() for value in parm_keyframes)

            return keyframes
        
        except UnboundLocalError:
            keyframes = []
            return keyframes

    def _sorted_cameras(self):
        """
        Sorts cameras by the lowest keyframe value and gets the start, end and all keyframes
        Return:
            dict : dictionnary containing all the cameras sorted
        """

        cameras_to_merge = {}

        for name, camera in self.cameras.items():
            frames = list(set(self._get_camera_frame_range(camera)))
            cameras_to_merge[name] = {
                "camera" : camera,
                "frames" : frames,
                "start" : min(frames) if frames else float("inf"),
                "end" : max(frames) if frames else float("inf")
            }

        # Sort cameras by their start frame
        sorted_cameras = dict(sorted(
            cameras_to_merge.items(),
            key = lambda x: x[1]["start"]
        ))

        return sorted_cameras

    def merge_cameras(self):
        """
        Merge all cameras in the scene into a single camera with sequential animations
        Camera and animations are arranged sequectially with each camera animations starting
        after the previous camera's last keyframe
        """

        # Make sure the list is up to date avoiding deleted cameras to break logic
        self.scan_scene_cameras()

        # Store the user start frame
        self.start_frame = self.node.parm("start_frame").eval()

        # Create the new camera node
        merged_cam_name = self.node.parm("merged_camera_name").evalAsString()
        if not merged_cam_name:
            merged_cam_name = "merged_cameras"    
        
        merged_cam = self.obj.createNode("cam", merged_cam_name)
        sorted_cameras = self._sorted_cameras()

        current_frame = self.start_frame

        # Process each camera sequentially
        for cam_name, cam_data in sorted_cameras.items():
            camera = cam_data["camera"]
            original_frames = cam_data["frames"]

            if original_frames:
                # Calcualte the frame offset between two consecutive cameras
                frame_offset = current_frame - cam_data["start"]

                for parm_name in self.CAMERA_PARMS:
                    source_parm = camera.parm(parm_name)
                    target_parm = merged_cam.parm(parm_name)

                    if source_parm and target_parm:
                        # Get keyframes for the parm
                        keyframes = source_parm.keyframes()

                        if keyframes:
                            for key in keyframes:
                                new_key = hou.Keyframe()
                                new_key.setFrame(key.frame() + frame_offset)
                                new_key.setValue(key.value())
                                new_key.setExpression(key.expression())
                                target_parm.setKeyframe(new_key)
                        else:
                            # If the parameter is not animated but has value
                            new_key = hou.Keyframe()
                            new_key.setFrame(current_frame)
                            new_key.setValue(source_parm.eval())
                            new_key.setExpression("constant()", hou.exprLanguage.Hscript)
                            target_parm.setKeyframe(new_key)

                # Updates current frame for the next camera
                current_frame += (cam_data["end"] - cam_data["start"] + 1)

            else:
                # For non animated camera - create a single keyframe
                for parm_name in self.CAMERA_PARMS:
                    source_parm = camera.parm(parm_name)
                    target_parm = merged_cam.parm(parm_name)

                    if source_parm and target_parm:
                        new_key = hou.Keyframe()
                        new_key.setFrame(current_frame)
                        new_key.setValue(source_parm.eval())
                        target_parm.setKeyframe(new_key)
                
                current_frame += 1

        if current_frame > self.start_frame:
            hou.playbar.setPlaybackRange(self.start_frame, current_frame)
            set_global_frame_range = f"tset `{self.start_frame - 1}/$FPS` `{current_frame}/$FPS"
            hou.hscript(set_global_frame_range)
            hou.setFrame(self.start_frame)

        self.scan_scene_cameras()

    def rename_cameras(self):
        """
        Batch rename cameras with prefix and/or suffix
        """
        
        for old_name, camera in self.cameras.items():
            new_name = f"{self.node.parm('name_prefix').evalAsString()}{old_name}{self.node.parm('name_suffix').evalAsString()}"

            try:
                camera.setName(new_name)
            except Exception as e:
                hou.ui.displayMessage(f"Failed to rename {old_name} to {new_name} : {str(e)}" , severity = hou.severityType.Error)

        # Refresh camera list
        self.scan_scene_cameras()


    def _select_cameras(self):
        """
        Prompt the user to select which cameras to render through a selectFromList popup window
        Store the selected cameras to self.cameras_to_render dictionnary for further use in render select_rendering_node() function
        """

        self.cameras_to_render = {}
        sorted_cameras = self._sorted_cameras()
        choices = list(sorted_cameras.keys())

        torender = hou.ui.selectFromList(choices,
                                        default_choices=(),
                                        exclusive = False,
                                        message = "Camera Picker",
                                        title = "Choose which cameras to render",
                                        column_header = "Cameras",
                                        num_visible_rows = len(choices),
                                        sort = False
                                        )
        cam_input = [self.cameras[choices[value]].name() for value in torender]
        
        if torender:
            self.node.parm("enable_render_btn").set(1)
        else :
            self.node.parm("enable_render_btn").set(0)
            hou.ui.displayMessage("Please, select at least one camera to render", severity = hou.severityType.Error)
            
        camera_selection = [cam.strip() for cam in cam_input]
        self.cameras_to_render = {name : sorted_cameras[name] for name in camera_selection if name in sorted_cameras}

        # Handle MultiParm list of string
        list_length = len(cam_input)
        multiparm_folder = self.node.parm("camera_list")
        multiparm_folder.set(list_length)

        # Create a list of dictionnaries containing the values to display
        data_list = []

        for cam_name, camera in self.cameras_to_render.items():
            
            camera_name = cam_name

            start = "" if str(camera["start"]) == "inf" else int(camera["start"])
            end = ""  if str(camera["end"]) == "inf" else int(camera["end"])
            camera_frame = f"{start}-{end}"

            if type(start) == int and type(end) == int :
                camera_duration = end-start
            else:
                camera_duration = "-"

            resx = camera["camera"].parm("resx").eval()
            resy = camera["camera"].parm("resy").eval()
            camera_resolution = f"{resx}x{resy}"

            if len(camera["frames"]) > 0:
                animated = "Yes"
            else:
                animated = "No"

            camera_dict = {
                "name" : camera_name,
                "animated" : animated,
                "frames" : camera_frame,
                "Duration" : camera_duration,
                "resolution" : camera_resolution,
            }

            data_list.append(camera_dict)

        # Parse the data list in the right table cell            
        for i, parm_template in enumerate(multiparm_folder.multiParmInstances()):
            
            ident = parm_template.name().split("camera_details")[1].split("_")
            cell_value = list(data_list[int(ident[0])-1].values())[int(ident[1])-1]
            
            parm_template.set(str(cell_value))

    def select_rendering_node(self):
        """
        Select a Karma node and setup the rendering parameters based on selected cameras
        """

        # Select a Karma node
        karma_node = hou.ui.selectNode(node_type_filter = hou.nodeTypeFilter.Rop)

        if not karma_node:
            hou.ui.displayMessage("No valid ROP node selected", severity = hou.severityType.Error)
            return
        
        karma_node = hou.node(karma_node)
            
        # Process each camera
        for cam_name, camera in self.cameras_to_render.items():
            base_output = f"$HIP/render/{cam_name}/$HIPNAME.$OS.$F4.exr"
            camera_output = base_output.replace(".$F4.exr", f".{cam_name}.$F4.exr")

            is_animated = camera["frames"]

            if is_animated:
                first_frame = min(is_animated)
                last_frame = max(is_animated)
                inc_frame = self.node.parm("nth_frame")
                set_value = 1
            else:
                set_value = 0

            resx = camera["camera"].parm("resx").eval()
            resy = camera["camera"].parm("resy").eval()

            # Set Karma parameters
            karma_node.parmTuple("f").deleteAllKeyframes()
            karma_node.parm("trange").set(set_value)
            if set_value:
                karma_node.parm("f1").set(first_frame)
                karma_node.parm("f2").set(last_frame)
                karma_node.parm("f3").set(inc_frame)
            karma_node.parm("picture").set(camera_output)
            karma_node.parm("camera").set(camera["camera"].path())
            karma_node.parm("resolutionx").set(resx)
            karma_node.parm("resolutiony").set(resy)
            karma_node.parm("render").pressButton()