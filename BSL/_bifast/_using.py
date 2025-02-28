from BSL import _bifcmds
from BSL._bifast import _node as _ast_node

try:
    from maya import cmds
except:
    pass


class Using(_ast_node.Node):
    def __init__(self, parser_node, node):
        super().__init__(parser_node)
        self._node = node

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Using(self._parser_node, self._node.copy(d_map))
        return d_map[self]

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        memory = graph.get_memory()

        node = self._node.to_vnn(graph)

        for s_name, type_ in zip(self._node.output_names(), self._node.output_types()):
            if memory.is_defined(s_name):
                memory.set(s_name, value=node//s_name)
            elif memory.is_setonly(s_name):
                graph.connect(node//s_name, memory.get_setonly(s_name)[0])
            else:
                memory.define(s_name, type_.s, value=node // s_name)

        self._vnn_result = True
