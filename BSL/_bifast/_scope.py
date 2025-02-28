from BSL import _type, _bifcmds
from BSL._bifast import _node as _ast_node
from BSL._bifast import _call as _ast_call

try:
    from maya import cmds
except:
    pass


class ScopeParameter(_ast_node.Node):
    def __init__(self, parser_node, s_name, s_type, default=None):
        super().__init__(parser_node)
        self._s_name = s_name
        self._type = _type.Type(s_type)
        self._default = default

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = ScopeParameter(self._parser_node, self._s_name, self._type.s, self._default.copy(d_map) if self._default else None)
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def is_constant(self) -> bool:
        return False

    def name(self):
        return self._s_name


class ScopeResult(_ast_node.Node):
    def __init__(self, parser_node, s_name, s_type, s_feedback=None):
        super().__init__(parser_node)
        self._s_name = s_name
        self._type = _type.Type(s_type)
        self._s_feedback = s_feedback

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = ScopeResult(self._parser_node, self._s_name, self._type.s, self._s_feedback)
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def is_constant(self) -> bool:
        return False

    def name(self):
        return self._s_name

    def feedback(self):
        return self._s_feedback


class Scope(_ast_node.Node, _ast_call._MixinCall):
    def __init__(self, parser_node, parameters, results, code, sa_terminal):
        super().__init__(parser_node)
        self._s_name = "unnamed"
        self._parameters = parameters
        self._results = results
        self._code = code
        self._sa_terminal = sa_terminal
        self._d_outputs = {r.name(): r.value_type() for r in self._results}

    def copy(self, d_map):
        if self not in d_map:
            parameters = [p.copy(d_map) for p in self._parameters]
            results = [r.copy(d_map) for r in self._results]
            code = [s.copy(d_map) for s in self._code]
            d_map[self] = Scope(self._parser_node, parameters, results, code, self._sa_terminal[:])
        return d_map[self]

    def value_type(self) -> _type.Type:
        return _type.Type("__NODE", node_data=self.outputs())

    def is_constant(self) -> bool:
        # return all([value.is_constant() if value else False for value in self._args])
        return bool(self._parameters)

    def set_name(self, s):
        self._s_name = s

    def parameters(self):
        return self._parameters

    def terminal(self):
        return self._sa_terminal

    def code(self):
        return self._code

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        compound = graph.create_compound_node(inputs=("input",), outputs=("output",))

        memory = _bifcmds.Memory()

        for parm in self._parameters:
            graph.add_out_port(compound/"input", parm.name(), parm.value_type().s)
            memory.define(parm.name(), s_type=parm.value_type().s, value=compound/"input"//parm.name())

            if parm._default is not None:
                graph.connect(parm._default.to_vnn(graph), compound//parm.name())
            # else:
            #      graph.connect(graph.get_memory().get(parm.name()), compound//parm.name())

        for result in self._results:
            graph.add_in_port(compound/"output", result.name(), result.value_type().s)
            memory.define_setonly(result.name(), s_type=result.value_type().s, target=compound/"output"//result.name())

            if result.feedback():
                cmds.vnnCompound(graph._graph, compound, setPortMetaDataValue=(result.name(), "feedbackPort", result.feedback()))

        graph.push_context2(compound, memory)

        for statement in self.code():
            statement.to_vnn(graph)

        graph.pop_context2()

        self._vnn_result = graph.rename(compound, s_name=self._s_name)

        graph.set_terminal(compound, self._sa_terminal)

        return self._vnn_result
