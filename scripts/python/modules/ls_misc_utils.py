import hou
import loputils
import random
import colorsys

def _is_in_solaris():
    """
    Check if the current network is Solaris
    """

    # Get the current network editor pane
    network_editor = hou.ui.curDesktop().paneTabOfType(hou.paneTabType.NetworkEditor)

    if network_editor.pwd().childTypeCategory().name() == "Lop":
        return True

    return False

def  calculate_prim_bounds(target_node):
    """
    Calculate the bounding box for a prim in Solaris
    Args:
        target_node = the LOP node
    Return:
        dict = Contains the bounding box information - min, max, center and size
    """

    # Get the USD stage
    stage = target_node.stage()

    if not stage:
        print("No USD stage found")
        return None
    
    # Get the target prim
    prim = stage.GetDefaultPrim()

    if not prim or not prim.IsValid():
        print(f"Invalid prim : {prim}")
        return None
    
    # Calculate the bounding box
    bounds = loputils.computePrimWorldBounds(target_node, [prim])

    # Extract the bounding box information
    range_3d = bounds.GetRange()
    min_point = hou.Vector3(range_3d.GetMin())
    max_point = hou.Vector3(range_3d.GetMax())

    center = (min_point + max_point) * 0.5
    size = max_point - min_point

    return {
        "min" : min_point,
        "max" : max_point,
        "center" : center,
        "size" : size,
        "bbox" : bounds
    }

def _random_color():
    """
    Generate random RGB values betweeen 0 and 1
    """

    red_color = random.random()
    green_color = random.random()
    blue_color = random.random()

    # Get the main color
    main_color = hou.Color(red_color, green_color, blue_color)

    # Convert RGB to HSV
    hue, saturation, value = colorsys.rgb_to_hsv(red_color, green_color, blue_color)
    new_saturation = saturation * 0.5

    # Get the secondary color
    sec_red, sec_green, sec_blue = colorsys.hsv_to_rgb(hue, new_saturation, value)
    secondary_color = hou.Color(sec_red, sec_green, sec_blue)

    return main_color, secondary_color

def create_organized_net_note(nodes_to_layout):
    """
    Creates a network box organization around selected nodes with a titled sticky note
    Args:
        asset_name = Text to display in the sticky note
        nodes_to_layout = list of nodes to be integrated in the box
    Return:
        None
    """

    # Get the parent context
    parent = nodes_to_layout[0].parent()

    out_node = nodes_to_layout[-1]

    # Get colors for the network box and the sticky note
    background_color = 0.14
    parent_color = hou.Color(background_color, background_color, background_color)

    child_color, sticky_note_color = _random_color()
    text = 0.0
    sticky_note_text = hou.Color(text, text, text)

    # Create the network boxes
    parent_box = parent.createNetworkBox()
    child_box = parent.createNetworkBox()

    # Calculate the node position
    positions = [node.position() for node in nodes_to_layout]
    center_x = sum(pos.x() for pos in positions) / len(positions)
    center_y = sum(pos.y() for pos in positions) / len(positions)
    center = hou.Vector2(center_x, center_y)

    # Position the boxes
    parent_box.setPosition(center)
    child_box.setPosition(center)

    parent_box.addItem(child_box)

    for node in nodes_to_layout:
        child_box.addItem(node)

    child_box.fitAroundContents()

    # Create the sticky node
    sticky_note = parent.createStickyNote()
    parent_box.addItem(sticky_note)

    # Get the dimensions for the sticky note based on the child box
    sticky_note_width = 0.2 * len(out_node.name())
    sticky_note_height = 0.75

    sticky_note.setSize(hou.Vector2(sticky_note_width, sticky_note_height))

    parent_box.fitAroundContents()  

    child_box_top = parent_box.position().y() + (child_box.size().y())
    sticky_note_x =  child_box.position().x()
    sticky_note_y = child_box_top + sticky_note_height

    sticky_note.setPosition(hou.Vector2(sticky_note_x, sticky_note_y))

    # Configure the sticky note color and text
    box_text = out_node.name().upper().replace("_", " ")

    sticky_note.setText(box_text)
    sticky_note.setTextSize(0.35)
    sticky_note.setTextColor(sticky_note_text)
    sticky_note.setColor(sticky_note_color)

    # Configure the network box color
    parent_box.setComment(box_text.capitalize())
    parent_box.setColor(parent_color)
    child_box.setColor(child_color)

    # Fit parent box around everything
    parent_box.fitAroundContents()  