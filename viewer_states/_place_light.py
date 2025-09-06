"""
State:          Place Light Highlight
State type:     place_light_highlight
Description:    Place Light Highlight
Author:         Lau
Date Created:   July 09, 2025 - 10:19:57
"""


import hou
import viewerstate.utils as su

HUD_TEMPLATE = {
        "title": f"Place Light Highlight", "desc": "tool", "icon": "LOP_light",
        "rows": [
            {"id": "sep_place", "type": "divider"},
            {"id": "place", "label": "Place Specular Highlight", "key": "LMB"},
            {"id": "distance", "label": "Light Distance", "key": "mousewheel", "value" : "0.0"},

            {"id": "sep_dimension", "type": "divider"},
            {"id": "dimension_x", "label": "Light Width - Mouse X", "key": "Ctrl LMB", "value" : "0.0"},
            {"id": "dimension_y", "label": "Light Height - Mouse Y", "key": "Ctrl LMB", "value" : "0.0"},
            {"id": "dimension_u", "label": "Uniform Light Dimensions", "key": "Ctrl Shift LMB"},

            {"id": "sep_intensity", "type": "divider"},
            {"id": "intensity", "label": "Light Intensity", "key": "Shift mousewheel", "value" : "0.0"},
            {"id": "exposure", "label": "Light Exposure", "key": "Ctrl mousewheel", "value" : "0.0"},

            {"id": "sep_enable", "type": "divider"},
            {"id": "enabler", "label": "Enable/Disable", "key": "H"},
        ]
    }

class State(object):
    def __init__(self, state_name, scene_viewer):
        self.state_name = state_name
        self.scene_viewer = scene_viewer
        self.obj = hou.node("/obj")

        # Settings for the light
        self.light = None
        self.light_distance = 1

        # Initialize transform for the light and guide geometry
        self.world_position = None
        self.reflection_ray = None
        self.light_new_position = None
        self.set_light_position = False

        # Create the rail guide geometry
        self._rail_guide = hou.GeometryDrawable(
            self.scene_viewer,
            hou.drawableGeometryType.Line,
            "rail_geometry"
        )

        self._rail_guide.show(False)

        self.mousex = 0
        self.mousey = 0
        self.light_width = 0
        self.light_height = 0
        self.is_placed = False
        self.light_type = None
        self.light_intensity = 0

        self.color_swatch_button = hou.qt.ColorSwatchButton()
        self.color_swatch_button.colorChanged.connect(self.on_color_changed)

    def _update_rail_geometry(self):
        """
        Update the rail guide geometry to show the reflection ray
        """

        # Safety cehck to see if we have both hit point and light to process
        if not self.world_position or not self.light:
            return
        
        # Get the current light posiiton in World Space
        light_position = hou.Vector3(self.light.worldTransform().extractTranslates())

        # Create the new geometry for the line
        line_geo = hou.Geometry()

        # Create two points - hit position and light position
        line_points = []
        line_points.append(line_geo.createPoints([self.world_position, light_position]))

        # Create the polygon co nnecting the two points
        line_geo.createPolygons(line_points, False)

        # Add the color arttribute to the line geometry
        color_attribute = line_geo.addAttrib(hou.attribType.Prim, "Cd", (1.0, 1.0, 1.0))
        alpha_attribute = line_geo.addAttrib(hou.attribType.Prim, "Alpha", 1.0)

        color = hou.Color(1.0, 0.5, 0.0)

        for prim in line_geo.prims():
            prim.setAttribValue(color_attribute, color.rgb())
            prim.setAttribValue(alpha_attribute, 0.5)

        # Update the drawable geometry
        self._rail_guide.setGeometry(line_geo)

    def onEnter(self,kwargs):
        """ Called on node bound states when it starts
        """
        state_parms = kwargs["state_parms"]

    def onExit(self,kwargs):
        """ Called when the state terminates
        """
        state_parms = kwargs["state_parms"]
        try:
            self.scene_viewer.endStateUndo()
        except:
            pass
        self._rail_guide.show(False)

    def onInterrupt(self, kwargs):
        """ Called when the state is interrupted e.g when the mouse 
        moves outside the viewport
        """
        pass

    def onResume(self, kwargs):
        """ Called when an interrupted state resumes
        """
        self._rail_guide.show(True)

    def _calculate_highlight_position(self, current_viewport, mouse_x, mouse_y):
        """
        Calculate the light position based on the surface highlight point.
        Args:
            current_viewport = current viewport
        """

        # Query the node at node position
        object_to_light = current_viewport.queryNodeAtPixel(int(mouse_x),int(mouse_y), hou.nodeTypeFilter.ObjGeometry)
        
        light_nodes = ["hlight::2.0"]

        if not object_to_light or object_to_light.type().name() in light_nodes:
            return False
                
        # Get the geometry information
        geometry_node = object_to_light.displayNode().geometry()
        geometry_transform = object_to_light.worldTransform() # Returns the Matrix4

        # Get ray information from current viewport
        direction, origin_point = current_viewport.mapToWorld(int(mouse_x),int(mouse_y))

        # Transform the World Space to Local Space to use the sopGeometryIntersection from the utils module

        local_origin = origin_point * geometry_transform.inverted()
        local_direction = direction.multiplyAsDir(geometry_transform.inverted())

        _, hit_position, _hit_normal, _ = su.sopGeometryIntersection(geometry_node, local_origin, local_direction)

        # Transform the hit_position and hit_normal back to World Space
        self.world_position = hit_position * geometry_transform
        world_normal = _hit_normal.multiplyAsDir(geometry_transform)

        # Calculate the angle of incidence using the formula cos(0i) = I.N
        incident_ray = direction.normalized()
        surface_normal = world_normal.normalized()

        # The formula for the angle of incidence to get the required angle for reflection ray
        cos_angle_incidence =  incident_ray.dot(surface_normal)

        # To calculate the  reflection ray - R = I-2(I.N)N where :
        # R is the reflection ray required for the light transform,
        # I is the Direction,
        # N is the surface Normal

        self.reflection_ray = incident_ray - 2 * cos_angle_incidence * surface_normal

        # Calculate the new light  position
        self.light_new_position = self.world_position + (self.reflection_ray * self.light_distance)     
        
        return True

    def onMouseEvent(self, kwargs):
        """ Process mouse and tablet events
        """
        ui_event = kwargs["ui_event"]
        dev = ui_event.device()
        reason = ui_event.reason()
        mouse = [dev.mouseX(), dev.mouseY()]



        self.scene_viewer.setPromptMessage(f"Click with LMB or hold LMB to place {self.light}")

        if not self.light:
            self.scene_viewer.setPromptMessage("Please select a light first")
            return False
        
        if reason == hou.uiEventReason.Start:
            self.mousex = mouse[0]
            self.mousey = mouse[1]
            self.light_width = self.light.parm("areasize1").eval()
            self.light_height = self.light.parm("areasize2").eval()
            self.light_type = self.light.parm("light_type").eval()

        if reason == hou.uiEventReason.Picked or reason == hou.uiEventReason.Active:
            # Get the current viewport
            current_viewport = self.scene_viewer.curViewport()



            if dev.isCtrlKey():

                mouseX_value = (self.mousex - mouse[0])/1000
                mouseY_value = (self.mousey - mouse[1])/1000

                width_value = max(0.01, self.light_width - mouseX_value)
                height_value = max(0.01, self.light_height - mouseY_value)

                if dev.isShiftKey():
                    if self.light_type == 2 or self.light_type == 3:
                        self.light.parm("areasize1").set(width_value)
                        self.light.parm("areasize2").set(width_value)

                else :
                    if self.light_type == 2 or self.light_type == 3:
                        self.light.parm("areasize1").set(width_value)
                        self.light.parm("areasize2").set(height_value)

                updates = {
                    "dimension_x" : f"{self.light.parm('areasize1').eval():0.2f}",
                    "dimension_y" : f"{self.light.parm('areasize2').eval():0.2f}",
                }  

                self.scene_viewer.hudInfo(values = updates)

            else:
                success = self._calculate_highlight_position(current_viewport, dev.mouseX(), dev.mouseY())
                if not success:
                    #self.is_placed = False
                    return False
                
                self.is_placed = True
                
                # Update the light transform
                light_matrix = hou.hmath.buildRotateZToAxis(self.reflection_ray)
                light_matrix *= hou.hmath.buildTranslate(self.light_new_position)

                self.light.setWorldTransform(light_matrix)

                self._rail_guide.show(True)
                self._update_rail_geometry()

                # Update the light position
                self.set_light_position = True

                updates = {
                    "distance" : f"{self.light_distance:0.2f}",
                }

                self.scene_viewer.hudInfo(values = updates)

            return True

    def onMouseWheelEvent(self, kwargs):
        """ Process a mouse wheel event
        """

        ui_event = kwargs["ui_event"]
        state_parms = kwargs["state_parms"]
        updates = {}

        device = ui_event.device()
        scroll = device.mouseWheel()
        additional_distance = scroll / 10

        if self.light:
            
            self.light_intensity = self.light.parm("light_intensity").eval()
            self.light_exposure = self.light.parm("light_exposure").eval()

            max_intensity = max(0,self.light_intensity + additional_distance)
            max_exposure = max(0,self.light_exposure + additional_distance)
        
            if device.isShiftKey():
                self.light.parm("light_intensity").set(max_intensity)

                updates = {
                    "intensity" : f"{self.light_intensity:0.2f}",
                } 

            elif device.isCtrlKey():
                self.light.parm("light_exposure").set(max_exposure)

                updates = {
                    "exposure" : f"{self.light_exposure:0.2f}"
                } 

            else:
                if self.light and self.is_placed:

                    # Calculate the new distance and ensure it doesn't go below 0
                    max_distance = max(0,self.light_distance + additional_distance)
                    self.light_distance = max_distance

                    if self.set_light_position:
                        # Update light position and transforms
                        self.light_new_position = self.world_position + (self.reflection_ray * self.light_distance)  
                        light_matrix = hou.hmath.buildRotateZToAxis(self.reflection_ray)
                        light_matrix *= hou.hmath.buildTranslate(self.light_new_position)
                        self.light.setWorldTransform(light_matrix)  

                        # Update the guide geometry
                        self._update_rail_geometry()

                    updates = {
                            "distance" : f"{self.light_distance:0.2f}",
                        }   

            self.scene_viewer.hudInfo(values = updates)

        return True

    def onMenuAction(self, kwargs):
        """ Callback implementing the actions of a bound menu. Called 
        when a menu item has been selected. 
        """

        menu_item = kwargs["menu_item"]
        state_parms = kwargs["state_parms"]

        method = getattr(self, "_" + menu_item)

        if self.light:
            return method(kwargs)
        
        else:
            hou.ui.displayMessage("Please select a Light first.", severity = hou.severityType.Message)
    
    def _grid(self, kwargs):
        """
        Setup the light as Grid
        """
        self.light.parm("light_type").set(2)

        updates = {
            "dimension_x" : f"{self.light.parm('areasize1').eval():0.2f}",
            "dimension_y" : f"{self.light.parm('areasize2').eval():0.2f}",
        } 

        self.scene_viewer.hudInfo(values = updates)

    def _disk(self, kwargs):
        """
        Setup the light as Disk
        """
        self.light.parm("light_type").set(3)

        updates = {
            "dimension_x" : f"{self.light.parm('areasize1').eval():0.2f}",
            "dimension_y" : f"{self.light.parm('areasize2').eval():0.2f}",
        } 

        self.scene_viewer.hudInfo(values = updates)

    def _distant(self, kwargs):
        """
        Setup the light as Distant
        """
        self.light.parm("light_type").set(7)

        updates = {
            "dimension_x" : f"--",
            "dimension_y" : f"--",
        } 

        self.scene_viewer.hudInfo(values = updates)

    def _sun(self, kwargs):
        """
        Setup the light as Sun
        """
        self.light.parm("light_type").set(8)

        updates = {
            "dimension_x" : f"--",
            "dimension_y" : f"--",
        } 

        self.scene_viewer.hudInfo(values = updates)

    def _enable_vp(self, kwargs):
        """
        Toggle the light Enable in Viewport feature
        """

        if kwargs["menu_item"] == "enable_vp":
            self.light.parm("ogl_enablelight").set(kwargs["enable_vp"])

    def _color_picker(self, kwargs):
        """
        Opens the color picker widget
        """

        # Recompose the RGB component of the light color to a hou.Color format
        hou_color = hou.Color((self.light.parm("light_colorr").eval(),self.light.parm("light_colorg").eval(),self.light.parm("light_colorb").eval()))

        # Convert hou.Color to QColor
        q_color = hou.qt.toQColor(hou_color, alpha=1.0)

        # Set the default color for the color picker widget
        self.color_swatch_button.setColor(q_color)

        # Open the color picker widget
        self.color_swatch_button.click()

    def on_color_changed(self, color):
        """
        Apply selected color to the light color parm
        """

        self.light.parm("light_colorr").set(color.getRgbF()[0])
        self.light.parm("light_colorg").set(color.getRgbF()[1])
        self.light.parm("light_colorb").set(color.getRgbF()[2])

    def onKeyEvent(self, kwargs):
        """ Called for processing a keyboard event
        """
        ui_event = kwargs["ui_event"]
        state_parms = kwargs["state_parms"]
        device = ui_event.device()

        key_pressed = device.keyString()

        if key_pressed == "h":

            if self.light.parm("light_enable").eval():
                self.light.parm("light_enable").set(False)
            else:
                self.light.parm("light_enable").set(True)

        # Must returns True to consume the event
        return False
    
    def onDraw(self, kwargs):
        """ Called for rendering a state e.g. required for 
        hou.AdvancedDrawable objects
        """
        draw_handle = kwargs["draw_handle"]

        parms = {
            "color1" : (1.0, 0.5, 0.0, 0.75),
            "fade_factor" : 0.5,
            "style" : hou.drawableGeometryLineStyle.Dot2,
            "glow_width" : 0.1,
            "line_width" : 5,
            "highlight_mode" : hou.drawableHighlightMode.Matte,
            "use_cd" : True,
            "use_uv" : True
        }

        self._rail_guide.draw(draw_handle, parms)

    def onSelection(self, kwargs):
        """ Called when a selector has selected something
        """        
        selection = kwargs["selection"]
        state_parms = kwargs["state_parms"]
        selector_name = "light_select"

        if len(selection) != 1:
            return False
        
        if selector_name == "light_select":
            self.light = selection[0]
            self.light_intensity = self.light.parm("light_intensity").eval()
            self.light_exposure = self.light.parm("light_exposure").eval()
            
            updates = {
                "distance" : f"{self.light_distance:0.2f}",
                "dimension_x" : f"{self.light.parm('areasize1').eval():0.2f}",
                "dimension_y" : f"{self.light.parm('areasize2').eval():0.2f}",
                "intensity" : f"{self.light_intensity:0.2f}",
                "exposure" : f"{self.light_exposure:0.2f}"

            }  

            self.scene_viewer.hudInfo(values = updates)
            
            #hou.ui.displayMessage(f"{self.light.name()} is selected", severity = hou.severityType.Message)
            
            return True

    def onGenerate(self, kwargs):
        """ Called when a nodeless state starts
        """
        state_parms = kwargs["state_parms"]

        self.scene_viewer.hudInfo(template = HUD_TEMPLATE)
        self.scene_viewer.beginStateUndo("Place a Light")

    def onMenuPreOpen( self, kwargs ):
        """
        Preset the enable_vp toggle to the selected light value
        """
        if self.light:
            menu_item_states = kwargs["menu_item_states"]
            menu_item_states["enable_vp"]["value"] = self.light.parm("ogl_enablelight").eval()
        
def create_context_menu():
    """
    Builds the context Menu
    """

    menu = hou.ViewerStateMenu("light_properties", "Light Type")
    menu.addActionItem("grid", "Grid Light")
    menu.addActionItem("disk", "Disk Light")
    menu.addActionItem("distant", "Distant Light")
    menu.addActionItem("sun", "Sun Light")
    menu.addSeparator()
    menu.addToggleItem("enable_vp", "Enable in Viewport", True)
    menu.addActionItem("color_picker", "Change Light Color")

    return menu

def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state 
        template to register. """

    state_typename = "_place_light"
    state_label = "Place Light Highlight"
    state_cat = hou.objNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(State)
    template.bindIcon("MISC_python")

    template.bindObjectSelector(prompt = "Select a Light", 
                                quick_select=True, 
                                auto_start=True, 
                                use_existing_selection=True, 
                                allow_multisel=False, 
                                secure_selection=hou.secureSelectionOption.Ignore, 
                                allowed_types=('hlight::2.0',), 
                                name="light_select")

    template.bindMenu(create_context_menu())

    return template