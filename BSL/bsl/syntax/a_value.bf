compound value_INTEGERS(){
    // Non annotated integer types are treated as "long"
    // Integers annotated with "u" are treated as "ulong"
    // This decision was made since many 'default' ports
    // like "max_iterations" or "current_index" are of
    // type long and the promotion mechanisms often
    // promote to the bigger types (long & double).
    // Type hints are case insensitive
    CHAR value1 = 0c;
    UCHAR value2 = 1UC;
    SHORT value3 = 2s;
    USHORT value4 = 3uS;
    INT value5 = 4i;
    UINT value6 = 5ui;
    LONG value7 = 6l;
    LONG value8 = 7;
    ULONG value9 = 8ul;
    ULONG value10 = 9u;

    ULONG value11 = - 9u;

    // negative unsigned values between -max and 0 wrap around
    // but values <-max and >max will result in 0
    UCHAR max_uchar = -1uc;   // -> '255'
    UCHAR invalid_zero1 = -256uc; // -> '0'
    UCHAR invalid_zero2 = 256c;   // -> '0'
}

compound value_FLOATING_POINT(){
    // Non annotated floating point numbers are treated as "double"
    FLOAT value1 = 9.0f;
    DOUBLE value2 = 10.0d;
    DOUBLE value3 = 11.0;

    // floating point numbers may be written in scientific notation
    DOUBLE value4 = 1e+10;
    DOUBLE value5 = 1.0e-2;
    FLOAT value6 = 1_000_000e-2_3_4f;
}

compound value_ALL_NUMBERS(){
    // all numbers may be written with underscores for visibility
    LONG value1 = 10_000;
    ULONG value2 = 1_000_000ul;
    FLOAT value3 = 1_234.567_789f;
}

compound value_STRINGS(){
    // strings are supported with both double (") and single (') quotes
    STRING double_quotes = "string";

    STRING escaped_double_quotes = "escaped \"string";
    STRING single_quotes = 'more strings';
    STRING more_strings = 'more \'escaped\' "strings"';

    // you can also use special characters "\n" and "\t"
    STRING multi_line = "First line\nSecond line\n\tThird, indented line";

    // you may also use "\t" as a character, this can throw off the error
    // print since \t can be printed at various lengths and I dont know
    // of a way to get that. To be on the safe site, I recommend to just
    // go with "\t" instead.
    // you may not span a string across multiple lines!
    STRING with_tab = "before	after";
    STRING also_with_tab = "before\tafter";

    // otherwise, escape sequences work as usualy
    STRING with_backslash_t = "before\\tafter";

    // you can concatenate strings using the "+" operator
    STRING[] multi_line2 = "First line" + "\n" +
                         "Second line" + ["\n"] +
                         "\tThird line";
}
compound value_VECTORS(){
    // vectors may have type hints. Type hints are specified by appending a
    // suffix behind the closing curly brace. If no type hint is specified, the
    // vector's members are assumed to be of type DOUBLE.
    // Components within a vector can have any type suffix, they get get converted
    // to the vectors type, even if its a lossy conversion. Type hints are again
    // case insensitive.
    FLOAT2 vec2 = {1.0, 2.0}f;  // double values get converted to float
    ULONG3 uvec3 = {1.2, 2.3f, 3c}u; // double, float and char get converted to ulong
    BOOL4 bvec4 = {true, false, 1.0, 0.0f}b; // values get converted to boolean

    // variables may be used to specify components in vectors.
    LONG vec_x = 1;
    LONG2 vec_xy = {vec_x, 2}L;
}

compound value_MATRICES(){
    // matrices are very similar to vectors in terms of type hints
    // may have both columns and values given through variables. Columns are
    // separated by pipes (|)
    DOUBLE3x3 identity1 = {1.0, 0.0, 0.0 | 0.0, 1.0, 0.0 | 0.0, 0.0, 1.0 };
    DOUBLE3x3 identity2 = {{1.0, 0.0, 0.0} | {0.0, 1.0, 0.0} | {0.0, 0.0, 1.0}};

    DOUBLE a = 1.0;
    DOUBLE b = 2.0;
    DOUBLE c = 3.0;
    DOUBLE3 abc = {a, b, c};
    DOUBLE4x4 mtx = { a, b    |  // only c0.x and c0.y will be set
                      a, b, c |  // c1.x, c1.y, c1.z
                      abc     |  // c2 will be set to abc (DOUBLE3)
                      a       }; // c3 will be set to a (DOUBLE)

    // when only a single value per column is given, that value gets connected to
    // the column. This mechanism is used to determine the matrix shape.
    // While using scalar values for a column is acceptable, they cant be used to
    // determine the final row count, therefore a matrix which has only scalar
    // values for all columns will create a type error.
    // DOUBLE3x3 err = { a | b | c };
}

compound value_OBJECTS(){
    // OBJECT function similar to dicts in python although you may use either equals (=)
    // or a colon (:) in the initialization
    OBJECT map1 = {}; // empty dict
    OBJECT map2 = {"key1": "value1", "key2"="value2"};

    // you may use variables for both keys and values
    STRING name = "pi";
    DOUBLE value = 3.14;
    OBJECT math_constants = {name: value};
}

compound value_ENUMS(){
    // for the most part, enums dont have special type aliasing.
    Geometry::PointShapes shape = Geometry::PointShapes.Disk;

    // The exception for enums is Math::rotate_order. It has an alias
    // named ROTATE_ORDER
    // these lines are identical
    ROTATE_ORDER ro1 = Math::rotation_order.XYZ;
    Math::rotation_order ro2 = ROTATE_ORDER.XYZ;
}

compound value_TRANSFORMS(){
    // transform type is not as interesting for the creation. TRANSFORM
    // values should be created through compute_transform() or similar
    // nodes. The alias for Core::Transform::Transform is TRANSFORM
    TRANSFORM xform := compute_transform();

    // three more special types are MATRIX2, MATRIX3, and MATRIX4. These
    // are square matrices of type DOUBLE
    MATRIX2 mtx2 = { 1,0 | 0,1 };
    MATRIX3 mtx3 = { 1,0,0 | 0,1,0 | 0,0,1 };
    MATRIX4 mtx4 = { 1,0,0,0 | 0,1,0,0 | 0,0,1,0 | 0,0,0,1};
}

compound value_ARRAYS(){
    // arrays get specified by appending [] between one and three times to
    // the type. This language currently does not support more than 3 levels
    // of nested arrays.
    // The type is inferred based on Bifrost's type promotion rules.
    STRING[] string_arr = ["one", "two", "three"];
    FLOAT3[] float3_arr = [1c, 2us, {3, 4, 5}f];
    LONG[] long_arr = [1, 2, 3];

    DOUBLE3[][] double3_arr2 = [float3_arr, long_arr];

    // enum arrays of more than one dimension currently crash Bifrost therefore
    // this is disabled.
    // ROTATE_ORDER[][] ro = [[Math::rotation_order.XYZ]];
}

compound value_CUSTOM(){
    // other types are GEOLOCATION (Common::Geometry::GeoLocation) and
    // GEOTYPE (Common::Geometry::GeoType). They primarily exist because
    // I am using them to showcase features later in the examples
    // Such struct types (types having members) can be created by calling
    // the type with curly braces
    GEOLOCATION location = GEOLOCATION{};

    // To avoid typing the type twice, you can use AUTO. You can also use
    // arguments to set values. There is no type casting so you need to pass
    // in the appropriate types.
    AUTO location2 = GEOLOCATION{index=0ui};

    // there is a chance that you'll use AUTO more often in the future and
    // there might be a day where you get type errors and you are not sure
    // where they are coming from. Since I dont have a fancy IDE that can
    // tell you the type of your AUTO variables, I have a debug function
    // that prints the types for one or more values or variables during
    // during code generation
    __debug::type(location, location_as_kwarg=location2);
    __debug::type(char=0c, uchar=0uc, short=1s, ushort=1us);

    // There is also a FIELD and FIELD3 (for ScalarField and VectorField)
    // since I dont commonly work with them, I did not bother creating
    // special constructors for them. The only way to create them currently
    // is through the scalar_field(), vector_field() or to_field() methods.
    FIELD field_scalar := scalar_field(3.0f);
    FIELD3 field_vector := vector_field({2.0, 3.0, 3.0}f);
    FIELD scalar_field_through_conversion := to_field(4);
    FIELD3 vector_field_through_conversion := to_field({4, 3, 2}l);
}

compound value_VARNAME(){
    // since in Bifrost types and port names are two distinct "things", its
    // perfectly fine to have a port called "float" or "FLOAT". Here, both
    // are just words, this can lead to issues if you have compounds that
    // have a port that is named after a type. Fear not, you can use a dollar
    // sign ($) in front of variable names to mitigate this.
    FLOAT $FLOAT = 10.0f;
    FLOAT $DOUBLE = $FLOAT * 2.0f;
}
