from BSL import _error, _type


def multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible, b_to_float=False):
    from BSL import _bifast

    for i in range(len(input_types)):
        if input_types[i].s in sa_possible:
            continue

        if input_types[i].s == "auto":
            return False, (_error.BfTypeError, f"'Missing required parameter '{sa_names_in[i]}'")

        promoted = _type.promotable_to_one_of(input_types[i], sa_possible)
        if not promoted:
            return False, (_error.BfTypeError, f"'{sa_names_in[i]}' with type '{input_types[i]}' unsupported")

        input_types[i] = _type.Type(promoted)

    types = [t for t in input_types]

    while len(types) > 1:
        lhs = types.pop(0)
        rhs = types.pop(0)

        status, result = _bifast.MathOp._get_type(lhs=lhs, rhs=rhs, op="?")
        if not status:
            return False, (_error.BfTypeError, result)

        types.insert(0, result)

    result = types[0]

    if b_to_float:
        # promote to floating points
        if not result.is_field():
            _, result = _bifast.MathOp._get_type(lhs=result, rhs=_type.Type("float"), op="?")

    return True, (input_types, [result.s])
