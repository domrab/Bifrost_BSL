from BSL import _error, _type
from BSL._port_types import *


def members(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    sa_possible = NUMERIC | BOOL

    if input_types[0].s not in sa_possible:
        if input_types[0].s == "auto":
            return False, (_error.BfTypeError, f"'Missing required parameter '{sa_names_in[0]}'")

        promoted = _type.promotable_to_one_of(input_types[0], sa_possible)
        if not promoted:
            return False, (_error.BfTypeError, f"'{sa_names_in[0]}' of type '{input_types[0]}' unsupported")
        input_types[0] = promoted

    if input_types[1].s not in sa_possible:
        if input_types[1].s == "auto":
            return False, (_error.BfTypeError, f"'Missing required parameter '{sa_names_in[1]}'")

        promoted = _type.promotable_to_one_of(input_types[1], sa_possible)
        if not promoted:
            return False, (_error.BfTypeError, f"'{sa_names_in[1]}' of type '{input_types[1]}' unsupported")
        input_types[1] = promoted

    status, result = _bifast.MathOp._get_type(lhs=input_types[0], rhs=input_types[1], op="?")
    if not status:
        return False, (_error.BfTypeError, result)

    arr = result.array_dim()
    if result.is_array():
        result = result.base_type()

    if result.is_matrix():
        result = _type.Type(arr * "array<" + "Math::bool" + result.s[-3:] + arr * ">")

    elif result.is_vector():
        result = _type.Type(arr * "array<" + "Math::bool" + result.s[-1] + arr * ">")

    else:
        result = _type.Type(arr * "array<" + "bool" + arr * ">")

    return True, (input_types, [result.s])


# def get_from_interpolated_array(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
