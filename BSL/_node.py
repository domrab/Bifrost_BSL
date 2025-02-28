
class Node:
    def __init__(self, type, children=None, lineno=-1, start=-1, end=-1, filename="", text=""):
        self.type = type
        self.children = children
        self._children = {child.type: i for i, child in enumerate(children) if isinstance(child, Node)}
        self.lineno = lineno
        self.start = start
        self.end = end
        self.filename = filename
        self.text = text

    def __repr__(self):
        s = f"Node<{self.type}>{{\n    "

        for child in self.children:
            s += repr(child).replace("\n", "\n    ") + "\n    "

        s += "}"

        return s

    def __getitem__(self, item):
        return self.children[self._children[item]]


class NodeVisitor:
    # this is useful for a lot of small nodes
    # that have the same code like operators or
    # the integer and float types when converting
    # them to python types
    VISIT_MAP = {}

    def visit(self, node):
        # if we get a list, we return a list
        if isinstance(node, list):
            return [self.visit(n) for n in node]

        # string or None get returned as they are
        if isinstance(node, str) or node is None:
            return node

        # for nodes containing literals, return the text directly since
        # we cant define visit rules for them
        if node.type.startswith('"') and node.type.endswith('"'):
            return node.text

        # check if there is a v_* method. If not, check if the node
        # type is in the VISIT_MAP. If thats also a no, fall back to
        # the generic_visit().
        func = getattr(self, f"v_{node.type}", self.VISIT_MAP.get(f"{node.type}", self.generic_visit))
        return func(node)

    def generic_visit(self, node):
        return node.children[0] if node.type.isupper() else self.visit(node.children)
