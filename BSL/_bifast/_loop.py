from BSL._bifast import _node as _ast_node, _call as _ast_call
from BSL import _type, _bifcmds

try:
    from maya import cmds
except:
    pass


class LoopParameter(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, s_name, s_type, default, b_iteration_target):
        type = _type.Type(s_type)

        if not type.is_array() and b_iteration_target:
            return False, "Not array type designated as iteration target"

        return True, cls(parser_node, s_name, s_type, default, b_iteration_target)

    def __init__(self, parser_node, s_name, s_type, default, b_iteration_target):
        super().__init__(parser_node)
        self._s_name = s_name
        self._type = _type.Type(s_type)
        self._default = default
        self._b_iteration_target = b_iteration_target

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = LoopParameter(self._parser_node, self._s_name, self._type.s, self._default.copy(d_map) if self._default else self._default, self._b_iteration_target)
        return d_map[self]

    def value(self):
        return self._default

    def value_type(self) -> _type.Type:
        return self._type

    def is_constant(self) -> bool:
        # not technically correct
        return False

    def is_iteration_target(self):
        return self._b_iteration_target

    def name(self):
        return self._s_name


class LoopResult(_ast_node.Node):
    def __init__(self, parser_node, s_name, s_type, b_iteration_target, s_state_port):
        super().__init__(parser_node)
        self._s_name = s_name
        self._type = _type.Type(s_type)
        self._b_iteration_target = b_iteration_target
        self._s_state_port = s_state_port

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = LoopResult(self._parser_node, self._s_name, self._type.s, self._b_iteration_target, self._s_state_port)
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def is_constant(self) -> bool:
        return False

    def name(self):
        return self._s_name

    def state(self):
        return self._s_state_port

    def is_iteration_target(self):
        return self._b_iteration_target


class LoopIndex(_ast_node.Node):
    def __init__(self, parser_node, s_name, value):
        super().__init__(parser_node)
        self._s_name = s_name
        self._value = value

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = LoopIndex(self._parser_node, self._s_name, self._value.copy(d_map))
        return d_map[self]

    def value_type(self) -> _type.Type:
        return _type.Type("long")

    def is_constant(self) -> bool:
        return False

    def name(self):
        return self._s_name

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        self._vnn_result = self._value.to_vnn(graph)
        return self._vnn_result


class _Loop(_ast_node.Node, _ast_call._MixinCall):
    def __init__(self, parser_node, parameters, results, code, max_iterations, current_index, sa_terminal):
        super().__init__(parser_node)
        self._parameters = parameters
        self._results = results
        self._code = code
        self._max_iterations = max_iterations
        self._current_index = current_index
        self._sa_terminal = sa_terminal
        self._d_outputs = {r.name(): r.value_type() for r in self._results}

    def copy(self, d_map):
        if self not in d_map:
            parameters = [p.copy(d_map) for p in self._parameters]
            results = [r.copy(d_map) for r in self._results]
            code = [s.copy(d_map) for s in self._code]
            mi = self._max_iterations.copy(d_map) if self._max_iterations else None
            ci = self._current_index.copy(d_map) if self._current_index else None
            d_map[self] = self.__class__(parser_node=self._parser_node, parameters=parameters, results=results, code=code, max_iterations=mi, current_index=ci, sa_terminal=self._sa_terminal[:])
        return d_map[self]

    def terminal(self):
        return self._sa_terminal

    def value_type(self) -> _type.Type:
        return _type.Type("__NODE", node_data=self.outputs())

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        node = graph.create_iterator_node(s_type=self.__class__.__name__[4:].lower())

        memory = _bifcmds.Memory()

        for parm in self._parameters:
            graph.add_out_port(node/"input", parm.name(), s_type=parm.value_type().s)
            if parm.is_iteration_target():
                memory.define(parm.name(), s_type=parm.value_type().s, value=node/"input"//parm.name())
                cmds.vnnCompound(graph._graph, node, setPortMetaDataValue=(parm.name(), "iterationTarget", "true"))
            else:
                memory.define(parm.name(), s_type=parm.value_type().s[6:-1], value=node/"input"//parm.name())

            if parm.value():
                graph.connect(parm.value().to_vnn(graph), node//parm.name())
            else:
                graph.connect(graph.get_memory().get(parm.name()), node//parm.name())

        for res in self._results:
            graph.add_in_port(node/"output", res.name(), s_type=res.value_type().s)
            memory.define_setonly(res.name(), s_type=res.value_type().s, target=node/"output"//res.name())

            if res.is_iteration_target() and not isinstance(self, LoopForEach):
                cmds.vnnCompound(graph._graph, node, setPortMetaDataValue=(res.name(), "iterationTarget", "true"))

            elif res.state():
                cmds.vnnCompound(graph._graph, node, setPortMetaDataValue=(res.name(), "statePort", res.state()))

        if self._max_iterations is not None:
            memory.define("max_iterations", s_type="long", value=node/"input"//"max_iterations")
            graph.connect(self._max_iterations.to_vnn(graph), node//"max_iterations")

        else:
            cmds.vnnCompound(graph._graph, node, deletePort="max_iterations")

        memory.define("#", s_type="long", value=node/"input"//"current_index")
        if self._current_index is not None:
            graph.connect(self._current_index.to_vnn(graph), node//"current_index")
            memory.define(self._current_index.name(), s_type="long", value=node/"input"//"current_index")

        graph.push_context2(node, memory)

        for statement in self._code:
            statement.to_vnn(graph)

        if hasattr(self, "_condition"):
            graph.connect(self._condition.to_vnn(graph), node/"output"//"looping_condition")

        graph.pop_context2()
        graph.set_terminal(node, self._sa_terminal)

        self._vnn_result = node
        return self._vnn_result


class LoopForEach(_Loop):
    pass


class LoopIterate(_Loop):
    pass


class LoopDoWhile(_Loop):
    @classmethod
    def create(cls, parser_node, parameters, results, code, condition, max_iterations, current_index, sa_terminal):
        sa_parms = [p.name() for p in parameters]
        for result in results:
            if result.state() and result.state() not in sa_parms:
                return False, f"Unknown state port: '{result.state()}'"

        return True, cls(parser_node, parameters, results, code, max_iterations, current_index, sa_terminal, condition)

    def __init__(self, parser_node, parameters, results, code, max_iterations, current_index, sa_terminal, condition=None):
        super().__init__(parser_node, parameters, results, code, max_iterations, current_index, sa_terminal)
        self._condition = condition

    def copy(self, d_map):
        if self not in d_map:
            super().copy(d_map)._condition = self._condition.copy(d_map)
        return d_map[self]
