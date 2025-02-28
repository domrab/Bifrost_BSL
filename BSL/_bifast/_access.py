from BSL._bifast import _node as _ast_node, _memory, _slice as _ast_slice, _call as _ast_call, _scope as _ast_scope
from BSL import _type, _error, _bifcmds

try:
    from maya import cmds
except:
    pass


class AccessRHS_Default(_ast_node.Node):
    def __init__(self, parser_node, key, value_or_type):
        super().__init__(parser_node)
        self._key = key
        self._type = value_or_type if isinstance(value_or_type, _type.Type) else value_or_type.value_type()
        self._value = None if isinstance(value_or_type, _type.Type) else value_or_type

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = AccessRHS_Default(self._parser_node, self._key.copy(d_map), self._value.copy(d_map) if self._value else self._type.copy())
        return d_map[self]

    def value_type(self):
        return self._type

    def is_constant(self):
        return self._key.is_constant() and ((self._value is None) or (self._value and self._value.is_constant()))

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        get_property = graph.create_node("Core::Object::get_property")
        graph.connect(self._key.to_vnn(graph), get_property//"key")
        if self._value is not None:
            s_value = self._value.to_vnn(graph)
            if self._value.value_type().is_node():
                s_value = s_value//list(self._value.value_type().node_data())[0]
            graph.connect(s_value, get_property//"default_and_type")
        else:
            graph.set_type(get_property, "default_and_type", self._type.s)

        self._vnn_result = get_property//"value"
        return self._vnn_result


class AccessByValue(_ast_node.Node):
    def __init__(self, parser_node, value):
        super().__init__(parser_node)
        self._value = value
        self._type = value.value_type()

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = AccessByValue(self._parser_node, self._value.copy(d_map))
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        s_value = self._value.to_vnn(graph)
        if self._value.value_type().is_node():
            s_value = s_value // list(self._value.value_type().node_data())[0]

        self._vnn_result = s_value
        return self._vnn_result


class AccessRHS(_ast_node.Node):
    def __init__(self, parser_node, value, access):
        super().__init__(parser_node)
        self._value = value
        self._access = access

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = AccessRHS(self._parser_node, self._value.copy(d_map), self._access if isinstance(self._access, str) else self._access.copy(d_map))
        return d_map[self]

    def value_type(self) -> _type.Type:
        type_value = self._value.value_type()

        if isinstance(self._access, str):
            return type_value.get_access(self._access)

        type_access = self._access.value_type()
        if type_value == "string":
            return type_value

        if type_value == "Object":
            return type_access

        if type_value.is_array():
            if type_access.is_array():
                return type_value
            return _type.Type(type_value.s[6:-1])

        raise NotImplementedError("This shouldn't have happened... o_O")

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        value = self._value.to_vnn(graph)

        if self._value.value_type().is_node():
            value = value//list(self._value.value_type().node_data())[0]

        if isinstance(self._access, _ast_slice.Slice):
            node = self._access.to_vnn(graph)
            if self._value.value_type() == "string":
                string_length = graph.create_node("Core::String::string_length")
                graph.connect(value, string_length//"string")
                graph.connect(string_length//"length", node//"size")
                get_from_string = graph.create_node("Core::String::get_from_string")
                graph.connect(value, get_from_string//"string")
                graph.connect(node//"out_indices", get_from_string//"index")
                build_string = graph.create_node("Core::String::build_string")
                cmds.vnnPort(graph._graph, f"{build_string}.strings", 0, 1, clear=2)
                graph.connect(get_from_string//"character", build_string//"strings")
                self._vnn_result = build_string//"joined"

            else:
                array_size = graph.create_node("Core::Array::array_size")
                graph.connect(value, array_size//"array")
                graph.connect(array_size//"size", node//"size")
                get_from_array = graph.create_node("Core::Array::get_from_array")
                graph.connect(value, get_from_array//"array")
                graph.connect(node//"out_indices", get_from_array//"index")
                self._vnn_result = get_from_array//"value"

            return self._vnn_result

        elif isinstance(self._access, AccessByValue):
            if self._value.value_type() == "string":
                get_from_string = graph.create_node("Core::String::get_from_string")
                graph.connect(value, get_from_string // "array")
                graph.connect(self._access._value.to_vnn(graph), get_from_string//"index")
                self._vnn_result = get_from_string//"character"

            else:
                get_from_array = graph.create_node("Core::Array::get_from_array")
                graph.connect(value, get_from_array // "array")

                s_value = self._access._value.to_vnn(graph)
                if self._access._value.value_type().is_node():
                    s_value = s_value//list(self._access._value.value_type().node_data())[0]
                graph.connect(s_value, get_from_array // "index")
                self._vnn_result = get_from_array//"value"

            return self._vnn_result

        elif isinstance(self._access, AccessRHS_Default):
            result = self._access.to_vnn(graph)
            graph.connect(value, result.parent//"object")
            self._vnn_result = result
            return self._vnn_result

        elif isinstance(self._access, str):
            node = graph.create_value_node(s_type=self._value.value_type().s)
            graph.connect(value, node//"value")
            self._vnn_result = node//f"output.{self._access}"
            return self._vnn_result

        raise NotImplementedError(repr(self._access))


class AccessLHS(_ast_node.Node):
    def __init__(self, parser_node, value, access):
        super().__init__(parser_node)
        self._value = value
        self._access = access
        self._base = None
        self._rhs = None

        type_value = self._value.value_type()

        if isinstance(self._access, str):
            self._method = "member"
            self._base = "_member"
            self._type = type_value.get_access(self._access)
            return

        type_access = self._access.value_type()
        if type_value == "string":
            self._method = "string"
            self._type = type_value
            self._base = type_value
            return

        if type_value == "Object":
            self._method = "object"
            self._base = type_value
            self._type = type_access
            return

        if type_value.is_array():
            self._base = type_value
            self._method = "array"
            if type_access.is_array():
                self._type = type_value
            self._type = _type.Type(type_value.s[6:-1])
            return

        raise NotImplementedError("This shouldn't have happened... o_O")

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = AccessLHS(self._parser_node, self._value.copy(d_map), self._access if isinstance(self._access, str) else self._access.copy(d_map))
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def base_type(self):
        return self._base

    def set_rhs(self, rhs):
        self._rhs = rhs

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph

        if self._method == "member":
            node = graph.create_value_node(s_type=self._value.value_type().s)
            graph.connect(self._rhs, node//f"value.{self._access}")
            self._vnn_result = node//"output"
            graph.get_memory().set(self._value.name(), self._vnn_result)
            return self._vnn_result

        elif self._method == "string":
            node = graph.create_node("set_in_string")

            s_value = self._value.to_vnn(graph)
            if self._value.value_type().is_node():
                s_value = s_value//(self._value.value_type().node_data())[0]

            graph.connect(s_value, node//"string")
            graph.connect(self._rhs, node//"characters")
            graph.connect(self._access.to_vnn(graph), node//"index")
            self._vnn_result = node//"out_string"
            graph.get_memory().set(self._value.name(), self._vnn_result)
            return self._vnn_result

        elif self._method == "array":
            node = graph.create_node("set_in_array")
            s_value = self._value.to_vnn(graph)
            if self._value.value_type().is_node():
                s_value = s_value//list(self._value.value_type().node_data())[0]
            graph.connect(s_value, node//"array")
            graph.connect(self._rhs, node//"value")
            graph.connect(self._access.to_vnn(graph), node//"index")
            self._vnn_result = node//"out_array"
            graph.get_memory().set(self._value.name(), self._vnn_result)
            return self._vnn_result

        elif self._method == "object":
            node = graph.create_node("set_property")
            s_value = self._value.to_vnn(graph)
            if self._value.value_type().is_node():
                s_value = s_value//list(self._value.value_type().node_data())[0]
            graph.connect(s_value, node//"object")
            graph.connect(self._rhs, node//"value")
            graph.connect(self._access.to_vnn(graph), node//"key")
            self._vnn_result = node//"out_object"
            graph.get_memory().set(self._value.name(), self._vnn_result)
            return self._vnn_result

        raise NotImplementedError(self._type)


class AccessPort(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, value, s_port, b_is_variable):
        value_ = value
        if b_is_variable:
            type_ = _memory.get_static_variable_type(value)
            if type_ is None:
                return False, (_error.BfNameError, f"Variable '{value}' referenced before assignment")

            if not type_.is_node():
                return False, (_error.BfTypeError, f"Cant access port with '->' on type '{type_}'. To access a member, use '.'")

            value_ = _memory.get_static_variable_value(value)

        if not value_.value_type().is_node():
            return False, (_error.BfTypeError, f"Need 'NODE' type to access port, got '{value_.value_type()}'")

        sa_names = value_.output_names()
        if s_port not in sa_names:
            return False, (_error.BfNameError, f"invalid port: '{s_port}'. Available: {sa_names}")

        return True, cls(parser_node, value, s_port, b_is_variable)

    def __init__(self, parser_node, value, s_port, b_is_variable, _real_value=None):
        super().__init__(parser_node)
        self._value = value
        self._s_port = s_port
        self._b_is_variable = b_is_variable

        if _real_value:
            self._real_value = _real_value

        else:
            self._real_value = value
            if self._b_is_variable:
                self._real_value = _memory.get_static_variable_value(self._value)

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = AccessPort(self._parser_node, self._value if isinstance(self._value, str) else self._value.copy(d_map), self._s_port, self._b_is_variable, self._real_value.copy(d_map))

        return d_map[self]

    def value_type(self) -> _type.Type:
        sa_names = self._real_value.output_names()
        types = self._real_value.output_types()
        return types[sa_names.index(self._s_port)]

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        node = self._real_value.to_vnn(graph)
        self._vnn_result = node//self._s_port
        return self._vnn_result
