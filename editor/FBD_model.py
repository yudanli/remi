import inspect

class Input():
    name = None
    default = None
    typ = None
    source = None #has to be an Output

    def __init__(self, name, default = inspect.Parameter.empty, typ = None):
        self.name = name
        self.default = default
        self.typ = typ

    def get_value(self):
        if not self.is_linked():
            return self.default
        return self.source.get_value()
    
    def has_default(self):
        return not (self.default == inspect.Parameter.empty)

    def link(self, output):
        self.source = output

    def is_linked(self):
        return self.source != None

    def unlink(self):
        Input.link(self, None)


class Output():
    name = None
    typ = None
    destinations = None #has to be an Input
    value = None

    def __init__(self, name, typ = None):
        self.name = name
        self.typ = typ
        self.destinations = []

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def link(self, destination):
        if not issubclass(type(destination), Input):
            return
        self.destinations.append(destination)

    def is_linked(self):
        return len(self.destinations) > 0

    def unlink(self, destination = None):
        if not destination is None:
            self.destinations.remove(destination)
            return
        self.destinations = []


class FunctionBlock():
    name = None
    inputs = None
    outputs = None

    execution_priority = 0

    def decorate_process(output_list):
        """ setup a method as a process FunctionBlock """
        """
            input parameters can be obtained by introspection
            outputs values (return values) are to be described with decorator
        """
        def add_annotation(method):
            setattr(method, "_outputs", output_list)
            return method
        return add_annotation

    def __init__(self, name, execution_priority = 0):
        self.name = name
        self.set_execution_priority(execution_priority)
        self.inputs = {}
        self.outputs = {}

    def set_execution_priority(self, execution_priority):
        self.execution_priority = execution_priority

    def add_io(self, io):
        if issubclass(type(io), Input):
            self.inputs[io.name] = io
        else:
            self.outputs[io.name] = io
    
    @decorate_process([])
    def do(self):
        return None


class Link():
    source = None
    destination = None
    def __init__(self, source_widget, destination_widget):
        self.source = source_widget
        self.destination = destination_widget

    def unlink(self):
        self.source.unlink(self.destination)
        self.destination.unlink()


class Process():
    function_blocks = None

    def __init__(self):
        self.function_blocks = {}

    def add_function_block(self, function_block):
        self.function_blocks[function_block.name] = function_block

    def do(self):
        execution_priority = 0
        for function_block in self.function_blocks.values():
            parameters = {}
            all_inputs_connected = True

            function_block.set_execution_priority(execution_priority)
            execution_priority += 1

            for IN in function_block.inputs.values():
                if (not IN.is_linked()) and (not IN.has_default()):
                    all_inputs_connected = False
                    continue
                parameters[IN.name] = IN.get_value()
            
            if not all_inputs_connected:
                continue
            output_results = function_block.do(**parameters)
            if output_results is None:
                continue
            i = 0
            for OUT in function_block.outputs.values():
                if type(output_results) in (tuple, list):
                    OUT.set_value(output_results[i])
                else:
                    OUT.set_value(output_results)
                i += 1

