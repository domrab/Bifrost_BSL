from BSL import _type, _bifcmds
from BSL._bifast import _node as _ast_node, _value as  _ast_value

try:
    from maya import cmds
except:
    pass


class Not(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, value):
        value_type = value.value_type()
        if value_type.is_node() and len(value_type.node_data()):
            value_type = list(value_type.node_data().values())[0]

        if not value_type.base_type().base_type().is_bool():
            return False, f"Cannot invert type '{value.value_type()}'"

        return True, cls(parser_node, value, value.value_type())

    def __init__(self, parser_node, value: _ast_node.Node, type):
        super().__init__(parser_node)
        self._value = value
        self._type = type

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Not(self._parser_node, self._value.copy(d_map), self._type.copy())
        return d_map[self]

    def value_type(self):
        # if not self._value.value_type().base_type().is_bool():
        #     raise Exception(f"Cant invert type: '{self._value.value_type()}'")
        return self._type

    def is_constant(self):
        return self._value.is_constant()

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph

        value = self._value.to_vnn(graph)
        if self._value.value_type().is_node():
            value = value//list(self._value.value_type().node_data())[0]

        self._vnn_result = graph.n_not(value)
        return self._vnn_result


class Negate(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, value):
        status, result = cls._get_type(value)
        if not status:
            return False, result

        return True, cls(parser_node, value, result)

    def __init__(self, parser_node, value: _ast_node.Node, type):
        super().__init__(parser_node)
        self._value = value
        self._type = type

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Negate(self._parser_node, self._value.copy(d_map), self._type.copy())
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    @classmethod
    def _get_type(cls, value):
        if isinstance(value, _type.Type):
            type_value = value
        else:
            type_value = value.value_type()

        if type_value.is_node() and len(type_value.node_data()):
            type_value = list(type_value.node_data().values())[0]

        if not (type_value.base_type().base_type().is_numeric() or type_value.base_type().is_field()):
            return False, f"Cant negate value of type '{value.value_type()}'"

        s_prefix = ""
        s_suffix = ""
        type_base = type_value.base_type()

        if type_value.is_array():
            s_prefix = type_value.array_dim() * "array<"
            s_suffix = type_value.array_dim() * ">"
            type_value = type_base
            type_base = type_value.base_type()

        s_base = type_base.s

        if type_base.is_field():
            return True, type_value

        if type_base.is_unsigned():
            if type_base.is_big():
                s_base = "double"

            elif type_base.s == "uint":
                s_base = "float"

            else:
                s_base = {2: "short", 4: "int", 8: "long"}[type_base.numeric_size()*2]

        if type_value.is_matrix():
            ia_dim = type_value.matrix_dim()
            s_suffix = f"{ia_dim[0]}x{ia_dim[1]}{s_suffix}"
            s_prefix += "Math::"

        elif type_value.is_vector():
            i_dim = type_value.vector_dim()
            s_suffix = f"{i_dim}{s_suffix}"
            s_prefix += "Math::"

        return True, _type.Type(s_prefix + s_base + s_suffix)

    def is_constant(self):
        return self._value.is_constant()

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph

        value = self._value.to_vnn(graph)
        if self._value.value_type().is_node():
            value = value//list(self._value.value_type().node_data())[0]
        self._vnn_result = graph.n_negate(value)
        return self._vnn_result


if __name__ == "__main__":
    print(Negate(None, _ast_value.Value(None, 0, "array<uint3>")).value_type())