from BSL import _error, _type
from BSL._port_types import *
from BSL._resolver import _multi


def random_(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = (FLOAT - MATRIX) | DOUBLE & SIMPLE | INT | LONG
    status, result = _multi.multi_same(sa_names_in[1:3], sa_names_out, sa_types_in, sa_types_out, input_types[1:3], sa_possible, b_to_float=False)
    if not status:
        return False, result

    status1, result1 = _multi.multi_same(sa_names_in[0::3], sa_names_out, sa_types_in, sa_types_out, input_types[0::3], LONG & SIMPLE, b_to_float=False)
    if not status1:
        return False, result1

    return True, (["long"] + result[0] + ["long"], result[1])


def randomize_geo_property(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible1 = AUTO_SCALAR
    sa_possible2 = NUMERIC - MATRIX - ARRAY

    auto_types = [t for s, t in zip(sa_types_in, input_types) if s == "auto"]
    auto_names = [t for s, t in zip(sa_types_in, sa_names_in) if s == "auto"]

    status1, result1 = _multi.multi_same(auto_names, sa_names_out, sa_types_in, sa_types_out, [auto_types[0]], sa_possible1, b_to_float=False)
    if not status1:
        return False, result1

    status2, result2 = _multi.multi_same(auto_names[1:], sa_names_out, sa_types_in, sa_types_out, auto_types[1:], sa_possible2, b_to_float=False)
    if not status2:
        return False, result2

    resolved_types = result1[0] + result2[0]

    idx = 0
    for i in range(len(sa_names_in)):
        if sa_types_in[i] == "auto":
            input_types[i] = resolved_types[idx]
            idx += 1

    return True, (input_types, [sa_types_out[0], f"array<{result2[1][0]}>"])
