from BSL import _error


def logic(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast
    status, result = _bifast.Logic._get_type(lhs=input_types[0], rhs=input_types[1], op="and/or/xor")
    if not status:
        return False, (_error.BfTypeError, result)
    return True, (input_types, [result.s])

