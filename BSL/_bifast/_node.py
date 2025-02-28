from BSL import _type


class Node:
    def __init__(self, parser_node):
        self._parser_node = parser_node
        self._vnn_result = None
        self._json_result = None
        self._xml_result = None

    def copy(self, d_map):
        raise NotImplementedError(self.__class__.__name__)

    def to_json(self):
        raise NotImplementedError(self.__class__.__name__)

    def to_xml(self):
        raise NotImplementedError(self.__class__.__name__)

    def to_vnn(self, graph):
        raise NotImplementedError(self.__class__.__name__)

    def is_constant(self) -> bool:
        raise NotImplementedError(self.__class__.__name__)

    def value_type(self) -> _type.Type:
        raise NotImplementedError(self.__class__.__name__)

    @classmethod
    def create(cls, *args, **kwargs):
        raise NotImplementedError(cls.__class__.__name__)
