from BSL import _error
from BSL._port_types import *
from BSL._resolver import _multi


def if_(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    ia_arr_dims = {t.array_dim() for t in input_types if t.is_array()}
    if len(ia_arr_dims) > 1:
        return False, (_error.BfTypeError, "Array dimension missmatch")

    i_dim = (list(ia_arr_dims) + [0])[0]

    base_types = [t.base_type() if t.is_array() else t for t in input_types]

    if base_types[0] != "bool":
        return False, (_error.BfTypeError, "BOOL or BOOL[] required as condition")

    # non-numeric types
    if not ((base_types[1].is_numeric() or base_types[1].is_field()) and (base_types[2].is_numeric() or base_types[2].is_field())):
        if base_types[1] == base_types[2]:
            return True, (input_types, [i_dim * "array<" + base_types[1].s + i_dim * ">"])
        return False, (_error.BfTypeError, f"Type missmatch '{input_types[1]}' <> '{input_types[2]}'")

    # numeric types
    status, result = _bifast.MathOp._get_type(lhs=base_types[1], rhs=base_types[2], op="if")
    if not status:
        return False, (_error.BfTypeError, result)
    return True, (input_types, [i_dim * "array<" + result.s + i_dim * ">"])


def members_if(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    ia_arr_dims = {t.array_dim() for t in input_types if t.is_array()}
    if len(ia_arr_dims) > 1:
        return False, (_error.BfTypeError, "Array dimension missmatch")

    i_dim = (list(ia_arr_dims) + [0])[0]
    base_types = [t.base_type() if t.is_array() else t for t in input_types]

    if base_types[0].base_type() != "bool":
        return False, (_error.BfTypeError, "Some form of BOOL required as condition")

    status, result = _multi.multi_same(sa_names_in[1:], sa_names_out, sa_types_in[1:], sa_types_out, base_types[1:], ALL_TYPES, b_to_float=False)
    if not status:
        return False, result

    # combine with condition
    status1, result1 = _bifast.MathOp._get_type(lhs=base_types[0], rhs=result[1][0], op="members_if")
    if not status1:
        return False, (_error.BfTypeError, result1)
    return True, ([input_types[0]] + result[0], [i_dim * "array<" + result1.s + i_dim * ">"])


def should_simulate(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    ia_arr_dims = {t.array_dim() for t in input_types if t.is_array()}
    if len(ia_arr_dims) > 1:
        return False, (_error.BfTypeError, "Array dimension missmatch")

    i_dim = (list(ia_arr_dims) + [0])[0]

    base_types = [t.base_type() if t.is_array() else t for t in input_types]

    # non-numeric types
    if not ((base_types[0].is_numeric() or base_types[0].is_field()) and (base_types[1].is_numeric() or base_types[1].is_field())):
        if base_types[0] == base_types[1]:
            return True, (input_types, [i_dim * "array<" + base_types[0].s + i_dim * ">"])
        return False, (_error.BfTypeError, f"Type missmatch '{input_types[0]}' <> '{input_types[1]}'")

    # numeric types
    status, result = _bifast.MathOp._get_type(lhs=input_types[0], rhs=input_types[0], op="should_simulate")
    if not status:
        return False, (_error.BfTypeError, result)
    return True, (input_types, [result.s])


def switch_is_a(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in[1:], sa_names_out, sa_types_in[1:], sa_types_out, input_types[1:], ALL_TYPES, b_to_float=False)
    if not status:
        return False, result

    if input_types[0] != "Object":
        return False, (_error.BfTypeError, f"'{sa_names_in[0]}' of type '{input_types[0].s}' not supported!")

    return True, (["Object"] + result[0], result[1])


def particle_property_from_age(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    # geo, string, NUMERIC-ARRAY2+, NUMERIC-ARRAY2+, float
    types = [{"Object"}, {"string"}, NUMERIC-ARRAY3-ARRAY2, NUMERIC-ARRAY3-ARRAY2, "float"]

    inputs = []
    for i, sa_types in enumerate(types):
        status, result = _multi.multi_same(sa_names_in[i:i+1], sa_names_out, sa_types_in[i:i+1], sa_types_out, input_types[i:i+1], sa_types, b_to_float=False)
        if not status:
            return False, result

        inputs += result[0]

    return True, (inputs, ["Object"])
