import hou
import voptoolutils

from modules import ls_misc_utils
from modules import ls_misc_utils as mu

def create_lookdev_camera_node(asset_name = None, spheres = True, checker = True):
    """
    Create a Python node with predefined script to create a look dev camera rig
    """

    # Get the selected node and check if it is in Solaris context
    selected_node= hou.selectedNodes()
    is_solaris = ls_misc_utils._is_in_solaris()

    if not selected_node or not is_solaris:
        hou.ui.displayMessage("No valid node selected, please select a node in Solaris context", 
                              severity = hou.severityType.Error
        )
        return False
    
    target_node = selected_node[0]
    stage = target_node.parent()

    if asset_name:
        python_name = asset_name + "_lookdev_camera"
        graft_name = asset_name + "_camera_rig"
    else:
        python_name = "lookdev_camera"
        graft_name = "camera_rig"

    python_node = stage.createNode("pythonscript", python_name)
    
    code = """
from tools import ls_lops_lookdev_camera
import importlib

importlib.reload(ls_lops_lookdev_camera)
ls_lops_lookdev_camera.create_lookdev_camera_script()
"""

    python_node.parm("python").set(code)
    python_node.setInput(0, target_node)

    nodes_to_layout = [python_node]

    if spheres or checker:
        env_node, mat_linker = create_env_meshes(stage, spheres, checker, asset_name)

        mat_linker.setInput(0, env_node)

        graft_branch = stage.createNode("graftbranches", graft_name)
        graft_branch.parm("srcprimpath1").set("/")
        graft_branch.parm("dstprimpath1").set("/cam/ThumbnailCamera/lookdev")

    
        graft_branch.setInput(0, python_node)
        graft_branch.setInput(1, mat_linker)

        graft_position = target_node.position()
        new_position_graft = hou.Vector2(graft_position[0], graft_position[1]-5)
        graft_branch.setPosition(new_position_graft)

        node_to_extend = [env_node,mat_linker, graft_branch]

        nodes_to_layout.extend(node_to_extend)
    else:
        python_position = target_node.position()
        new_position_python = hou.Vector2(python_position[0]-1, python_position[1]-3)
        python_node.setPosition(new_position_python)
    
    stage.layoutChildren(items = nodes_to_layout)

    target_node.setSelected(True, True)
    target_node.setDisplayFlag(True)
    target_node.setDisplayFlag(True)

    if spheres or checker:
        graft_branch.setSelected(True, True)
        graft_branch.setDisplayFlag(True)
        graft_branch.setDisplayFlag(True)
    else:
        python_node.setSelected(True, True)
        python_node.setDisplayFlag(True)
        python_node.setDisplayFlag(True)

    mu.create_organized_net_note(nodes_to_layout)
            
def create_env_meshes(stage, spheres, checker, asset_name):
    """
    Create environment spheres besides the asset
    """

    if asset_name:
        sop_node_name = asset_name + "_lookdev_meshes"
        material_library_name = asset_name + "_material_library"
    else:
        sop_node_name = "lookdev_meshes"
        material_library_name = "material_library"

    sop_node = stage.createNode("sopcreate", sop_node_name)
    sop_node_context = hou.node(sop_node.path()+"/sopnet/create")

    material_library = stage.createNode("materiallibrary", material_library_name)

    nodes_to_layout = []

    def _create_spheres():
    
        # Spheres settings
        mirror_sphere_position = hou.Vector3(-0.1175, -0.12, -1)
        matte_sphere_position = hou.Vector3(-0.0722, -0.12, -1)
        sphere_scale = 0.02

        # Mirror sphere node
        mirror_sphere = sop_node_context.createNode("sphere", "mirror_sphere")
        mirror_sphere.parm("type").set(1)
        mirror_sphere.parm("scale").set(sphere_scale)
        mirror_sphere.parm("freq").set(10)
        mirror_sphere.parmTuple("t").set(mirror_sphere_position)

        # Mirror sphere name
        mirror_name = sop_node_context.createNode("name", "mirror_sphere_name")
        mirror_name.parm("name1").set("mirror_sphere")     

        # Matte sphere node
        matte_sphere = sop_node_context.createNode("sphere", "matte_sphere")
        matte_sphere.parm("type").set(1)
        matte_sphere.parm("scale").set(sphere_scale)
        matte_sphere.parm("freq").set(10)
        matte_sphere.parmTuple("t").set(matte_sphere_position)

        # Matte sphere name
        matte_name = sop_node_context.createNode("name", "matte_sphere_name")
        matte_name.parm("name1").set("matte_sphere")

        # Connecting the nodes
        mirror_name.setInput(0,mirror_sphere)
        matte_name.setInput(0,matte_sphere)

        nodes_to_extend = [mirror_sphere, mirror_name, matte_sphere, matte_name]

        nodes_to_layout.extend(nodes_to_extend)

        # Create the materials
        material_to_create = [mirror_sphere, matte_sphere]

        for sphere in material_to_create:
            material_mtlx_builder =  voptoolutils._setupMtlXBuilderSubnet(
                        subnet_node=None, 
                        destination_node = material_library, 
                        name = sphere.name(), 
                        mask = voptoolutils.MTLX_TAB_MASK,
                        folder_label = 'MaterialX Builder', 
                        render_context='mtlx')
            
            material_surface = hou.node(material_mtlx_builder.path() + "/mtlxstandard_surface")

            if "mirror" in sphere.name():
                material_surface.parmTuple("base_color").set((0.7, 0.7, 0.7))
                material_surface.parm("metalness").set(1.0)
                material_surface.parmTuple("specular_color").set((0.7, 0.7, 0.7))
                material_surface.parm("specular_roughness").set(0.06)
            else:
                material_surface.parmTuple("base_color").set((0.18, 0.18, 0.18))
                material_surface.parmTuple("specular_color").set((0.35, 0.35, 0.35))
                material_surface.parm("specular_roughness").set(0.5)
    
        material_library.layoutChildren()

        return mirror_name, matte_name
    
    def _create_color_checker():

        # Color checker grid settings
        color_checker_position = hou.Vector3(0.105, -0.116, -1)
        color_checker_scale_x = 0.0715
        color_checker_scale_y = 0.05

        # Color checker node
        color_checker = sop_node_context.createNode("grid", "color_checker")
        color_checker.parm("orient").set(0)
        color_checker.parmTuple("size").set(hou.Vector2(color_checker_scale_x, color_checker_scale_y))
        color_checker.parm("ry").set(180.0)
        color_checker.parm("rows").set(2)
        color_checker.parm("cols").set(2)
        color_checker.parmTuple("t").set(color_checker_position)

        # Color checker name
        checker_name = sop_node_context.createNode("name", "color_checker_name")
        checker_name.parm("name1").set("color_checker")

        # Connecting the nodes
        checker_name.setInput(0,color_checker)
        nodes_to_extend = [color_checker, checker_name]

        nodes_to_layout.extend(nodes_to_extend)

        # Create the materials
        material_mtlx_builder =  voptoolutils._setupMtlXBuilderSubnet(
                    subnet_node=None, 
                    destination_node = material_library, 
                    name = color_checker.name(), 
                    mask = voptoolutils.MTLX_TAB_MASK,
                    folder_label = 'MaterialX Builder', 
                    render_context='mtlx')
            
        material_surface = hou.node(material_mtlx_builder.path() + "/mtlxstandard_surface")
        checker_texture = hou.expandString("$LSTools/toolbar/textures/color_checker.png")
        texture_node = material_mtlx_builder.createNode("mtlximage", "color_checker_texture")
        texture_node.parm("file").set(checker_texture)

        material_surface.setInput(1, texture_node)

        material_surface.parmTuple("base_color").set((0.7, 0.7, 0.7))
        material_surface.parmTuple("specular_color").set((0.35, 0.35, 0.35))
        material_surface.parm("specular_roughness").set(0.5)

        material_mtlx_builder.layoutChildren()
    
        material_library.layoutChildren()

        return checker_name
    
    if spheres and checker :
        mirror_name, matte_name = _create_spheres()
        checker_name = _create_color_checker()

        material_library.parm("materials").set(3)
        material_library.parm("matnode1").set("mirror_sphere")
        material_library.parm("matpath1").set("mirror_sphere")
        material_library.parm("assign1").set(True)
        material_library.parm("geopath1").set(sop_node.name() + "/mirror_sphere")

        material_library.parm("matnode2").set("matte_sphere")
        material_library.parm("matpath2").set("matte_sphere")
        material_library.parm("assign2").set(True)
        material_library.parm("geopath2").set(sop_node.name() + "/matte_sphere")

        material_library.parm("matnode3").set("color_checker")
        material_library.parm("matpath3").set("color_checker")
        material_library.parm("assign3").set(True)
        material_library.parm("geopath3").set(sop_node.name() + "/color_checker")

        merge_node = sop_node_context.createNode("merge", "env_merge")

        merge_node.setInput(0, mirror_name)
        merge_node.setInput(1, matte_name)
        merge_node.setInput(2, checker_name)

        nodes_to_layout.append(merge_node)

        node_to_connect = merge_node

    elif spheres:
        mirror_name, matte_name = _create_spheres()

        material_library.parm("materials").set(2)
        material_library.parm("matnode1").set("mirror_sphere")
        material_library.parm("matpath1").set("mirror_sphere")
        material_library.parm("assign1").set(True)
        material_library.parm("geopath1").set(sop_node.name() + "/mirror_sphere")

        material_library.parm("matnode2").set("matte_sphere")
        material_library.parm("matpath2").set("matte_sphere")
        material_library.parm("assign2").set(True)
        material_library.parm("geopath2").set(sop_node.name() + "/matte_sphere")

        merge_node = sop_node_context.createNode("merge", "env_merge")
        merge_node.setInput(0, mirror_name)
        merge_node.setInput(1, matte_name)

        nodes_to_layout.append(merge_node)

        node_to_connect = merge_node

    elif checker:
        checker_name = _create_color_checker()

        material_library.parm("materials").set(1)

        material_library.parm("matnode1").set("color_checker")
        material_library.parm("matpath1").set("color_checker")
        material_library.parm("assign1").set(True)
        material_library.parm("geopath1").set(sop_node.name() + "/color_checker")


        node_to_connect = checker_name

    xform_node = sop_node_context.createNode("xform", "env_xform")
    output_node = sop_node_context.createNode("output", "env_out")    
    
    xform_node.setInput(0, node_to_connect)
    output_node.setInput(0, xform_node)

    nodes_to_extend = [xform_node, output_node]

    nodes_to_layout.extend(nodes_to_extend)

    sop_node_context.layoutChildren(items = nodes_to_layout)

    return sop_node, material_library
