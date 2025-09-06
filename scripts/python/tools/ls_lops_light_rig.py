import hou
import numpy as np

from modules import ls_misc_utils as mu

def create_light_rig(asset_name = None, three_points_bool = True, dome_bool = True, hdr_file = None):
    """
    Creates a three point light setup around selected object in Solaris
    """

    # Get the selected node and check if it is in Solaris context
    selected_node= hou.selectedNodes()
    is_solaris = mu._is_in_solaris()

    if not selected_node or not is_solaris:
        hou.ui.displayMessage("No valid node selected, please select a node in Solaris context", 
                              severity = hou.severityType.Error
        )
        return False
    
    target_node = selected_node[0]

    # Get Stage
    stage = hou.node("/stage")
    
    def _create_three_points_setup(stage, asset_name):
        """
        Creates the three light points branch when requested
        """

        # Get the bounding box for the asset
        bounds = mu.calculate_prim_bounds(target_node)

        # Calculate the center and dimensions
        center = bounds["center"]
        size = bounds["size"]
        max_dim = max(size)

        # Calculate the light positions

        # Key Light
        key_position = hou.Vector3(
            center[0] + max_dim * -0.5,
            center[1] + max_dim * 1.5,
            center[2] + max_dim * 1
        )

        # Fill Light
        fill_position = hou.Vector3(
            center[0] + max_dim * 1.5,
            center[1] + max_dim * 1.5,
            center[2] + max_dim * 1
        )

        # Back Light
        back_position = hou.Vector3(
            center[0] - max_dim * 1.5,
            center[1] + max_dim * 1.5,
            center[2] - max_dim * 1
        )

        if asset_name:
            key_light_name = asset_name + "_key_light"
            fill_light_name = asset_name + "_fill_light"
            back_light_name = asset_name + "_back_light"
            xform_light_name = asset_name + "_light_rig_transform"
        else:
            key_light_name = "key_light"
            fill_light_name = "fill_light"
            back_light_name = "back_light"
            xform_light_name = "light_rig_transform"

        key_light = stage.createNode("light::2.0", key_light_name)
        fill_light = stage.createNode("light::2.0", fill_light_name)
        back_light = stage.createNode("light::2.0", back_light_name)
        
        # Set the light position
        key_light.parmTuple("t").set(key_position)
        fill_light.parmTuple("t").set(fill_position)
        back_light.parmTuple("t").set(back_position)

        # Make the lights look at the center
        for light in [key_light, fill_light, back_light]:
            light.parm("lighttype").set(2)
            light.parm("xn__inputsexposure_vya").set(3)
            light_position = hou.Vector3(light.parmTuple("t").eval())
            light_direction = center - light_position

            # Convert the direction into angles
            x_angle_pitch = np.arctan2(light_direction[1], np.sqrt(light_direction[0]**2 + light_direction[2]**2))
            y_angle_yaw = np.arctan2(-light_direction[0], -light_direction[2])

            # Convert radians to degrees
            light.parmTuple("r").set((np.degrees(x_angle_pitch), np.degrees(y_angle_yaw), 0))

        # Adjust light settings

        # Key Light
        key_light.parm("xn__inputsintensity_i0a").set(5)

        # Fill Light
        fill_light.parm("xn__inputsintensity_i0a").set(3)
        fill_light.parmTuple("xn__inputscolor_zta").set((1, 0.5, 0))

        # Back Light
        back_light.parm("xn__inputsintensity_i0a").set(2)
        back_light.parmTuple("xn__inputscolor_zta").set((0, 0.5, 1))

        # Support nodes
        xform_light = stage.createNode("xform", xform_light_name)

        # xform to control all lights
        xform_light.parm("primpattern").set("%type:Light")

        # Format the "lights_to_add" to allow multiple asset to be built in the same stage
        key_string = f'"type": "LightItem", "path": "/lights/{key_light.name()}", "prim_path": "/lights/{key_light.name()}", "rgb": [55, 55, 55], "controls": ["buttons"], "contents": []'
        fill_string = f'"type": "LightItem", "path": "/lights/{fill_light.name()}", "prim_path": "/lights/{fill_light.name()}", "rgb": [55, 55, 55], "controls": ["buttons"], "contents": []'
        back_string = f'"type": "LightItem", "path": "/lights/{back_light.name()}", "prim_path": "/lights/{back_light.name()}", "rgb": [55, 55, 55], "controls": ["buttons"], "contents": []'

        lights_to_add = (
            "{" + key_string + "}, " +
            "{" + fill_string + "}, " +
            "{" + back_string + "} "
        )

        fill_light.setInput(0, key_light)
        back_light.setInput(0, fill_light)
        xform_light.setInput(0, back_light)

        nodes_to_layout = [key_light, fill_light, back_light, xform_light]

        return lights_to_add, nodes_to_layout, xform_light

    def _create_dome_setup(stage, asset_name):
        """
        Creates the dome light branch when requested
        """

        # Get the bounding box for the asset
        bounds = mu.calculate_prim_bounds(target_node)

        # Calculate the center and dimensions
        center = bounds["center"]
        size = bounds["size"]

        # Dome Light Position
        dome_position = hou.Vector3(
            center[0],
            center[1] - size[1]  * 0.5,
            center[2]
        )

        if asset_name:
            dome_light_name = asset_name + "_dome_light"
            xform_dome_name = asset_name + "_dome_rig_transform"
        else:
            dome_light_name = "dome_light"
            xform_dome_name = "dome_rig_transform"

        # Create dome light
        dome_light = stage.createNode("domelight::3.0", dome_light_name)

        # Set dome position
        dome_light.parmTuple("t").set(dome_position)

        # Adjust dome settings
        if hdr_file:
            dome_light.parm("xn__inputstexturefile_r3ah").set(hdr_file)

        # Support nodes
        xform_dome = stage.createNode("xform", xform_dome_name)

        # xform to control all lights
        xform_dome.parm("primpattern").set("%type:Light")

        # Format the light to add to allow multiple asset to be built in the same stage
        dome_string = f'"type": "LightItem", "path": "/lights/{dome_light.name()}", "prim_path": "/lights/{dome_light.name()}", "rgb": [55, 55, 55], "controls": ["buttons"], "contents": []'

        dome_to_add = (
            "{" + dome_string + "} "
        )

        xform_dome.setInput(0, dome_light)

        nodes_to_layout = [dome_light, xform_dome]

        return dome_to_add, nodes_to_layout, xform_dome

    # Trigger the creation of the light rigs depending on user choices
    if asset_name:
        merge_node_name = asset_name + "_light_setups_merge"
        light_mixer_name = asset_name + "_light_rig_mixer"
        graft_name = asset_name + "_light_rig"
    else:
        merge_node_name = "light_setups_merge"
        light_mixer_name = "light_rig_mixer"
        graft_name = "light_rig"

    if three_points_bool and dome_bool:

        lights_to_add, nodes_to_layout, xform_light = _create_three_points_setup(stage, asset_name)
        dome_to_add, dome_to_layout, xform_dome = _create_dome_setup(stage, asset_name)

        lights_to_add += ", " + dome_to_add
        lights_to_add = f"[{lights_to_add}]"

        merge_node = stage.createNode("merge", merge_node_name)
        merge_node.setInput(0, xform_light)
        merge_node.setInput(1, xform_dome)

        nodes_to_layout.extend(dome_to_layout)
        nodes_to_layout.append(merge_node)

        node_to_mixer = merge_node

    elif three_points_bool:
        lights_to_add, nodes_to_layout, xform_light = _create_three_points_setup(stage, asset_name)
        lights_to_add = f"[{lights_to_add}]"

        node_to_mixer = xform_light

    elif dome_bool:
        lights_to_add, nodes_to_layout, xform_dome = _create_dome_setup(stage, asset_name)
        lights_to_add = f"[{lights_to_add}]"
        node_to_mixer = xform_dome

    # Create the rest of the tree graph
    light_mixer = stage.createNode("lightmixer", light_mixer_name)
    ptg = light_mixer.parmTemplateGroup()

    settings_folder = hou.FolderParmTemplate(
        name = "settings_folder",
        label = "Settings",
        folder_type = hou.folderType.Simple
    )

    settings_layout = hou.StringParmTemplate(
        name = "setting_layout",
        label = "Layout",
        num_components = 1
    )

    # Add String parm to the folder
    settings_folder.addParmTemplate(settings_layout)
    ptg.append(settings_folder)

    # Set the parmTemplateGroup
    light_mixer.setParmTemplateGroup(ptg)

    # Set the light nodes string to layout parm in order to add the light to the mixer
    light_mixer.parm("setting_layout").set(lights_to_add)

    graft_branch = stage.createNode("graftbranches", graft_name)

    # Configure graft branch
    graft_branch.parm("srcprimpath1").set("/")

    light_mixer.setInput(0, node_to_mixer)
    graft_branch.setInput(1, light_mixer)
    graft_branch.setInput(0, target_node)

    # Add the latest created nodes to the layout pool
    nodes_to_layout.extend([light_mixer, graft_branch])

    graft_position = graft_branch.moveToGoodPosition()
    new_position_graft = hou.Vector2(graft_position[0]+7, graft_position[1])
    graft_branch.setPosition(new_position_graft)
    stage.layoutChildren(items = nodes_to_layout)

    # Set display and render flags
    graft_branch.setDisplayFlag(True)
    graft_branch.setSelected(True, True)

    mu.create_organized_net_note(nodes_to_layout)
