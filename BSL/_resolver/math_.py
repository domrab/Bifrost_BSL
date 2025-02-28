from BSL import _error, _type
from BSL._port_types import *
from BSL._resolver import _multi


def atan_2D(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=(FLOATING - MATRIX) | FIELD, b_to_float=True)


def distance(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL._overlord import _to_scalar
    sa_possible = FLOATING & VECTOR3
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=sa_possible, b_to_float=True)
    if not status:
        return False, status
    return True, (result[0], [_to_scalar(result[1][0])])


def distance_float_ULP(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL._overlord import _replace_base

    sa_possible = FLOATING
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=sa_possible, b_to_float=True)
    if not status:
        return result

    return True, (result[0], [_replace_base(result[1][0], "int")])


def equivalent_float_ULP(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL._overlord import _replace_base

    ia_arr_dims = {t.array_dim() for t in input_types if t.is_array()}
    if len(ia_arr_dims) > 1:
        return False, (_error.BfTypeError, "Array dimension missmatch")

    i_dim = (list(ia_arr_dims) + [0])[0]
    base_types = [t.base_type() if t.is_array() else t for t in input_types]

    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, base_types[:2], sa_possible=FLOATING, b_to_float=True)
    if not status:
        return result

    if base_types[2] != "int":
        return False, (_error.BfTypeError, "'epsilon' must be provided as INT")

    return True, (result[0] + ["int"], [i_dim * "array<" + _replace_base(result[1][0], "bool") + i_dim * ">"])


def equivalent_float_epsilon(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL._overlord import _replace_base

    ia_arr_dims = {t.array_dim() for t in input_types if t.is_array()}
    if len(ia_arr_dims) > 1:
        return False, (_error.BfTypeError, "Array dimension missmatch")

    i_dim = (list(ia_arr_dims) + [0])[0]
    base_types = [t.base_type() if t.is_array() else t for t in input_types]

    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, base_types[:2], sa_possible=FLOATING, b_to_float=True)
    if not status:
        return result

    if base_types[2] not in ["float", "double"]:
        return False, (_error.BfTypeError, "'epsilon' must be provided as FLOAT or DOUBLE")

    return True, (result[0] + [input_types[2]], [i_dim * "array<" + _replace_base(result[1][0], "bool") + i_dim * ">"])



def lerp(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = (FLOATING - MATRIX) | FIELD
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=sa_possible, b_to_float=True)


def linear_interpolate(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = (FLOATING - MATRIX) | FIELD
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:3], sa_possible=sa_possible, b_to_float=True)
    if not status:
        return False, result

    sa_possible1 = BOOL & SIMPLE
    status1, result1 = _multi.multi_same(sa_names_in[3:], sa_names_out, sa_types_in, sa_types_out[3:], input_types[3:], sa_possible=sa_possible1, b_to_float=True)
    if not status1:
        return False, result1

    return True, (result[0] + result1[0], result[1])


def lerp_vec(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = (FLOATING & VECTOR)
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:2], sa_possible=sa_possible, b_to_float=True)
    if not status:
        return False, result

    sa_possible = (FLOATING & SIMPLE)
    status1, result1 = _multi.multi_same([sa_names_in[2]], sa_names_out, sa_types_in, sa_types_out, [input_types[2]], sa_possible=sa_possible, b_to_float=True)
    if not status1:
        return False, result1

    sa_possible = (BOOL & SIMPLE)
    status2, result2 = _multi.multi_same(sa_names_in[3:], sa_names_out, sa_types_in, sa_types_out, input_types[3:], sa_possible=sa_possible, b_to_float=True)
    if not status2:
        return False, result2

    return True, (result[0] + result1[0] + result2[0], result[1])


def clamp(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = NUMERIC
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible=sa_possible, b_to_float=False)


def clamp_influence(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = AUTO_VECTOR - STRING

    i_min = sa_names_in.index("min")
    i_max = sa_names_in.index("max")

    t_min = input_types[i_min]
    t_max = input_types[i_max]
    sa_types_in[i_min] = t_min.s
    sa_types_in[i_max] = t_max.s

    status, result = _multi.multi_same(["min", "max"], sa_names_out, sa_types_in, sa_types_out, [t_min, t_max], sa_possible=sa_possible, b_to_float=True)
    if not status:
        return False, result

    return True, (sa_types_in, sa_types_out)


def srt_to_matrix(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    for i in range(len(input_types)):
        sa_possible = FLOATING & (VECTOR3 if i != 2 else VECTOR4)

        if input_types[i].s == "auto":
            return False, (_error.BfTypeError, f"'Missing required parameter '{sa_names_in[i]}'")

        if input_types[i].s not in sa_possible:
            promoted = _type.promotable_to_one_of(input_types[i], sa_possible)
            if not promoted:
                return False, (_error.BfTypeError, f"'{sa_names_in[i]}' with type '{input_types[i]}' unsupported")

            input_types[i] = promoted

    arr_dims = list({t.array_dim() for t in input_types if t.is_array()})
    if len(arr_dims) > 1:
        return False, (_error.BfTypeError, f"Incompatible array dimensions")

    arr_dim = (arr_dims + [0])[0]
    types = [t.base_type().base_type() for t in input_types]

    while len(types) > 1:
        lhs = types.pop(0)
        rhs = types.pop(0)

        status, result = _bifast.MathOp._get_type(lhs=lhs, rhs=rhs, op="?")
        if not status:
            return False, (_error.BfTypeError, result)

        types.insert(0, result)

    return True, (input_types, [arr_dim * "array<" + "Math::" + types[0].s + "4x4" + arr_dim * ">"])


def cross(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = FLOATING & VECTOR3 | FIELD3
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible, b_to_float=True)


def dot(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa_possible = NUMERIC & VECTOR | FIELD3
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa_possible, b_to_float=False)
    if not status:
        return False, result

    inputs = result[0]
    type = _type.Type(result[1][0])
    arr = type.array_dim()
    return True, (inputs, [arr * "array<" + type.base_type().base_type().s + arr * ">"])


def change_range(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:5], NUMERIC, b_to_float=False)
    if not status:
        return result

    status1, result1 = _multi.multi_same([sa_names_in[5]], sa_names_out, sa_types_in, sa_types_out, [input_types[5]], BOOL & SIMPLE, b_to_float=False)
    if not status1:
        return result1

    return True, (result[0] + result1[0], result[1])


def multiply_quaternions(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, FLOATING & VECTOR4, b_to_float=True)


def normal_and_tangent_to_orientation(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:2], FLOATING & VECTOR3, b_to_float=True)
    if not status:
        return False, result

    status2, result2 = _multi.multi_same(sa_names_in[2:], sa_names_out, sa_types_in, sa_types_out, input_types[2:], BOOL & SIMPLE, b_to_float=True)
    if not status2:
        return False, result2

    inputs = result[0] + result2[0]
    type = _type.Type(result[1][0])
    arr = type.array_dim()
    return True, (inputs, [arr * "array<" + "Math::" + type.base_type().base_type().s + "4" + arr * ">"])


def rotation_between_vectors(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, FLOATING & VECTOR3, b_to_float=True)
    if not status:
        return False, result

    inputs = result[0]
    type = _type.Type(result[1][0])
    arr = type.array_dim()
    return True, (inputs, [arr * "array<" + "Math::" + type.base_type().base_type().s + "4" + arr * ">"])


def rotation_around_position_to_matrix(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:1], FLOATING & VECTOR4, b_to_float=True)
    if not status:
        return False, result

    status1, result1 = _multi.multi_same(sa_names_in[1:], sa_names_out, sa_types_in, sa_types_out, input_types[1:], FLOATING & VECTOR3, b_to_float=True)
    if not status1:
        return False, result1

    status2, result2 = _bifast.MathOp._get_type(lhs=_type.Type(result[0][0]), rhs=_type.Type(result1[0][0]), op="?")
    if not status2:
        return False, (_error.BfTypeError, result2)

    arr = result2.array_dim()
    return True, (result[0] + result1[0], [arr * "array<" + "Math::" + result2.base_type().base_type().s + "4x4" + arr * ">"])


def rotate_by_quaternion(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:1], FLOATING & VECTOR3, b_to_float=True)
    if not status:
        return False, result

    status1, result1 = _multi.multi_same(sa_names_in[1:], sa_names_out, sa_types_in, sa_types_out, input_types[1:], FLOATING & VECTOR4, b_to_float=True)
    if not status1:
        return False, result1

    main = result[1]
    all_results = [_type.Type(s) for s in result[1] + result1[1]]
    arr_dims = sorted(set([t.array_dim() for t in all_results if t.array_dim()])) + [0]
    if len(arr_dims) > 2:
        return False, (_error.BfTypeError, "Cant mix array dimensions")
    if arr_dims:
        main[0] = arr_dims[0] * "array<" + main[0].rpartition("<")[2].strip(">") + arr_dims[0] * ">"

    inputs = result[0] + result1[0]
    return True, (inputs, result[1])


def rotate_by_matrix(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:1], FLOATING & VECTOR3, b_to_float=True)
    if not status:
        return False, result

    status1, result1 = _multi.multi_same(sa_names_in[1:], sa_names_out, sa_types_in, sa_types_out, input_types[1:], FLOATING & MATRIX4x4, b_to_float=True)
    if not status1:
        return False, result1

    main = result[1]
    all_results = [_type.Type(s) for s in result[1] + result1[1]]
    arr_dims = sorted(set([t.array_dim() for t in all_results if t.array_dim()])) + [0]
    if len(arr_dims) > 2:
        return False, (_error.BfTypeError, "Cant mix array dimensions")
    if arr_dims:
        main[0] = arr_dims[0] * "array<" + main[0].rpartition("<")[2].strip(">") + arr_dims[0] * ">"

    inputs = result[0] + result1[0]
    return True, (inputs, result[1])


def transform_vector_as(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:1], FLOATING & VECTOR3, b_to_float=True)
    if not status:
        return False, result

    status1, result1 = _multi.multi_same(sa_names_in[1:], sa_names_out, sa_types_in, sa_types_out, input_types[1:], FLOATING & MATRIX4x4, b_to_float=True)
    if not status1:
        return False, result1

    main = result[1]
    all_results = [_type.Type(s) for s in result[1] + result1[1]]
    arr_dims = sorted(set([t.array_dim() for t in all_results if t.array_dim()])) + [0]
    if len(arr_dims) > 2:
        return False, (_error.BfTypeError, "Cant mix array dimensions")
    if arr_dims:
        main[0] = arr_dims[0] * "array<" + main[0].rpartition("<")[2].strip(">") + arr_dims[0] * ">"

    inputs = result[0] + result1[0]
    return True, (inputs, result[1])


def quaternion_slerp(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:2], FLOATING & VECTOR4, b_to_float=True)
    if not status:
        return False, result

    status1, result1 = _multi.multi_same(sa_names_in[2::4], sa_names_out, sa_types_in, sa_types_out, input_types[2::4], FLOATING & SIMPLE, b_to_float=True)
    if not status1:
        return False, result1

    status2, result2 = _multi.multi_same(sa_names_in[3:6], sa_names_out, sa_types_in, sa_types_out, input_types[3:6], BOOL & SIMPLE, b_to_float=True)
    if not status2:
        return False, result2

    status3, result3 = _multi.multi_same(sa_names_in[6:], sa_names_out, sa_types_in, sa_types_out, input_types[6:], FLOATING & SIMPLE, b_to_float=True)
    if not status3:
        return False, result3

    main = result[1]
    all_results = [_type.Type(s) for s in result[1] + result1[1] + result2[1] + result3[1]]
    arr_dims = sorted(set([t.array_dim() for t in all_results if t.array_dim()])) + [0]
    if len(arr_dims) > 2:
        return False, (_error.BfTypeError, "Cant mix array dimensions")
    if arr_dims:
        main[0] = arr_dims[0] * "array<" + main[0].rpartition("<")[2].strip(">") + arr_dims[0] * ">"

    # quat_output = _type.Type(result[1][0])
    # parm_output = _type.Type(result1[1][0])
    # if parm_output.is_array() and quat_output.is_array():
    #     if parm_output.array_dim() != quat_output.array_dim():
    #         return False, (_error.BfTypeError, "Cant mix array dimensions")
    # elif parm_output.is_array():
    #     i_arr_dim = max(parm_output.array_dim(), quat_output.array_dim())
    #     if i_arr_dim > 0:
    #         result[1][0] = i_arr_dim * "array<" + result[1][0] + i_arr_dim * ">"
    # return True, (result[0] + [result1[0][0]] + result2[0] + [result1[0][1]], result[1])
    return True, (result[0] + [result1[0][0]] + result2[0] + [result1[0][1]], main)


def within_bounds(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:3], NUMERIC, b_to_float=False)
    if not status:
        return False, result

    status1, result1 = _multi.multi_same(sa_names_in[3:], sa_names_out, sa_types_in, sa_types_out, input_types[3:], BOOL & SIMPLE, b_to_float=False)
    if not status1:
        return False, result1

    inputs = result[0] + result1[0]
    type = _type.Type(result[1][0])
    arr = type.array_dim()
    return True, (inputs, [arr * "array<" + "bool" + arr * ">"])


def any_n_to_1(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    return _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, ALL_TYPES, b_to_float=False)


def scalar_to_vec2(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa = NUMERIC - MATRIX - VECTOR
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa, b_to_float=False)
    if not status:
        return False, result

    inputs = result[0]
    type = _type.Type(result[1][0])
    arr = type.array_dim()
    return True, (inputs, [arr * "array<" + "Math::" + type.base_type().s + "2" + arr * ">"])


def scalar_to_vec3(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa = FIELD | NUMERIC - MATRIX - VECTOR
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa, b_to_float=False)
    if not status:
        return False, result

    inputs = result[0]
    type = _type.Type(result[1][0])
    arr = type.array_dim()

    if type.is_field():
        return True, (inputs, [arr * "array<" + "Core::Fields::VectorField" + arr * ">"])

    return True, (inputs, [arr * "array<" + "Math::" + type.base_type().s + "3" + arr * ">"])


def scalar_to_vec4(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    sa = NUMERIC - MATRIX - VECTOR
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types, sa, b_to_float=False)
    if not status:
        return False, result

    inputs = result[0]
    type = _type.Type(result[1][0])
    arr = type.array_dim()
    return True, (inputs, [arr * "array<" + "Math::" + type.base_type().s + "4" + arr * ">"])


def vec3_to_vec4(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    sa = NUMERIC - MATRIX - VECTOR4
    status, result = _multi.multi_same(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types[:1], sa, b_to_float=False)
    if not status:
        return False, result

    status1, result1 = _multi.multi_same(sa_names_in[1:], sa_names_out, sa_types_in, sa_types_out, input_types[1:], sa, b_to_float=False)
    if not status1:
        return False, result1

    status2, result2 = _bifast.MathOp._get_type(lhs=_type.Type(result[0][0]), rhs=_type.Type(result1[0][0]), op="?")
    if not status2:
        return False, (_error.BfTypeError, result2)

    inputs = result[0] + result1[0]
    arr = result2.array_dim()
    return True, (inputs, [arr * "array<" + "Math::" + result2.base_type().s + "4" + arr * ">"])
