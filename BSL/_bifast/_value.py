from BSL import _type, _bifcmds
from BSL._bifast import _node as _ast_node
from BSL._bifast import _memory as _static_memory

try:
    from maya import cmds
except:
    pass


class Value(_ast_node.Node):
    def __init__(self, parser_node, value, type_value):
        super().__init__(parser_node)
        self._value = value
        self._type = type_value if isinstance(type_value, _type.Type) else _type.Type(type_value)

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Value(self._parser_node, self._value, self._type.copy())
        return d_map[self]

    def value_type(self):
        return self._type

    def is_constant(self):
        return True

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        self._vnn_result = graph.create_const_value(value=self._value, s_type=self.value_type().s)
        return self._vnn_result


class Variable(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, s_name):
        if _static_memory.get_static_variable_type(s_name) is None:
            return False, f"Reference to undefined variable: '{s_name}'"

        return True, cls(parser_node, s_name)

    def __init__(self, parser_node, s_name, s_type=None):
        super().__init__(parser_node)
        self._s_name = s_name
        if s_type is None:
            self._type = _static_memory.get_static_variable_type(self._s_name)
        elif isinstance(s_type, _type.Type):
            self._type = s_type
        else:
            self._type = _type.Type(s_type)

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Variable(self._parser_node, self._s_name, self._type.copy())
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def set_value_type(self, type):
        self._type = type

    def name(self):
        return self._s_name

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        self._vnn_result = graph.get_memory().get(self.name())
        return self._vnn_result


class Vector(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, values, type_component):
        status, result = cls._get_type(values, type_component)
        if not status:
            return False, result
        return True, cls(parser_node, values, type_component, type_=result)

    def __init__(self, parser_node, values, type_component, type_):
        super().__init__(parser_node)
        self._values = values
        self._type_component = type_component
        self._type = type_

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Vector(self._parser_node, [v.copy(d_map) for v in self._values], self._type_component.copy(), self._type.copy())
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    @classmethod
    def _get_type(cls, values, type_component):
        array_dims = set()
        for value in values:
            type_base = value.value_type()

            if type_base.is_array():
                array_dims.add(value.value_type().array_dim())
                type_base = type_base.base_type()

            if type_base.is_vector() or type_base.is_matrix():
                return False, "Must be single value"

        if len(array_dims) > 1:
            return False, "Incompatible array dimensions"

        array_dim = list(array_dims)[0] if array_dims else 0

        s_prefix = array_dim * "array<"
        s_base = f"Math::{type_component}{len(values)}"
        s_suffix = array_dim * ">"

        return True, _type.Type(s_prefix + s_base + s_suffix)

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        node = graph.create_value_node(s_type=self.value_type().s)

        base_type = self.value_type().base_type().base_type().s
        if base_type in ["double", "float", "char", "short", "int", "long", "bool"]:
            s_cast = f"to_{base_type}"
        else:
            s_cast = f"to_unsigned_{base_type[1:]}"

        for value, s in zip(self._values, "xyzw"):
            s_value = value.to_vnn(graph)

            vt = value.value_type()
            if vt.is_node():
                s_value = s_value//list(vt.node_data())[0]
                vt = list(vt.node_data().values())[0]

            if vt != self.value_type().base_type():
                convert = graph.create_node(f"Core::Type_Conversion::{s_cast}")
                graph.connect(s_value, convert//"from")
                s_value = convert//s_cast[3:]

            graph.connect(s_value, node//f"value.{s}")

        self._vnn_result = node//"output"
        return self._vnn_result


class Matrix(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, cols, type_component):
        status, result = cls._get_type(cols, type_component)
        if not status:
            return False, result
        return True, cls(parser_node, cols, type_component, type_=result)

    def __init__(self, parser_node, cols, type_component, type_):
        super().__init__(parser_node)
        self._cols = cols
        self._type_component = type_component
        self._type = type_

    def copy(self, d_map):
        if self not in d_map:
            cols = [[v.copy(d_map) for v in row] for row in self._cols]
            d_map[self] = Vector(self._parser_node, cols, self._type_component.copy(), self._type.copy())
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    @classmethod
    def _get_type(cls, cols, type_component):
        array_dims = set()

        i_rows = 0
        i_cols = len(cols)

        for col in cols:
            # value connected to column
            if len(col) == 1:
                type_col = col[0].value_type()

                # is array?
                if type_col.is_array():
                    array_dims.add(type_col.array_dims())
                    type_col = type_col.base_type()

                if type_col.is_vector():
                    i_rows = max(i_rows, type_col.vector_dim())

                elif type_col.is_matrix():
                    return False, "Cant connect matrix to matrix column"

                elif not type_col.is_numeric():
                    return False, "Need to connect numeric value to column"

                continue

            i_rows = max(i_rows, len(col))
            for value in col:
                type_value = value.value_type()

                # is array?
                if type_value.is_array():
                    array_dims.add(type_value.array_dims())
                    type_value = type_value.base_type()

                if not type_value.is_numeric():
                    return False, "Need to connect numeric value to value"

        if len(array_dims) > 1:
            return False, "Array dimension missmatch"

        if i_rows == 0:
            return False, "Cant determine row count"

        array_dim = list(array_dims)[0] if array_dims else 0

        s_prefix = array_dim * "array<"
        s_base = f"Math::{type_component.s}{i_rows}x{i_cols}"
        s_suffix = array_dim * ">"
        return True, _type.Type(s_prefix + s_base + s_suffix)

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        # node = graph.create_const_matrix_value(self._cols, self.value_type().s)
        node = graph.create_value_node(s_type=self.value_type().s)

        base_type = self.value_type().base_type().base_type().s
        if base_type in ["double", "float", "char", "short", "int", "long", "bool"]:
            s_cast = f"to_{base_type}"
        else:
            s_cast = f"to_unsigned_{base_type[1:]}"

        for col, c in zip(self._cols, ["c0", "c1", "c2", "c3"]):
            if len(col) == 1:
                col = col[0]
                s_value = col.to_vnn(graph)

                vt = col.value_type()
                if vt.is_node():
                    s_value = s_value // list(vt.node_data())[0]
                    vt = list(vt.node_data().values())[0]

                if vt != self.value_type().base_type():
                    convert = graph.create_node(f"Core::Type_Conversion::{s_cast}")
                    graph.connect(s_value, convert//"from")
                    s_value = convert//s_cast[3:]

                graph.connect(s_value, node//f"value.{c}")
                continue

            for row, r in zip(col, "xyzw"):
                s_value = row.to_vnn(graph)

                vt = row.value_type()
                if vt.is_node():
                    s_value = s_value // list(vt.node_data())[0]
                    vt = list(vt.node_data().values())[0]

                if vt != self.value_type().base_type():
                    convert = graph.create_node(f"Core::Type_Conversion::{s_cast}")
                    graph.connect(s_value, convert//"from")
                    s_value = convert//s_cast[3:]

                graph.connect(s_value, node//f"value.{c}.{r}")

        self._vnn_result = node//"output"
        return self._vnn_result


class Array(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, values):
        types = [v.value_type() for v in values]

        for i in range(len(types)):
            if types[i].is_node() and len(types[i].node_data()) == 1:
                types[i] = list(types[i].node_data().values())[0]

        base_types = [t.base_type() if t.is_array() else t for t in types]
        ia_dims = list({t.array_dim() for t in types})

        sa_type_names = [t.s for t in types]
        if len(set(sa_type_names)) == 1:
            if sa_type_names[0].count(">") > 2:
                return False, "Arrays beyond 3 dimensions are not supported"

            if types[0].is_node():
                if len(types[0].node_data()) != 1:
                    return False, "NODE types cannot be put into arrays"

                types[0] = list(types[0].node_data().values())[0]

            return True, cls(parser_node, values, types[0])

        ba_is_array = [t.is_array() for t in types]
        if any(ba_is_array) and not all(ba_is_array):
            return False, "Mixed array and non-array types. This is not yet supported"

        if len(ia_dims) > 1:
            return False, "Mixed arrays of different dimensions. This is not yet supported"

        ba_numeric = [t.is_numeric() for t in base_types]

        if all(ba_numeric):
            s_prefix = ""
            s_base = ""
            s_suffix = ""
            ba_is_fraction = [t.is_fraction() for t in base_types]
            ba_is_big = [t.is_big() for t in types]
            if any(ba_is_fraction):
                s_base = "double" if any(ba_is_big) else "float"

            else:
                ba_unsigned = [t.is_unsigned() for t in base_types]
                ia_sizes = [t.numeric_size() for t in base_types]

                d_base_types = {1: "char", 2: "short", 4: "int", 8: "long"}

                # same integer base type
                if len(set(ia_sizes)) == 1:
                    s_base = d_base_types[ia_sizes[0]]

                    if any(ba_unsigned):
                        s_base = "u" + s_base

                # different integer base types
                else:
                    i_max_size = max(ia_sizes)
                    ba_max_unsigned = [t.is_unsigned() for t in types if t.numeric_size() == i_max_size]
                    s_base = d_base_types[i_max_size]
                    if any(ba_max_unsigned):
                        s_base = "u" + s_base

            ba_is_matrix = [t.is_matrix() for t in base_types]
            ba_is_vector = [t.is_vector() for t in base_types]

            if any(ba_is_matrix):
                iaa_matrix_dims = [t.matrix_dim() for t in base_types]
                ia_vector_dims = [t.vector_dim() for t in base_types]
                ia_row_counts = [ia[0] for ia in iaa_matrix_dims] + ia_vector_dims
                ia_col_counts = [ia[1] for ia in iaa_matrix_dims]
                i_rows = max(ia_row_counts)
                i_cols = max(ia_col_counts)
                s_prefix = f"Math::{s_prefix}"
                s_suffix = f"{i_rows}x{i_cols}"

            elif any(ba_is_vector):
                ia_vector_dims = [t.vector_dim() for t in base_types]
                s_prefix = f"Math::{s_prefix}"
                s_suffix = str(max(ia_vector_dims))

            s_prefix = ia_dims[0] * "array<" + s_prefix
            s_suffix += ia_dims[0] * ">"

            return True, cls(parser_node, values, _type.Type(s_prefix + s_base + s_suffix))

        if any(ba_numeric):
            return False, "Mixed numeric and non numeric values"

        return False, "Type missmatch"

    def __init__(self, parser_node, values, base_type):
        super().__init__(parser_node)
        self._values = values
        self._type_value = base_type

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Array(self._parser_node, [v.copy(d_map) for v in self._values], _type.Type(self._type_value.s))
        return d_map[self]

    def is_constant(self) -> bool:
        return all([v.is_constant() for v in self._values])

    def value_type(self) -> _type.Type:
        return _type.Type("array<" + self._type_value.s + ">")

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        # cant use the const array since we might need access to variables
        # return graph.create_const_array_value(self._values, self.value_type().s)

        # # single dimension, just dump it into a build_array()
        # if self.value_type().array_dim() == 1:
        #     node = graph.create_node("build_array")
        #     for i, value in enumerate(self._values):
        #         port = graph.add_in_port(node, f"index_{i}", s_type=self._type_value.s)
        #         graph.connect(value.to_vnn(graph), port)
        #
        #     return node
        # raise NotImplementedError

        sa_values = []
        for v in self._values:
            s = v.to_vnn(graph)
            if v.value_type().is_node():
                s = s//list(v.value_type().node_data())[0]
            sa_values.append(s)

        self._vnn_result = graph.create_array_value(values=sa_values, s_type=self.value_type().s)
        return self._vnn_result


class EmptyArray(_ast_node.Node):
    def __init__(self, parser_node, value_count, type_value):
        super().__init__(parser_node)
        self._value_count = value_count
        self._type_value = type_value if isinstance(type_value, _type.Type) else _type.Type(type_value)

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = EmptyArray(self._parser_node, self._value_count.copy(d_map), self._type_value.s)
        return d_map[self]

    def value_type(self) -> _type.Type:
        return _type.Type("array<" + self._type_value.s + ">")

    def is_constant(self) -> bool:
        return self._value_count.is_constant()

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph

        size = self._value_count.to_vnn(graph)
        if self._value_count.value_type().is_node():
            size = size//list(self._value_count.value_type().node_data())[0]

        self._vnn_result = graph.create_const_default_array_value(size=size, s_type=self.value_type().s)
        return self._vnn_result


class Object(_ast_node.Node):
    def __init__(self, parser_node, keys_and_values=None):
        super().__init__(parser_node)
        self._keys_and_values = keys_and_values or []

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Object(self._parser_node, [(k.copy(d_map), v.copy(d_map)) for k, v in self._keys_and_values])
        return d_map[self]

    def value_type(self) -> _type.Type:
        return _type.Type("Object")

    def is_constant(self) -> bool:
        for k, v in self._keys_and_values:
            if k.is_constant() and v.is_constant():
                continue
            return False
        return True

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph

        sa_keys = []
        sa_values = []
        for key, value in self._keys_and_values:
            s_temp_key = key.to_vnn(graph)
            if key.value_type().is_node():
                s_temp_key = s_temp_key//list(key.value_type().node_data().keys())[0]
            sa_keys.append(s_temp_key)

            s_temp_value = value.to_vnn(graph)
            if value.value_type().is_node():
                s_temp_value = s_temp_value//list(value.value_type().node_data().keys())[0]
            sa_values.append(s_temp_value)

        self._vnn_result = graph.create_object_value(sa_keys, sa_values)
        return self._vnn_result


class Enum(_ast_node.Node):
    def __init__(self, parser_node, s_value, s_type):
        super().__init__(parser_node)
        self._s_value = s_value
        self._type = _type.Type(s_type)

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Enum(self._parser_node, self._s_value, self._type.copy())
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        self._vnn_result = graph.create_const_enum_value(self._s_value, s_type=self._type.s)
        return self._vnn_result
