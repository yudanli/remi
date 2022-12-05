"""
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import remi.gui as gui
import remi.server
from remi import start, App
import os #for path handling
import inspect
import time
from editor_widgets import *
import FBD_model
import types

import widgets.toolbox_opencv

class MixinPositionSize():
    def get_position(self):
        return float(self.attr_x), float(self.attr_y)

    def get_size(self):
        return float(self.attr_width), float(self.attr_height)


class MoveableWidget(gui.EventSource, MixinPositionSize):
    container = None
    x_start = 0
    y_start = 0
    def __init__(self, container, *args, **kwargs):
        gui.EventSource.__init__(self)
        self.container = container
        self.active = False
        self.onmousedown.do(self.start_drag, js_stop_propagation=True, js_prevent_default=True)
            
    def start_drag(self, emitter, x, y):
        self.x_start = float(x)
        self.y_start = float(y)
        self.active = True
        self.container.onmousemove.do(self.on_drag, js_stop_propagation=True, js_prevent_default=True)
        self.onmousemove.do(None, js_stop_propagation=False, js_prevent_default=True)
        self.container.onmouseup.do(self.stop_drag)
        self.container.onmouseleave.do(self.stop_drag, 0, 0)

    @gui.decorate_event
    def stop_drag(self, emitter, x, y):
        self.active = False
        return (x, y)

    @gui.decorate_event
    def on_drag(self, emitter, x, y):
        if self.active:
            #self.set_position(float(x) - float(self.attr_width)/2.0, float(y) - float(self.attr_height)/2.0)
            self.set_position(float(x) - self.x_start, float(y) - self.y_start)
        return (x, y)


class SvgTitle(gui.Widget, gui._MixinTextualWidget):
    def __init__(self, text='svg text', *args, **kwargs):
        super(SvgTitle, self).__init__(*args, **kwargs)
        self.type = 'title'
        self.set_text(text)


class InputView(FBD_model.Input, gui.SvgSubcontainer, MixinPositionSize):
    placeholder = None
    label = None
    previous_value = None
    link_view = None
    def __init__(self, name, *args, **kwargs):
        gui.SvgSubcontainer.__init__(self, 0, 0, 0, 0, *args, **kwargs)
        self.placeholder = gui.SvgRectangle(0, 0, 0, 0)
        self.append(self.placeholder)

        self.label = gui.SvgText("0%", "50%", name)
        self.append(self.label)

        FBD_model.Input.__init__(self, name, *args, **kwargs)
        self.set_default_look()

    def set_default_look(self):
        self.placeholder.set_stroke(1, 'black')
        self.placeholder.set_fill("lightgray")
        self.placeholder.style['cursor'] = 'pointer'

        self.label.attr_dominant_baseline = 'central'
        self.label.attr_text_anchor = "start"
        self.label.style['cursor'] = 'pointer'
        self.label.set_fill('black')

    def link(self, source, link_view):
        FBD_model.Input.link(self, source)
        self.link_view = link_view

    def unlink(self):
        FBD_model.Input.unlink(self)
        self.set_default_look()

    def get_value(self):
        v = FBD_model.Input.get_value(self)

        if self.is_linked() or self.has_default():
            try:
                if self.previous_value == v:
                    return v
            except:
                pass

            if type(v) == bool:
                self.label.set_fill('white')
                self.placeholder.set_fill('blue' if v else 'BLACK')
            self.append(SvgTitle(str(v)), "title")
            self.previous_value = v

        return v

    def set_size(self, width, height):
        if self.placeholder:
            gui._MixinSvgSize.set_size(self.placeholder, width, height)
        return gui._MixinSvgSize.set_size(self, width, height)

    @gui.decorate_event
    def onpositionchanged(self):
        if not self.link_view is None:
            self.link_view.update_path()
        return ()


class OutputView(FBD_model.Output, gui.SvgSubcontainer, MixinPositionSize):
    placeholder = None
    label = None
    def __init__(self, name, *args, **kwargs):
        gui.SvgSubcontainer.__init__(self, 0, 0, 0, 0, *args, **kwargs)
        self.placeholder = gui.SvgRectangle(0, 0, 0, 0)
        self.placeholder.set_stroke(1, 'black')
        self.placeholder.set_fill("lightgray")
        self.placeholder.style['cursor'] = 'pointer'
        self.append(self.placeholder)

        self.label = gui.SvgText("100%", "50%", name)
        self.label.attr_dominant_baseline = 'central'
        self.label.attr_text_anchor = "end"
        self.label.style['cursor'] = 'pointer'
        self.append(self.label)

        FBD_model.Output.__init__(self, name, *args, **kwargs)

    def link(self, destination, container):
        link_view = LinkView(self, destination, container)
        container.append(link_view)
        bt_unlink = DeleteButton()
        container.append(bt_unlink)
        link_view.set_unlink_button(bt_unlink)
        FBD_model.Output.link(self, destination)
        destination.link(self, link_view)

    def unlink(self, destination = None):
        if not destination is None:
            destination.link_view = None
        FBD_model.Output.unlink(self, destination)

    def set_size(self, width, height):
        if self.placeholder:
            self.placeholder.set_size(width, height)
        return gui._MixinSvgSize.set_size(self, width, height)

    def set_value(self, value):
        try:
            if value == self.value:
                return
        except:
            pass
        if type(value) == bool:
            self.label.set_fill('white')
            self.placeholder.set_fill('blue' if value else 'BLACK')
        
        self.append(SvgTitle(str(value)), "title")

        self.label.attr_title = str(value)

        FBD_model.Output.set_value(self, value)

    @gui.decorate_event
    def onpositionchanged(self):
        for node in self.linked_nodes:
            node.link_view.update_path()
        return ()


class DeleteButton(gui.SvgSubcontainer):
    def __init__(self, x=0, y=0, w=12, h=12, *args, **kwargs):
        gui.SvgSubcontainer.__init__(self, x, y, w, h, *args, **kwargs)
        self.outline = gui.SvgRectangle(0, 0, "100%", "100%")
        self.outline.set_fill('red')
        self.outline.set_stroke(1, 'darkred')
        self.append(self.outline)
        
        line = gui.SvgLine("20%","20%","80%","80%")
        line.set_stroke(2, 'white')
        self.append(line)
        line = gui.SvgLine("80%", "20%", "20%", "80%")
        line.set_stroke(2, 'white')
        self.append(line)

    def get_size(self):
        """ Returns the rectangle size.
        """
        return float(self.attr_width), float(self.attr_height)


class LinkView(gui.SvgPolyline, FBD_model.Link):
    bt_unlink = None
    container = None
    def __init__(self, source_widget, destination_widget, container, *args, **kwargs):
        self.container = container
        gui.SvgPolyline.__init__(self, 2, *args, **kwargs)
        FBD_model.Link.__init__(self, source_widget, destination_widget)
        self.set_stroke(1, 'black')
        self.set_fill('transparent')
        self.attributes['stroke-dasharray'] = "4 2"

        #this is to prevent stopping elements drag when moving over a link
        self.style['pointer-events'] = 'none' 
        self.onmousemove.do(None, js_stop_propagation=False, js_prevent_default=True)
        self.onmouseleave.do(None, js_stop_propagation=False, js_prevent_default=True)

        self.update_path()

    def set_unlink_button(self, bt_unlink):
        self.bt_unlink = bt_unlink
        self.bt_unlink.onclick.do(self.unlink)
        self.update_path()

    def unlink(self, emitter = None):
        self.get_parent().remove_child(self.bt_unlink)
        self.get_parent().remove_child(self)
        FBD_model.Link.unlink(self)

    def get_absolute_node_position(self, node):
        np = node.get_parent()
        if np == self.container:
            return node.get_position()
        
        x, y = node.get_position()
        xs, ys = self.get_absolute_node_position(np)
        return x+xs, y+ys

    def update_path(self, emitter=None):
        self.attributes['points'] = ''

        xsource,ysource = self.get_absolute_node_position( self.source )
        w,h = self.source.get_size()
        xsource += w
        ysource += h/2
        xsource_parent, ysource_parent = self.get_absolute_node_position(self.source.get_parent())
        wsource_parent, hsource_parent = self.source.get_parent().get_size()

        #xsource = xsource_parent + wsource_parent
        #ysource = ysource_parent + y + h/2.0
        self.add_coord(xsource, ysource)

        x,y = self.get_absolute_node_position( self.destination )
        w,h = self.destination.get_size()
        xdestination_parent, ydestination_parent = self.get_absolute_node_position(self.destination.get_parent())
        wdestination_parent, hdestination_parent = self.destination.get_parent().get_size()

        xdestination, ydestination = self.get_absolute_node_position( self.destination )
        ydestination +=  + h/2.0
        #ydestination = ydestination_parent + y + h/2.0

        offset = 20

        if xdestination - xsource < offset*2:
            self.maxlen = 6
            """
                    [   source]---,
                                  |
                        __________|
                        |
                        '----[destination   ]
            """
            self.add_coord(xsource + offset, ysource)

            if ydestination > ysource:
                #self.add_coord(xsource + offset, ysource + (ydestination - ysource)/2.0)
                #self.add_coord(xdestination - offset, ysource + (ydestination - ysource)/2.0)
                self.add_coord(xsource + offset, (ysource_parent + hsource_parent)  + (ydestination_parent - (ysource_parent + hsource_parent))/2.0)
                self.add_coord(xdestination - offset, (ysource_parent + hsource_parent)  + (ydestination_parent - (ysource_parent + hsource_parent))/2.0)
            else:
                self.add_coord(xsource + offset, (ydestination_parent + hdestination_parent)  + (ysource_parent - (ydestination_parent + hdestination_parent))/2.0)
                self.add_coord(xdestination - offset, (ydestination_parent + hdestination_parent)  + (ysource_parent - (ydestination_parent + hdestination_parent))/2.0)
            self.add_coord(xdestination - offset, ydestination)

        else:
            self.maxlen = 4
            """
                    [   source]---,
                                  |
                                  '------[destination   ]
            """
            self.add_coord(xsource + (xdestination-xsource)/2.0, ysource)
            self.add_coord(xdestination - (xdestination-xsource)/2.0, ydestination)

        self.add_coord(xdestination, ydestination)
        if self.bt_unlink != None:

            w, h = self.bt_unlink.get_size()
            self.bt_unlink.set_position(xdestination - offset / 2.0 - w/2, ydestination -h/2)


class FunctionBlockView(FBD_model.FunctionBlock, gui.SvgSubcontainer, MoveableWidget):

    @property
    @gui.editor_attribute_decorator("WidgetSpecific",'''Defines if the function block has to be enabled''', bool, {})
    def has_enabling_input(self): return 'EN' in self.inputs.keys()
    @has_enabling_input.setter
    def has_enabling_input(self, value): 
        if value:
            self.add_enabling_input_widget()
        else:
            self.remove_enabling_input_widget()

    label = None
    label_priority = None
    label_font_size = 12

    outline = None

    io_font_size = 12
    io_left_right_offset = 10

    execution_priority = 0

    def __init__(self, name, container, x = 10, y = 10, execution_priority = 0, *args, **kwargs):
        FBD_model.FunctionBlock.__init__(self, name, execution_priority)
        gui.SvgSubcontainer.__init__(self, x, y, self.calc_width(), self.calc_height(), *args, **kwargs)
        MoveableWidget.__init__(self, container, *args, **kwargs)

        self.outline = gui.SvgRectangle(0, 0, "100%", "100%")
        self.outline.set_fill('white')
        self.outline.set_stroke(2, 'black')
        self.append(self.outline)

        self.label = gui.SvgText("50%", 0, self.name)
        self.label.attr_text_anchor = "middle"
        self.label.attr_dominant_baseline = 'text-before-edge'
        self.label.style['pointer-events'] = 'none'
        self.label.css_font_size = gui.to_pix(self.label_font_size)
        self.append(self.label)

        self.label_priority = gui.SvgText("100%", 0, str(self.execution_priority))
        self.label_priority.style['pointer-events'] = 'none'
        self.label_priority.attr_text_anchor = "end"
        self.label_priority.attr_dominant_baseline = 'text-before-edge'
        self.label_priority.set_fill("red")
        self.label_priority.css_font_size = gui.to_pix(self.label_font_size)
        #self.append(self.label_priority)

        self.priority_container = gui.SvgSubcontainer(self.calc_width()-2, 2, 0, 0)
        self.priority_container.css_overflow = "visible"
        self.priority_container.style['pointer-events'] = 'none'
        self.append(self.priority_container)
        self.priority_container.append(self.label_priority)

        self.delete_button = DeleteButton()
        self.delete_button.onclick.do(self.on_delete_button_pressed, js_stop_propagation=True, js_prevent_default=True)
        self.append(self.delete_button)

        self.populate_io()

        self.stop_drag.do(lambda emitter, x, y:self.adjust_geometry())

    @gui.decorate_event
    def on_delete_button_pressed(self, emitter):
        return ()

    def set_execution_priority(self, execution_priority):
        if not self.label_priority is None:
            self.label_priority.set_text(str(self.execution_priority))
        FBD_model.FunctionBlock.set_execution_priority(self, execution_priority)

    def populate_io(self):
        #for all the outputs defined by decorator on FunctionBlock.do
        #   add the related Outputs
        if hasattr(self.do, "_outputs"):
            for o in self.do._outputs:
                self.add_io_widget(OutputView(o))

        signature = inspect.signature(self.do)
        for arg in signature.parameters:
            self.add_io_widget(InputView(arg, default = signature.parameters[arg].default))

    def calc_height(self):
        inputs_count = 0 if self.inputs == None else len(self.inputs)
        outputs_count = 0 if self.outputs == None else len(self.outputs)
        return self.label_font_size + (max(outputs_count, inputs_count)+2) * self.io_font_size

    def calc_width(self):
        max_name_len_input = 0
        if self.inputs != None:
            for inp in self.inputs.values():
                max_name_len_input = max(max_name_len_input, len(inp.name))

        max_name_len_output = 0
        if self.outputs != None:
            for o in self.outputs.values():
                max_name_len_output = max(max_name_len_output, len(o.name))

        return max((len(self.name) * self.label_font_size*0.6), (max(max_name_len_input, max_name_len_output)*self.io_font_size*0.6) * 2) + self.io_left_right_offset

    def add_io_widget(self, widget):
        widget.label.css_font_size = gui.to_pix(self.io_font_size)
        widget.set_size(len(widget.name) * self.io_font_size*0.6, self.io_font_size)

        FBD_model.FunctionBlock.add_io(self, widget)
        self.append(widget)
        widget.onmousedown.do(self.container.onselection_start, js_stop_propagation=True, js_prevent_default=True)
        widget.onmouseup.do(self.container.onselection_end, js_stop_propagation=True, js_prevent_default=True)

        self.adjust_geometry()

    def remove_io_widget(self, name):
        io = self.inputs[name]
        if io.is_linked():
            if issubclass(type(io), FBD_model.Input):
                io.link_view.unlink()
            else:
                for dest in io.linked_nodes:
                    if dest.name == name:
                        dest.link_view.unlink()
                        break
        self.remove_child(io)
        del self.inputs[name]

    def add_enabling_input_widget(self):
        self.add_io_widget(InputView('EN', default = False))

    def remove_enabling_input_widget(self):
        self.remove_io_widget('EN')

    def onposition_changed(self):
        for inp in self.inputs.values():
            inp.onpositionchanged()

        for o in self.outputs.values():
            o.onpositionchanged()

    def adjust_geometry(self):
        gui._MixinSvgSize.set_size(self, self.calc_width(), self.calc_height())
        w, h = self.get_size()
        self.priority_container.set_position(w-2, 2)

        i = 1
        for inp in self.inputs.values():
            inp.set_position(0, self.label_font_size + self.io_font_size*i)
            inp.onpositionchanged()
            i += 1

        i = 1
        for o in self.outputs.values():
            ow, oh = o.get_size()
            o.set_position(w - ow, self.label_font_size + self.io_font_size*i)
            o.onpositionchanged()
            i += 1

    def set_position(self, x, y):
        if self.inputs != None:
            for inp in self.inputs.values():
                inp.onpositionchanged()

            for o in self.outputs.values():
                o.onpositionchanged()
        return super().set_position(x, y)

    def set_name(self, name):
        self.name = name
        self.label.set_text(name)
        self.adjust_geometry()


"""
    Bisogna gestire
        nome processo
        tipo di esecuzione
        parametri in input e output
        vedere i processi a più alto livello come function blocks
        entrare in un function block e comporlo come un processo
        eliminazione fb, con relativi link
        ordinamento esecuzione
"""

class ProcessView(gui.Svg, FBD_model.Process):
    name = None

    selected_input = None
    selected_output = None

    selected_function_block = None

    label = None
    label_font_size = 18

    process_outputs_fb = None #this is required to route result values outside of Process
    process_inputs_fb = None #this is required to route parameters inside the Process

    def __init__(self, name, *args, **kwargs):
        self.name = name
        gui.Svg.__init__(self, *args, **kwargs)
        FBD_model.Process.__init__(self)
        
        self.css_border_color = 'black'
        self.css_border_width = '0px'
        self.css_border_style = 'solid'
        #self.style['background-color'] = 'lightyellow'
        self.css_background_color = 'rgb(250,248,240)'
        self.css_background_image = "url('/editor_resources:background.png')"

        self.label = gui.SvgText("50%", 0, self.name)
        self.label.attr_text_anchor = "middle"
        self.label.attr_dominant_baseline = 'text-before-edge'
        #self.label.set_stroke(1, "gray")
        self.label.set_fill("darkgray")
        self.label.style['pointer-events'] = 'none'
        self.label.css_font_size = gui.to_pix(self.label_font_size)
        self.append(self.label)

        self.process_inputs_fb = FunctionBlockView("Process INPUTS", self)
        self.process_inputs_fb.add_io_widget(OutputView("in1"))
        self.process_inputs_fb.outputs['in1'].set_value(True)
        self.process_inputs_fb.add_io_widget(OutputView("in2"))
        self.process_inputs_fb.outputs['in2'].set_value(False)
        self.process_inputs_fb.outline.set_fill("transparent")
        self.add_function_block(self.process_inputs_fb)

        self.process_outputs_fb = FunctionBlockView("Process OUTPUTS", self)
        self.process_outputs_fb.add_io_widget(InputView("out1"))
        self.process_outputs_fb.add_io_widget(InputView("out2"))
        self.process_outputs_fb.outline.set_fill("transparent")
        self.add_function_block(self.process_outputs_fb)

    def onselection_start(self, emitter, x, y):
        self.selected_input = self.selected_output = None
        print("selection start: ", type(emitter))
        if issubclass(type(emitter), FBD_model.Input):
            self.selected_input = emitter
        else:
            self.selected_output = emitter

    def onselection_end(self, emitter, x, y):
        print("selection end: ", type(emitter))
        if issubclass(type(emitter), FBD_model.Input):
            self.selected_input = emitter
        else:
            self.selected_output = emitter

        if self.selected_input != None and self.selected_output != None:
            if self.selected_input.is_linked():
                return
            self.selected_output.link(self.selected_input, self)

    def add_function_block(self, function_block):
        function_block.onclick.do(self.onfunction_block_clicked)
        function_block.on_delete_button_pressed.do(self.remove_function_block)
        self.append(function_block, function_block.name)
        FBD_model.Process.add_function_block(self, function_block)

    def remove_function_block(self, emitter):
        if issubclass(type(emitter), FBD_model.FunctionBlock):
            self.remove_child(emitter)
            for IN in emitter.inputs.values():
                if IN.is_linked():
                    IN.link_view.unlink()
            
            for OUT in emitter.outputs.values():
                if OUT.is_linked():
                    for IN in OUT.linked_nodes:
                        IN.link_view.unlink()
            FBD_model.Process.remove_function_block(self, emitter)

    @gui.decorate_event
    def onfunction_block_clicked(self, function_block):
        if not self.selected_function_block is None:
            self.selected_function_block.label.css_font_weight = "normal"
        self.selected_function_block = function_block
        self.selected_function_block.label.css_font_weight = "bolder"
        return (function_block,)


class FBToolbox(gui.Container):
    def __init__(self, appInstance, **kwargs):
        self.appInstance = appInstance
        super(FBToolbox, self).__init__(**kwargs)
        self.lblTitle = gui.Label("Widgets Toolbox", height=20)
        self.lblTitle.add_class("DialogTitle")
        self.widgetsContainer = gui.HBox(width='100%', height='calc(100% - 20px)')
        self.widgetsContainer.style.update({'overflow-y': 'scroll',
                                            'overflow-x': 'hidden',
                                            'align-items': 'flex-start',
                                            'flex-wrap': 'wrap',
                                            'background-color': 'white'})

        self.append([self.lblTitle, self.widgetsContainer])

        import FBD_library
        # load all widgets
        self.add_widget_to_collection(FBD_library.NONE)
        self.add_widget_to_collection(FBD_library.BOOL)
        self.add_widget_to_collection(FBD_library.NOT)
        self.add_widget_to_collection(FBD_library.AND)
        self.add_widget_to_collection(FBD_library.OR)
        self.add_widget_to_collection(FBD_library.XOR)
        self.add_widget_to_collection(FBD_library.PULSAR)
        self.add_widget_to_collection(FBD_library.STRING)
        self.add_widget_to_collection(FBD_library.STRING_SWAP_CASE)
        self.add_widget_to_collection(FBD_library.RISING_EDGE)
        self.add_widget_to_collection(FBD_library.PRINT)
        
    def add_widget_to_collection(self, functionBlockClass, group='standard_tools', **kwargs_to_widget):
        # create an helper that will be created on click
        # the helper have to search for function that have 'return' annotation 'event_listener_setter'
        if group not in self.widgetsContainer.children.keys():
            self.widgetsContainer.append(EditorAttributesGroup(group), group)
            self.widgetsContainer.children[group].style['width'] = "100%"

        helper = FBHelper(
            self.appInstance, functionBlockClass, **kwargs_to_widget)
        helper.attributes['title'] = functionBlockClass.__doc__
        #self.widgetsContainer.append( helper )
        self.widgetsContainer.children[group].append(helper)


class FBHelper(gui.HBox):
    """ Allocates the Widget to which it refers,
        interfacing to the user in order to obtain the necessary attribute values
        obtains the constructor parameters, asks for them in a dialog
        puts the values in an attribute called constructor
    """

    def __init__(self, appInstance, functionBlockClass, **kwargs_to_widget):
        self.kwargs_to_widget = kwargs_to_widget
        self.appInstance = appInstance
        self.functionBlockClass = functionBlockClass
        super(FBHelper, self).__init__()
        self.style.update({'background-color': 'rgb(250,250,250)', 'width': "auto", 'margin':"2px", 
                           "height": "60px", "justify-content": "center", "align-items": "center",
                           'font-size': '12px'})
        if hasattr(functionBlockClass, "icon"):
            if type(functionBlockClass.icon) == gui.Svg:
                self.icon = functionBlockClass.icon
            elif functionBlockClass.icon == None:
                self.icon = default_icon(self.functionBlockClass.__name__)
            else:
                icon_file = functionBlockClass.icon
                self.icon = gui.Image(icon_file, width='auto', margin='2px')
        else:
            icon_file = '/editor_resources:widget_%s.png' % self.functionBlockClass.__name__
            if os.path.exists(self.appInstance._get_static_file(icon_file)): 
                self.icon = gui.Image(icon_file, width='auto', margin='2px')
            else:
                self.icon = default_icon(self.functionBlockClass.__name__)

        self.icon.style['max-width'] = '100%'
        self.icon.style['image-rendering'] = 'auto'
        self.icon.attributes['draggable'] = 'false'
        self.icon.attributes['ondragstart'] = "event.preventDefault();"
        self.append(self.icon, 'icon')
        self.append(gui.Label(self.functionBlockClass.__name__), 'label')
        self.children['label'].style.update({'margin-left':'2px', 'margin-right':'3px'})

        self.attributes.update({'draggable': 'true',
                                'ondragstart': "this.style.cursor='move'; event.dataTransfer.dropEffect = 'move';   event.dataTransfer.setData('application/json', JSON.stringify(['add',event.target.id,(event.clientX),(event.clientY)]));",
                                'ondragover': "event.preventDefault();",
                                'ondrop': "event.preventDefault();return false;"})

        # this dictionary will contain optional style attributes that have to be added to the widget once created
        self.optional_style_dict = {}

        self.onclick.do(self.create_instance)

    def build_widget_name_list_from_tree(self, node):
        if not issubclass(type(node), FBD_model.FunctionBlock) and not issubclass(type(node), ProcessView):
            return
        if issubclass(type(node), FBD_model.FunctionBlock):
            self.varname_list.append(node.name)
        for child in node.children.values():
            self.build_widget_name_list_from_tree(child)

    def build_widget_used_keys_list_from_tree(self, node):
        if not issubclass(type(node), FBD_model.FunctionBlock) and not issubclass(type(node), ProcessView):
            return
        self.used_keys_list.extend(list(node.children.keys()))
        for child in node.children.values():
            self.build_widget_used_keys_list_from_tree(child)

    def on_dropped(self, left, top):
        self.optional_style_dict['left'] = gui.to_pix(left)
        self.optional_style_dict['top'] = gui.to_pix(top)
        self.create_instance(None)

    def create_instance(self, widget):
        """ Here the widget is allocated
        """
        self.varname_list = []
        self.build_widget_name_list_from_tree(self.appInstance.process)
        self.used_keys_list = []
        self.build_widget_used_keys_list_from_tree(self.appInstance.process)
        print("-------------used keys:" + str(self.used_keys_list))
        variableName = ''
        for i in range(0, 1000):  # reasonably no more than 1000 widget instances in a project
            variableName = self.functionBlockClass.__name__.lower() + str(i)
            if not variableName in self.varname_list and not variableName in self.used_keys_list:
                break

        """
        if re.match('(^[a-zA-Z][a-zA-Z0-9_]*)|(^[_][a-zA-Z0-9_]+)', variableName) == None:
            self.errorDialog = gui.GenericDialog("Error", "Please type a valid variable name.", width=350,height=120)
            self.errorDialog.show(self.appInstance)
            return

        if variableName in self.varname_list:
            self.errorDialog = gui.GenericDialog("Error", "The typed variable name is already used. Please specify a new name.", width=350,height=150)
            self.errorDialog.show(self.appInstance)
            return
        """
        # here we create and decorate the widget
        function_block = self.functionBlockClass(variableName, self.appInstance.process, **self.kwargs_to_widget)
        function_block.attr_editor_newclass = False

        for key in self.optional_style_dict:
            function_block.style[key] = self.optional_style_dict[key]
        self.optional_style_dict = {}

        self.appInstance.add_function_block_to_editor(function_block)


class MyApp(App):
    process = None
    toolbox = None
    attributes_editor = None

    def __init__(self, *args):
        editor_res_path = os.path.join(os.path.dirname(__file__), 'res')
        super(MyApp, self).__init__(
            *args, static_file_path={'editor_resources': editor_res_path})

    def idle(self):
        if self.process is None:
            return
        self.process.do()

    def main(self):
        self.main_container = gui.AsciiContainer(width="100%", height="100%", margin='0px auto')
        self.main_container.set_from_asciiart(
            """
            |toolbox  |process_view               |attributes|
            |container|process_view               |attributes|
            """, 0, 0
        )

        self.process = ProcessView("Process", width=600, height=600)
        self.process.onfunction_block_clicked.do(self.onprocessview_function_block_clicked)
        self.attributes_editor = EditorAttributes(self)
        self.toolbox = FBToolbox(self)
        
        #a container to put some widgets for debugging inside
        self.container = gui.VBox()
        self.main_container.append(self.container, "container")

        import FBD_library
        imread = widgets.toolbox_opencv.OpencvImRead(r"C:\Users\davide\Documents\GIT\remi\editor\widgets\camera.png")
        fb = FBD_library.FBWrapObjectMethod("imread", imread.get_image_data, self.process)
        #fb.add_io_widget(OutputView("IMAGE"))
        self.process.add_function_block(fb)
        self.container.append(imread)

        imthreshold = widgets.toolbox_opencv.OpencvThreshold()
        fb = FBD_library.FBWrapObjectMethod("imthreshold", imthreshold.set_image_data, self.process)
        self.process.add_function_block(fb)
        self.container.append(imthreshold)

        self.main_container.append(self.toolbox, 'toolbox')
        self.main_container.append(self.process, 'process_view')
        self.main_container.append(self.attributes_editor, 'attributes')
        
        # returning the root widget
        return self.main_container

    def onprocessview_function_block_clicked(self, emitter, function_block):
        self.attributes_editor.set_widget(function_block)

    def add_function_block_to_editor(self, function_block):
        self.process.add_function_block(function_block)

    
if __name__ == "__main__":
    start(MyApp, debug=False, address='0.0.0.0', port=0, update_interval=0.01)
