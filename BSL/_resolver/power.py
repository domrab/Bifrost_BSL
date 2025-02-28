from BSL import _error
from BSL._port_types import *
from BSL._resolver import _multi


def power(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast
    status, result = _bifast.MathOp._get_type(lhs=input_types[0], rhs=input_types[1], op="**")
    if not status:
        return False, (_error.BfTypeError, result)
    return True, (input_types, [result.s])


def modulo(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=NUMERIC, b_to_float=False)


def remainder(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=FLOATING - MATRIX | MATRIX_SQUARE, b_to_float=True)


def copy_sign(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=NUMERIC, b_to_float=False)
