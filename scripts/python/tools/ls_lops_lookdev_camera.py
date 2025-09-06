import hou

from husd import assetutils
from pxr import Usd, Gf, UsdGeom

def create_lookdev_camera_script():
    """
    Creates a lookddev camera based on the bbox for the selected asset
    It also allows the user to select a custom camera
    """

    node = hou.pwd()
    stage = node.editableStage()

    _create_parameters(node)

    # The default values
    target_path = node.evalParm("target")
    camera_path = node.evalParm("camera_path")
    spin = node.evalParm("spin")
    pitch = node.evalParm("pitch")
    distance = node.evalParm("distance")
    animate = node.evalParm("animate")
    use_existing_camera = node.evalParm("use_existing_camera")
    existing_camera_path = node.evalParm("existing_camera")
    frames = node.evalParm("frames")
    start_frame = node.evalParm("start_frame")

    # Ensure the target path is valid (from the component output node)
    if not target_path.startswith('/'):
        target_path = '/' + target_path
    
    # Get the target prim
    target_prim = stage.GetPrimAtPath(target_path)

    # Use the BBoxCache instead; directly using extentsHint is annoying/painful
    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.EarliestTime(), ["default", "render"])
    bounds = bbox_cache.ComputeLocalBound(target_prim).GetBox()

    # Check if the camera exists
    existing_camera = None
    temp_camera = None

    if use_existing_camera:
        existing_prim = stage.GetPrimAtPath(existing_camera_path)

        if existing_prim and existing_prim.IsA(UsdGeom.Camera):
            existing_camera = UsdGeom.Camera(existing_prim)
        else:
            raise hou.NodeError(f"Existing camera not found at {existing_camera_path}")
        
    # Create or use the custom camera
    if existing_camera:
        camera = existing_camera
    else:
        camera = UsdGeom.Camera.Define(stage, camera_path)
        
        # Add settings to the new camera
        camera.GetHorizontalApertureAttr().Set(10.0)
        camera.GetVerticalApertureAttr().Set(10.0)
        camera.GetFocalLengthAttr().Set(35.0)
        camera.GetClippingRangeAttr().Set(Gf.Vec2f(0.001, 100000))
 
    if animate:

        for frame in range(frames):
            # Create an animated camera by setting the matrix value at each frame
            current_frame = start_frame + frame
            time_code = Usd.TimeCode(current_frame)
            
            # Calculate the spin angle nased on the frame
            current_spin = spin + (frame/frames * 360)

            # Current SOP create xform
            
            temp_stage = Usd.Stage.CreateInMemory()
            temp_camera = _create_framed_camera(temp_stage, bounds, pitch, current_spin, distance)

            # Get the transform matrix
            temp_xform = UsdGeom.Xformable(temp_camera)

            for xform_op in temp_xform.GetOrderedXformOps():
                if xform_op.GetOpName().endswith("frameToBounds"):
                    matrix = xform_op.Get()

                    # Apply the matrix to our actual camera at this time sample
                    main_xform_camera = UsdGeom.Xformable(camera)

                    if frame == 0:
                        transform_op = main_xform_camera.AddTransformOp(opSuffix = "orbitTransform")
                        transform_op.Set(matrix)
                    else:
                        # Get the existing transform op
                        for op in main_xform_camera.GetOrderedXformOps():
                            if op.GetOpName().endswith("orbitTransform"):
                                # Set the matrix at this time sample
                                op.Set(matrix, time_code)
                                break
                    break

    else:
        # Static camera setup
        # Create cameras using the method createFramedCameraToBounds
        if existing_camera:
            # For existing camera, add a transform to place the camera
            main_xform_camera = UsdGeom.Xformable(camera)

            # Create a temporary stage to generate the camera tansform
            temp_stage = Usd.Stage.CreateInMemory()
            temp_camera = _create_framed_camera(temp_stage, bounds, pitch, spin, distance)
            
            # Get the transform matrix
            temp_xform = UsdGeom.Xformable(temp_camera)

            for xform_op in temp_xform.GetOrderedXformOps():
                if xform_op.GetOpName().endswith("frameToBounds"):
                    matrix = xform_op.Get()
                    transform_op = main_xform_camera.AddTransformOp(opSuffix = "orbitTransform")
                    transform_op.Set(matrix)
                    break
        else:
            # Create a new camera
            temp_camera = assetutils.createFramedCameraToBounds(
                stage, 
                bounds, 
                cameraprimpath = camera_path,
                rotatex = 25 + pitch, 
                rotatey = 35 + spin, 
                offsetdistance = distance)
              
def _create_framed_camera(stage, bounds, pitch, spin, distance):
    """
    Creates a Thumbnail camera using trhe assetutils createFramedCameraToBounds method
    Args:
    bounds, primpath, pitch, spin, distance
    Return:
        temp_camera = The camera generated by the createFramedCameraToBounds method
    """

    # Create a temporary stage to generate the camera tansform
    temp_camera = assetutils.createFramedCameraToBounds(
        stage, 
        bounds, 
        cameraprimpath = "/temp_camera",
        rotatex = 25 + pitch, 
        rotatey = 35 + spin, 
        offsetdistance = distance)
    
    return temp_camera

def _create_parameters(node):
    """
    Creates all the required parameters inside the python node
    """

    ptg = node.parmTemplateGroup()

    find_parm = ptg.find("target")
    
    if not find_parm:

        base_parm_folder = hou.FolderParmTemplate(
            name = "base_folder",
            label = "Base Parameters",
            folder_type = hou.folderType.Simple
        )

        target_prim = hou.StringParmTemplate(
            name = "target",
            label = "Target Prim",
            num_components = 1
        )

        camera_string = hou.StringParmTemplate(
            name = "camera_path",
            label = "Camera Path",
            num_components = 1,
            default_value = ("/cam/ThumbnailCamera",)
        )

        spacer = hou.SeparatorParmTemplate(
            name = "spacer"
        )

        use_camera = hou.ToggleParmTemplate(
            name = "use_existing_camera",
            label = "Use Existing Camera",
            default_value = False
        )

        existing_camera = hou.StringParmTemplate(
            name = "existing_camera",
            label = "Existing Camera Path",
            num_components = 1,
            disable_when = "{use_existing_camera == 0}"
        )

        separator = hou.SeparatorParmTemplate(
            name = "sep"
        )

        spin_slider = hou.FloatParmTemplate(
            name = "spin",
            label = "Spin",
            num_components = 1,
            default_value = (0,),
            min = -180.0,
            max = 180.0
        )

        pitch_slider = hou.FloatParmTemplate(
            name = "pitch",
            label = "Pitch",
            num_components = 1,
            default_value = (0,),
            min = -90.0,
            max = 90.0
        )

        distance_slider = hou.FloatParmTemplate(
            name = "distance",
            label = "Distance",
            num_components = 1,
            default_value = (0,),
            min = 0.0,
            max = 20.0
        )

        anim_parm_folder = hou.FolderParmTemplate(
            name = "anim_folder",
            label = "Animated Parameters",
            folder_type = hou.folderType.Simple
        )

        animate_toggle = hou.ToggleParmTemplate(
            name = "animate",
            label = "Animate",
            default_value = False
        )        

        number_frames = hou.IntParmTemplate(
            name = "frames",
            label = "Number of Frames",
            num_components = 1,
            default_value = (60,),
            min = 30,
            max = 500,
            disable_when = "{animate == 0}"
        )

        start_frame = hou.IntParmTemplate(
            name = "start_frame",
            label = "Start Frame",
            num_components = 1,
            default_value = (0,),
            disable_when = "{animate == 0}"
        )

        base_parm_folder.addParmTemplate(target_prim)
        base_parm_folder.addParmTemplate(camera_string)
        base_parm_folder.addParmTemplate(spacer)
        base_parm_folder.addParmTemplate(use_camera)
        base_parm_folder.addParmTemplate(existing_camera)
        base_parm_folder.addParmTemplate(separator)
        base_parm_folder.addParmTemplate(spin_slider)
        base_parm_folder.addParmTemplate(pitch_slider)
        base_parm_folder.addParmTemplate(distance_slider)

        ptg.append(base_parm_folder)

        anim_parm_folder.addParmTemplate(animate_toggle)
        anim_parm_folder.addParmTemplate(number_frames)
        anim_parm_folder.addParmTemplate(start_frame)

        ptg.append(anim_parm_folder)
        
        node.setParmTemplateGroup(ptg)
