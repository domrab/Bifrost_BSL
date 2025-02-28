from BSL import _error


def compare(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, op):
    if not op:
        return False, "missing operator"

    from BSL import _bifast
    status, result = _bifast.Compare._get_type(lhs=input_types[0], rhs=input_types[1], op=op)
    if not status:
        return False, (_error.BfTypeError, result)
    return True, (input_types, [result.s])
