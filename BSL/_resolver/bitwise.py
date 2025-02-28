from BSL._port_types import *
from BSL._resolver import _multi


def bitwise(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = INTEGER
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=sa_possible, b_to_float=False)
