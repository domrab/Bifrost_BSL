from BSL import _type, _bifcmds
from BSL._bifast import _node as _ast_node

try:
    from maya import cmds
except:
    pass


class BinOp(_ast_node.Node):
    def __init__(self, parser_node, lhs, rhs, op, type):
        super().__init__(parser_node)
        self.op = op
        self._lhs: _ast_node.Node = lhs
        self._rhs: _ast_node.Node = rhs
        self._type = type

    def copy(self, d_map):
        if self not in d_map:
             d_map[self] = self.__class__(self._parser_node, self._lhs.copy(d_map), self._rhs.copy(d_map), self.op, self._type.copy())
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def is_constant(self):
        return self._lhs.is_constant() and self._rhs.is_constant()

    @classmethod
    def resolve_value_type(cls, value):
        if isinstance(value, str):
            value = _type.Type(value)

        if isinstance(value, _type.Type):
            if value.is_node():
                if len(value.node_data()) == 1:
                    return True, list(value.node_data().values())[0]
                return False, f"Too many ports on node (names unknown): {[n for n in value.node_data()]}"
            return True, value
        if value.value_type().s == "__NODE":
            if hasattr(value, "output_types"):
                if len(value.output_types()) > 1:
                    return False, f"Too many ports on node: {value.output_names()}"
                elif len(value.output_types()) == 0:
                    return False, f"No output ports on node."
                return True, value.output_types()[0]
        return True, value.value_type()


class MathOp(BinOp):
    @classmethod
    def create(cls, parser_node, lhs, rhs, op):
        status, result = cls._get_type(lhs, rhs, op, b_support_string=True)
        if not status:
            return False, result

        return True, cls(parser_node, lhs, rhs, op, type=result)

    @classmethod
    def _get_type(cls, lhs, rhs, op, b_support_string=False):
        status, result = cls.resolve_value_type(lhs)
        if not status:
            return False, result
        type_lhs = result

        status, result = cls.resolve_value_type(rhs)
        if not status:
            return False, result
        type_rhs = result

        ia_array_dims = {i for i in (type_lhs.array_dim(), type_rhs.array_dim()) if i}
        if len(ia_array_dims) > 1:
            return False, "Array dimensions missmatch"

        i_dim = (list(ia_array_dims) + [0])[0]
        type_lhs_base = type_lhs.base_type() if type_lhs.is_array() else type_lhs
        type_rhs_base = type_rhs.base_type() if type_rhs.is_array() else type_rhs

        # todo: implement compounds int*string
        # # int * string
        # if op == "*" and type_lhs.is_integer() and type_rhs.is_string():
        #     return True, type_rhs
        if type_lhs_base.is_string() or type_rhs_base.is_string():
            if b_support_string and op == "+" and type_lhs_base.is_string() and type_rhs_base.is_string():
                # this could be implemented with a simple build_string node, but I believe
                # that would be counterintuitive:
                #     x + [-1, 0, 1] -> [x-1, x, x+1]
                # using the same logic for strings, we should get
                #     "s" + ["1", "2", "3"] -> ["s1", "s2", "s3"]
                # with a simple build_string, we would get "s123" though.
                # Instead, I'll create a compound with set string ports that will auto loop
                # and produce the array in question.

                return True, _type.Type(i_dim * "array<" + "string" + i_dim * ">")

        if type_lhs_base.is_field() or type_rhs_base.is_field():
            if not (type_lhs_base.is_field() and type_rhs_base.is_field()):
                return False, f"Operation '{op}' unsupported between '{type_lhs}' and '{type_rhs}'"
            if "VectorField" in type_lhs_base.s or "VectorField" in type_rhs_base.s:
                return True, _type.Type(i_dim * "array<" + "Core::Fields::VectorField" + i_dim * ">")
            return True, _type.Type(i_dim * "array<" + "Core::Fields::ScalarField" + i_dim * ">")

        # numeric +/- numeric
        if type_lhs.is_numeric() and type_rhs.is_numeric():
            return True, _type.get_numeric_base_type(type_lhs, type_rhs)

        # array +/- array
        if type_lhs.is_array() and type_rhs.is_array():
            if type_lhs.array_dim() != type_rhs.array_dim():
                return False, "Array dimensions missmatch"

            type_lhs_base = type_lhs.base_type()
            type_rhs_base = type_rhs.base_type()

            s_prefix = type_lhs.array_dim() * "array<"
            s_suffix = type_lhs.array_dim() * ">"
            s_base = _type.get_numeric_base_type(type_lhs_base, type_rhs_base).s

            return True, _type.Type(s_prefix + s_base + s_suffix)

        # array +/- numeric
        if (type_lhs.is_array() or type_rhs.is_array()) and (type_lhs.is_numeric() or type_rhs.is_numeric()):
            type_arr = type_lhs if type_lhs.is_array() else type_rhs
            type_num = type_rhs if type_lhs.is_array() else type_lhs
            type_arr_base = type_arr.base_type()

            s_prefix = type_arr.array_dim() * "array<"
            s_suffix = type_arr.array_dim() * ">"
            s_base = _type.get_numeric_base_type(type_num, type_arr_base).s

            return True, _type.Type(s_prefix + s_base + s_suffix)

        return False, f"Operation '{op}' not supported between '{type_lhs}' and '{type_rhs}'"

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph

        # strings get special treatment as there is no type promotion
        if self.value_type().is_string():
            sides_to_check = [self._lhs, self._rhs]
            values = []
            while len(sides_to_check) > 0:
                side = sides_to_check.pop(0)
                # the second part of this condition should always be true if the first is
                # if we made it this far
                if isinstance(side, self.__class__) and side.value_type().is_string():
                    sides_to_check = [side._lhs, side._rhs] + sides_to_check
                    continue

                values.append(side.to_vnn(graph))

            self._vnn_result = graph.n_build_string(*values)
            return self._vnn_result

        values = [self._lhs.to_vnn(graph), self._rhs.to_vnn(graph)]

        if self._lhs.value_type() == "__NODE":
            values[0] = values[0]//self._lhs.output_names()[0]

        if self._rhs.value_type() == "__NODE":
            values[1] = values[1]//self._rhs.output_names()[0]

        if self.op not in ["&&", "||", "^"]:
            if self._lhs.value_type().base_type().base_type() == "bool":
                convert = graph.create_node(f"Core::Type_Conversion::to_char")
                graph.connect(values[0], convert // "from")
                values[0] = convert//"char"

            if self._rhs.value_type().base_type().base_type() == "bool":
                convert = graph.create_node(f"Core::Type_Conversion::to_char")
                graph.connect(values[1], convert//"from")
                values[1] = convert//"char"

        if self.op == "+":
            self._vnn_result = graph.n_add(*values)
            return self._vnn_result

        elif self.op == "-":
            self._vnn_result = graph.n_subtract(*values)
            return self._vnn_result

        elif self.op == "*":
            self._vnn_result = graph.n_multiply(*values)
            return self._vnn_result

        elif self.op == "/":
            self._vnn_result = graph.n_divide(*values)
            return self._vnn_result

        elif self.op == "%":
            self._vnn_result = graph.n_modulo(values[0], values[1])
            return self._vnn_result

        elif self.op == "**":
            self._vnn_result = graph.n_power(values[0], values[1])
            return self._vnn_result

        elif self.op == "==":
            self._vnn_result = graph.n_equal(values[0], values[1])
            return self._vnn_result

        elif self.op == "!=":
            self._vnn_result = graph.n_not_equal(values[0], values[1])
            return self._vnn_result

        elif self.op == ">=":
            self._vnn_result = graph.n_greater_or_equal(values[0], values[1])
            return self._vnn_result

        elif self.op == "<=":
            self._vnn_result = graph.n_less_or_equal(values[0], values[1])
            return self._vnn_result

        elif self.op == ">":
            self._vnn_result = graph.n_greater(values[0], values[1])
            return self._vnn_result

        elif self.op == "<":
            self._vnn_result = graph.n_less(values[0], values[1])
            return self._vnn_result

        elif self.op == "&&":
            self._vnn_result = graph.n_and(values[0], values[1])
            return self._vnn_result

        elif self.op == "||":
            self._vnn_result = graph.n_or(values[0], values[1])
            return self._vnn_result

        elif self.op == "^":
            self._vnn_result = graph.n_xor(values[0], values[1])
            return self._vnn_result

        raise NotImplementedError(self.op)


class Pow(MathOp):
    pass


class Compare(_ast_node.Node):
    @classmethod
    def create(cls, parser_node, pairs):
        results = []
        for pair in pairs:
            status, result = cls._get_type(pair[0], pair[1], pair[2])
            if not status:
                return False, result
            results.append(result)

        while len(results) > 1:
            lhs = results.pop(0)
            rhs = results.pop(0)
            status, result = Logic._get_type(lhs, rhs, "&&")
            if not status:
                return False, result
            results.insert(0, result)

        return True, cls(parser_node, pairs, type=results[0])

    def __init__(self, parser_node, pairs, type):
        super().__init__(parser_node)
        self._pairs = pairs
        self._type = type

    def copy(self, d_map):
        if self not in d_map:
            d = {}
            pairs = []

            for a, b, op in self._pairs:
                if id(a) not in d:
                    d[id(a)] = a.copy(d_map)

                if id(b) not in d:
                    d[id(b)] = b.copy(d_map)

                pairs.append((d[id(a)], d[id(b)], op))

            d_map[self] = Compare(self._parser_node, pairs, self._type.copy())

        return d_map[self]

    def is_constant(self) -> bool:
        return all([p[0].is_constant() and p[1].is_constant() for p in self._pairs])

    def value_type(self) -> _type.Type:
        return self._type

    @classmethod
    def _get_type(cls, lhs, rhs, op):
        status, result = MathOp.resolve_value_type(lhs)
        if not status:
            return False, result

        type_lhs_value = result

        status, result = MathOp.resolve_value_type(rhs)
        if not status:
            return False, result

        type_rhs_value = result

        s_prefix, s_suffix = "", ""
        if type_lhs_value.is_array() or type_rhs_value.is_array():
            i_dim_lhs = type_lhs_value.array_dim()
            i_dim_rhs = type_rhs_value.array_dim()
            s_prefix = max(i_dim_lhs, i_dim_rhs) * "array<"
            s_suffix = max(i_dim_lhs, i_dim_rhs) * ">"

        type_lhs_base = type_lhs_value.base_type() if type_lhs_value.is_array() else type_lhs_value
        type_rhs_base = type_rhs_value.base_type() if type_rhs_value.is_array() else type_rhs_value

        if op not in ["==", "!="]:
            if type_lhs_base.is_matrix() or type_lhs_base.is_vector() or type_rhs_base.is_matrix() or type_rhs_base.is_vector():
                return False, f"Comparing vectors/matrices with '{op}' not yet supported"

        if not ((type_lhs_base.is_numeric() and type_rhs_base.is_numeric()) or (type_lhs_base.is_string() and type_rhs_base.is_string())):
            return False, f"Operation '{op}' not supported between '{type_lhs_value}' and '{type_rhs_value}'"

        type_lhs_base = type_lhs_base.base_type()
        type_rhs_base = type_rhs_base.base_type()
        if type_lhs_base.is_numeric() != type_rhs_base.is_numeric():
            return False, f"Cannot compare numeric with non numeric values '{type_lhs_value}' {op} '{type_rhs_value}'"

        if not type_lhs_base.is_numeric() and (type_lhs_base != type_rhs_base):
            return False, f"Cannot compare non numeric types '{type_lhs_value}' {op} '{type_rhs_value}'"

        # todo: this needs much more work to account for the difference in
        #   equal/not_equal and greater/less, etc
        #   Adding this for now so I can move forward
        #   May be able to use the overlord here
        return True, _type.Type(s_prefix + "bool" + s_suffix)

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        results = []
        for pair in self._pairs:
            lhs = pair[0].to_vnn(graph)
            rhs = pair[1].to_vnn(graph)

            if pair[0].value_type().is_node():
                lhs = lhs//pair[0].output_names()[0]

            if pair[1].value_type().is_node():
                rhs = rhs//pair[1].output_names()[0]

            if pair[2] == "==":
                results.append(graph.n_equal(lhs, rhs))
            elif pair[2] == "!=":
                results.append(graph.n_not_equal(lhs, rhs))
            elif pair[2] == ">=":
                results.append(graph.n_greater_or_equal(lhs, rhs))
            elif pair[2] == "<=":
                results.append(graph.n_less_or_equal(lhs, rhs))
            elif pair[2] == ">":
                results.append(graph.n_greater(lhs, rhs))
            elif pair[2] == "<":
                results.append(graph.n_less(lhs, rhs))
            else:
                raise NotImplementedError

        while len(results) > 1:
            lhs = results.pop(0)
            rhs = results.pop(0)
            results.insert(0, graph.n_and(lhs, rhs))

        self._vnn_result = results[0]
        return self._vnn_result


class Logic(MathOp):
    @classmethod
    def _get_type(cls, lhs, rhs, op, **kwargs):
        type_lhs = lhs
        if not isinstance(type_lhs, _type.Type):
            status, result = cls.resolve_value_type(lhs)
            if not status:
                return False, result
            type_lhs = result

        type_rhs = rhs
        if not isinstance(type_rhs, _type.Type):
            status, result = cls.resolve_value_type(rhs)
            if not status:
                return False, result
            type_rhs = result

        # outputs = Overlord.resolve_outputs("Core::Logic::and", sa_input_types=[type_lhs, type_rhs])
        # print("outputs", outputs)
        # raise Exception

        # check array dims
        array_dims = {t.array_dim() for t in [type_rhs, type_rhs] if t.is_array()}
        if len(array_dims) > 1:
            return False, "Array dimensions missmatch"

        type_lhs = type_lhs.base_type() if type_lhs.is_array() else type_lhs
        type_rhs = type_rhs.base_type() if type_rhs.is_array() else type_rhs
        type_lhs_base = type_lhs.base_type()
        type_rhs_base = type_rhs.base_type()

        if not (type_lhs_base.is_bool() and type_rhs_base.is_bool()):
            return False, f"Operation '{op}' not supported between '{type_lhs}' and '{type_rhs}'"

        i_arr_dim = (list(array_dims) + [0])[0]
        i_mtx_dim = [-1, -1]
        if type_lhs.is_vector():
            i_mtx_dim[0] = max(i_mtx_dim[0], type_lhs.vector_dim())

        if type_lhs.is_matrix():
            i_mtx_dim[0] = max(i_mtx_dim[0], type_lhs.matrix_dim()[0])
            i_mtx_dim[1] = max(i_mtx_dim[1], type_lhs.matrix_dim()[1])

        if type_rhs.is_vector():
            i_mtx_dim[0] = max(i_mtx_dim[0], type_rhs.vector_dim())

        if type_lhs.is_matrix():
            i_mtx_dim[0] = max(i_mtx_dim[0], type_rhs.matrix_dim()[0])
            i_mtx_dim[1] = max(i_mtx_dim[1], type_rhs.matrix_dim()[1])

        s_prefix = i_arr_dim * "array<"
        s_suffix = i_arr_dim * ">"

        if i_mtx_dim[0] != -1 and i_mtx_dim[1] != -1:
            s_prefix += "Math::"
            s_suffix = str(i_mtx_dim[0]) + (f"x{i_mtx_dim[1]}" if i_mtx_dim[1] != -1 else "") + s_suffix

        return True, _type.Type(s_prefix + "bool" + s_suffix)
