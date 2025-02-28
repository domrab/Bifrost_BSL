from BSL import _error, _type
from BSL._port_types import *
from BSL._resolver import _multi


def expect_equal(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    if input_types[2] != "string":
        return False, (_error.BfTypeError, f"'{sa_names_in[2]}' must be a string")

    ia_arr_dims = {t.array_dim() for t in input_types if t.is_array()}
    if len(ia_arr_dims) > 1:
        return False, (_error.BfTypeError, "Array dimension missmatch")

    i_dim = (list(ia_arr_dims) + [0])[0]
    base_types = [t.base_type() if t.is_array() else t for t in input_types]

    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, base_types[:2], sa_possible=FLOATING, b_to_float=True)
    if not status:
        return result

    return True, (result[0] + ["string"], [i_dim * "array<" + "string" + i_dim * ">"])


def expect_almost_equal(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    if input_types[3] != "string":
        return False, (_error.BfTypeError, f"'{sa_names_in[3]}' must be a string")

    ia_arr_dims = {t.array_dim() for t in input_types if t.is_array()}
    if len(ia_arr_dims) > 1:
        return False, (_error.BfTypeError, "Array dimension missmatch")

    i_dim = (list(ia_arr_dims) + [0])[0]
    base_types = [t.base_type() if t.is_array() else t for t in input_types]

    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, base_types[:2], sa_possible=FLOATING, b_to_float=True)
    if not status:
        return result

    status1, result1 = _multi.multi_same(sa_names_in[2:3], sa_names_out, sa_types_in, sa_types_out, base_types[2:3], sa_possible={"float"}, b_to_float=True)
    if not status1:
        return result1

    return True, (result[0] + ["float", "string"], [i_dim * "array<" + "string" + i_dim * ">"])


def expect_arrays_equal(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    if input_types[3] != "string":
        return False, (_error.BfTypeError, f"'{sa_names_in[3]}' must be a string")

    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:2], sa_possible=FLOATING, b_to_float=True)
    if not status:
        return result

    status1, result1 = _multi.multi_same(sa_names_in[2:3], sa_names_out, sa_types_in, sa_types_out, input_types[2:3], sa_possible={"float"}, b_to_float=True)
    if not status1:
        return result1

    return True, (result[0] + ["float", "string"], ["string"])
