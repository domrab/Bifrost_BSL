from BSL import _file_io, _constants, _bifres

import json


def _is_integer(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return (
        ":char" in s or
        ":short" in s or
        ":int" in s or
        ":long" in s or
        "char" == s or
        "short" == s or
        "int" == s or
        "long" == s
    )


def _is_scalar_field(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return "Core::Fields::ScalarField" == s


def _is_vector_field(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return "Core::Fields::VectorField" == s


def _is_geo_location(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return "Geometry::Common::GeoLocation" == s


def _is_big(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return (
        ":long" in s or
        ":ulong" in s or
        ":double" in s or
        "long" == s or
        "ulong" == s or
        "double" == s
    )


def _is_bool(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return (
        ":bool" in s or
        "bool" == s
    )


def _is_long(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return (
        ":long" in s or
        ":ulong" in s or
        "long" == s or
        "ulong" == s
    )


def _is_int(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return (
        ":int" in s or
        ":uint" in s or
        "int" == s or
        "uint" == s
    )


def _is_floating(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return (
        ":float" in s or
        ":double" in s or
        "float" == s or
        "double" == s
    )


def _is_unsigned(s):
    s = s.partition(">")[0].rpartition("<")[2]
    return (
        ":uchar" in s or
        ":ushort" in s or
        ":uint" in s or
        ":ulong" in s or
        "uchar" == s or
        "ushort" == s or
        "uint" == s or
        "ulong" == s
    )


def _is_vector(s, size="234"):
    s = s.strip(">")
    return s[-1] in size and s[-3] not in "234"


def _is_matrix(s, rows="234", cols="234"):
    s = s.strip(">")
    return s[-1] in cols and s[-3] in rows


sa_types = list(_bifres.TYPES.keys())
# future dom: I dont think this is necessary since the enums are already part of types...
sa_types += list(_bifres.ENUMS.keys())

for i in range(3):
    sa_types += [f"array<{s}>" for s in sa_types]

ALL_TYPES = set(sa_types)

ARRAY = {s for s in sa_types if s.count(">") > 0}
ARRAY1 = {s for s in sa_types if s.count(">") == 1}
ARRAY2 = {s for s in sa_types if s.count(">") == 2}
ARRAY3 = {s for s in sa_types if s.count(">") == 3}

SIMPLE = {s for s in sa_types if "::" not in s}
ANY = {s for s in sa_types if s == "any" or "<any>" in s}
BOOL = {s for s in sa_types if _is_bool(s)}
STRING = {s for s in sa_types if s == "string" or "<string>" in s}
OBJECT = {s for s in sa_types if s == "Object" or "<Object>" in s}

VECTOR = {s for s in sa_types if _is_vector(s, "234")}
VECTOR2 = {s for s in VECTOR if _is_vector(s, "2")}
VECTOR3 = {s for s in VECTOR if _is_vector(s, "3")}
VECTOR4 = {s for s in VECTOR if _is_vector(s, "4")}

MATRIX = {s for s in sa_types if _is_matrix(s, "234", "234")}
MATRIX2x2 = {s for s in MATRIX if _is_matrix(s, "2", "2")}
MATRIX2x3 = {s for s in MATRIX if _is_matrix(s, "2", "3")}
MATRIX2x4 = {s for s in MATRIX if _is_matrix(s, "2", "4")}
MATRIX3x2 = {s for s in MATRIX if _is_matrix(s, "3", "2")}
MATRIX3x3 = {s for s in MATRIX if _is_matrix(s, "3", "3")}
MATRIX3x4 = {s for s in MATRIX if _is_matrix(s, "3", "4")}
MATRIX4x2 = {s for s in MATRIX if _is_matrix(s, "4", "2")}
MATRIX4x3 = {s for s in MATRIX if _is_matrix(s, "4", "3")}
MATRIX4x4 = {s for s in MATRIX if _is_matrix(s, "4", "4")}
MATRIX_SQUARE = MATRIX2x2 | MATRIX3x3 | MATRIX4x4
MATRIX_x4 = MATRIX2x4 | MATRIX3x4 | MATRIX4x4 | MATRIX4x3 | MATRIX4x2

DOUBLE = {s for s in sa_types if s.rpartition("<")[2].split("::")[-1].startswith("double")}
FLOAT = {s for s in sa_types if s.rpartition("<")[2].split("::")[-1].startswith("float")}
FLOATING = FLOAT | DOUBLE
UNSIGNED = {s for s in sa_types if _is_unsigned(s)}
INTEGER = {s for s in sa_types if _is_integer(s)} | UNSIGNED
BIG = {s for s in sa_types if _is_big(s)}
LONG = {s for s in sa_types if _is_long(s)}
INT = {s for s in sa_types if _is_int(s)}

FIELD = {s for s in sa_types if _is_scalar_field(s)}
FIELD3 = {s for s in sa_types if _is_vector_field(s)}
FIELDS = FIELD | FIELD3

GEOLOCATION = {s for s in sa_types if _is_geo_location(s)}

NUMERIC = FLOATING | INTEGER

AUTO_SCALAR = {"float", "array<float>", "array<bool>", "array<long>", "string"} | (FIELD-ARRAY)
AUTO_VECTOR = {"float", "Math::float3", "array<Math::float3>", "string"} | (FIELDS - ARRAY)
AUTO_TAG = {"array<bool>", "array<long>", "array<uint>", "long", "string"}


SIM_SCALAR = {"float", "Core::Fields::ScalarField"}
SIM_VECTOR = {"float", "Math::float3", "Core::Fields::ScalarField", "Core::Fields::VectorField"}

USD_ATTR = ((DOUBLE & MATRIX_SQUARE) | (FLOATING & VECTOR) | (NUMERIC & SIMPLE) | STRING | (BOOL & SIMPLE)) - ARRAY3 - ARRAY2