from BSL import _error, _type
from BSL._port_types import *


def axis_angle_to_quaternion(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    sa_possible1 = NUMERIC - VECTOR4 - MATRIX
    sa_possible2 = NUMERIC | SIMPLE

    if input_types[0].s not in sa_possible1:
        if input_types[0].s == "auto":
            return False, (_error.BfTypeError, f"'Missing required parameter '{sa_names_in[0]}'")

        promoted = _type.promotable_to_one_of(input_types[0], sa_possible1)
        if not promoted:
            return False, (_error.BfTypeError, f"'{sa_names_in[0]}' of type '{input_types[0]}' unsupported")
        input_types[0] = promoted

    if input_types[1].s not in sa_possible2:
        if input_types[1].s == "auto":
            return False, (_error.BfTypeError, f"'Missing required parameter '{sa_names_in[1]}'")

        promoted = _type.promotable_to_one_of(input_types[1], sa_possible2)
        if not promoted:
            return False, (_error.BfTypeError, f"'{sa_names_in[1]}' of type '{input_types[1]}' unsupported")
        input_types[1] = promoted

    status, result = _bifast.MathOp._get_type(lhs=input_types[0], rhs=input_types[1], op="?")
    if not status:
        return False, (_error.BfTypeError, result)

    arr = result.array_dim()
    _, result = _bifast.MathOp._get_type(lhs=result.base_type().base_type(), rhs=_type.Type("float"), op="?")

    return True, (input_types, [arr * "array<" + "Math::" + result.s + "4" + arr * ">"])

