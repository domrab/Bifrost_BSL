from BSL._bifast import _node as _ast_node

try:
    from maya import cmds
except:
    pass


class OverloadType(_ast_node.Node):
    def __init__(self, parser_node, s_name, sa_types):
        super().__init__(parser_node)
        self._s_name = s_name
        self._sa_type = list(dict.fromkeys(sa_types))

    def name(self):
        return self._s_name

    def types(self):
        return self._sa_type
