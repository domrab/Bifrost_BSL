from BSL import _error, _type
from BSL._port_types import *


def to_field(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    s = input_types[0].s.partition(">")[0].rpartition("<")[2]

    # no conversion needed
    if s in ["Core::Fields::ScalarField", "Core::FieldsVectorField"]:
        return True, (input_types, input_types)

    i_arr = input_types[0].s.count(">")
    t = input_types[0].base_type() if input_types[0].is_array() else input_types[0]

    if (not t.is_numeric()) or t.is_matrix() or (t.is_vector() and t.vector_dim() == 4):
        return False, (_error.BfTypeError, f"Cant convert '{t.s}' to field")

    if t.is_vector():
        return True, (input_types, [_type.Type(i_arr * "array<" + "Core::Fields::VectorField" + i_arr * ">")])

    return True, (input_types, [_type.Type(i_arr * "array<" + "Core::Fields::ScalarField" + i_arr * ">")])


def switch_fields(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    from BSL import _bifast

    ia_arr_dims = {t.array_dim() for t in input_types if t.is_array()}
    if len(ia_arr_dims) > 1:
        return False, (_error.BfTypeError, "Array dimension missmatch")

    i_dim = (list(ia_arr_dims) + [0])[0]

    base_types = [t.base_type() if t.is_array() else t for t in input_types]

    if base_types[0] != "Core::Fields::ScalarField":
        return False, (_error.BfTypeError, "FIELD or FIELD[] required as condition")

    # non-numeric types
    if not ((base_types[1].is_field()) and (base_types[2].is_field())):
        return False, (_error.BfTypeError, f"Type missmatch '{input_types[1]}' <> '{input_types[2]}'")

    # numeric types
    status, result = _bifast.MathOp._get_type(lhs=input_types[1], rhs=input_types[2], op="?")
    if not status:
        return False, (_error.BfTypeError, result)
    return True, (input_types, [result.s])
