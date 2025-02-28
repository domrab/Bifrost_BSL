from BSL import _error, _type
from BSL._port_types import *
from BSL._resolver import _multi


def force_eval(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    return True, (input_types, [input_types[0]])
