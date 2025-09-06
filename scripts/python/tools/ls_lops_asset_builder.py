import hou
import os
import voptoolutils

from pxr import UsdGeom
from tools import ls_tex_to_mtlx
from modules import ls_misc_utils as mu

def create_component_builder(selected_directory = None):
    """
    Main function to create the component builder based on a provided asset
    """

    # Get the file
    if selected_directory == None :
        selected_directory = hou.ui.selectFile(title = "Select the file to import",
                                            file_type = hou.fileType.Geometry,
                                            multiple_select = False
                                            )
        
    selected_directory = hou.text.expandString(selected_directory)

    try:
        if os.path.exists(selected_directory):

            # Define the context
            stage_context = hou.node("/stage")

            # Get the file, filename and folder with the textures
            path, filename = os.path.split(selected_directory)
            folder_texture = os.path.join(path, "maps/").replace(os.sep, "/")

            # get the asset name and the extension
            asset_name =  filename.split(".")[0]
            asset_extension = filename.split(".")[-1]

            # Create nodes for the component builder setup
            comp_geo = stage_context.createNode("componentgeometry", f"{asset_name}_geo")
            material_library = stage_context.createNode("materiallibrary", f"{asset_name}_mtl")
            comp_material = stage_context.createNode("componentmaterial", f"{asset_name}_assign")
            comp_out = stage_context.createNode("componentoutput", f"{asset_name}_asset")

            # Set parms
            comp_geo.parm("geovariantname").set(asset_name)
            material_library.parm("matpathprefix").set("/ASSET/mtl/")
            comp_material.parm("nummaterials").set(0)

            # Create auto assignment for materials
            comp_material_edit = comp_material.node("edit")
            output_node = comp_material_edit.node("output0")

            assign_material = comp_material_edit.createNode("assignmaterial", f"{asset_name}_assign")

            assign_material.setParms({
                "primpattern1" : "%type:Mesh",
                "matspecmethod1" : 2,
                "matspecvexpr1" : '"/ASSET/mtl/"+@primname;',
                "bindpurpose1" : "full"
            })

            # Connect nodes
            comp_material.setInput(0, comp_geo)
            comp_material.setInput(1, material_library)
            comp_out.setInput(0, comp_material)

            # Connect the input of assign node to the first subnet indirect input
            assign_material.setInput(0, comp_material_edit.indirectInputs()[0])
            output_node.setInput(0, assign_material)

            # Nodes to layout
            nodes_to_layout = [comp_geo, material_library, comp_material, comp_out]
            stage_context.layoutChildren(items = nodes_to_layout)

            # Prepare imported geo
            _prepare_imported_asset(comp_geo, asset_name, asset_extension, path, comp_out)

            # Create materials with the tex_to_mtlx script
            material_amount = _create_materials(folder_texture, material_library, comp_geo)

            # Add network boxes to organize nodes
            mu.create_organized_net_note(nodes_to_layout)

            # Set display and render flags
            comp_out.setDisplayFlag(True)
            comp_out.setSelected(True, True)

            if material_amount[1] >0:
                hou.ui.displayMessage(f"Created {material_amount[1]} materials in {material_library.path()}", 
                                      severity = hou.severityType.Message)

    except Exception as e:
        hou.ui.displayMessage(f"An error happened creating component builder : {str(e)}", 
                              severity = hou.severityType.Error)

def _prepare_imported_asset(parent, name, extension, path, out_node):
    """
    Creates the network layout for the default, proxy and sim outputs
    Args:
        parent = node where the file needs to be imported and prepared
        name = asset's name
        extension = file extension to work with
        path = path where the asset is located
    Return:
        None
    """

    try:
        # Get the three outputs nodes present in the component geo
        default_output = parent.node("sopnet/geo/default")
        proxy_output = parent.node("sopnet/geo/proxy")
        sim_output = parent.node("sopnet/geo/simproxy")

        # Set the parent node where the nodes are going to be created
        parent = hou.node(parent.path()+"/sopnet/geo")

        # Create the node to import file based on its extension
        file_extensions = ["fbx", "obj", "bgeo", "bgeo.sc"]
        if extension in file_extensions:
            file_import = parent.createNode("file", f"import_{name}")  
            parm_name = "file"
        elif extension == "abc" :
            file_import = parent.createNode("alembic", f"import_{name}")  
            parm_name = "filename"
        else:
            return
        
        # Create the main nodes
        match_size = parent.createNode("matchsize", f"matchsize_{name}")
        attrib_wrangle = parent.createNode("attribwrangle", f"convert_mat_to_name")
        attrib_delete = parent.createNode("attribdelete", f"keep_P_N_UV_NAME")
        remove_points = parent.createNode("add", f"remove_unused_points")

        # Set parms for main nodes
        file_import.parm(parm_name).set(f"{path}/{name}.{extension}")

        match_size.setParms({
            "justify_x" : 0,
            "justify_y" : 1,
            "justify_z" : 0
        })

        attrib_wrangle.setParms({
            "class" : 1,
            "snippet" : 'string material_to_name[] = split(s@shop_materialpath, "/");\ns@name = material_to_name[-1];'
        })

        attrib_delete.setParms({
            "negate" : True,
            "ptdel" : "N P",
            "vtxdel" : "uv",
            "primdel" : "name"
        })

        remove_points.parm("remove").set(True)

        # Connect main nodes
        match_size.setInput(0, file_import)
        attrib_wrangle.setInput(0, match_size)
        attrib_delete.setInput(0, attrib_wrangle)
        remove_points.setInput(0, attrib_delete)
        default_output.setInput(0, remove_points)

        # Prepare Proxy branch
        poly_reduce = parent.createNode("polyreduce::2.0", "reduce_mesh_density")
        attrib_color = parent.createNode("attribwrangle", "set_color")
        color_node = parent.createNode("color", "unique_color")
        attrib_promote = parent.createNode("attribpromote", "promote_Cd")
        attrib_delete_name = parent.createNode("attribdelete", f"delete_asset_name")

        # Set parms for proxy setup
        poly_reduce.parm("percentage").set(5)

        # Custom attribute node using the ParmTemplateGroup() for the attrib_color
        attrib_color.parm("class").set(1)

        ptg = attrib_color.parmTemplateGroup()

        new_string = hou.StringParmTemplate(
            name = "asset_name",
            label = "Asset Name",
            num_components = 1
        )

        ptg.insertAfter("class", new_string)

        attrib_color.setParmTemplateGroup(ptg)

        # Need to grab the rootprim from the component output and paste a reference
        relative_path = attrib_color.relativePathTo(out_node)
        expression_parm = f'`chs("{relative_path}/rootprim")`'

        attrib_color.setParms({
            "asset_name" : expression_parm,
            "snippet" : 's@asset_name = chs("asset_name");'
        })

        color_node.setParms({
            "class" : 1,
            "colortype" : 4,
            "rampattribute" : "asset_name"
        })

        attrib_promote.setParms({
            "inname" : "Cd",
            "inclass" : 1,
            "outclass" : 0
        })

        attrib_delete_name.parm("primdel").set("asset_name")

        # Connect nodes
        poly_reduce.setInput(0, remove_points)
        attrib_color.setInput(0, poly_reduce)
        color_node.setInput(0, attrib_color)
        attrib_promote.setInput(0, color_node)
        attrib_delete_name.setInput(0, attrib_promote)
        proxy_output.setInput(0, attrib_delete_name)

        # Prepare the scene setup
        python_sop = _create_convex(parent)

        # Create name node for the proxy
        name_node = parent.createNode("name", "proxy_name")

        # Get the relative path from the component output and paste a reference
        relative_path = name_node.relativePathTo(out_node)
        expression_parm = f'`chs("{relative_path}/rootprim")`'

        name_node.parm("name1").set(expression_parm)

        # Connect the nodes
        python_sop.setInput(0, remove_points)
        name_node.setInput(0, python_sop)
        sim_output.setInput(0, name_node)

        # Layout all nodes
        parent.layoutChildren()

    except Exception as e:
        hou.ui.displayMessage(f"An error happened preparing the asset : {str(e)}", severity = hou.severityType.Error)

def _create_convex(parent):
    """
    Create the python sop node that is used to create a convex hull using scipy
    Args:
        parent = the component geometry node where the file is imported
    Return:
        python_sop = python node to create convex hull
    """

    # Create the python node
    python_sop = parent.createNode("python", "convex_hull_setup")

    # Create the extra parms
    ptg = python_sop.parmTemplateGroup()

    # Normalize toggle
    normalize_toggle = hou.ToggleParmTemplate(
        name = "normalize",
        label = "Normalize",
        default_value = True
    )

    # Flip normals toggle
    flip_toggle = hou.ToggleParmTemplate(
        name = "flip_normals",
        label = "Flip Normals",
        default_value = True
    )
    # Simplify toggle
    simplify_toggle = hou.ToggleParmTemplate(
        name = "simplify",
        label = "Simplify",
        default_value = True
    )
    #  Level of details slider
    level_details = hou.FloatParmTemplate(
        name = "level_details",
        label = "Level of Details",
        num_components = 1,
        disable_when = "{simplify == 0}"
    )

    # Append to node
    ptg.append(normalize_toggle)
    ptg.append(flip_toggle)
    ptg.append(simplify_toggle)
    ptg.append(level_details)

    python_sop.setParmTemplateGroup(ptg)

    code = """
from modules import ls_convex_hull_utils

node = hou.pwd()
geo = node.geometry()

# Get user parms
normalize_parm = node.parm("normalize").eval()
flip_normals_parm = node.parm("flip_normals").eval()
simplify_parm = node.parm("simplify").eval()
level_details = node.parm("level_details").eval()

# Get the points
points = [point.position() for point in geo.points()]

ls_convex_hull_utils.create_convex_hull(geo, points)
"""

    python_sop.parm("python").set(code)

    return python_sop

def _create_materials(folder_texture, material_library, comp_geo):
    """
    Create the asset materials using the tex_to_mtls script
    Args:
        folder_texture = the folder taht contains the textures for the asset
        material_library = the material library node whe the materials will be created
    Return:
        None
    """

    try:
        if not os.path.exists(folder_texture):
            # hou.ui.displayMessage(f"Folder doesn't exist : {folder_texture}", severity = hou.severityType.Error)

            material_amount = _create_placeholder_materials(material_library, comp_geo)

            return True, material_amount
            

        # Initialize the texture handle TxToMtlx
        material_handler = ls_tex_to_mtlx.TxToMtlx()

        # Check if the folder contains valid textures
        if material_handler.folder_with_texture(folder_texture):

            # Get the textures details
            texture_list = material_handler.get_texture_details(folder_texture)

            if texture_list and isinstance(texture_list, dict):
                common_data = {
                    "mtlTX" : False, # Set to True to create TX files
                    "path" : material_library.path(),
                    "node" : material_library,
                    "folder_path" : folder_texture
                }
                    
                # Create the materials for each texture set
                for material_name in texture_list:

                    create_material = ls_tex_to_mtlx.MtlxMaterial(
                        material_name,
                        **common_data,
                        texture_list = texture_list
                    )

                    create_material.create_materialx()
                    material_amount = len(texture_list)

                return True, material_amount

            else:
                hou.ui.displayMessage("No valid texture set found 1", severity = hou.severityType.Error)
                return False, 0
                    
        else:
            hou.ui.displayMessage("No valid texture set found 2", severity = hou.severityType.Error)
            # return False, 0
                    
    except Exception as e:
        hou.ui.displayMessage(f"Error creating the materials: {str(e)}", severity = hou.severityType.Error)
        return False, 0
    
def _create_placeholder_materials(material_library, comp_geo):
    """
    Creates placeholder materials in case no textures related to the asset are found
    """

    stage = comp_geo.stage()
    names = []

    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            path = prim.GetPath().pathString.split("/")
            if "render" in path:
                names.append(path[-1])

    for name in names:
        material_mtlx_builder =  voptoolutils._setupMtlXBuilderSubnet(
                    subnet_node=None, 
                    destination_node = material_library, 
                    name = name, 
                    mask = voptoolutils.MTLX_TAB_MASK,
                    folder_label = 'MaterialX Builder', 
                    render_context='mtlx')
    
    material_amount = len(names)
    material_library.layoutChildren()

    return material_amount
