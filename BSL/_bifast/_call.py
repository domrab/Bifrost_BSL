from BSL._bifast import _node as _ast_node, _binOp as _ast_binOp, _value as _ast_value
from BSL import _type, _error, _bifcmds, _file_io, _constants, _bifres, _bifast
from BSL._overlord import Overlord
import json

try:
    from maya import cmds
except:
    pass


class Argument(_ast_node.Node):
    def __init__(self, parser_node, s_name, value):
        super().__init__(parser_node)
        if isinstance(value, str):
            value = _ast_value.Value(parser_node, None, _type.Type(value))
        self._value = value
        self._type = value.value_type()
        self._s_name = s_name

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = Argument(self._parser_node, self._s_name, self._value.copy(d_map))
        return d_map[self]

    def value_type(self) -> _type.Type:
        return self._type

    def is_constant(self) -> bool:
        return self._value.is_constant()

    def name(self):
        return self._s_name

    def to_vnn(self, graph):
        return self._value.to_vnn(graph)


class _MixinCall:
    _d_outputs = {}

    def output_count(self):
        return len(self._d_outputs)

    def output_types(self):
        return list(self._d_outputs.values())

    def output_names(self):
        return list(self._d_outputs)

    def outputs(self):
        return self._d_outputs


class CallAssociative(_ast_node.Node, _MixinCall):
    @classmethod
    def create(cls, parser_node, s_name, args, kwargs, sa_terminal):
        status, result = cls._get_type(s_name, [arg for arg in (args + kwargs)])
        if not status:
            return False, result

        return True, cls(parser_node, s_name, args, kwargs, sa_terminal, output=result)

    def __init__(self, parser_node, s_name, args, kwargs, sa_terminal, output):
        super().__init__(parser_node)
        self._sa_terminal = sa_terminal or []
        self._s_name = s_name
        self._values = []
        self._names = []
        self._args = args
        self._kwargs = kwargs
        for i, arg in enumerate(args + kwargs):
            self._names.append(f"item{i}" + (f"_{arg.name()}" if arg.name() else ""))
            self._values.append(arg)

        sa_input_names, sa_output_names = Overlord.get_port_names(s_name)
        self._d_outputs = {sa_output_names[0]: output}  # self._get_type(self._s_name, self._values)[1]}

    def copy(self, d_map):
        if self not in d_map:
            d_map[self] = CallAssociative(self._parser_node, self._s_name, [a.copy(d_map) for a in self._args], [kw.copy(d_map) for kw in self._kwargs], self._sa_terminal[:], self.output_types()[0].copy())
        return d_map[self]

    def is_constant(self) -> bool:
        return all([arg.is_consant() for arg in self._values])

    def value_type(self) -> _type.Type:
        return _type.Type("__NODE", node_data=self.outputs())

    @classmethod
    def _get_type(cls, s_name, values):
        arg_types = [arg.value_type() for arg in values]

        if s_name.endswith("::build_array"):
            arg_types = [t.base_type() if t.is_array() else t for t in arg_types]

            for i in range(len(arg_types)):
                if arg_types[i].is_node() and len(arg_types[i].node_data()) == 1:
                    arg_types[i] = list(arg_types[i].node_data().values())[0]

            ba_numeric = [t.is_numeric() for t in arg_types]
            ba_field = [t.is_field() for t in arg_types]
            sa_types = [t.s for t in arg_types]
            b_all_same = len(set(sa_types)) == 1

            if any(ba_numeric) and (not all(ba_numeric)):
                return False, f"Cant build array with mixed types: {sa_types}"

            elif any(ba_field) and (not all(ba_field)):
                return False, f"Cant build array with mixed types: {sa_types}"

            elif (not any(ba_numeric) and not any(ba_field)) and len(set(sa_types)) > 1:
                return False, f"Cant build array with mixed types: {sa_types}"

            if not b_all_same:
                if all(ba_numeric):
                    while len(arg_types) > 1:
                        first = arg_types.pop(0)
                        second = arg_types.pop(0)
                        arg_types.insert(0, _type.get_numeric_base_type(first, second))

                elif all(ba_field):
                    _VF = "Core::Fields::VectorField"
                    _SF = "Core::Fields::ScalarField"
                    while len(arg_types) > 1:
                        first = arg_types.pop(0)
                        second = arg_types.pop(0)
                        arg_types.insert(0, _VF if first == _VF or second.s == _VF else _SF)

            return True, _type.Type(f"array<{arg_types[0].s}>")

        set_array_dims = set()
        for i, t in enumerate(arg_types):
            if t.is_array():
                set_array_dims.add(t.array_dim())
                arg_types[i] = t.base_type()

            if t.is_node():
                if len(t.node_data()) == 1:
                    arg_types[i] = list(t.node_data().values())[0]

        ba_numeric = [t.is_numeric() for t in arg_types]
        ba_field = [t.is_field() for t in arg_types]

        if not (all(ba_numeric) or all(ba_field)):
            return False, "All arguments must be fields or numeric."

        if len(set_array_dims) > 1:
            return False, "Differing array dimensions found"

        if s_name.endswith("::matrix_multiply"):
            if any(ba_field):
                return False, "Cant use fields in matrix_multiply"

            iaa_matrix_dims = []
            for t in arg_types:
                if t.is_matrix():
                    iaa_matrix_dims.append(t.matrix_dim())
                elif t.is_vector():
                    iaa_matrix_dims.append((t.vector_dim(), -1))
                else:
                    iaa_matrix_dims.append((-1, -1))

            while len(iaa_matrix_dims) > 1:
                ia_lhs = iaa_matrix_dims.pop(0)
                ia_rhs = iaa_matrix_dims.pop(0)
                if ia_lhs[1] == -1:
                    ia_lhs = (2, 2)

                if ia_lhs[1] != ia_rhs[0]:
                    if ia_lhs[0] == -1:
                        ia_lhs = (2, ia_lhs[1])

                    if ia_rhs[0] < ia_lhs[1]:
                        ia_rhs = (ia_lhs[1], ia_rhs[1])

                    else:
                        ia_lhs = (ia_lhs[0], ia_rhs[1])

                iaa_matrix_dims.insert(0, (ia_lhs[0], ia_rhs[1]))

            rows, cols = iaa_matrix_dims[0]

            base_types = [t.base_type() for t in arg_types]

            while len(base_types) > 1:
                lhs = base_types.pop(0)
                rhs = base_types.pop(0)
                base_types.insert(0, _ast_binOp.MathOp._get_type(lhs, rhs, "-")[1])

            s_type = f"Math::{base_types[0].s}{rows}" + (f"x{cols}" if cols > 1 else "")
            arr_dim = (list(set_array_dims) + [0])[0]
            return True, _type.Type(arr_dim * "array<" + s_type + arr_dim * ">")

        # I believe all others (min, max, add, subtract, multiply, divide)
        # follow the rules established in the binOps
        while len(arg_types) > 1:
            first = arg_types.pop(0)
            second = arg_types.pop(0)
            arg_types.insert(0, _ast_binOp.MathOp._get_type(first, second, "*")[1])

        i_arr_dim = (list(set_array_dims) + [0])[0]
        s_prefix = i_arr_dim * "array<"
        s_suffix = i_arr_dim * ">"
        return True, _type.Type(s_prefix + arg_types[0].s + s_suffix)

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        node = graph.create_node(s_type=self._s_name)

        for s_name, arg in zip(self._names, self._values):
            value = arg.to_vnn(graph)

            # todo: node expansion (to for others too)
            value_type = arg.value_type()
            if value_type.is_node():
                # value = value//arg._value.output_names()[0]
                # value_type = arg._value.output_types()[0]
                s_port = list(value_type.node_data())[0]
                value = value//s_port
                value_type = value_type.node_data()[s_port]

            # todo: test bool promotion
            result_value_type = list(self._d_outputs.values())[0]
            if value_type.base_type().base_type() == "bool" and result_value_type.base_type().base_type() != "bool":
                value = graph.n_to_char(value)

            graph.connect(value, graph.add_in_port(node, s_name))

        self._vnn_result = node
        return self._vnn_result


def _validate_arguments(sa_input_names, input_types, args, kwargs):
    if len(input_types) < len(args) + len(kwargs):
        return False, (_error.Error, "Too many arguments")

    parm_types = len(sa_input_names) * [None]
    sa_arg_names = []
    for i, (arg, s_key) in enumerate(zip(args, sa_input_names)):
        sa_arg_names.append(s_key)
        input_types[i] = arg.value_type()
        parm_types[i] = arg.value_type()

    for kwarg in kwargs:
        if kwarg.name() in sa_arg_names:
            return False, (_error.BfNameError, f"Multiple values found for argument: '{kwarg.name()}'")

        if kwarg.name() not in sa_input_names:
            return False, (_error.BfNameError, f"Unknown port name: '{kwarg.name()}'. Use one of: {sa_input_names}")

        input_types[sa_input_names.index(kwarg.name())] = kwarg.value_type()
        parm_types[sa_input_names.index(kwarg.name())] = kwarg.value_type()

    return True, (input_types, [t for t in parm_types])


class CallNative(_ast_node.Node, _MixinCall):
    @classmethod
    def create(cls, parser_node, s_name, args, kwargs, sa_terminal):
        saa_input_types, saa_output_types = Overlord.get_all_port_types(s_name)
        # sa_input_types, sa_output_types = Overlord.get_port_types(s_name)
        sa_input_names, sa_output_names = Overlord.get_port_names(s_name)

        status, result = None, None
        for sa_input_types, sa_output_types in zip(saa_input_types, saa_output_types):
            input_types = [_type.Type(s) for s in sa_input_types if s]
            # validate args and kwargs
            status, result = _validate_arguments(sa_input_names, input_types, args, kwargs)
            if status:
                break
        else:
            return False, result

        sa_input_types = result[0]
        parm_types = result[1]

        # for i in range(len(parm_types)):
        #     parm_types[i] = parm_types[i] or input_types[i]

        # resolve port types
        status, result = Overlord.resolve_inputs_and_outputs(s_name, input_types)
        if not status:
            return False, result

        return True, cls(parser_node, s_name, args, kwargs, sa_terminal,
                         parm_types=parm_types, sa_input_types=result[0], sa_output_types=result[1])


    def __init__(self, parser_node, s_name, args, kwargs, sa_terminal,
                 parm_types, sa_input_types, sa_output_types):
        super().__init__(parser_node)
        self._sa_terminal = sa_terminal or []
        self._s_name = s_name
        self._args = args
        # sa_input_types, sa_output_types = Overlord.get_port_types(s_name)
        sa_input_names, sa_output_names = Overlord.get_port_names(s_name)
        self._kwargs = sorted(kwargs, key=lambda arg: sa_input_names.index(arg.name()))
        self._sa_output_types = sa_output_types
        self._input_types = [_type.Type(s) for s in sa_input_types]
        self._parm_types = [t.copy() for t in parm_types if t]
        self._arg_types = [arg.value_type() for arg in self._args + self._kwargs]

        self._d_outputs = {k: _type.Type(v) for k, v in zip(sa_output_names, sa_output_types)}

    def copy(self, d_map):
        if self not in d_map:
            args = [a.copy(d_map) for a in self._args]
            kwargs = [kw.copy(d_map) for kw in self._kwargs]
            it = [t.copy() for t in self._input_types]
            pt = [(t.copy() if t else t) for t in self._parm_types]
            d_map[self] = CallNative(self._parser_node, self._s_name, args, kwargs, self._sa_terminal[:], pt, it, self._sa_output_types[:])
        return d_map[self]

    def is_constant(self) -> bool:
        return all([arg.is_consant() for arg in self._args + self._kwargs])

    def value_type(self) -> _type.Type:
        return _type.Type("__NODE", node_data=self.outputs())

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        node = graph.create_node(s_type=self._s_name)

        # todo: disable all fan-in ports

        if self._s_name == "build_string" or self._s_name.endswith("::build_string"):
            cmds.vnnPort(graph._graph, f"{node}.strings", 0, 1, clear=2)

        elif self._s_name == "terminal" or self._s_name.endswith("::terminal"):
            cmds.vnnPort(graph._graph, f"{node}.final", 0, 1, clear=2)
            cmds.vnnPort(graph._graph, f"{node}.proxy", 0, 1, clear=2)
            cmds.vnnPort(graph._graph, f"{node}.diagnostic", 0, 1, clear=2)

        sa_input_names, sa_output_names = Overlord.get_port_names(self._s_name)

        sa_arg_names = []
        sa_values = len(sa_input_names) * [None]
        for i, (arg, s_key) in enumerate(zip(self._args, sa_input_names)):
            sa_arg_names.append(s_key)

            value = arg.to_vnn(graph)

            value_type = arg.value_type()
            if value_type.is_node():
                s_port = list(value_type.node_data())[0]
                value = value//s_port
                value_type = value_type.node_data()[s_port]
                # value = value//arg._value.output_names()[0]
                # value_type = arg._value.output_types()[0]

            # todo: test bool promotion
            if value_type.base_type().base_type() == "bool" and self._input_types[i].base_type().base_type() != "bool":
                value = graph.n_to_char(value)

            sa_values[i] = value

        for kwarg in self._kwargs:
            value = kwarg.to_vnn(graph)

            value_type = kwarg.value_type()
            if value_type.is_node():
                s_port = list(value_type.node_data())[0]
                value = value//s_port
                value_type = value_type.node_data()[s_port]
                # value = value//kwarg._value.output_names()[0]
                # value_type = kwarg._value.output_types()[0]

            # todo: test bool promotion
            if value_type.base_type().base_type() == "bool" and self._input_types[sa_input_names.index(kwarg.name())].base_type().base_type() != "bool":
                value = graph.n_to_char(value)

            sa_values[sa_input_names.index(kwarg.name())] = value

        for s_port, value in zip(sa_input_names, sa_values):
            if value is None:
                continue
            graph.connect(value, node//s_port)

        graph.set_terminal(node, self._sa_terminal)

        self._vnn_result = node
        return self._vnn_result


class CallScope(_ast_node.Node, _MixinCall):
    @classmethod
    def create(cls, parser_node, s_name, scope, args, kwargs, sa_terminal, x_compat):
        d_overloads = scope["overloads"]
        scope = scope["scope"]

        sa_input_names = [arg.name() for arg in scope.parameters()]
        # input_types = [arg.value_type() for arg in scope.parameters()]

        # set_input_names = set(sa_input_names)
        # set_kwarg_names = {arg.name() for arg in kwargs}
        # if set_kwarg_names - set_input_names:
        #     return False,
        result_ = None
        error_ = None
        for sa_input_types, output_types in d_overloads.items():
            input_types = [_type.Type(s) for s in sa_input_types]

            _it_copy = input_types.copy()
            status, result = _validate_arguments(sa_input_names, _it_copy, args, kwargs)
            if not status:
                result_ = result
                continue
                # return False, result

            _, parm_types = result
            try:
                for n, pt, it in zip(sa_input_names, parm_types, input_types):
                    if pt is None:
                        continue
                    if pt.is_node() and len(pt.node_data()) == 1:
                        pt = list(pt.node_data().values())[0]
                    # print(pt, it, n)
                    _ = x_compat(pt.copy(), it.copy(), n)
                kwargs = sorted(kwargs, key=lambda arg: sa_input_names.index(arg.name()))
                # todo: output types is wrong on overloaded function
                return True, cls(parser_node, s_name, scope, args, kwargs, sa_terminal, input_types, parm_types, sa_output_types=[t.s for t in output_types])
            except Exception as e:
                error_ = e
                continue

        if error_:
            raise error_

        return False, result_

    def __init__(self, parser_node, s_name, scope, args, kwargs, sa_terminal, input_types, parm_types, sa_output_types):
        super().__init__(parser_node)
        self._sa_terminal = sa_terminal or []
        self._s_name = s_name
        self._args = args
        self._kwargs = kwargs
        self._scope = scope

        sa_output_names = [s for s in scope.output_names()]
        # sa_output_types = [t.s for t in scope.output_types()]

        # self._input_types = [arg.value_type() for arg in scope.parameters()]
        self._input_types = input_types#[_type.Type(t.s) for t in input_types]
        self._parm_types = [t for t in parm_types if t]
        self._arg_types = [arg.value_type() for arg in args + kwargs]

        self._d_outputs = {k: _type.Type(v) for k, v in zip(sa_output_names, sa_output_types)}

    def copy(self, d_map):
        if self not in d_map:
            args = [a.copy(d_map) for a in self._args]
            kwargs = [kw.copy(d_map) for kw in self._kwargs]
            it = [t.copy() for t in self._input_types]
            pt = [t.copy() for t in self._parm_types]
            # not sure if I actually need to copy the scope or not but shouldnt hurt
            d_map[self] = CallScope(self._parser_node, self._s_name, self._scope.copy(d_map), args, kwargs, self._sa_terminal[:], it, pt, self.output_types())
        return d_map[self]

    def value_type(self) -> _type.Type:
        return _type.Type("__NODE", node_data=self.outputs())

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result
        # print(f"CallScope: {self._s_name}")

        graph = graph  # type: _bifcmds.Graph

        # node = self._scope.copy().to_vnn(graph)
        node = self._scope.to_vnn(graph)

        sa_input_names = [arg.name() for arg in self._scope.parameters()]

        sa_values = len(sa_input_names) * [None]
        for i, (arg, s_key) in enumerate(zip(self._args, sa_input_names)):
            value = arg.to_vnn(graph)

            value_type = arg.value_type()
            if value_type.is_node():
                # value = value//arg._value.output_names()[0]
                # value_type = arg._value.output_types()[0]
                s_port = list(value_type.node_data())[0]
                value = value//s_port
                value_type = value_type.node_data()[s_port]

            # todo: test bool promotion
            if value_type.base_type().base_type() == "bool" and self._input_types[i].base_type().base_type() != "bool":
                value = graph.n_to_char(value)

            sa_values[i] = value

        for kwarg in self._kwargs:
            value = kwarg.to_vnn(graph)

            value_type = kwarg.value_type()
            if value_type.is_node():
                # value = value//kwarg._value.output_names()[0]
                # value_type = kwarg._value.output_types()[0]
                s_port = list(value_type.node_data())[0]
                value = value//s_port
                value_type = value_type.node_data()[s_port]

            # todo: test bool promotion
            if value_type.base_type().base_type() == "bool" and self._input_types[sa_input_names.index(kwarg.name())].base_type().base_type() != "bool":
                value = graph.n_to_char(value)

            sa_values[sa_input_names.index(kwarg.name())] = value

        for s_port, value in zip(sa_input_names, sa_values):
            if value is None:
                continue
            graph.connect(value, node//s_port)

        self._vnn_result = graph.rename(node, f"call: '{self._s_name}'")
        if self._vnn_result is None:
            raise Exception

        graph.set_terminal(self._vnn_result, self._sa_terminal)

        return self._vnn_result


class CallType(_ast_node.Node, _MixinCall):
    def __init__(self, parser_node, s_name, args, kwargs, x_compat):
        super().__init__(parser_node)
        self._s_name = s_name
        self._args = args
        self._kwargs = kwargs
        self._x_compat = x_compat

        self._d_type_data = _bifres.TYPES[self._s_name]
        sa_port_names = [s for s in list(self._d_type_data.keys()) if "." not in s]

        values = len(sa_port_names) * [None]
        for i, (arg, s_key) in enumerate(zip(self._args, sa_port_names)):
            values[i] = arg

        for kwarg in self._kwargs:
            # print(s_name, kwarg.name(), sa_port_names)
            values[sa_port_names.index(kwarg.name())] = kwarg

        for s_port, value in zip(sa_port_names, values):
            if value is None:
                continue

            # todo: permit lossy conversion
            x_compat(v=value.value_type(), t=_type.Type(self._d_type_data[s_port]))

    def copy(self, d_map):
        if self not in d_map:
            args = [a.copy(d_map) for a in self._args]
            kwargs = [kw.copy(d_map) for kw in self._kwargs]
            d_map[self] = CallType(self._parser_node, self._s_name, args, kwargs, self._x_compat)
        return d_map[self]

    def value_type(self) -> _type.Type:
        return _type.Type(self._s_name)

    def to_vnn(self, graph):
        if self._vnn_result:
            return self._vnn_result

        graph = graph  # type: _bifcmds.Graph
        node = graph.create_value_node(s_type=self.value_type().s)

        sa_input_names = list(self._d_type_data.keys())
        port_types = [_type.Type(s) for s in list(self._d_type_data.values())]

        sa_values = len(sa_input_names) * [None]
        for i, (arg, s_key) in enumerate(zip(self._args, sa_input_names)):
            value = arg.to_vnn(graph)

            # todo: node expansion (to for others too)
            value_type = arg.value_type()
            if value_type.is_node():
                # value = value//arg._value.output_names()[0]
                # value_type = arg._value.output_types()[0]
                s_port = list(value_type.node_data())[0]
                value = value//s_port
                value_type = value_type.node_data()[s_port]

            # todo: test bool promotion
            if value_type.base_type().base_type() == "bool" and port_types[i].base_type().base_type() != "bool":
                value = graph.n_to_char(value)

            sa_values[i] = value

        for kwarg in self._kwargs:
            value = kwarg.to_vnn(graph)

            # todo: node expansion (to for others too)
            value_type = kwarg.value_type()
            if value_type.is_node():
                # value = value//kwarg._value.output_names()[0]
                # value_type = kwarg._value.output_types()[0]
                s_port = list(value_type.node_data())[0]
                value = value//s_port
                value_type = value_type.node_data()[s_port]

            # todo: test bool promotion
            if value_type.base_type().base_type() == "bool" and port_types[sa_input_names.index(kwarg.name())].base_type().base_type() != "bool":
                value = graph.n_to_char(value)

            sa_values[sa_input_names.index(kwarg.name())] = value

        for s_port, value in zip(sa_input_names, sa_values):
            if value is None:
                continue

            graph.connect(value, node//f"value.{s_port}")

        self._vnn_result = node//"output"
        return self._vnn_result
