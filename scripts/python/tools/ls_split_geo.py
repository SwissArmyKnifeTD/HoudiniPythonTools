import hou

''' This function splits a geometry in multiple separate parts based on a specified attribute.
    The user is asked to choose between point and primitive attribute and have to specify the name of the attribute to use.
'''

def split_geo():
        
    # Fetch selected Node.
    selected_node = hou.selectedNodes()

    # Check if Selection is valid.
    if not selected_node:
        hou.ui.displayMessage("No selected nodes\nPlease select a node")
        raise ValueError("No selected nodes")

    if len(selected_node) > 1:
        hou.ui.displayMessage("Too much selected nodes\nPlease select only one node")
        raise ValueError("Too much selected nodes")
        
    selected_node = selected_node[0]

    if selected_node.type().category().name() != "Sop":
        hou.ui.displayMessage("Selected node is not a SOP\nPlease select a SOP node")
        raise ValueError("Selected node is not a SOP")
            
    # Set Working Context.
    parent_context = selected_node.parent()
    geo_info = selected_node.geometry()

    # Request user to choose between Points and Primitives attributes
    split_list = ["Points","Primitives"]
    split_type = hou.ui.selectFromList(split_list,
                                        default_choices=(),
                                        exclusive = True,
                                        message = "Choose what Attribute Type to use",
                                        title = "Choose Attribute Type",
                                        column_header = "Attribute Type",
                                        num_visible_rows = len(split_list),
                                        height = 1)

    # Check if choice is valid.
    if not split_type or len(split_type) > 1:
        hou.ui.displayMessage("Please select one Attribute Type")
        raise ValueError("Please select one Attribute Type")
    else:
        attribute_type = split_list[split_type[0]]

    # Request user for Attribute Name to use.
    button_pressed, attribute_name = hou.ui.readInput("Provide the Attribute name to split the Geometry parts.",
                                                        buttons = ("Ok","Cancel"),
                                                        title = "Attribute Name")

    # Check if Name is valid.
    if button_pressed == 1 or not attribute_name:
        hou.ui.displayMessage("No Attribute provided\nPlease Specify an Attribute")
        raise ValueError("No Attribute provided")

    # Find Attribute per Type
    if attribute_type == "Points":
        attribute_split = geo_info.findPointAttrib(attribute_name)
    else:
        attribute_split = geo_info.findPrimAttrib(attribute_name)
        
    # Check if Attribute is valid.
    if not attribute_split:
        hou.ui.displayMessage(f"Specified Attribute - {attribute_name} - in {attribute_type} Attributes doesn't exist")
        raise ValueError(f"Specified Attribute - {attribute_name} - in {attribute_type} Attributes doesn't exist")

    # Get Value from Attribute as a Set
    unique_values = set()

    if attribute_type == "Points":
        for point in geo_info.points():
            unique_values.add(point.attribValue(attribute_name))
    else:
        for prim in geo_info.prims():
            unique_values.add(prim.attribValue(attribute_name))
        
    # Create Main Nodes and Layout List
    merge_node = parent_context.createNode("merge", "Merge_all")
    layout_list = [selected_node]

    # Iterate over Elements
    for index, item in enumerate(unique_values):
        # Create Blast Non Selected Node
        blast_node = parent_context.createNode("blast",f"{attribute_name}_{item}_Blast")
        blast_node.parm("group").set(f"@{attribute_name}={item}")
        
        # Set Group Type per Attribute Type
        if attribute_type == "Points":
            blast_node.parm("grouptype").set(3)
        else:
            blast_node.parm("grouptype").set(4)  
        
        blast_node.parm("negate").set(True)
        blast_node.setInput(0,selected_node)
        
        # Create Null OUT Node
        null_node = parent_context.createNode("null",f"OUT_{item}")
        null_node.setInput(0,blast_node)
        
        # Connect Null Node to Merge Node
        merge_node.setInput(index,null_node)
        
        # Add the created Nodes to the Layout List
        layout_list.extend([blast_node,null_node])

    # Add the Merge to the Layout List and Layout Children
    layout_list.append(merge_node)
    parent_context.layoutChildren(items = layout_list)

    # Set display and render flags
    merge_node.setDisplayFlag(True)
    merge_node.setRenderFlag(True)