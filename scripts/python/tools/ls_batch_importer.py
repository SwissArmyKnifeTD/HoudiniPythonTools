import hou

''' Batch import of geometry files. 
    The user is requested to choose between multiple source unit to scale the object correctly at import. 
'''
    
def batch_import():
    # Declare Variables
    hip_file = hou.text.expandString("$HIP")
    imported_assets = hou.ui.selectFile(start_directory = hip_file,
                                        title = "Select files to import",
                                        file_type = hou.fileType.Geometry,
                                        multiple_select=True)

    # Check if Imported Assets are valid
    if not imported_assets:
        hou.ui.displayMessage("Please select a minimum of one file")
        raise ValueError("Please select a minimum of one file")

    # Split Assets based on separator
    imported_assets = imported_assets.split(";")

    # Fetch the Models Source Unit
    unit_dict = {"Custom":1.0,"Inches":0.0254,"Feet":0.3048,"Millimeters":0.001,"Centimeters":0.01,"Meters (No Change)":1.0}
    unit_list = list(unit_dict.keys())
    source_unit = hou.ui.selectFromList(unit_list,
                                        default_choices = (),
                                        exclusive = True,
                                        message = "Choose the assets source unit",
                                        title = "Assets Source Unit",
                                        column_header = "Source Unit",
                                        num_visible_rows = len(unit_dict))

    # Check if Source Unit is valid
    if not source_unit or len(source_unit) > 1:
        hou.ui.displayMessage("Please select one Source Unit")
        raise ValueError("Please select one Source Unit")

    # Convert tuple to dictionary Key
    user_unit = unit_list[source_unit[0]]

    # Fetch Custom Scale Value
    if user_unit == "Custom":
        button_pressed, custom_scale = hou.ui.readInput("Set Custom Scale",
                                                            buttons = ("Ok", "Cancel"),
                                                            title = "Custom Scale")

        # Check if Custom Scale is valid
        if button_pressed == 1 or not custom_scale:
            hou.ui.displayMessage("No Custom Scale provided\nPlease Specify a Custom Scale")
            raise ValueError("No Custom Scale provided")
        
        # Set the new Custom Scale in the Unit Dictionary    
        unit_dict["Custom"] = custom_scale

    # Create Main Nodes
    obj = hou.node("/obj")
    geo_node = obj.createNode("geo",node_name = "Batch_Import")
    merge_node = geo_node.createNode("merge",node_name = "Merge_All")

    # Iterate over Imported Assets
    for index, item in enumerate(imported_assets):
        # String Management
        item = item.strip()
        asset = item.split("/")
        file = asset[-1].split(".")
        file_name = file[0]
        file_ext = file[-1]
        
        # Alembic Importer
        if file_ext == "abc" :
            alembic_node = geo_node.createNode("alembic",node_name = file_name)
            alembic_node.parm("fileName").set(item)
            
            unpack_node = geo_node.createNode("unpack",node_name = file_name + "_Unpack")
            unpack_node.setInput(0,alembic_node)
            
            import_node = unpack_node
        # File Importer     
        else :
            file_node = geo_node.createNode("file",node_name = file_name)
            file_node.parm("file").set(item)
            
            import_node = file_node
        
        # Transform Node
        transform_node = geo_node.createNode("xform",node_name = file_name + "_XForm")
        transform_node.parm("scale").set(unit_dict[user_unit])
        transform_node.setInput(0,import_node)
        
        # Material Node
        material_node = geo_node.createNode("material",node_name = file_name + "_Material")
        material_node.setInput(0,transform_node)
        
        # Connect Material Node to Merge Node
        merge_node.setInput(index,material_node)

    # Layout Children
    geo_node.layoutChildren()