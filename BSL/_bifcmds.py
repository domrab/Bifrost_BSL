import time

from maya import cmds

from BSL import _error
from BSL import _file_io
from BSL import _bifres


TYPES = _file_io.get_type_dict()
ENUMS = _bifres.ENUMS
NODES = _bifres.NODES


class NodeType:
    kCompound = "BifrostGraph,Core::Graph,compound"  # xml: AminoVnn_Compound

    kAdd = "BifrostGraph,Core::Math,add"
    kSubtract = "BifrostGraph,Core::Math,subtract"
    kMultiply = "BifrostGraph,Core::Math,multiply"
    kDivide = "BifrostGraph,Core::Math,divide"
    kPower = "BifrostGraph,Core::Math,power"

    kAnd = "BifrostGraph,Core::Logic,and"
    kOr = "BifrostGraph,Core::Logic,or"
    kNot = "BifrostGraph,Core::Logic,not"
    kEqual = "BifrostGraph,Core::Logic,equal"
    kNotEqual = "BifrostGraph,Core::Logic,not_equal"
    kGreater = "BifrostGraph,Core::Logic,greater"
    kGreaterOrEqual = "BifrostGraph,Core::Logic,greater_or_equal"
    kLess = "BifrostGraph,Core::Logic,less"
    kLessOrEqual = "BifrostGraph,Core::Logic,less_or_equal"

    kInput = "_input"
    kOutput = "_output"

    kBuildArray = "BifrostGraph,Core::Array,build_array"
    kSetInArray = "BifrostGraph,Core::Array,set_in_array"
    kSetProperty = "BifrostGraph,Core::Object,set_property"


class BifPath(str):
    def __truediv__(self, other):
        return self.__class__("/" + (self + "/" + str(other)).strip("/"))

    def __floordiv__(self, other):
        return self.__class__("/" + (self + "." + str(other)).strip("/"))

    @property
    def name(self):
        if "." in self:
            return self.partition(".")[2]
        return self.rpartition("/")[2]

    @property
    def parent(self):
        if "." in self:
            return self.__class__("/" + self.partition(".")[0].strip("/"))
        return self.__class__("/" + self.rpartition("/")[0].strip("/"))


class Memory:
    def __init__(self):
        self._data = {}
        self._setonly = {}
        self._readonly = {}

    def define_setonly(self, s_name, s_type, target):
        if s_name in self._data or s_name in self._setonly:
            print(self)
            raise Exception(f"Output variable already defined: '{s_name}'")

        self._setonly[s_name] = {"target": target, "type": s_type}

    def define(self, s_name, s_type, value=None):
        if s_name in self._data:
            print(self)
            raise Exception(f"Variable already defined: '{s_name}'")

        self._data[s_name] = {"value": value, "type": s_type}

    def is_defined(self, s_name):
        return s_name in self._data

    def is_setonly(self, s_name):
        return s_name in self._setonly

    def get_setonly(self, s_name):
        d = self._setonly.pop(s_name)
        return d["target"], d["type"]

    def set(self, s_name, value, _type=None):
        if s_name in self._setonly:
            raise Exception("Must connect through Graph.connect() to set_only value!")

        self._data[s_name]["value"] = value
        if _type:
            self._data[s_name]["type"] = _type


    def get(self, s_name):
        return self._data[s_name]["value"]

    def get_type(self, s_name):
        if s_name not in self._setonly:
            return self._data[s_name]["type"]
        return self._setonly[s_name]["type"]

    def __getitem__(self, item):
        return self.get(item)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __str__(self):
        s = "+-- Memory ---\n"
        s += "|  setonly:\n"
        for k, v in self._setonly.items():
            s += f"|     {k} ({v['type']}): {v['target']}\n"

        s += "|  data:\n"
        for k, v in self._data.items():
            s += f"|     {k} ({v['type']}): {v['value']}\n"

        return s


class Graph:
    def __init__(self, graph, parent):
        self._graph = graph
        self._contexts = [BifPath(parent)]
        self._memory_scope = [Memory()]
        self._d_terminals = {}

    def __enter__(self):
        self._time_start = time.time()
        cmds.vnnChangeBracket(self._graph, open=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        cmds.vnnChangeBracket(self._graph, close=True)

        for s_node in sorted(self._d_terminals):
            self._set_terminal(s_node, self._d_terminals[s_node])

        print(f"Graph took: {time.time()-self._time_start:.02f} seconds")

    @classmethod
    def resolve_node_type(cls, s_type):
        if "," not in s_type:
            s_type_resolved = NODES.resolves(s_type)
            if not s_type_resolved:
                raise Exception(f"Unknown function or oeprator: '{s_type}'")
            s_namespace, _, s_type = s_type_resolved.rpartition("::")
            s_type = f"BifrostGraph,{s_namespace},{s_type}"

        return s_type

    @classmethod
    def resolve_port_type(cls, s_type):
        i_dim = s_type.count("[")
        s_base = s_type.strip("[]")
        s_type = i_dim * "array<" + TYPES.get(s_base, s_base) + i_dim * ">"
        if s_type.count(">") > 3:
            raise Exception(f"Invalid array type: '{s_type}'")
        return s_type

    @classmethod
    def get_base_port_type(cls, s_type):
        s_type = s_type.strip("[]")
        while s_type.startswith("array<"):
            s_type = s_type[6:-1]
        return s_type

    def push_context(self, context):
        self._contexts.append(context)
        self._memory_scope.append(Memory())
        return self._contexts[-1]

    def pop_context(self):
        self._memory_scope.pop(-1)
        return self._contexts.pop(-1)

    def push_context2(self, context, memory=None):
        self._contexts.append(context)
        self._memory_scope.append(memory or Memory())
        return self._contexts[-1], self._memory_scope[-1]

    def pop_context2(self):
        return self._contexts.pop(-1), self._memory_scope.pop(-1)

    def get_memory(self):
        return self._memory_scope[-1]

    def create_node(self, s_type, s_name=None, context=None):
        context = BifPath(context or self._contexts[-1])

        # create IO node
        if s_type in [NodeType.kInput, NodeType.kOutput]:
            node = context/cmds.vnnCompound(self._graph, context, addIONode=s_type == NodeType.kInput)[0]

        # create node of specific type
        else:
            s_type = self.resolve_node_type(s_type)
            node = context/cmds.vnnCompound(self._graph, context, addNode=s_type)[0]

        # if a name is given, decide whether to rename the node or set the node display value
        if s_name and s_name != node.name:
            if "{" in s_name:
                self.set_node_value_display(node, s_name)
            else:
                node = self.rename(node, s_name)

        return node

    def create_value_node(self, s_type, s_name=None, context=None):
        node = self.create_node(f"BifrostGraph,Core::Constants,float", s_name=s_name, context=context)
        self.set_meta_data(node, "valuenode_type", s_type)
        return node

    def create_compound_node(self, s_name=None, inputs=None, outputs=None, context=None, _type=NodeType.kCompound):
        compound = self.create_node(_type, s_name=s_name, context=context)
        inputs = [inputs] if isinstance(inputs, str) else inputs
        inputs = [] if not inputs else (["input"] if isinstance(inputs, bool) else inputs)
        outputs = [outputs] if isinstance(outputs, str) else outputs
        outputs = [] if not outputs else (["output"] if outputs and isinstance(outputs, bool) else outputs)

        for s in inputs:
            self.create_node(NodeType.kInput, s_name=s, context=compound)

        for s in outputs:
            self.create_node(NodeType.kOutput, s_name=s, context=compound)

        return compound

    def n_if(self, s_condition, s_true_case, s_false_case):
        node_if = self.create_node("BifrostGraph,Core::Logic,if")
        self.connect(s_condition, node_if//"condition")
        self.connect(s_true_case, node_if//"true_case")
        self.connect(s_false_case, node_if//"false_case")
        return node_if//"output"

    def n_equal(self, s_a, s_b):
        equal = self.create_node("BifrostGraph,Core::Logic,equal")
        self.connect(s_a, equal//"first")
        self.connect(s_b, equal//"second")
        return equal//"output"

    def n_not_equal(self, s_a, s_b):
        equal = self.create_node("BifrostGraph,Core::Logic,not_equal")
        self.connect(s_a, equal//"first")
        self.connect(s_b, equal//"second")
        return equal//"output"

    def n_less(self, s_a, s_b):
        less = self.create_node("BifrostGraph,Core::Logic,less")
        self.connect(s_a, less//"first")
        self.connect(s_b, less//"second")
        return less//"output"

    def n_greater(self, s_a, s_b):
        greater = self.create_node("BifrostGraph,Core::Logic,greater")
        self.connect(s_a, greater//"first")
        self.connect(s_b, greater//"second")
        return greater//"output"

    def n_greater_or_equal(self, s_a, s_b):
        greater_or_equal = self.create_node("BifrostGraph,Core::Logic,greater_or_equal")
        self.connect(s_a, greater_or_equal//"first")
        self.connect(s_b, greater_or_equal//"second")
        return greater_or_equal//"output"

    def n_less_or_equal(self, s_a, s_b):
        less_or_equal = self.create_node("BifrostGraph,Core::Logic,less_or_equal")
        self.connect(s_a, less_or_equal//"first")
        self.connect(s_b, less_or_equal//"second")
        return less_or_equal//"output"

    def n_or(self, s_a, s_b):
        or_ = self.create_node("BifrostGraph,Core::Logic,or")
        self.connect(s_a, or_//"first")
        self.connect(s_b, or_//"second")
        return or_//"output"

    def n_xor(self, s_a, s_b):
        xor = self.create_node("BifrostGraph,Core::Logic,xor")
        self.connect(s_a, xor//"first")
        self.connect(s_b, xor//"second")
        return xor//"output"

    def n_and(self, s_a, s_b):
        and_ = self.create_node("BifrostGraph,Core::Logic,and")
        self.connect(s_a, and_//"first")
        self.connect(s_b, and_//"second")
        return and_//"output"

    def n_negate(self, s_value):
        negate = self.create_node("negate")
        self.connect(s_value, negate//"value")
        return negate//"negated"

    def n_not(self, s_value):
        node_not = self.create_node("not")
        self.connect(s_value, node_not//"value")
        return node_not//"output"

    def n_add(self, *sa_values):
        add = self.create_node("add")
        for i, s_value in enumerate(sa_values):
            self.connect(s_value, self.add_in_port(add, f"value{i}"))
        return add//"output"

    def n_build_string(self, *sa_values):
        build_string_wrapper = self.create_compound_node("build_string2", inputs=("input",), outputs=("output",))
        build_string = self.create_node("build_string", context=build_string_wrapper)
        for i, s_value in enumerate(sa_values):
            self.add_out_port(build_string_wrapper/"input", f"string{i}", s_type="string")
            self.connect(s_value, build_string_wrapper//f"string{i}")
            self.connect(build_string_wrapper/"input"//f"string{i}", self.add_in_port(build_string, f"strings.string{i}"))

        self.connect(build_string//"joined", self.add_in_port(build_string_wrapper/"output", "output", s_type="string"))
        return build_string_wrapper//"output"

    def n_subtract(self, *sa_values):
        subtract = self.create_node("subtract")
        for i, s_value in enumerate(sa_values):
            self.connect(s_value, self.add_in_port(subtract, f"value{i}"))
        return subtract//"output"

    def n_modulo(self, s_value, s_divisor):
        mod = self.create_node("modulo")
        self.connect(s_value, mod // "value")
        self.connect(s_divisor, mod//"divisor")
        return mod//"remainder"

    def n_divide(self, *sa_values):
        divide = self.create_node("divide")
        for i, s_value in enumerate(sa_values):
            self.connect(s_value, self.add_in_port(divide, f"value{i}"))
        return divide//"output"

    def n_multiply(self, *sa_values):
        multiply = self.create_node("multiply")
        for i, s_value in enumerate(sa_values):
            self.connect(s_value, self.add_in_port(multiply, f"value{i}"))
        return multiply//"output"

    def n_power(self, s_base, s_exponent):
        power = self.create_node("power")
        self.connect(s_base, power // "base")
        self.connect(s_exponent, power // "exponent")
        return power//"power"

    def n_to_char(self, s_from):
        power = self.create_node("to_char")
        self.connect(s_from, power//"from")
        return power//"char"

    def create_slice_node(self, s_name=None, context=None):
        scope = self.create_compound_node(s_name=s_name, context=context, inputs=("input",), outputs=("output",))
        self.push_context2(scope)

        # in ports
        s_size = self.add_out_port(scope/"input", "size", s_type="long")
        s_start_is_none = self.add_out_port(scope/"input", "start_is_none", s_type="bool")
        s_start = self.add_out_port(scope/"input", "start", s_type="long")
        s_stop_is_none = self.add_out_port(scope/"input", "stop_is_none", s_type="bool")
        s_stop = self.add_out_port(scope/"input", "stop", s_type="long")
        s_step_is_none = self.add_out_port(scope/"input", "step_is_none", s_type="bool")
        s_step = self.add_out_port(scope/"input", "step", s_type="long")

        # out ports
        s_out_start = self.add_in_port(scope/"output", "out_start", s_type="long")
        s_out_stop = self.add_in_port(scope/"output", "out_stop", s_type="long")
        s_out_step = self.add_in_port(scope/"output", "out_step", s_type="long")
        s_out_count = self.add_in_port(scope/"output", "out_count", s_type="long")
        s_out_indices = self.add_in_port(scope/"output", "out_indices", s_type="array<long>")

        # constants
        s_const_0 = self.create_const_value(0, s_type="long")
        s_const_1 = self.create_const_value(1, s_type="long")
        s_const_n1 = self.create_const_value(-1, s_type="long")

        # `step = 1 if step in [None, 0] else step`
        s_set_step = self.n_or(self.n_equal(s_step, s_const_0), s_step_is_none)
        s_step = self.n_if(s_set_step, s_const_1, s_step)
        self.connect(s_step, s_out_step)

        # step < 0
        s_negative_step = self.n_less(s_step, s_const_0)

        # start = (size if step < 0 else 0) if start is None else start
        s_start_alt = self.n_if(s_negative_step, s_size, s_const_0)
        s_start = self.n_if(s_start_is_none, s_start_alt, s_start)

        # stop = (-size if step < 0 else size) if stop is None else stop
        s_stop_alt = self.n_if(s_negative_step, self.n_negate(s_size), s_size)
        s_stop = self.n_if(s_stop_is_none, s_stop_alt, s_stop)

        # -1 if step < 0 else 0
        s_n1_or_0 = self.n_if(s_negative_step, s_const_n1, s_const_0)

        # (-1 if step < 0 else 0) if (start+length) < 0 else (start+length)
        s_start_plus_length = self.n_add(s_start, s_size)
        s_start_neg_alt = self.n_if(self.n_less(s_start_plus_length, s_const_0), s_n1_or_0, s_start_plus_length)

        # (size - (1 if step < 0 else 0)) if start >= length else start
        s_start_big_alt = self.n_if(self.n_greater_or_equal(s_start, s_size), self.n_add(s_size, s_n1_or_0), s_start)

        s_start = self.n_if(self.n_less(s_start, s_const_0), s_start_neg_alt, s_start_big_alt)
        self.connect(s_start, s_out_start)

        # (-1 if step < 0 else 0) if (stop+length) < 0 else (stop+length)
        s_stop_plus_length = self.n_add(s_stop, s_size)
        s_stop_neg_alt = self.n_if(self.n_less(s_stop_plus_length, s_const_0), s_n1_or_0, s_stop_plus_length)

        # (size - (1 if step < 0 else 0)) if stop >= length else stop
        s_stop_big_alt = self.n_if(self.n_greater_or_equal(s_stop, s_size), self.n_add(s_size, s_n1_or_0), s_stop)

        s_stop = self.n_if(self.n_less(s_stop, s_const_0), s_stop_neg_alt, s_stop_big_alt)
        self.connect(s_stop, s_out_stop)

        s_start_minus_stop_minus_1 = self.n_subtract(s_start, s_stop, s_const_1)
        s_ans_div_neg_step = self.n_divide(s_start_minus_stop_minus_1, self.n_negate(s_step))
        s_count_step_neg_stop_less_start = self.n_add(s_ans_div_neg_step, s_const_1)

        s_stop_minus_start_minus_1 = self.n_subtract(s_stop, s_start, s_const_1)
        s_ans_div_step = self.n_divide(s_stop_minus_start_minus_1, s_step)
        s_count_step_pos_start_less_stop = self.n_add(s_ans_div_step, s_const_1)

        s_count = self.n_if(
                s_negative_step,
                self.n_if(
                        self.n_less(s_stop, s_start),
                        s_count_step_neg_stop_less_start,
                        s_const_0
                ),
                self.n_if(
                        self.n_less(s_start, s_stop),
                        s_count_step_pos_start_less_stop,
                        s_const_0
                )
        )
        self.connect(s_count, s_out_count)

        for_each, _ = self.push_context2(self.create_iterator_node(s_type="for_each"))
        s_loop_start = self.add_out_port(for_each/"input", s_name="start", s_type="long")
        s_loop_step = self.add_out_port(for_each/"input", s_name="step", s_type="long")
        s_loop_indices = self.add_in_port(for_each/"output", s_name="indices", s_type="array<long>")

        s_index_times_step = self.n_multiply(s_loop_step, for_each/"input"//"current_index")
        s_add_offset = self.n_add(s_index_times_step, s_loop_start)
        self.connect(s_add_offset, s_loop_indices)

        self.pop_context2()

        self.connect(s_count, for_each//"max_iterations")
        self.connect(s_start, for_each//"start")
        self.connect(s_step, for_each//"step")
        self.connect(for_each//"indices", s_out_indices)

        self.pop_context2()

        return scope

    def create_iterator_node(self, s_type, s_name=None, inputs=("input",), outputs=("output",), context=None):
        s_type = {
            "for_each": "BifrostGraph,Core::Iterators,for_each",
            "foreach": "BifrostGraph,Core::Iterators,for_each",
            "iterate": "BifrostGraph,Core::Iterators,iterate",
            "do_while": "BifrostGraph,Core::Iterators,do_while",
            "dowhile": "BifrostGraph,Core::Iterators,do_while"
        }[s_type]
        return self.create_compound_node(s_name, inputs=inputs, outputs=outputs, context=context, _type=s_type)

    def connect(self, src, tgt):
        try:
            cmds.vnnPort(self._graph, src, 1, 1, set=16)
            cmds.vnnConnect(self._graph, src, tgt)
            cmds.vnnPort(self._graph, src, 1, 1, clear=16)

        except Exception as e:
            raise _error.BfRuntimeError(f"Cannot connect '{src}' -> '{tgt}'")
            # print(src, "->", tgt)
            # print(f"   source: {self.get_type(src)}")
            # print(f"   target: {self.get_type(tgt)}")

    def rename(self, node, s_name, b_auto_rename=True):
        if node.name == s_name:
            return node

        if "." in node:
            sa_ports = cmds.vnnCompound(self._graph, node.parent, listPorts=True)
            if s_name in sa_ports:
                raise Exception("Port exists! Auto rename only works for nodes")

            cmds.vnnCompound(self._graph, node.parent, renamePort=(node.name, s_name))
            return node.parent // s_name

        self.set_node_value_display(node, s_name)
        return node

        # sa_nodes = cmds.vnnCompound(self._graph, node.parent, listNodes=True)
        # if s_name in sa_nodes:
        #     if not b_auto_rename:
        #         raise Exception("Node already exists!")
        #
        #     i = 1
        #     while s_name + str(i) in sa_nodes:
        #         i += 1
        #
        #     s_name += str(i)
        #
        # cmds.vnnCompound(self._graph, node.parent, renameNode=(node.name, s_name))
        # return node.parent / s_name

    def set_node_value_display(self, node, s_expr):
        data = f"{{show=1;format=\"{s_expr}\"}}"
        cmds.vnnNode(self._graph, node, setMetaDataFromString=f"NodeValueDisplay={data};")

    def add_in_port(self, node, s_name, s_type="auto", value=None):
        s_type = self.resolve_port_type(s_type)
        cmds.vnnNode(self._graph, node, createInputPort=(s_name, s_type))
        if value:
            self.set_value(node, s_name, value=value)

        return node//s_name

    def add_out_port(self, node, s_name, s_type="auto"):
        s_type = self.resolve_port_type(s_type)
        cmds.vnnNode(self._graph, node, createOutputPort=(s_name, s_type))
        return node//s_name

    def set_value(self, node, s_port=None, value=None):
        if value is None:
            raise Exception("Value cannot be 'None'!")

        if isinstance(value, bool):
            value = int(value)

        if s_port is None:
            if "." not in node:
                raise Exception("No port given!")
            s_port = node.name
            node = node.parent

        cmds.vnnNode(self._graph, node, setPortDefaultValues=(s_port, value))

    def set_type(self, node, s_port=None, s_type=None):
        if s_type is None:
            raise Exception("Type cannot be 'None'!")

        if s_port is None:
            if "." not in node:
                raise Exception("No port given!")
            s_port = node.name
            node = node.parent

        s_type = self.resolve_port_type(s_type)
        cmds.vnnNode(self._graph, node, setPortDataType=(s_port, s_type))

    def get_type(self, node, s_port=None, b_accept_auto=True):
        if s_port is None:
            if "." not in node:
                raise Exception("No port given!")
            s_port = node.name
            node = node.parent

        s_type = cmds.vnnNode(self._graph, node, queryPortDataType=s_port)
        if s_type == "auto" and not b_accept_auto:
            cmds.vnnChangeBracket(self._graph, close=True)
            s_type = cmds.vnnNode(self._graph, node, queryPortDataType=s_port)
            cmds.vnnChangeBracket(self._graph, open=True)

        return s_type

    def _set_terminal(self, node, flags):
        # cmds.vnnChangeBracket(self._graph, close=True)
        for flag in "DPF":
            cmds.vnnNode(self._graph, node, setStateFlag=(flag, False))

        for flag in flags:
            try:
                cmds.vnnNode(self._graph, node, setStateFlag=(flag, True))
            except:
                print("meeeep")
        # cmds.vnnChangeBracket(self._graph, open=True)

    def set_terminal(self, node, flags):
        if None in flags:
            return
        self._d_terminals[node] = flags

    def set_meta_data(self, node, key, value):
        cmds.vnnNode(self._graph, node, setMetaData=(key, value))

    def create_const_enum_value(self, value, s_type, context=None):
        s_type = self.resolve_port_type(s_type)

        if isinstance(value, str):
            value = ENUMS[s_type]["values"][value]

        node = self.create_value_node("float", context=context)
        self.set_meta_data(node, "valuenode_type", s_type)
        self.set_value(node, "value", value)

        return node//"output"

    def create_const_default_array_value(self, size, s_type, context=None):
        s_type = self.resolve_port_type(s_type)
        # node = self.create_value_node(s_type, context=context)
        # self.set_meta_data(node, "valuenode_size", size)
        # return node//"output"
        node = self.create_node("Core::Array::resize_array")
        self.set_type(node, "array", s_type)

        if isinstance(size, str):
            self.connect(size, node//"new_size")
        else:
            self.set_value(node, "new_size", size)

        return node//"resized"

    def create_const_matrix_value(self, value, s_type, context=None):
        s_type = self.resolve_port_type(s_type)

        for i in range(len(value)):
            if s_type.rpartition("::")[-1].startswith("bool"):
                value[i] = bool(value[i])

            if isinstance(value[i], bool):
                value[i] = int(value[i])

        if s_type == "Object":
            raise Exception("Only supports numeric types!")

        if s_type[-1] not in "234":
            raise Exception("Use create_single_value() for anything that is not a vector or matrix!")

        if s_type[-3] in "234":
            if len(value) != int(s_type[-3]) * int(s_type[-1]):
                raise Exception(f"Incorrect value count: {s_type} <> {value}")

        else:
            if len(value) != int(s_type[-1]):
                raise Exception(f"Incorrect value count: {s_type} <> {value}")

        node = self.create_value_node(s_type, context=context)
        if value is not None:
            value = ("{" + ", ".join([str(x) for x in value]) + "}") if isinstance(value, (list, tuple)) else value
            self.set_value(node, "value", value)

        return node//"output"

    def create_const_simple_value(self, value, s_type, context=None):
        s_type = self.resolve_port_type(s_type)

        if value is None:
            return self.create_value_node(s_type, context=context)//"output"

        if isinstance(value, bool):
            value = int(value)

        if s_type == "Object" and value is not None:
            raise Exception("Value for Object not yet supported")

        if s_type[-1] in "234":
            raise Exception("Use create_matrix_value() for vectors and matrices!")

        node = self.create_node(f"BifrostGraph,Core::Constants,{s_type}", context=context)
        if value is not None:
            self.set_value(node, "value", value)

        return node // "output"

    def create_const_array_value(self, values, s_type, context=None):
        s_type = self.resolve_port_type(s_type)

        if not s_type.startswith("array<"):
            raise Exception(f"Expected array type, got '{s_type}'")

        if not isinstance(values, (list, tuple)):
            return self.create_const_default_array_value(values, s_type=s_type, context=context)

        node = self.create_compound_node(s_name="{_}", inputs=("input",), outputs=("output",), context=context)
        self.push_context(node)

        # set the node value display
        self.add_out_port(node/"input", "_", "string")
        self.set_value(node, "_", s_type)

        # add the output port
        self.add_in_port(node/"output", "output", s_type)

        # figure out the base type of the array
        s_sub_type = s_type[6:-1]

        # can only use build array for 1D arrays
        if not s_sub_type.startswith("array<"):
            build_array = self.create_node(s_type=NodeType.kBuildArray, context=node)
            self.connect(build_array // "array", node / "output" // "output")

            for i, value in enumerate(values):
                cmds.vnnNode(self._graph, build_array, createInputPort=(f"value{i}", s_sub_type))

                if hasattr(value, "to_vnn"):
                    value = value.to_vnn(self)

                elif s_sub_type[-1] in "234":
                    value = self.create_const_matrix_value(value, s_type=s_sub_type, context=node)

                elif s_sub_type in ENUMS.keys():
                    value = self.create_const_enum_value(value, s_type=s_sub_type, context=node)

                else:
                    value = self.create_const_simple_value(value, s_type=s_sub_type, context=node)

                self.connect(value, build_array // f"value{i}")

        # 2D or 3D arrays
        else:
            latest = self.create_const_default_array_value(len(values), s_type=s_type, context=node)

            for i, value in enumerate(values):
                set_in_array = self.create_node(NodeType.kSetInArray, s_name="[{index}] = {value}", context=node)
                self.connect(latest, set_in_array//"array")
                self.set_value(set_in_array, "index", i)

                if hasattr(value, "to_vnn"):
                    value = value.to_vnn(self)

                self.connect(self.create_const_array_value(value, s_type=s_sub_type, context=node), set_in_array//"value")
                latest = set_in_array//"out_array"

            self.connect(latest, node/"output"//"output")

        self.pop_context()

        return node//"output"

    def create_array_value(self, values, s_type, context=None):
        s_type = self.resolve_port_type(s_type)

        if not s_type.startswith("array<"):
            raise Exception(f"Expected array type, got '{s_type}'")

        if not isinstance(values, (list, tuple)):
            return self.create_const_default_array_value(values, s_type=s_type, context=context)

        node = self.create_compound_node(s_name="{_}", inputs=("input",), outputs=("output",), context=context)
        # set the node value display
        self.add_out_port(node/"input", "_", "string")
        self.set_value(node, "_", s_type)

        for i, s_value in enumerate(values):
            self.add_out_port(node/"input", f"item_{i}", s_type=s_type[6:-1])
            self.connect(s_value, node//f"item_{i}")

        self.push_context(node)

        # add the output port
        self.add_in_port(node/"output", "output", s_type)

        resize_array = self.create_node(s_type="Core::Array::resize_array")
        self.set_type(resize_array, "array", s_type=s_type)
        self.set_value(resize_array, "new_size", value=len(values))

        latest = resize_array//"resized"

        for i in range(len(values)):
            set_in_array = self.create_node(NodeType.kSetInArray, s_name="[{index}] = {value}", context=node)
            self.connect(latest, set_in_array//"array")
            self.set_value(set_in_array, "index", i)
            self.connect(node/"input"//f"item_{i}", set_in_array//"value")
            latest = set_in_array//"out_array"

        self.connect(latest, node/"output"//"output")

        self.pop_context()

        return node//"output"

    def create_const_value(self, value, s_type, s_name=None, context=None):
        s_type = self.resolve_port_type(s_type)

        if value is None:
            return self.create_value_node(s_type, s_name=s_name, context=context)//"output"
            # operator = self.create_const_simple_value(None, s_type=s_type, context=context)
            # if s_name:
            #     self.set_node_value_display(operator.parent, s_name)
            # return operator

        if not s_type.startswith("array<"):
            if s_type in ENUMS.keys():
                operator = self.create_const_enum_value(value, s_type=s_type, context=context)
                if s_name:
                    self.set_node_value_display(operator.parent, s_name)
                return operator

            if s_type in ["bool",
                          "float", "double",
                          "uchar", "char",
                          "ushort", "short",
                          "uint", "int",
                          "ulong", "long",
                          "string"]:
                operator = self.create_const_simple_value(value, s_type=s_type, context=context)
                if s_name:
                    self.set_node_value_display(operator.parent, s_name)
                return operator

            if s_type[-1] in "234":
                operator = self.create_const_matrix_value(value, s_type=s_type, context=context)
                if s_name:
                    self.set_node_value_display(operator.parent, s_name)
                return operator

            if s_type in ["Object", "object"]:
                raise NotImplementedError("Object is not yet implemented since I havent figured out how to do types")

            else:
                raise NotImplementedError(s_type)

        operator = self.create_const_array_value(value, s_type=s_type, context=context)
        if s_name:
            self.set_node_value_display(operator.parent, s_name)
        return operator

    def create_object_value(self, sa_keys, sa_values, context=None):
        node = self.create_compound_node(s_name="{_}", inputs=("input",), outputs=("output",), context=context)
        # set the node value display
        self.add_out_port(node/"input", "_", "string")
        self.set_value(node, "_", "Object")

        for i, (s_key, s_value) in enumerate(zip(sa_keys, sa_values)):
            self.add_out_port(node/"input", f"key_{i}", s_type="string")
            self.connect(s_key, node//f"key_{i}")
            self.add_out_port(node/"input", f"value_{i}", s_type="auto")
            self.connect(s_value, node//f"value_{i}")

        self.push_context(node)

        # add the output port
        self.add_in_port(node/"output", "output", "Object")

        latest = None

        for i in range(len(sa_values)):
            set_property = self.create_node(NodeType.kSetProperty, s_name="[{key}] = {value}", context=node)
            if latest:
                self.connect(latest, set_property//"object")
            self.connect(node/"input"//f"key_{i}", set_property//"key")
            self.connect(node/"input"//f"value_{i}", set_property//"value")
            latest = set_property//"out_object"

        if latest:
            self.connect(latest, node/"output"//"output")

        self.pop_context()

        return node//"output"