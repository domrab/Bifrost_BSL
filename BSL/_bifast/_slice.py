from BSL import _type, _bifcmds
from BSL._bifast import _node as _ast_node

try:
    from maya import cmds
except:
    pass


class Slice(_ast_node.Node):
    def __init__(self, parser_node, start, stop, step):
        super().__init__(parser_node)
        self._start = start
        self._stop = stop
        self._step = step

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Slice(
                self._parser_node,
                None if self._start is None else self._start.copy(d_map),
                None if self._stop is None else self._stop.copy(d_map),
                None if self._step is None else self._step.copy(d_map)
            )
        return d_map[self]

    def value_type(self) -> _type.Type:
        return _type.Type("array<long>")

    def to_vnn(self, graph):
        graph = graph  # type: _bifcmds.Graph
        node = graph.create_slice_node()

        if self._start is None:
            graph.set_value(node, "start_is_none", True)
        else:
            graph.connect(self._start.to_vnn(graph), node//"start")

        if self._stop is None:
            graph.set_value(node, "stop_is_none", True)
        else:
            graph.connect(self._stop.to_vnn(graph), node//"stop")

        if self._step is None:
            graph.set_value(node, "step_is_none", True)
        else:
            graph.connect(self._step.to_vnn(graph), node//"step")

        return node