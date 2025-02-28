import json

from BSL import _file_io, _bifres

_D_TYPES = _bifres.TYPES
_D_ENUMS = _bifres.ENUMS

_D_TYPE_DICT = _file_io.get_type_dict()


class Type:
    def __init__(self, s_type, node_data=None):
        if isinstance(s_type, Type):
            node_data = s_type._node_data
            s_type = s_type.s

        s_base = s_type.rpartition("<")[2].partition(">")[0]
        i_array_dim = s_type.count(">")

        if s_base in _D_TYPE_DICT:
            s_base = _D_TYPE_DICT[s_base]

        if s_base in ["*", "[]", "[1]", "[2]", "[3]"]:
            s_base = "auto"

        if s_base not in _D_TYPES and s_base not in _D_ENUMS and s_base not in ["__NODE", "auto"]:
            raise Exception(f"Unknown type: '{s_type}'")

        if i_array_dim > 3:
            raise Exception(f"Max array dim is 3, got '{s_type}'")

        self._s_type = s_type
        if self.is_node() and node_data is None:
            raise Exception
        self._node_data = node_data

        self._accessors = _D_TYPES.get(s_base, {})

    def has_access(self, s):
        return s in self._accessors

    def get_access(self, s):
        i_array_dim = self.array_dim()
        s_prefix = i_array_dim * "array<"
        s_suffix = i_array_dim * ">"
        return self.__class__(s_prefix + self._accessors.get(s, "NONE") + s_suffix, node_data=self.node_data())

    def base_type(self):
        s_type = self._s_type
        if self.is_array():
            return self.__class__(s_type.rpartition("<")[2].partition(">")[0], node_data=self.node_data())

        if self.is_matrix():
            return self.__class__(s_type.rpartition("::")[2][:-3], node_data=self.node_data())

        if self.is_vector():
            return self.__class__(s_type.rpartition("::")[2][:-1], node_data=self.node_data())

        return self.__class__(s_type, node_data=self.node_data())

    def is_array(self):
        return self.s.startswith("array<")

    def is_numeric(self):
        return (self.is_bool() or self.is_integer() or self.is_fraction()) and not self.is_array()

    def is_vector(self):
        return self.s[-1] in "234" and not self.is_matrix()

    def is_matrix(self):
        return self.s[-3] in "234" and self.s[-2] in "x" and self.s[-1] in "234"

    def is_fraction(self):
        return self.base_type().s in ["float", "double"]

    def is_integer(self):
        return self.base_type().s in ["char", "uchar", "short", "ushort", "int", "uint", "long", "ulong"]

    def is_unsigned(self):
        return self.base_type().s in ["uchar", "ushort", "uint", "ulong"]

    def is_bool(self):
        return self.base_type().s in ["bool"]

    def is_string(self):
        return self.base_type().s in ["string"]

    def is_node(self):
        return self.s == "__NODE"

    def is_field(self):
        return self.base_type().s in ["Core::Fields::ScalarField", "Core::Fields::VectorField"]

    def is_big(self):
        return self.base_type().s in ["long", "ulong", "double"]

    def vector_dim(self):
        return int(self.s[-1]) if self.is_vector() else -1

    def matrix_dim(self):
        return (int(self.s[-3]), int(self.s[-1])) if self.is_matrix() else (-1, -1)

    def array_dim(self):
        return self.s.count("<")

    def numeric_size(self):
        if self.is_bool() or self.s in ["char", "uchar"]:
            return 1

        if self.s in ["short", "ushort"]:
            return 2

        if self.s in ["int", "uint", "float"]:
            return 4

        if self.is_big():
            return 8

        return -1

    def node_data(self):
        return self._node_data

    def copy(self):
        return self.__class__(self.s, self.node_data())

    def __eq__(self, other):
        if isinstance(other, Type):
            return self.s == other.s
        return self.s == str(other)

    @property
    def s(self):
        return self._s_type

    def __str__(self):
        return self._s_type


def _prio():
    if not _D_TYPES:
        return []

    _sa_base = ["char", "uchar", "short", "ushort", "int", "uint", "long", "ulong", "float", "double"]
    sa_prios = _sa_base[:]
    for s in _sa_base:
        for i in range(2, 5):
            sa_prios.append(f"Math::{s}{i}")

    for s in _sa_base:
        for r in range(2, 5):
            for c in range(2, 5):
                sa_prios.append(f"Math::{s}{r}x{c}")

    type_prio_list = [Type(s) for s in sa_prios]
    return type_prio_list


PROMOTION_PRIORITY_LIST = _prio()
# print([t.s for t in PROMOTION_PRIORITY_LIST])

ARRAY_DIM_MISSMATCH = 1
INCOMPATIBLE_TYPES = 2
NUMERIC_AUTO_CONVERSION = 4
NUMERIC_LOSSY_CONVERSION = 8
MATRIX_DIM_EXTENSION = 16
MATRIX_DIM_INCOMPATIBLE = 32


def _numeric_scalar(type_target, type_value):
    status = 0
    # if the target is a fraction, it's only a matter of float or double
    # if we have a float, we just cant assign ulong or long
    if type_target.is_fraction():
        if type_value.numeric_size() > type_target.numeric_size():
            status |= NUMERIC_LOSSY_CONVERSION
            return status
        status |= NUMERIC_AUTO_CONVERSION
        return status

    # the target is an integer, if the value is a float, its lossy
    if type_value.is_fraction():
        status |= NUMERIC_LOSSY_CONVERSION
        return status

    # if the value has fewer bytes than the target, this can be automatically converted
    if type_value.numeric_size() < type_target.numeric_size():
        status |= NUMERIC_AUTO_CONVERSION
        return status

    # if the value has more bytes than the target, bifrost wont auto convert
    elif type_value.numeric_size() > type_target.numeric_size():
        status |= NUMERIC_LOSSY_CONVERSION
        return status

    # this means we have equal byte counts on both sides

    # I dont think this would ever be true since identical types are checked above
    # but better safe than sorry
    if type_target.is_unsigned() == type_value.is_unsigned():
        return status

    if type_target.is_unsigned() and (not type_value.is_unsigned()):
        status |= NUMERIC_AUTO_CONVERSION
        return status

    if (not type_target.is_unsigned()) and type_value.is_unsigned():
        status |= NUMERIC_LOSSY_CONVERSION
        return status

    raise Exception(f"I thought I covered every case...: target='{type_target}', value='{type_value}'")


def compatibility(type_target: Type, type_value: Type):
    type_target = Type(type_target)
    type_value = Type(type_value)

    if type_value == type_target:
        return 0

    # if type_value.is_node() and len(type_value.node_data()) == 1:
    #     type_value = type_value.node_data()[0]

    type_value_base = type_value.base_type() if type_value.is_array() else type_value
    type_target_base = type_target.base_type() if type_target.is_array() else type_target

    status = 0
    if type_value.array_dim() != type_target.array_dim():
        status |= ARRAY_DIM_MISSMATCH

    if type_value_base == type_target_base:
        return status

    if type_value_base.is_numeric() and type_target_base.is_numeric():
        # both numeric, good sign

        # if the target is a scalar, make sure the value is as well
        if not (type_target_base.is_vector() or type_target_base.is_matrix()):
            if type_value_base.is_vector() or type_value_base.is_matrix():
                status |= INCOMPATIBLE_TYPES
                return status

            # both are scalar
            status |= _numeric_scalar(type_target=type_target_base, type_value=type_value_base)
            return status

        # the target is a vector or matrix...
        # if its a vector, we accept the same or less components, including scalar values
        # if its a matrix, we accept anything with less or equal rows and cols, including scalars
        if type_target_base.is_vector():
            ia_dims = type_target_base.vector_dim(), -1
            type_target_base = type_target_base.base_type()
        elif type_target_base.is_matrix():
            ia_dims = type_target_base.matrix_dim()
            type_target_base = type_target_base.base_type()
        else:
            raise NotImplementedError

        if type_value_base.is_vector():
            ia_value_dims = type_value_base.vector_dim(), -1
            type_value_base = type_value_base.base_type()
        elif type_value_base.is_matrix():
            ia_value_dims = type_value_base.matrix_dim()
            type_value_base = type_value_base.base_type()
        else:
            ia_value_dims = -1, -1

        if ia_value_dims == ia_dims:
            pass

        elif ia_value_dims[0] <= ia_dims[0] and ia_value_dims[1] <= ia_dims[1]:
            status |= MATRIX_DIM_EXTENSION

        else:
            status |= MATRIX_DIM_INCOMPATIBLE

        status |= _numeric_scalar(type_target=type_target_base, type_value=type_value_base)
        return status

    elif type_value_base.is_numeric() and (not type_target_base.is_numeric()):
        # one numeric, one non numeric, bad
        status |= INCOMPATIBLE_TYPES

    elif (not type_value_base.is_numeric()) and type_target_base.is_numeric():
        # one numeric, one non numeric, bad
        status |= INCOMPATIBLE_TYPES

    elif type_value_base != type_target_base:
        status |= INCOMPATIBLE_TYPES

    return status


def promotable(type, target):
    i_compat = compatibility(target, type)
    if i_compat == 0:
        return True

    if i_compat & ARRAY_DIM_MISSMATCH:
        return False

    if i_compat & INCOMPATIBLE_TYPES:
        return False

    if i_compat & NUMERIC_LOSSY_CONVERSION:
        return False

    if i_compat & MATRIX_DIM_INCOMPATIBLE:
        return False

    return True


def promotable_to_one_of(type, targets):
    i_arr_dim = type.array_dim()
    _x_arr = lambda s, i: i * "array<" + s + i * ">"
    promotion_list = [t for t in PROMOTION_PRIORITY_LIST if _x_arr(t.s, i_arr_dim) in targets]

    for t in promotion_list:
        type_base = type.base_type() if type.is_array() else type
        if promotable(type_base, Type(t)):
            return Type(i_arr_dim * "array<" + t.s + i_arr_dim * ">")
    return False


def get_numeric_base_type(type_lhs, type_rhs, b_char_as_bool=False):
    s_prefix = ""
    s_suffix = ""

    # fractions
    if type_lhs.is_fraction() or type_rhs.is_fraction():
        s_base = "double" if type_lhs.is_big() or type_rhs.is_big() else "float"

    else:
        if type_lhs.is_unsigned() or type_rhs.is_unsigned():
            if (type_lhs.is_unsigned() and type_lhs.numeric_size() >= type_rhs.numeric_size()) or (type_rhs.is_unsigned() and type_rhs.numeric_size() >= type_lhs.numeric_size()):
                s_prefix = "u"

        i_size = max(type_lhs.numeric_size(), type_rhs.numeric_size())
        s_base = {1: "bool" if b_char_as_bool else "char", 2: "short", 4: "int", 8: "long"}[i_size]

    if type_lhs.is_matrix() or type_rhs.is_matrix():
        i_rows_lhs, i_cols_lhs = type_lhs.matrix_dim()
        i_rows_rhs, i_cols_rhs = type_rhs.matrix_dim()
        i_rows_vec_lhs = type_lhs.vector_dim()
        i_rows_vec_rhs = type_rhs.vector_dim()
        i_rows = max(i_rows_lhs, i_rows_rhs, i_rows_vec_lhs, i_rows_vec_rhs)
        i_cols = max(i_cols_lhs, i_cols_rhs)
        s_prefix = f"Math::{s_prefix}"
        s_suffix = f"{i_rows}x{i_cols}"

    elif type_lhs.is_vector() or type_rhs.is_vector():
        i_size_lhs = type_lhs.vector_dim()
        i_size_rhs = type_rhs.vector_dim()
        s_prefix = f"Math::{s_prefix}"
        s_suffix = str(max(i_size_lhs, i_size_rhs))

    return Type(s_prefix + s_base + s_suffix)


if __name__ == "__main__":
    t_float = Type("float")
    t_float_arr1 = Type("array<float>")
    t_float_arr2 = Type("array<array<float>>")

    t_float3 = Type("Math::float3")
    t_float3_arr1 = Type("array<Math::float3>")
    t_float3_arr2 = Type("array<array<Math::float3>>")

    t_uint = Type("uint")
    t_uint_arr1 = Type("array<uint>")
    t_uint_arr2 = Type("array<array<uint>>")

    t_int = Type("int")
    t_int_arr1 = Type("array<int>")
    t_int_arr2 = Type("array<array<int>>")
    
    t_long = Type("long")
    t_long_arr1 = Type("array<long>")
    t_long_arr2 = Type("array<array<long>>")

    print(compatibility(type_target=t_float, type_value=t_float3))
    print(compatibility(type_target=t_float, type_value=t_uint))
    print(compatibility(type_target=t_int, type_value=t_uint))
    print(compatibility(type_target=t_int_arr1, type_value=t_uint))
    print(compatibility(type_target=t_long, type_value=t_uint))
    print(compatibility(type_target=t_float3, type_value=t_float))

