from BSL import _error


def negate(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast
    status, result = _bifast.Negate._get_type(input_types[0])
    if not status:
        return False, (_error.BfTypeError, result)
    return True, (input_types, [result.s])
