"""
todo: include this in an 'official' list and overwrite the invalid values

randomize_geo_property
    default_value: not auto port but has suggestion meta data

resample_strands
    count_per_strand: not auto port but has suggestion meta data
    minimum_resample_distance: wrong suggestions

tag_by_threshold
    min: only max has suggested types

displace_by_wave
    magnitude: missing suggestions

wave_set_foam
    magnitude: missing suggestions

define_usd_curves
    basis: not auto port but has suggestion meta data
    type: not auto port but has suggestion meta data
"""
import itertools

from BSL import _error, _special_types, _type, _resolver
from BSL._constants import PATH_BIFROST_NODES

from BSL._port_types import *

import json


def _replace_base(x, s):
    arr = x.count(">")
    for _ in range(arr):
        x = x[6:-1]

    if x in VECTOR:
        s = "Math::" + s + x[-1]
    elif x in MATRIX:
        s = "Math::" + s + x[-3:]

    return arr * "array<" + s + arr * ">"


def _replace_full_base(x, s):
    arr = x.count(">")
    result = arr * "array<" + s + arr * ">"
    return result


def _arrDown(x):
    return x[6:-1]


def _arrUp(x):
    return f"array<{x}>"


def _arrFlat(x):
    dim = x.count(">")
    if dim == 0:
        return _arrUp(x)
    return _arrUp(x[6*dim:-dim])


def _transpose(x):
    arr = x.count(">")
    for _ in range(arr):
        x = x[6:-1]

    return arr * "array<" + x[:-3] + x[-1] + "x" + x[-3] + arr * ">"


def _to_vec4(x):
    arr = x.count(">")
    for _ in range(arr):
        x = x[6:-1]

    if "::" not in x:
        return arr * "array<" + f"Math::{x}4" + arr * ">"

    if x[-3] in "234" and x[-1] in "234" and x[-2] == "x":
        x = x[:-3]
    elif x[-1] in "234":
        x = x[:-1]

    return arr * "array<" + f"{x}4" + arr * ">"


def _to_vec3(x):
    arr = x.count(">")
    for _ in range(arr):
        x = x[6:-1]

    if "::" not in x:
        return arr * "array<" + f"Math::{x}3" + arr * ">"

    if x[-3] in "234" and x[-1] in "234" and x[-2] == "x":
        x = x[:-3]
    elif x[-1] in "234":
        x = x[:-1]

    return arr * "array<" + f"{x}3" + arr * ">"


def _to_scalar(x):
    arr = x.count(">")
    for _ in range(arr):
        x = x[6:-1]

    if "::" not in x:
        return arr * "array<" + f"{x}" + arr * ">"

    if x[-3] in "234" and x[-1] in "234" and x[-2] == "x":
        x = x.partition("::")[2][:-3]

    elif x[-1] in "234":
        x = x.partition("::")[2][:-1]

    return arr * "array<" + f"{x}" + arr * ">"


def _to_mtx3x3(x):
    arr = x.count(">")
    for _ in range(arr):
        x = x[6:-1]

    if "::" not in x:
        return arr * "array<" + f"Math::{x}3x3" + arr * ">"

    if x[-3] in "234" and x[-1] in "234" and x[-2] == "x":
        x = x[:-3]
    elif x[-1] in "234":
        x = x[:-1]

    return arr * "array<" + f"{x}3x3" + arr * ">"


def _to_float(x):
    small_types = ["char", "uchar", "short", "ushort", "int", "uint", "float"]
    big_types = ["long", "ulong", "double"]

    if x in small_types:
        return "float"

    if x in big_types:
        return "double"

    for i in range(2, 5):
        for s in small_types:
            if f"::{s}{i}" in x:
                return x.replace(f"::{s}{i}", f"::float{i}")

        for s in big_types:
            if f"::{s}{i}" in x:
                return x.replace(f"::{s}{i}", f"::double{i}")

    raise NotImplementedError


class Overlord:
    CHECK_EXISTS = False

    _d_operators = None
    _d_overloads = None
    _sa_tests_done = []
    _sa_tests_skipped = []

    def __new__(cls, *args, **kwargs):
        raise _error.Error("Overlord is acts like a singleton. Use class methods directly")

    @classmethod
    def init(cls):
        cls._d_operators = _special_types.Namespaces(json.loads(PATH_BIFROST_NODES.read_text()))
        cls._d_overloads = {}

        cls.load_graph_overloads()
        cls.load_conversion_overloads()
        cls.load_array_overloads()
        cls.load_object_overloads()
        cls.load_math_overloads()
        cls.load_constants_overloads()
        cls.load_logic_overloads()
        cls.load_geometry_overloads()
        cls.load_ml_overloads()
        cls.load_random_overloads()
        cls.load_display_overloads()
        cls.load_field_overloads()
        cls.load_simulation_overloads()
        cls.load_usd_overloads()

        # this will not produce an exhaustive list
        cls.load_simple_overloads_from_suggestions()

        sa_dont = {
            "Core::Type_Conversion::promote",
            "Simulation::Common::simulation_example",
        }

        for s_func, d_data in cls._d_operators.items():
            if s_func in sa_dont:
                continue

            if s_func.startswith("Print::") or s_func.startswith("Heimdall::"):
                continue

            # sa_keys = list(d_data["overloads"])
            # if sa_keys[0].count("auto") > 0 and len(sa_keys) == 1 and s_func not in cls._d_overloads:
            #     print(s_func, "auto" in d_data["overloads"][sa_keys[0]])

        # for s_func in cls._d_operators:
        #     if cls.is_associative(s_func):
        #         print(s_func)

        print(f"Passed {len(cls._sa_tests_done)} tests, skipped {len(cls._sa_tests_skipped)}")

    @classmethod
    def force_auto_ports(cls, s_func, *sa_auto_ports):
        if s_func not in cls._d_operators:
            raise _error.Error(f"Operator or compound '{s_func}' does not exist!")

        d_overloads = cls._d_operators[s_func]["overloads"]
        sa_input_names = cls._d_operators[s_func]["inputs"]
        sa_output_names = cls._d_operators[s_func]["outputs"]

        for s_port in sa_auto_ports:
            if s_port not in sa_input_names + sa_output_names:
                raise _error.Error(f"Invalid port '{s_port}'. Chose from {sa_input_names + sa_output_names}")

        saa_input_types = [s.split("-") for s in d_overloads.keys()]
        saa_output_types = list(d_overloads.values())

        sa_input_first = saa_input_types[0][:]
        for i, s_name in enumerate(sa_input_names):
            if s_name in sa_auto_ports:
                sa_input_first[i] = "auto"

        sa_output_first = saa_output_types[0][:]
        for i, s_name in enumerate(sa_output_names):
            if s_name in sa_auto_ports:
                sa_output_first[i] = "auto"

        if sa_input_first in saa_input_types:
            idx = saa_input_types.index(sa_input_first)
            saa_output_types.pop(idx)
            saa_input_types.pop(idx)

        saa_input_types = [sa_input_first] + saa_input_types
        saa_output_types = [sa_output_first] + saa_output_types

        cls._d_operators[s_func]["overloads"] = {"-".join(sa_in): sa_out for sa_in, sa_out in zip(saa_input_types, saa_output_types)}

    @classmethod
    def define_overload(cls, s_func, *types_and_funcs):
        if cls.CHECK_EXISTS and s_func not in cls._d_operators:
            raise _error.Error(f"Operator or compound '{s_func}' does not exist!")

        d_overloads = cls._d_operators[s_func]["overloads"]

        if "auto" not in list(d_overloads.keys())[0].split("-"):
            raise _error.Error(f"Operator or compound '{s_func}' has no auto ports!")

        sa_keys = list(d_overloads)[0].split("-")
        i_auto_ports = sa_keys.count("auto") + d_overloads["-".join(sa_keys)].count("auto")

        for types, funcs in types_and_funcs:
            if not types:
                raise _error.Error(f"Valid types are empty!")

            if isinstance(types, str):
                raise _error.Error(f"Should be a set: '{types}'")

            b_is_iter = isinstance(funcs, (list, tuple))
            b_all = all([hasattr(f, "__call__") or f is None or isinstance(f, str) for f in funcs])

            if not (b_is_iter and b_all):
                raise _error.Error(f"Funcs must be list of None, string, or callables: '{s_func}'")

        sa_input_names, sa_output_names = cls.get_port_names(s_func)
        sa_input_types, sa_output_types = cls.get_port_types(s_func)
        count = 0
        for types, funcs in types_and_funcs:
            if count >= len(sa_input_names):
                print(sa_input_names)
                print(count)
                raise _error.Error(f"Output types must be given through type func: '{s_func}'")

            count += 1 + len(funcs)

        if i_auto_ports != count:
            sa_auto_in_names = [n for n, t in zip(sa_input_names, sa_input_types) if t == "auto"]
            sa_auto_out_names = [n for n, t in zip(sa_output_names, sa_output_types) if t == "auto"]
            raise _error.Error(f"'{s_func}' has {i_auto_ports} auto ports but got {count}.\n    {sa_auto_in_names}\n    {sa_auto_out_names}")

        if s_func not in cls._d_overloads:
            cls._d_overloads[s_func] = []
        cls._d_overloads[s_func] += [types_and_funcs]

        sa_input_types_default, sa_output_types_default = cls._d_operators[s_func]["default_overload"]
        if "auto" in sa_input_types_default:
            cls._sa_tests_skipped.append(s_func)
            return

        types_in_test = [_type.Type(t) for t in sa_input_types_default]
        status, result = cls.resolve_inputs_and_outputs(s_func, input_types=types_in_test)
        if not status:
            raise result[0](result[1])

        if result[0] != sa_input_types_default:
            s_compare = "\n    ".join(f"{r} <> {s}" for r, s in zip(result[0], sa_input_types_default))
            raise _error.Error(f"'{s_func}' missmatch in inputs:\n    {s_compare}")

        if result[1] != sa_output_types_default:
            s_compare = "\n    ".join(f"{r} <> {s}" for r, s in zip(result[1], sa_output_types_default))
            raise _error.Error(f"'{s_func}' missmatch in outputs:\n    {s_compare}")

        saa_suggestions = cls._d_operators[s_func]["suggestions"]

        ba_suggestions = [len(sa) > 1 for sa in saa_suggestions]
        b_all = all([bool(sa) for sa in saa_suggestions])
        b_one = sum(ba_suggestions) == 1
        # only test if there is exactly one port with suggestions. Some ports like in
        # the case of set_geo_property have ports with dependencies. I could probably use the overload system to deduce
        # the dependent port types from the list of suggestions but thats probably gonna add a couple of hours...

        sa_special_cases = [
            # it appears the suggested types for this node are incorrect
            "Geometry::Tags::tag_by_angle_between_vectors",
        ]

        if s_func not in sa_special_cases and b_one and b_all:
            for perm in itertools.product(*saa_suggestions):
                perm = [_type.Type(s) for s in perm]
                status, result = cls.resolve_inputs_and_outputs(s_func, input_types=perm)
                if not status:
                    raise result[0](result[1])

                if result[0] != perm:
                    s_compare = "\n    ".join(f"{name}: {r} <> {s}" for name, r, s in zip(sa_input_names, result[0], perm))
                    raise _error.Error(f"'{s_func}' missmatch on suggested inputs:\n    {s_compare}")

        cls._sa_tests_done.append(s_func)

    @classmethod
    def define_overload_resolver(cls, s_func, x_resolver):
        if cls.CHECK_EXISTS and s_func not in cls._d_operators:
            raise _error.Error(f"Operator or compound '{s_func}' does not exist!")

        if not hasattr(x_resolver, "__call__"):
            raise _error.Error("Did you mean define_overload()?")

        if s_func not in cls._d_overloads:
            cls._d_overloads[s_func] = []

        cls._d_overloads[s_func] += [x_resolver]

        sa_input_types_default, sa_output_types_default = cls._d_operators[s_func]["default_overload"]
        if "auto" in sa_input_types_default:
            cls._sa_tests_skipped.append(s_func)
            return

        types_in_test = [_type.Type(t) for t in sa_input_types_default]
        status, result = cls.resolve_inputs_and_outputs(s_func, input_types=types_in_test)
        if not status:
            raise result[0](result[1])

        if result[0] != sa_input_types_default:
            raise _error.Error(f"'{s_func}' missmatch in inputs: {result[0]} <> {sa_input_types_default}")

        if result[1] != sa_output_types_default:
            raise _error.Error(f"'{s_func}' missmatch in outputs: {result[1]} <> {sa_output_types_default}")

        cls._sa_tests_done.append(s_func)

    @classmethod
    def _resolve_inputs_and_outputs(cls, s_func, d_operator, sa_input_port_types, sa_output_port_types, input_types):
        sa_all_ports = sa_input_port_types + sa_output_port_types
        ia_auto_ports = [i for i, s in enumerate(sa_all_ports) if s == "auto"]

        b_debug = False  # s_func.endswith("delete_mesh_points")
        if b_debug:
            print(f"debugging: '{s_func}'")
            print(f"    in: {sa_input_port_types}")
            print(f"    out: {sa_output_port_types}")
            print(f"    given: {[t.s for t in input_types]}")
            print(f"    auto: {ia_auto_ports}")
            print(f"    overloads: {cls._d_operators[s_func]['overloads']}")

        if len(input_types) > len(sa_input_port_types):
            return False, (_error.Error, "Too many arguments")

        if "auto" in sa_all_ports and s_func not in cls._d_overloads:
            for idx, s_type in enumerate(sa_all_ports):
                if s_type != "auto":
                    continue

                if idx >= len(cls._d_operators[s_func]["suggestions"]):
                    continue

                if cls._d_operators[s_func]["suggestions"][idx]:
                    if input_types[idx].s in cls._d_operators[s_func]["suggestions"][idx]:
                        sa_all_ports[idx] = input_types[idx].s
                    else:
                        sa_all_ports[idx] = cls._d_operators[s_func]["suggestions"][idx][0]

            ia_auto_ports = [i for i, s in enumerate(sa_all_ports) if s == "auto"]

        if "auto" in sa_all_ports and s_func not in cls._d_overloads:
            sa_input_names, sa_output_names = cls.get_port_names(s_func)
            sa_all_names = sa_input_names + sa_output_names
            sa_ports = []
            for i, s in enumerate(sa_all_ports):
                if s == "auto":
                    sa_ports.append(sa_all_names[i])
            return False, (_error.BfNameError, f"Cant find overload information for ports {sa_ports} on '{s_func}'")

        # test for each overload
        overloads = cls._d_overloads.get(s_func, [])

        sa_all_ports_orig = sa_all_ports[:]
        saa_possible_resolutions = []
        baa_promoted_info = []

        if not ia_auto_ports:
            saa_possible_resolutions.append(sa_all_ports)
            # this is technically a lie but also not
            baa_promoted_info.append(len(sa_all_ports) * [False])

        sa_names_in, sa_names_out = cls.get_port_names(s_func)
        sa_auto_names = [n for n, t in zip(sa_names_in, sa_all_ports) if t == "auto"]

        if b_debug:
            print(f"    auto names: {sa_auto_names}")
            # for i, (s_auto_name, s_type) in enumerate(zip(sa_names_in, sa_all_ports)):
            #     print(i, s_auto_name, s_type)
            print(f"\n    evaluating overload sets (total: {len(overloads)})")

        result = None
        for _, overload_set in enumerate(overloads):
            sa_all_ports = sa_all_ports_orig[:]
            ba_all_promoted = len(sa_all_ports) * [False]

            if b_debug:
                print(f"        overload set: {_}, {str(overload_set)[:30]}...")
                print(f"            ports: {sa_all_ports}")
                print(f"            callable: {hasattr(overload_set, '__call__')}")

            if hasattr(overload_set, "__call__"):
                input_types_copy = ([_type.Type(t.s) for t in input_types])
                status, result1 = overload_set(tuple(sa_names_in), tuple(sa_names_out), sa_input_port_types[:], sa_output_port_types[:], input_types_copy)
                if status:
                    if len(result1[0]) != len(sa_names_in):
                        raise _error.Error(f"'{s_func}' returned the wrong number of input port types")

                    if len(result1[1]) != len(sa_names_out):
                        raise _error.Error(f"'{s_func}' returned the wrong number of output port types")

                    return True, result1

                result = result1
                continue

            result = None

            # required auto types, the rest will be inferred
            ia_required = []
            if ia_auto_ports:
                i_auto_port_index = 0
                # index = ia_auto_ports[0]
                for types_and_funcs in overload_set:
                    # print(ia_required, ia_auto_ports, i_auto_port_index)
                    ia_required.append(ia_auto_ports[i_auto_port_index])
                    i_auto_port_index += len(types_and_funcs[1]) + 1

                if ia_required and ia_required[-1] >= len(input_types):
                    if ia_required[-1] >= len(input_types):
                        print(f"inputs: {len(input_types)}")
                        print(f"auto: {len(ia_auto_ports)}")
                        print(f"auto: {ia_auto_ports}")
                        raise _error.Error(f"Too many key types: '{s_func}'")

                    result = (_error.BfTypeError, f"Cant infer type for port '{d_operator['inputs'][ia_required[-1]]}'")
                    continue

            required_types = [input_types[idx] for idx in ia_required]
            sa_required_names = [sa_names_in[idx] for idx in ia_required]

            if b_debug:
                print(f"            required: {[t.s for t in required_types]}")

            # list of types
            sa_auto_types = []
            ba_promoted = []

            if ia_auto_ports:
                index = ia_auto_ports[0]

            b_break = False

            for name_, type_, types_and_funcs in zip(sa_required_names, required_types, overload_set):
                if b_debug:
                    print(f"                resolving port '{name_}': {type_}")

                # if there are already suggested types somewhere, might as well make use of them...
                if type_.s == "auto":
                    saa_suggestions = cls._d_operators[s_func]["suggestions"]
                    if index < len(saa_suggestions) and saa_suggestions[index]:
                        type_ = _type.Type(saa_suggestions[index][0])

                s_orig = type_.s
                if type_.s not in types_and_funcs[0]:
                    if b_debug:
                        print(f"    [{name_}] {type_.s} not in {types_and_funcs[0]}")

                    if type_ == "auto":
                        result = (_error.BfTypeError, f"Missing required argument for port '{d_operator['inputs'][index]}'")
                        b_break = True
                        break

                    i_arr_dim = type_.array_dim()
                    _x_arr = lambda s, i: i*"array<" + s + i*">"
                    promotion_list = [t for t in _type.PROMOTION_PRIORITY_LIST if _x_arr(t.s, i_arr_dim) in types_and_funcs[0]]

                    for target_type in promotion_list:
                        type_base = type_.base_type() if type_.is_array() else type_
                        if _type.promotable(type_base, _type.Type(target_type)):
                            type_ = _type.Type(i_arr_dim * "array<" + target_type.s + i_arr_dim * ">")
                            break

                    else:
                        # since I decided to auto promote bool to char
                        if type_.base_type().base_type() == "bool":
                            type_ = _type.Type(type_.s.replace("bool", "char"))
                            for target_type in promotion_list:
                                if _type.promotable(type_, _type.Type(target_type)):
                                    type_ = _type.Type(target_type)
                                    break
                            else:
                                result = (_error.BfTypeError, f"Invalid value type '{type_}' for port '{d_operator['inputs'][index]}'")
                                b_break = True
                                break
                        else:
                            result = (_error.BfTypeError, f"Invalid type '{type_}' for port '{d_operator['inputs'][index]}'")
                            b_break = True
                            break

                ba_promoted.append(type_.s != s_orig)
                sa_auto_types.append(type_.s)

                for func in types_and_funcs[1]:
                    ba_promoted.append(ba_promoted[-1])
                    index += 1
                    if func is None:
                        sa_auto_types.append(type_.s)
                        if b_debug:
                            print(f"                        -> {sa_auto_types[-1]}")
                        continue

                    elif hasattr(func, "__call__"):
                        sa_auto_types.append(func(type_.s))
                        if b_debug:
                            print(f"                        -> {sa_auto_types[-1]}")
                        continue

                    elif isinstance(func, str):
                        sa_auto_types.append(func)
                        if b_debug:
                            print(f"                        -> {sa_auto_types[-1]}")
                        continue

                    else:
                        raise NotImplementedError

            if b_break:
                continue

            for idx, type_, b_promoted in zip(ia_auto_ports, sa_auto_types, ba_promoted):
                sa_all_ports[idx] = type_
                ba_all_promoted[idx] = b_promoted

            if b_debug:
                print(f"         -> {sa_all_ports}")

            if sa_all_ports not in saa_possible_resolutions:
                saa_possible_resolutions.append(sa_all_ports)
                baa_promoted_info.append(ba_all_promoted)

        if not saa_possible_resolutions and input_types:
            if not result:
                return False, (_error.Error, f"No resolutions found for '{s_func}'")
            return False, result

        if b_debug:
            print(f"    passing on to compat check ({len(saa_possible_resolutions)})")
            print(f"    promoted info: {len(baa_promoted_info)}")

        result = None
        valid_results = []
        for sa_all_ports, ba_all_promoted in zip(saa_possible_resolutions, baa_promoted_info):
            if b_debug:
                print(f"        compat: {sa_all_ports}")
                print(f"                {ba_all_promoted}")

            b_perfect_match = True

            for i, (input_type, s_target) in enumerate(zip(input_types, sa_all_ports)):
                if input_type.is_node() and len(input_type.node_data()) == 1:
                    input_type = list(input_type.node_data().values())[0]

                if b_debug:
                    print(f"            {input_type} <> {s_target}")

                # if the argument for this auto port is missing, check if it can
                # be inferred # todo: this looks sus double check this works
                if input_type == "auto" and s_target != "auto":
                    input_types[i] = s_target
                    continue

                # if there is an exact type match, no need to check for promotions
                if input_type == s_target and not any(ba_all_promoted):
                    if b_debug:
                        print("             -> exact match!")
                    continue
                    # return True, (sa_all_ports[:len(sa_input_port_types)], sa_all_ports[len(sa_input_port_types):])

                b_perfect_match = False

                # arbitrary overload
                if s_target == "*":
                    continue

                # array
                if s_target in ("[]", "[1]", "[2]", "[3]"):
                    if len(s_target) == 2:
                        if "<" in input_type.s:
                            continue
                        else:
                            s_target = "array"

                    elif int(s_target[1]) == input_type.s.count("<"):
                        continue

                    else:
                        s_target = f"{s_target[1]}D-array"

                # i_compat = _type.compatibility(_type.Type(s_target), _type.Type(s_input))
                # if i_compat != 0 and i_compat - _type.NUMERIC_AUTO_CONVERSION != 0:
                if not _type.promotable(_type.Type(input_type), _type.Type(s_target)):
                    s_msg = f"Cant promote '{input_type}' to '{s_target}' on port '{d_operator['inputs'][i]}'"
                    result = _error.BfTypeError, s_msg
                    if b_debug:
                        print(f"           -> {result}")
                    break

                # if s_input != s_target:
                #     s_msg = f"Cant promote '{s_input}' to '{s_target}' on port '{d_operator['inputs'][i]}'"
                #     result = _error.BfTypeError, s_msg
                #     if b_debug:
                #         print(result)
                #     continue

            else:
                valid_results.append((sa_all_ports[:len(sa_input_port_types)], sa_all_ports[len(sa_input_port_types):]))

            if b_perfect_match:
                if b_debug:
                    print(f"    Perfect match: {valid_results[-1]}")
                return True, valid_results[-1]

        if len(valid_results) == 1:
            if b_debug:
                print(f"    Only one valid result: {valid_results[0]}")
            return True, valid_results[0]

        if valid_results:
            if b_debug:
                print("    multiple valid results found. Checking compatibility")

            # check if those types have the same vector/matrix dimensionality
            sa_ref_inputs, sa_ref_outputs = valid_results[0]
            sa_ref_inputs = [t.base_type().s if t.is_array() else t.s for t in [_type.Type(s) for s in sa_ref_inputs]]

            print(f"        ref: {[s for s in sa_ref_inputs]}")

            for sa_other_inputs, sa_other_outputs in valid_results[1:]:
                sa_other_inputs = [t.base_type().s if t.is_array() else t.s for t in [_type.Type(s) for s in sa_other_inputs]]

                b_break = False
                for i, (ref, other) in enumerate(zip(sa_ref_inputs, sa_other_inputs)):
                    ref = _type.Type(ref)
                    other = _type.Type(other)
                    if ref.vector_dim() == other.vector_dim() and ref.matrix_dim() and other.matrix_dim():
                        continue

                    b_break = True
                    break

                if b_break:
                    break

            else:
                return True, valid_results[0]

            sa_names_in, _ = cls.get_port_names(s_func)
            return False, (_error.BfTypeError, f"Ambiguous promotion on port '{sa_names_in[i]}'")

        if result:
            return False, result
        return True, (sa_all_ports[:len(sa_input_port_types)], sa_all_ports[len(sa_input_port_types):])

    @classmethod
    def functions(cls):
        return cls._d_operators

    @classmethod
    def resolve_inputs_and_outputs(cls, s_func, input_types):
        if s_func not in cls._d_operators:
            return False, (_error.BfNameError, f"Operator/compound '{s_func}' does not exist!")

        d_operator = cls._d_operators[s_func]

        for i in range(len(input_types)):
            if input_types[i].is_node() and len(input_types[i].node_data()) == 1:
                input_types[i] = list(input_types[i].node_data().values())[0]

        # print(s_func,  30 * "=")
        d_overloads = d_operator["overloads"]
        result = (_error.BfNameError, f"No matching overload found for '{s_func}'")
        for _, (s_key, sa_output_port_types) in enumerate(d_overloads.items()):
            if _ > 0:
                break

            status, result = cls._resolve_inputs_and_outputs(
                    s_func=s_func,
                    d_operator=d_operator,
                    sa_input_port_types=[s for s in s_key.split("-") if s],
                    sa_output_port_types=sa_output_port_types,
                    input_types=input_types
            )
            if status:
                # print(" -- RESOLVED --")
                return status, ([_type.Type(t).s for t in result[0]], [_type.Type(t).s for t in result[1]])

            # print(result)

        return False, result

    @classmethod
    def function(cls, s_func):
        return cls._d_operators.resolves(s_func)

    @classmethod
    def get_port_types(cls, s_func):
        d_op = cls._d_operators[s_func]
        s_key = list(d_op["overloads"].keys())[0]
        sa_input_types = s_key.split("-")
        sa_output_types = d_op["overloads"][s_key]
        return sa_input_types, sa_output_types[:]

    @classmethod
    def get_all_port_types(cls, s_func):
        d_op = cls._d_operators[s_func]
        saa_input_types = []
        saa_output_types = []
        for s_key, sa_output_types in d_op["overloads"].items():
            saa_output_types.append(sa_output_types[:])
            saa_input_types.append([s for s in s_key.split("-") if s])

        return saa_input_types, saa_output_types

    @classmethod
    def get_port_names(cls, s_func):
        d_op = cls._d_operators[s_func]
        return d_op["inputs"], d_op["outputs"]

    @classmethod
    def is_associative(cls, s_func):
        d_op = cls._d_operators[s_func]
        return d_op["has_auto_output"] and len(d_op["outputs"]) ==1 and len(d_op["inputs"]) == 0 and not d_op["has_auto_input"]

    @classmethod
    def is_fake_associative(cls, s_func):
        s_func = cls.function(s_func)
        if not s_func:
            return False

        if s_func.endswith("::build_string"):
            return True

        return False

    @classmethod
    def load_conversion_overloads(cls):
        cls.define_overload(
                "Core::Type_Conversion::to_type_any",
                (ALL_TYPES, [])
        )

        cls.define_overload(
                "Core::Type_Conversion::from_type_any",
                (ALL_TYPES, [None])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_bool",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "bool")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_char",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "char")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_unsigned_char",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "uchar")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_short",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "short")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_unsigned_short",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "ushort")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_int",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "int")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_unsigned_int",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "uint")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_long",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "long")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_unsigned_long",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "ulong")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_float",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "float")])
        )

        cls.define_overload(
                "Core::Type_Conversion::to_double",
                (FLOATING | INTEGER | BOOL, [lambda x: _replace_base(x, "double")])
        )

        cls.define_overload(
                "Core::Conversion::degrees_to_radians",
                (FLOATING & (SIMPLE | VECTOR2 | VECTOR3), [None])
        )

        cls.define_overload(
                "Core::Conversion::radians_to_degrees",
                (FLOATING & (SIMPLE | VECTOR2 | VECTOR3), [None])
        )

        cls.force_auto_ports("Core::String::number_to_string", "string")
        cls.define_overload("Core::String::number_to_string", ((NUMERIC | BOOL) & SIMPLE, [lambda x: _replace_full_base(x, "string")]))

        cls.define_overload("Core::Conversion::vector2_to_scalar", (NUMERIC & VECTOR2, [_to_scalar, _to_scalar]))
        cls.define_overload("Core::Conversion::vector3_to_scalar", (NUMERIC & VECTOR3, [_to_scalar, _to_scalar, _to_scalar]))
        cls.define_overload("Core::Conversion::vector3_to_scalar", (FIELD3, [lambda x: _replace_full_base(x, "Core::Fields::ScalarField"), lambda x: _replace_full_base(x, "Core::Fields::ScalarField"), lambda x: _replace_full_base(x, "Core::Fields::ScalarField")]))
        cls.define_overload("Core::Conversion::vector4_to_scalar", (NUMERIC & VECTOR4, [_to_scalar, _to_scalar, _to_scalar, _to_scalar]))
        cls.define_overload("Core::Conversion::vector4_to_vector3", (NUMERIC & VECTOR4, [_to_vec3, _to_scalar]))

        cls.define_overload_resolver("Core::Conversion::scalar_to_vector2", _resolver.scalar_to_vec2)
        cls.define_overload_resolver("Core::Conversion::scalar_to_vector3", _resolver.scalar_to_vec3)
        cls.define_overload_resolver("Core::Conversion::scalar_to_vector4", _resolver.scalar_to_vec4)
        cls.define_overload_resolver("Core::Conversion::vector3_to_vector4", _resolver.vec3_to_vec4)

        cls.define_overload("Core::Transform::interpret_auto_port_as_transform", (FLOATING & MATRIX4x4, []))
        cls.define_overload("Core::Transform::interpret_auto_port_as_transform", (OBJECT - ARRAY, []))

        cls.define_overload("Geometry::Common::interpret_auto_port_as_scalar", (AUTO_SCALAR, []))
        cls.define_overload("Geometry::Common::sample_interpreted_auto_port_as_scalar", (AUTO_SCALAR, []))

        cls.define_overload("Geometry::Common::interpret_auto_port_as_vector", (AUTO_VECTOR, []))
        cls.define_overload("Geometry::Common::sample_interpreted_auto_port_as_vector", (AUTO_VECTOR, []))

    @classmethod
    def load_array_overloads(cls):
        cls.force_auto_ports("Core::Array::all_true_in_array", "array", "all_true")
        cls.define_overload("Core::Array::all_true_in_array", (ARRAY & BOOL, [_arrDown]))

        cls.force_auto_ports("Core::Array::any_true_in_array", "array", "any_true")
        cls.define_overload("Core::Array::any_true_in_array", (ARRAY & BOOL, [_arrDown]))

        cls.define_overload("Core::Array::array_bounds", (ARRAY, [_arrDown, _arrDown]))
        cls.define_overload("Core::Array::array_bounds_impl", (ARRAY, [_arrDown, _arrDown]))
        cls.define_overload("Core::Array::array_dimensions", (ARRAY, []))
        cls.define_overload("Core::Array::array_size", (ARRAY, []))
        cls.define_overload("Core::Array::array_is_empty", (ARRAY, ["bool"]))
        cls.define_overload("Core::Array::cumulative_sum_array", (ARRAY, [None]))
        cls.define_overload("Core::Array::empty_array", (ALL_TYPES - ARRAY3, [_arrUp]))
        cls.define_overload("Core::Array::filter_array", (ARRAY, [None, "array<long>"]))
        cls.define_overload("Core::Array::find_all_in_array", (ARRAY, [_arrDown]))
        cls.define_overload("Core::Array::find_in_array", (ARRAY, [_arrDown]))
        cls.define_overload("Core::Array::find_in_sorted_array", (ARRAY, [_arrDown]))
        cls.define_overload("Core::Array::first_in_array", (ARRAY, [_arrDown]))
        cls.define_overload("Core::Array::flatten_nested_array", (ARRAY, [_arrFlat]))
        cls.define_overload("Core::Array::get_array_indices", (ARRAY, []), (INTEGER, [_arrUp]))
        cls.define_overload("Core::Array::get_from_array", (ARRAY, [_arrDown]))
        cls.define_overload("Core::Array::interleave_arrays", (ARRAY, [None, None]))
        cls.define_overload("Core::Array::intersect_arrays", (ARRAY, [None, None]))
        cls.define_overload("Core::Array::last_in_array", (ARRAY, [_arrDown]))
        cls.define_overload("Core::Array::prefix_sum", (((INTEGER | FLOATING) & SIMPLE & ARRAY), [None, None]))
        cls.define_overload("Core::Array::remove_from_array", (ARRAY, [None]))
        cls.define_overload("Core::Array::resize_array", (ARRAY, [_arrDown, None]))
        cls.define_overload("Core::Array::reverse_array", (ARRAY, [None]))
        cls.define_overload("Core::Array::reverse_find_in_array", (ARRAY, [_arrDown]))
        cls.define_overload("Core::Array::sequence_array", ((FLOATING | INTEGER) - ARRAY, [None, _arrUp]))
        cls.define_overload("Core::Array::set_in_array", (ARRAY, [_arrDown, None]))
        cls.define_overload("Core::Array::shuffle_array", (ARRAY, [None]))
        cls.define_overload("Core::Array::slice_array", (ARRAY, [None]))
        cls.define_overload("Core::Array::small_slice", (ARRAY, [None]))
        cls.define_overload("Core::Array::sort_array", (ARRAY & SIMPLE & (INTEGER | FLOATING | STRING), [None]))
        cls.define_overload("Core::Array::sort_array_and_remove_duplicates", (ARRAY & SIMPLE & (INTEGER | FLOATING | STRING), [None]))
        cls.define_overload("Core::Array::sort_array_with_indices", (ARRAY & SIMPLE & (INTEGER | FLOATING | STRING), [None]))
        cls.define_overload("Core::Array::sum_array", (ARRAY & SIMPLE & (INTEGER | FLOATING | STRING), [_arrDown]))
        cls.define_overload("Core::Array::sum_array_impl", (ARRAY & (INTEGER | FLOATING), [_arrDown]))

        cls.define_overload("Core::Math::get_from_interpolated_array", (ARRAY, ["float", _arrDown]))
        cls.define_overload("Core::Math::get_from_interpolated_array", (ARRAY, ["double", _arrDown]))

    @classmethod
    def load_graph_overloads(cls):
        cls.define_overload("Core::Graph::pass", (ALL_TYPES, [None]))
        cls.define_overload("Diagnostic::Profiling::profiler_start", (ALL_TYPES, [None]))
        cls.define_overload("Diagnostic::Profiling::profiler_end", (ALL_TYPES, [None]))

        cls.define_overload_resolver("Rendering::Terminals::final_mode_switch", _resolver.any_n_to_1)

        cls.define_overload("Core::Error::error", (ALL_TYPES, [None]))
        cls.define_overload("Core::Logging::log_message", (ALL_TYPES, [None]))

        cls.define_overload("Core::Compound_Tests::expect_type", (ALL_TYPES, []), (ALL_TYPES, ["string"]))
        cls.define_overload_resolver("Core::Compound_Tests::expect_equal", _resolver.expect_equal)
        cls.define_overload_resolver("Core::Compound_Tests::expect_members_equal", _resolver.expect_equal)
        cls.define_overload_resolver("Core::Compound_Tests::expect_almost_equal", _resolver.expect_almost_equal)
        cls.define_overload_resolver("Core::Compound_Tests::expect_arrays_equal", _resolver.expect_arrays_equal)

    @classmethod
    def load_object_overloads(cls):
        cls.define_overload("Core::Object::set_property", (ALL_TYPES, []))
        cls.force_auto_ports("Core::Object::get_property", "default_and_type", "value")
        cls.define_overload("Core::Object::get_property", (ALL_TYPES, [None]))

        cls.force_auto_ports("Modeling::Primitive::create_mesh_cube", "width")

    @classmethod
    def load_constants_overloads(cls):
        cls.define_overload("Core::Constants::identity", (NUMERIC & MATRIX, [None]))
        cls.define_overload("Core::Constants::identity", (FLOATING & VECTOR4, [None]))

        cls.define_overload("Core::Constants::default_value", (ALL_TYPES, [None]))

        cls.define_overload("Core::Constants::zero", (NUMERIC, [None]))
        cls.define_overload("Core::Constants::one", (NUMERIC, [None]))
        cls.define_overload("Core::Constants::golden_ratio", (NUMERIC, [None]))
        cls.define_overload("Core::Constants::e", (NUMERIC, [None]))
        cls.define_overload("Core::Constants::pi", (NUMERIC, [None]))
        cls.define_overload("Core::Constants::tau", (NUMERIC, [None]))

        cls.define_overload("Core::Constants::numeric_min", (NUMERIC | BOOL, [None]))
        cls.define_overload("Core::Constants::numeric_max", (NUMERIC | BOOL, [None]))
        cls.define_overload("Core::Constants::numeric_small", (NUMERIC, [_to_float]))

    @classmethod
    def load_logic_overloads(cls):
        cls.define_overload_resolver("Core::Logic::if", _resolver.if_)
        cls.define_overload_resolver("Core::Logic::members_if", _resolver.members_if)

        cls.define_overload_resolver("Core::Logic::equal", lambda *args: _resolver.compare(*args, op="=="))
        cls.define_overload_resolver("Core::Logic::not_equal", lambda *args: _resolver.compare(*args, op="!="))
        cls.define_overload_resolver("Core::Logic::greater_or_equal", lambda *args: _resolver.compare(*args, op=">="))
        cls.define_overload_resolver("Core::Logic::less_or_equal", lambda *args: _resolver.compare(*args, op="<=>="))
        cls.define_overload_resolver("Core::Logic::greater", lambda *args: _resolver.compare(*args, op="=>"))
        cls.define_overload_resolver("Core::Logic::less", lambda *args: _resolver.compare(*args, op="<"))

        cls.define_overload("Core::Logic::almost_equal", ((FLOATING - MATRIX) | (FLOATING & MATRIX_SQUARE), [None, None]))

        cls.define_overload_resolver("Core::Logic::and", _resolver.logic)
        cls.define_overload_resolver("Core::Logic::or", _resolver.logic)
        cls.define_overload_resolver("Core::Logic::xor", _resolver.logic)

        cls.define_overload("Core::Logic::not", (BOOL, [None]))

        cls.force_auto_ports("Core::Logic::all_members_true", "output")
        cls.define_overload("Core::Logic::all_members_true", (BOOL & (VECTOR | MATRIX), [lambda x: _replace_full_base(x, "bool")]))

        cls.force_auto_ports("Core::Logic::any_members_true", "output")
        cls.define_overload("Core::Logic::any_members_true", (BOOL & (VECTOR | MATRIX), [lambda x: _replace_full_base(x, "bool")]))

        cls.define_overload("Core::Logic::any_members_true", (BOOL & (VECTOR | MATRIX), [lambda x: _replace_full_base(x, "bool")]))

        cls.define_overload_resolver("Core::Logic::members_equal", _resolver.members)
        cls.define_overload_resolver("Core::Logic::members_not_equal", _resolver.members)
        cls.define_overload_resolver("Core::Logic::members_greater", _resolver.members)
        cls.define_overload_resolver("Core::Logic::members_greater_or_equal", _resolver.members)
        cls.define_overload_resolver("Core::Logic::members_less", _resolver.members)
        cls.define_overload_resolver("Core::Logic::members_less_or_equal", _resolver.members)

    @classmethod
    def load_math_overloads(cls):
        cls.define_overload("Core::Math::absolute_value", (NUMERIC - UNSIGNED, [None]))
        cls.define_overload("Core::Math::absolute_value", (LONG & UNSIGNED, [lambda x: _replace_base(x, "double")]))
        cls.define_overload("Core::Math::absolute_value", (INT & UNSIGNED, [lambda x: _replace_base(x, "float")]))

        cls.define_overload_resolver("Core::Math::remainder", _resolver.remainder)
        cls.define_overload_resolver("Core::Math::modulo", _resolver.modulo)
        cls.define_overload("Core::Math::split_fraction", (FLOATING - MATRIX, [None, None]))

        cls.define_overload("Core::Math::truncate", (FLOATING, [None]))
        cls.define_overload("Core::Math::twice_of", (NUMERIC, [None]))
        cls.define_overload("Core::Math::two_to_power_of", (NUMERIC, [None]))
        cls.define_overload("Core::Math::half_of", (NUMERIC, [None]))
        cls.define_overload("Core::Math::square_root", (FLOATING, [None]))
        cls.define_overload("Core::Math::cube_root", (FLOATING, [None]))
        cls.define_overload("Core::Math::one_over", (FLOATING, [None]))

        cls.define_overload_resolver("Core::Math::lerp", _resolver.lerp)
        cls.define_overload_resolver("Core::Math::linear_interpolate", _resolver.linear_interpolate)
        cls.define_overload_resolver("Core::Math::linear_interpolate_normalized", _resolver.lerp_vec)

        cls.define_overload("Core::Math::round_to_ceiling", (FLOATING, [None]))
        cls.define_overload("Core::Math::round_to_floor", (FLOATING, [None]))
        cls.define_overload("Core::Math::round_to_nearest", (FLOATING, [None]))

        cls.define_overload("Core::Math::log_base_e", (FLOATING, [None]))
        cls.define_overload("Core::Math::log_base_two", (FLOATING, [None]))
        cls.define_overload("Core::Math::log_base_ten", (FLOATING, [None]))

        cls.define_overload("Core::Math::exponential", (FLOATING, [None]))

        cls.define_overload("Core::Math::get_member", (NUMERIC | BOOL, [_to_scalar]))

        cls.define_overload("Core::Math::increment", (NUMERIC, [None]))
        cls.define_overload("Core::Math::decrement", (NUMERIC, [None]))

        cls.define_overload("Core::Math::normalize", ((FLOATING & VECTOR) - BIG, [None]))  #lambda x: _replace_base(x, "float")]))
        cls.define_overload("Core::Math::normalize", ((FLOATING & VECTOR) & BIG, [None]))  #lambda x: _replace_base(x, "double")]))
        cls.define_overload("Core::Math::normalize", (FIELD3, [lambda x: _replace_base(x, "Core::Fields::ScalarField")]))

        cls.define_overload("Core::Math::length", ((FLOATING & VECTOR) - BIG, [lambda x: _replace_full_base(x, "float")]))
        cls.define_overload("Core::Math::length", ((FLOATING & VECTOR) & BIG, [lambda x: _replace_full_base(x, "double")]))
        cls.define_overload("Core::Math::length", (FIELD3, [lambda x: _replace_base(x, "Core::Fields::ScalarField")]))

        cls.define_overload_resolver("Core::Math::distance", _resolver.distance)
        cls.define_overload_resolver("Core::Math::distance_float_ULP", _resolver.distance_float_ULP)
        cls.define_overload_resolver("Core::Math::equivalent_float_ULP", _resolver.equivalent_float_ULP)
        cls.define_overload_resolver("Core::Math::equivalent_float_epsilon", _resolver.equivalent_float_epsilon)

        cls.define_overload("Core::Math::length_squared", ((FLOATING & VECTOR) - BIG, [lambda x: _replace_full_base(x, "float")]))
        cls.define_overload("Core::Math::length_squared", ((FLOATING & VECTOR) & BIG, [lambda x: _replace_full_base(x, "double")]))
        cls.define_overload("Core::Math::length_squared", (FIELD3, [lambda x: _replace_base(x, "Core::Fields::ScalarField")]))

        cls.define_overload("Core::Math::direction_and_length", ((FLOATING & VECTOR) - BIG, [None, lambda x: _replace_full_base(x, "float"), lambda x: _replace_full_base(x, "float")]))
        cls.define_overload("Core::Math::direction_and_length", ((FLOATING & VECTOR) & BIG, [None, lambda x: _replace_full_base(x, "double"), lambda x: _replace_full_base(x, "double")]))
        cls.define_overload("Core::Math::direction_and_length", (FIELD3, [None, lambda x: _replace_full_base(x, "Core::Fields::ScalarField"), lambda x: _replace_full_base(x, "Core::Fields::ScalarField")]))

        cls.define_overload_resolver("Core::Math::cross", _resolver.cross)
        cls.define_overload_resolver("Core::Math::dot", _resolver.dot)
        cls.define_overload_resolver("Core::Math::change_range", _resolver.change_range)

        cls.define_overload("Core::Math::euler_to_rotation_vector", ((FLOAT & VECTOR3), [None]))
        cls.define_overload("Core::Math::euler_to_rotation_vector", (FIELD3, [None]))
        cls.define_overload("Core::Math::euler_to_quaternion", (FLOAT & VECTOR3, [_to_vec4]))

        cls.define_overload_resolver("Core::Math::within_bounds", _resolver.within_bounds)

        cls.define_overload_resolver("Core::Math::quaternion_slerp", _resolver.quaternion_slerp)
        cls.define_overload_resolver("Core::Math::multiply_quaternions", _resolver.multiply_quaternions)
        cls.define_overload_resolver("Core::Math::normal_and_tangent_to_orientation", _resolver.normal_and_tangent_to_orientation)
        cls.define_overload_resolver("Core::Math::rotation_between_vectors", _resolver.rotation_between_vectors)

        cls.define_overload_resolver("Core::Math::rotation_around_position_to_matrix", _resolver.rotation_around_position_to_matrix)

        cls.define_overload_resolver("Core::Math::rotate_by_quaternion", _resolver.rotate_by_quaternion)
        cls.define_overload_resolver("Core::Math::rotate_vector_by_matrix", _resolver.rotate_by_matrix)
        cls.define_overload_resolver("Core::Math::transform_vector_as_direction", _resolver.transform_vector_as)
        cls.define_overload_resolver("Core::Math::transform_vector_as_normal", _resolver.transform_vector_as)
        cls.define_overload_resolver("Core::Math::transform_vector_as_position", _resolver.transform_vector_as)

        cls.define_overload("Core::Math::project_vector", (FLOATING - BIG & VECTOR3, [None, None, None]))
        cls.define_overload("Core::Math::project_vector", (FLOATING & BIG & VECTOR3, [None, None, None]))
        cls.define_overload("Core::Math::project_vector", (FIELD3, [None, None, None]))

        for s in ["sin", "cos", "tan"]:
            cls.define_overload(f"Core::Math::{s}", (NUMERIC - BIG, [lambda x: _replace_base(x, "float")]))
            cls.define_overload(f"Core::Math::{s}", (NUMERIC & BIG, [lambda x: _replace_base(x, "double")]))
            cls.define_overload(f"Core::Math::{s}_hyperbolic", (NUMERIC - BIG, [lambda x: _replace_base(x, "float")]))
            cls.define_overload(f"Core::Math::{s}_hyperbolic", (NUMERIC & BIG, [lambda x: _replace_base(x, "double")]))
            cls.define_overload(f"Core::Math::a{s}", (NUMERIC - BIG, [lambda x: _replace_base(x, "float")]))
            cls.define_overload(f"Core::Math::a{s}", (NUMERIC & BIG, [lambda x: _replace_base(x, "double")]))
            cls.define_overload(f"Core::Math::a{s}_hyperbolic", (NUMERIC - BIG, [lambda x: _replace_base(x, "float")]))
            cls.define_overload(f"Core::Math::a{s}_hyperbolic", (NUMERIC & BIG, [lambda x: _replace_base(x, "double")]))

        cls.define_overload_resolver("Core::Math::atan_2D", _resolver.atan_2D)

        cls.define_overload_resolver("Core::Math::power", _resolver.power)
        cls.define_overload_resolver("Core::Math::negate", _resolver.negate)
        cls.define_overload_resolver("Core::Math::copy_sign", _resolver.copy_sign)

        cls.define_overload("Core::Math::transpose_matrix", (MATRIX, [_transpose]))
        cls.define_overload("Core::Math::inverse_matrix", (FLOATING & MATRIX_SQUARE, [None]))
        cls.define_overload("Core::Math::matrix_determinant", (MATRIX_SQUARE - BIG, [lambda x: _replace_full_base(x, "float")]))
        cls.define_overload("Core::Math::matrix_determinant", (MATRIX_SQUARE & BIG, [lambda x: _replace_full_base(x, "double")]))
        cls.define_overload("Core::Math::matrix_is_identity", (MATRIX, [lambda x: _replace_full_base(x, "bool")]))

        cls.define_overload("Core::Math::matrix_to_quaternion", (FLOATING & MATRIX3x3, [_to_vec4]))
        cls.define_overload("Core::Math::matrix_to_SRT", (FLOATING & MATRIX4x4, [_to_vec3, _to_vec3, _to_vec4, _to_vec3]))
        cls.define_overload_resolver("Core::Math::SRT_to_matrix", _resolver.srt_to_matrix)

        cls.define_overload("Core::Math::quaternion_to_matrix", (FLOATING & VECTOR4, [_to_mtx3x3]))
        cls.define_overload("Core::Math::quaternion_to_axis_angle", (FLOATING & VECTOR4, [_to_vec3, _to_scalar]))
        cls.define_overload("Core::Math::quaternion_to_rotation_vector", (FLOATING & VECTOR4, [_to_vec3]))
        cls.define_overload("Core::Math::quaternion_to_euler", (FLOATING & VECTOR4, [_to_vec3]))
        cls.define_overload("Core::Math::rotation_vector_to_quaternion", (FLOATING & VECTOR3, [_to_vec4]))
        cls.define_overload("Core::Math::transform_to_rotation_matrix", (FLOATING & MATRIX4x4, [_to_mtx3x3]))
        cls.define_overload_resolver("Core::Math::axis_angle_to_quaternion", _resolver.axis_angle_to_quaternion)

        cls.define_overload("Core::Math::find_orthogonal_vectors", (FLOATING & VECTOR3, [None, None]))

        cls.define_overload("Core::Math::quaternion_invert", (FLOATING & VECTOR4, [None]))

        cls.define_overload_resolver("Core::Math::clamp", _resolver.clamp)

        cls.define_overload("Core::Math::bitwise_not", (INTEGER, [None]))
        cls.define_overload_resolver("Core::Math::bitwise_and", _resolver.bitwise)
        cls.define_overload_resolver("Core::Math::bitwise_or", _resolver.bitwise)
        cls.define_overload_resolver("Core::Math::bitwise_xor", _resolver.bitwise)
        cls.define_overload_resolver("Core::Math::bitwise_shift_left", _resolver.bitwise)
        cls.define_overload_resolver("Core::Math::bitwise_shift_left_circular", _resolver.bitwise)
        cls.define_overload_resolver("Core::Math::bitwise_shift_right", _resolver.bitwise)
        cls.define_overload_resolver("Core::Math::bitwise_shift_right_circular", _resolver.bitwise)

        cls.define_overload("Core::FCurve::evaluate_fcurve", (FLOATING & SIMPLE, [None]))

        cls.define_overload("Rigging::Solver::Utils::enabled_with_weight", (NUMERIC & SIMPLE - ARRAY, []))
        cls.define_overload("Rigging::Solver::Utils::equivalent_weight", (NUMERIC & SIMPLE - ARRAY, []))

    @classmethod
    def load_geometry_overloads(cls):
        cls.define_overload("Geometry::Properties::points_to_transforms", (OBJECT-ARRAY, ["array<Math::float4x4>", "array<Math::float4x4>"]))
        cls.define_overload("Geometry::Strands::create_strands_from_counts", (INTEGER & ARRAY1, []))
        cls.define_overload("Geometry::Instances::flatten_instance_selection", (OBJECT - ARRAY, ["array<long>", "array<Object>"]))

        cls.define_overload("Geometry::Query::get_closest_locations", ((FLOAT & VECTOR3) - ARRAY2 - ARRAY3, [lambda x: _replace_full_base(x, "Geometry::Common::GeoLocation"), lambda x: _replace_full_base(x, "bool")]))
        cls.define_overload("Geometry::Query::get_closest_point", ((FLOAT & VECTOR3) - ARRAY2 - ARRAY3, [lambda x: _replace_full_base(x, "Geometry::Common::GeoLocation"), lambda x: _replace_full_base(x, "long"), lambda x: _replace_full_base(x, "bool")]))
        cls.define_overload("Geometry::Query::sample_closest_accelerator", ((FLOAT & VECTOR3) - ARRAY2 - ARRAY3, [lambda x: _replace_full_base(x, "Geometry::Common::GeoLocation"), lambda x: _replace_full_base(x, "bool")]))
        cls.define_overload("Geometry::Query::sample_closest_point_accelerator", ((FLOAT & VECTOR3) - ARRAY2 - ARRAY3, [lambda x: _replace_full_base(x, "long"), lambda x: _replace_full_base(x, "bool")]))
        cls.define_overload("Geometry::Query::get_points_in_radius", ((FLOAT & VECTOR3) - ARRAY2 - ARRAY3, [lambda x: _replace_full_base(x, "array<Geometry::Common::GeoLocation>"), lambda x: _replace_full_base(x, "array<long>")]))
        cls.define_overload("Geometry::Query::sample_closest_in_radius_accelerator", ((FLOAT & VECTOR3) - ARRAY2 - ARRAY3, [lambda x: _replace_full_base(x, "array<long>")]))

        cls.define_overload("Geometry::Query::sample_points_by_radius", (FLOAT - MATRIX - ARRAY3, [_arrUp]))

        cls.define_overload("Geometry::Query::sample_property", (FLOATING - ARRAY, [_arrUp]))
        cls.define_overload("Geometry::Query::sample_property_2D", (FLOATING - ARRAY, [lambda x: _arrUp(_arrUp(x))]))

        cls.define_overload("Geometry::Properties::get_geo_component_indices", (INTEGER & SIMPLE - ARRAY3, [_arrUp]))
        cls.define_overload("Geometry::Properties::get_geo_property_or_default", (ALL_TYPES, [_arrUp]))
        cls.define_overload("Geometry::Properties::set_geo_property_data", (ALL_TYPES, []))

        cls.define_overload("Geometry::Properties::get_geo_property", (ARRAY, [None, _arrDown]))
        cls.define_overload("Geometry::Properties::get_geo_property_check", (ARRAY, [None, _arrDown]))
        cls.define_overload("Geometry::Properties::get_indexed_geo_property", (ARRAY, [None, _arrDown]))

        cls.define_overload("Geometry::Mesh::get_mesh_UVs", (FLOAT & (VECTOR2 | VECTOR3), [_arrFlat, "array<uint>"]))
        cls.define_overload("Geometry::Mesh::sample_mesh_UVs", (FLOAT & (VECTOR2 | VECTOR3) - ARRAY, [_arrUp]))
        cls.define_overload("Geometry::Mesh::set_mesh_UVs", (FLOAT & (VECTOR2 | VECTOR3) & ARRAY1, []))

        cls.define_overload("Geometry::Tags::interpret_auto_port_as_component_tag", (AUTO_TAG, []))
        cls.define_overload("Geometry::Tags::set_component_tag", (AUTO_TAG, []))

        cls.define_overload("Geometry::Tags::tag_by_angle_between_vectors",
                            (AUTO_TAG, []),  # elements_to_tag
                            (AUTO_VECTOR, []),  # vector_property
                            (NUMERIC & SIMPLE - ARRAY3 - ARRAY2, []),  # weights_scale
                            (AUTO_VECTOR, []),  # direction
                            (AUTO_SCALAR, []),  # max_angle
        )

        cls.force_auto_ports("Geometry::Tags::tag_by_threshold", "elements_to_tag", "threshold_property", "min", "max")
        cls.define_overload("Geometry::Tags::tag_by_threshold",
                            ({"array<bool>", "array<long>", "long", "string"}, []),  # elements_to_tag
                            (AUTO_SCALAR, []),  # threshold_property
                            (AUTO_SCALAR, []),  # min
                            (AUTO_SCALAR, []),  # max
        )

        cls.force_auto_ports("Geometry::Tags::tag_inside_geometry", "elements_to_tag", "position_property", "weights_scale")
        cls.define_overload("Geometry::Tags::tag_inside_geometry",
                            (AUTO_TAG, []),  # elements_to_tag
                            (AUTO_VECTOR, []),  # position_property
                            (AUTO_SCALAR, []),  # weights_scale
        )

        cls.force_auto_ports("Geometry::Tags::tag_strand_ends", "strands_filter", "weights_scale", "start", "end")
        cls.define_overload("Geometry::Tags::tag_strand_ends",
                            (AUTO_TAG, []),  # strands_filter
                            (AUTO_SCALAR, []),  # weights_scale
                            (AUTO_SCALAR, []),
                            (AUTO_SCALAR, [])
        )

        cls.define_overload("Modeling::Mesh::disconnect_mesh_faces", (AUTO_SCALAR, []))
        cls.define_overload("Modeling::Points::cull_points", (AUTO_SCALAR, ["array<long>", "array<long>"]))

        cls.define_overload("Modeling::Points::randomize_point_rotation", (AUTO_SCALAR, ["array<Math::float4>"]))
        cls.define_overload("Modeling::Points::randomize_point_scale", (AUTO_SCALAR, ["array<Math::float3>"]))
        cls.define_overload("Modeling::Points::randomize_point_translation", (AUTO_SCALAR, ["array<Math::float3>"]))
        cls.define_overload("Modeling::Points::transform_points", (AUTO_SCALAR, []))

        cls.define_overload("Modeling::Instances::bake_instanced_geometry", ({"Object"}, ["Object", "Object", "Object"]))
        cls.define_overload("Modeling::Instances::create_instances", (AUTO_SCALAR, ["Object"]))

        cls.define_overload("Geometry::Volume::remap_property", (FLOAT-ARRAY, []), (FLOAT-ARRAY, []))
        cls.define_overload("Geometry::Volume::remap_property", (DOUBLE-ARRAY-VECTOR4-MATRIX, []), (DOUBLE-ARRAY-VECTOR4-MATRIX, []))

        cls.define_overload("Geometry::Properties::set_geo_property", (ALL_TYPES-ARRAY3-ARRAY2, [None]))
        cls.define_overload("Geometry::Properties::set_geo_property", (ALL_TYPES-ARRAY3-ARRAY2, [_arrUp]))

        cls.define_overload("Geometry::Properties::set_indexed_geo_property", (ALL_TYPES-ARRAY3-ARRAY2, [None]))
        cls.define_overload("Geometry::Properties::set_indexed_geo_property", (ALL_TYPES-ARRAY3-ARRAY2, [_arrUp]))

        cls.define_overload("Modeling::Points::scatter_points", (AUTO_SCALAR, []), (AUTO_VECTOR, []), (AUTO_VECTOR, []))

        cls.define_overload_resolver("Geometry::Common::switch_is_a", _resolver.switch_is_a)
        cls.define_overload_resolver("Geometry::Common::randomize_geo_property", _resolver.randomize_geo_property)

        cls.define_overload("Modeling::Points::translate_points", (AUTO_SCALAR, []), (AUTO_VECTOR, ["array<Math::float3>"]))
        cls.define_overload("Modeling::Points::rotate_points", (AUTO_SCALAR, []), (AUTO_VECTOR, []), (AUTO_SCALAR, ["array<Math::float4>"]))
        cls.define_overload("Modeling::Points::scale_points", (AUTO_SCALAR, []), (AUTO_VECTOR, ["array<Math::float3>"]))
        cls.define_overload("Modeling::Points::displace_points", (AUTO_SCALAR, []), (AUTO_VECTOR, ["Object"]))
        cls.define_overload("Modeling::Points::orient_points_by_geometry", (AUTO_VECTOR, []), (AUTO_VECTOR, []), (AUTO_SCALAR, ["Object", "array<Math::float4>"]))

        cls.define_overload("Geometry::Strands::strands_basis_to_orientation", (AUTO_VECTOR, ["array<Math::float4>"]))

        cls.define_overload("Geometry::Query::get_raycast_locations", ({"Math::float3", "array<Math::float3>"}, [None, lambda x: _replace_full_base(x, "Geometry::Common::GeoLocation"), lambda x: _replace_full_base(x, "bool")]))
        cls.define_overload("Geometry::Query::sample_raycast_accelerator", ({"Math::float3", "array<Math::float3>"}, [None, lambda x: _replace_full_base(x, "Geometry::Common::GeoLocation"), lambda x: _replace_full_base(x, "bool")]))

        cls.define_overload("Modeling::Points::randomize_selection", ({"Object"}, []), (AUTO_SCALAR, ["Object", "array<long>"]))
        cls.define_overload("Modeling::Points::randomize_selection_by_probabilities", ({"Object"}, []), (AUTO_SCALAR, ["Object", "array<long>"]))

        types = (FLOAT - MATRIX | FLOAT & (MATRIX3x3 | MATRIX4x4 | MATRIX4x2) | DOUBLE & SIMPLE | DOUBLE & VECTOR3) - ARRAY
        # I know! Right???
        # I also dont know if thats on purpose or a bug...
        cls.define_overload("Geometry::Query::sample_volume", ({"Object", "array<Math::float3>"}, []), (types, [_arrUp]))

        cls.define_overload("Geometry::Query::sample_volume_gradient", ({"Object", "array<Math::float3>"}, []), ({"float", "double"}, [lambda x: _arrUp(_to_vec3(x))]))

    @classmethod
    def load_ml_overloads(cls):
        for s in ["CELU", "ELU", "PReLU", "RReLU", "ReLU", "ReLU6", "SELU", "hard_shrink", "hard_sigmoid", "hard_swish",
                  "hard_tanh", "leaky_ReLU", "log_sigmoid", "mish", "sigmoid", "soft_plus", "soft_shrink", "soft_sign",
                  "tanh", "tanh_shrink", "threshold"]:
            cls.define_overload(f"MachineLearning::Activation::activation_{s}", (NUMERIC - BIG, [lambda x: _replace_base(x, "float")]))
            cls.define_overload(f"MachineLearning::Activation::activation_{s}", (NUMERIC & BIG, [lambda x: _replace_base(x, "double")]))

        # I believe this should match the lerp signature
        cls.define_overload_resolver("MachineLearning::Utils::z_score_denormalize", _resolver.lerp)
        cls.define_overload_resolver("MachineLearning::Utils::z_score_normalize", _resolver.lerp)

        _base = (INT | LONG | FLOAT | DOUBLE)
        cls.define_overload("File::NumPy::read_NumPy", (_base & SIMPLE | _base & MATRIX_SQUARE | _base & VECTOR, [None, "array<int>", "string", "bool"]))
        cls.define_overload("File::NumPy::write_NumPy", (_base & SIMPLE | _base & MATRIX_SQUARE | _base & VECTOR, [None, "bool", "string"]))


    @classmethod
    def load_random_overloads(cls):
        cls.force_auto_ports("Core::Randomization::fractal_noise", "noise")
        cls.define_overload("Core::Randomization::fractal_noise", (LONG | FLOAT, [lambda x: _replace_full_base(x, "float")]))

        cls.force_auto_ports("Core::Randomization::fractal_turbulence", "noise")
        cls.define_overload("Core::Randomization::fractal_turbulence", (LONG | FLOAT, [lambda x: _replace_full_base(x, "Math::float3")]))

        cls.define_overload("Core::Randomization::random_value_array", (NUMERIC | BOOL, [_arrUp]))

        cls.define_overload("Core::Randomization::simplex_noise", (FLOATING - MATRIX, [_to_scalar]))

        cls.define_overload_resolver("Core::Randomization::random_value", _resolver.random_)

    @classmethod
    def load_display_overloads(cls):
        cls.define_overload("Diagnostic::Display::assign_diagnostic_material", (FLOAT & VECTOR3, ["Object"]))
        cls.define_overload("Diagnostic::Display::assign_diagnostic_material", (STRING - ARRAY, ["Object"]))
        cls.define_overload("Diagnostic::Display::assign_diagnostic_material", (FIELDS, ["Object"]))
        cls.define_overload("Diagnostic::Display::assign_diagnostic_material", (FLOAT & SIMPLE, ["Object"]))

        cls.define_overload("Diagnostic::Display::location_scope", (GEOLOCATION, ["array<Object>"]))

        cls.force_auto_ports("Diagnostic::Display::point_scope", "diagnostic_geo")
        cls.define_overload("Diagnostic::Display::point_scope", (OBJECT - ARRAY2 - ARRAY3, ["array<Object>"]))

        cls.force_auto_ports("Diagnostic::Display::volume_scope", "diagnostic_geo")
        cls.define_overload("Diagnostic::Display::volume_scope", (OBJECT - ARRAY2 - ARRAY3, ["array<Object>"]))

        cls.force_auto_ports("Diagnostic::Display::particle_collision_scope", "point_size", "arrow_size", "point_color", "arrow_color")
        cls.define_overload("Diagnostic::Display::particle_collision_scope", (OBJECT - ARRAY, []), (AUTO_SCALAR, []), (AUTO_SCALAR, []), (AUTO_VECTOR, []), (AUTO_VECTOR, ["array<Object>", "array<long>", "array<long>"]))

        # this is too much atm... Leaving this out for now
        # cls.define_overload("Diagnostic::Display::particle_collision_scope", (OBJECT - ARRAY, []), (NUMERIC-BIG-ARRAY, []))

    @classmethod
    def load_field_overloads(cls):
        cls.define_overload_resolver("Core::Fields::to_field", _resolver.to_field)
        cls.define_overload_resolver("Core::Fields::switch_fields", _resolver.switch_fields)

        cls.force_auto_ports("Core::Fields::field_is_empty", "output")
        cls.define_overload("Core::Fields::field_is_empty", (FIELDS, [lambda x: _replace_full_base(x, "bool")]))

        cls.define_overload("Core::Fields::advect_field", (FIELDS, [None]))

        cls.force_auto_ports("Core::Fields::curl_noise_field", "noise_field")
        cls.define_overload("Core::Fields::curl_noise_field", (FLOAT | FIELD, [lambda x: _replace_full_base(x, "Core::Fields::VectorField")]))

        cls.define_overload("Core::Fields::fcurve_field", (FIELDS, [None]))

        cls.force_auto_ports("Core::Fields::fractal_block_noise_field", "noise_field")
        cls.define_overload("Core::Fields::fractal_block_noise_field", (FLOAT | FIELD, [lambda x: _replace_full_base(x, "Core::Fields::ScalarField")]))

        cls.force_auto_ports("Core::Fields::fractal_disturbance_field", "noise_field")
        cls.define_overload("Core::Fields::fractal_disturbance_field", (FLOAT | FIELD, [lambda x: _replace_full_base(x, "Core::Fields::VectorField")]))

        cls.force_auto_ports("Core::Fields::fractal_noise_field", "noise_field")
        cls.define_overload("Core::Fields::fractal_noise_field", (FLOAT | FIELD, [lambda x: _replace_full_base(x, "Core::Fields::ScalarField")]))

        cls.force_auto_ports("Core::Fields::fractal_turbulence_field", "noise_field")
        cls.define_overload("Core::Fields::fractal_turbulence_field", (FLOAT | FIELD, [lambda x: _replace_full_base(x, "Core::Fields::VectorField")]))

        cls.define_overload("Core::Fields::property_proxy_field", (FIELDS, [None]))
        cls.define_overload("Core::Fields::rotate_field", (FIELDS, [None]))
        cls.define_overload("Core::Fields::scale_field", (FIELDS, [None]))
        cls.define_overload("Core::Fields::translate_field", (FIELDS, [None]))
        cls.define_overload("Core::Fields::transform_field", (FIELDS, [None]))
        cls.define_overload("Core::Fields::warp_field", (FIELDS, [None]))
        cls.define_overload("Core::Fields::voxel_field", (FIELDS, [None]))

        cls.define_overload("Core::Fields::sample_field", (FIELD, [lambda x: _replace_full_base(x, "float")]))
        cls.define_overload("Core::Fields::sample_field", (FIELD3, [lambda x: _replace_full_base(x, "Math::float3")]))

        cls.define_overload("Core::Fields::sample_field_with_proxies", (FIELD, [lambda x: _replace_full_base(x, "array<float>")]))
        cls.define_overload("Core::Fields::sample_field_with_proxies", (FIELD3, [lambda x: _replace_full_base(x, "array<Math::float3>")]))

        cls.define_overload("Core::Fields::voxel_proxy_field", (FIELDS, [None]))

    @classmethod
    def load_simulation_overloads(cls):
        cls.define_overload("Simulation::Common::compute_on_frame", (ALL_TYPES, [None]))

        cls.force_auto_ports("Simulation::Influence::attract_repulse_influence", "attraction", "drag")
        cls.define_overload("Simulation::Influence::attract_repulse_influence", (SIM_VECTOR, []), (SIM_SCALAR, []))

        cls.force_auto_ports("Simulation::Influence::dissipation_influence", "rate", "background_value")
        cls.define_overload("Simulation::Influence::dissipation_influence", (SIM_SCALAR, []), (SIM_VECTOR, []))

        cls.force_auto_ports("Simulation::Influence::ground_plane_influence", "bounciness", "friction", "pushout", "pushout_velocity", "offset")
        cls.define_overload("Simulation::Influence::ground_plane_influence", (SIM_VECTOR, []), (SIM_VECTOR, []), (SIM_SCALAR, []), (SIM_SCALAR, []), (SIM_SCALAR, []))

        cls.define_overload("Simulation::Influence::influence_set_orientation", (SIM_VECTOR, []))
        cls.define_overload("Simulation::Influence::influence_set_spin", (SIM_VECTOR, []))

        cls.force_auto_ports("Simulation::Influence::influence_set_property", "out_influence")
        cls.define_overload("Simulation::Influence::influence_set_property", (((FLOAT - VECTOR2 - MATRIX) | (BOOL & SIMPLE) | FIELDS), [lambda x: _replace_full_base(x, "Object")]))

        cls.force_auto_ports("Simulation::Influence::radial_influence", "magnitude", "drag")
        cls.define_overload("Simulation::Influence::radial_influence", (SIM_VECTOR, []), (SIM_SCALAR, []))

        cls.define_overload("Simulation::Influence::set_influence_force", (SIM_VECTOR, []))
        cls.define_overload("Simulation::Influence::set_influence_drag", (SIM_SCALAR, []))
        cls.define_overload("Simulation::Influence::set_influence_kill", (SIM_SCALAR, []))
        cls.define_overload("Simulation::Influence::set_influence_mask", (SIM_SCALAR, []))

        cls.define_overload("Simulation::Common::compute_point_velocities", (FLOAT & SIMPLE - ARRAY3 - ARRAY2, []))
        cls.define_overload("Simulation::Common::compute_velocity", (OBJECT - ARRAY3 - ARRAY2, [None]))

        cls.define_overload("Simulation::Particles::filter_particles", (SIM_VECTOR | {"int", "Math::int3"}, ["Object"]))
        cls.define_overload("Simulation::Particles::property_kill_points", (SIM_VECTOR | {"int", "Math::int3"}, []))

        # this first float is min_hole_radius. Since that gets converted to ANY, it technically accepts any time
        # but I have a feeling that is not correct...
        types = [({"float"}, [])] + 5 * [(SIM_SCALAR, [])] + [(SIM_VECTOR, [])] + 2 * [(SIM_SCALAR, [])] + [(SIM_SCALAR, ["array<Object>"])]

        cls.force_auto_ports("Simulation::MPM::source_mpm_fluid", "mass_density", "viscosity", "surface_tension", "vibration_speed", "initial_speed", "direction", "inherit_velocity", "viscoelasticity", "relaxation_time")
        cls.define_overload("Simulation::MPM::source_mpm_fluid", *types)

        cls.define_overload("Simulation::BOSS::create_wave_map", (AUTO_VECTOR | FLOAT - VECTOR4 - ARRAY3 - ARRAY2, []))

        cls.force_auto_ports("Simulation::BOSS::dynamic_wave_settings", "drift", "depth")
        cls.define_overload("Simulation::BOSS::dynamic_wave_settings", (FLOAT & VECTOR2 | AUTO_VECTOR | OBJECT - ARRAY, []), ({"Object"}, []))

        cls.define_overload("Simulation::Common::vary_source_property", (NUMERIC-ARRAY, [None]))

        cls.define_overload_resolver("Simulation::Influence::clamp_influence", _resolver.clamp_influence)

        cls.force_auto_ports("Simulation::Influence::collide_field_influence", "distance_field_velocity", "friction", "bounciness", "pushout", "pushout_velocity", "offset")
        cls.define_overload("Simulation::Influence::collide_field_influence", (SIM_VECTOR, []), (SIM_SCALAR, []), (SIM_SCALAR, []), (SIM_SCALAR, []), (SIM_SCALAR, []), (SIM_SCALAR, []))

        cls.force_auto_ports("Simulation::Influence::modifier_influence", "min", "max", "value", "rate")
        cls.define_overload("Simulation::Influence::modifier_influence", (SIM_VECTOR, []), (SIM_SCALAR, []), (SIM_VECTOR, []), (SIM_VECTOR, []))

        cls.define_overload_resolver("Simulation::Common::force_pull_port", _resolver.force_eval)
        cls.define_overload_resolver("Simulation::Common::should_simulate", _resolver.should_simulate)
        cls.define_overload_resolver("Simulation::Particles::set_particle_property_from_age", _resolver.particle_property_from_age)

        cls.define_overload("Simulation::BOSS::scale_wave_height", (AUTO_SCALAR, []), (AUTO_SCALAR, ["array<Object>"]))


    @classmethod
    def load_usd_overloads(cls):
        cls.define_overload("USD::Stage::add_to_stage", ({"BifrostUsd::Layer"}, []))
        cls.define_overload("USD::Layer::add_sublayer", ({"BifrostUsd::Layer", "array<BifrostUsd::Layer>"}, []))

        # this technically takes anything but I presume its only supposed to take in what can be pulled out again
        cls.define_overload("USD::Attribute::define_usd_attribute", (USD_ATTR, ["Object"]))

        cls.define_overload("USD::Attribute::get_prim_attribute_data", (USD_ATTR, [None]))
        cls.define_overload("USD::Attribute::set_prim_attribute", (USD_ATTR, []))
        cls.define_overload("USD::Prim::define_usd_geom_subset", ((LONG | INT) & SIMPLE & ARRAY1 - UNSIGNED, []))
        cls.define_overload("USD::Prim::duplicate_usd_prim_definition", (AUTO_VECTOR, []), (AUTO_VECTOR, []), (AUTO_VECTOR, []))
        cls.define_overload("USD::VariantSet::add_to_stage_in_variant", ({"BifrostUsd::Layer"}, []))
        cls.define_overload("USD::Attribute::get_usd_attribute_value", (USD_ATTR, [None, "bool"]))

    @classmethod
    def load_simple_overloads_from_suggestions(cls):
        """
        this wont be an exhaustive list of overloads but at least the suggestions will be taken into account
        This only works for nodes with no auto out ports
        """
        for s_func, d_data in cls._d_operators.items():
            sa_keys = list(d_data["overloads"])
            if sa_keys[0].count("auto") > 0 and len(sa_keys) == 1 and s_func not in cls._d_overloads:
                if "auto" in d_data["overloads"][sa_keys[0]]:
                    continue

                b_any = any([len(sa) > 1 for sa in d_data["suggestions"]])
                b_all = all([bool(sa) for sa in d_data["suggestions"]])
                if not (b_any and b_all):
                    continue

                for perm in itertools.product(*d_data["suggestions"]):
                    d_data["overloads"]["-".join(perm)] = d_data["overloads"][sa_keys[0]]


if __name__ == "__main__":
    Overlord.init()
