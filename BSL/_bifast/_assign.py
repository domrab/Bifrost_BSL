from BSL import _type, _bifcmds, _bifast
from BSL._bifast import _node as _ast_node
from BSL._bifast import _value as _ast_value
from BSL._bifast import _access as _ast_access
from BSL._bifast import _scope as _ast_scope


class AssignLHS_TypeName(_ast_node.Node):
    def __init__(self, parser_node, s_name, s_type):
        super().__init__(parser_node)
        self._s_name = s_name
        self._type = _type.Type(s_type, {})

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = AssignLHS_TypeName(self._parser_node, self._s_name, self._type.s)
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def name(self):
        return self._s_name

    def set_value_type(self, type):
        self._type = type


class Assignment(_ast_node.Node):
    def __init__(self, parser_node, lhs_list, rhs, s_op):
        super().__init__(parser_node)
        self._lhs_list = lhs_list
        self._rhs = rhs
        self._s_op = s_op

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Assignment(self._parser_node, [(lhs.copy(d_map) if lhs is not None else None) for lhs in self._lhs_list], self._rhs.copy(d_map), self._s_op)
        return d_map[self]

    def is_constant(self):
        return self._rhs.is_constant()

    def value_type(self):
        return None

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph: _bifcmds.Graph = graph
        memory = graph.get_memory()

        rhs_value = self._rhs.to_vnn(graph)

        # match the logic from the ast graph
        # I need to figure out a way to do this only once
        type_rhs = self._rhs.value_type()
        if type_rhs.is_node():
            if len(self._lhs_list) > 1 or self._s_op == ":=":
                rhs_values = [rhs_value//s for s in self._rhs.output_names()]
            else:
                rhs_values = [rhs_value]
        else:
            rhs_values = len(self._lhs_list) * [rhs_value]

        for lhs, rhs in zip(self._lhs_list, rhs_values):
            if isinstance(lhs, AssignLHS_TypeName):
                memory.define(lhs.name(), lhs.value_type().s, value=rhs)

            elif isinstance(lhs, _ast_value.Variable):
                if memory.is_setonly(lhs.name()):
                    graph.connect(rhs, memory.get_setonly(lhs.name())[0])
                else:
                    memory.set(lhs.name(), rhs)

            elif lhs is None:
                continue

            elif isinstance(lhs, _ast_access.AccessLHS):
                lhs.set_rhs(rhs)
                lhs.to_vnn(graph)

            else:
                raise NotImplementedError(type(lhs))

        self._vnn_result = True
