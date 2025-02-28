function func(STRING test, FLOAT3 test2){}

compound(){
    func(test2=FLOAT3, test=STRING);

    BOOL3 vec3 = {true, false, false}b;

    BOOL a1 := any_members_true(vec3);
    BOOL[] a2 := any_members_true([vec3]);

    __debug::outputs(if([true], {}, {}));
    __debug::outputs(one_over(true));

    __debug::outputs(round_to_ceiling(true));
    __debug::outputs(length({1.0, 1.0}l));
    __debug::outputs(normalize({1.0, 1.0}l));
    __debug::outputs(normalize([{1.0, 1.0}l]));
    __debug::outputs(direction_and_length({1.0, 1.0}l));
    __debug::outputs(direction_and_length([{1.0, 1.0}l]));
    __debug::outputs(matrix_is_identity([{1.0, 1.0 | 2, 3 | 3, 4}i]));
    __debug::outputs(transpose_matrix([{1.0, 1.0 | 2, 3 | 3, 4}i]));
    __debug::outputs(matrix_to_quaternion([{1.0, 1.0 | 2, 3 | 3, 4}i]));

    __debug::outputs(identity(FLOAT4));

    __debug::outputs(matrix_to_quaternion(identity(FLOAT3x3)));
    __debug::outputs(matrix_to_SRT(identity(FLOAT3x3)));

    __debug::outputs(quaternion_invert(identity(DOUBLE4)));
    __debug::outputs(quaternion_invert(identity([FLOAT4])));
    __debug::outputs(transform_to_rotation_matrix(identity([INT4x4])));

    __debug::outputs(get_closest_locations(positions=FLOAT3[]));

    AUTO x := increment({true, false}b);

    BOOL check = "abc" > "cde";

    FIELD f1 := scalar_field(2i);
    FIELD3 f3 := vector_field(3.0f);
    AUTO f1_2 = -f1;
    AUTO f3_2 = -f3;
    AUTO f1_3 = f1 * f1_2;
    AUTO f3_3 := multiply(f1, f3_2);

    __debug::type(f1_3);
    __debug::type(f3_3);

    __debug::outputs(atan_2D(scalar_field(), scalar_field()));
    __debug::outputs(atan_2D(INT, LONG));
    __debug::outputs(random_value(min=LONG, max=UINT));
    __debug::outputs(remap_property(new_min=INT, new_max=DOUBLE));

    __debug::outputs(lerp(INT3[], DOUBLE, FLOAT[]));

    __debug::outputs(clamp_influence(min=FLOAT, max=FLOAT3));

    __debug::outputs(distance(FLOAT3[][], LONG[][]));
    __debug::outputs(distance_float_ULP(FLOAT3[][], LONG[][]));
    __debug::outputs(remainder(FLOAT3x2, LONG[][]));

    __debug::outputs(dot(FLOAT3, UINT3[][]));
    __debug::outputs(quaternion_slerp(FLOAT3, UINT3[][], FLOAT, use_nlerp_if_closer=FLOAT));

    __debug::outputs(randomize_geo_property(OBJECT, STRING, min=INT, max=LONG3, default_value=CHAR));

    __debug::outputs(get_raycast_locations(positions=FLOAT, directions=FLOAT));

    __debug::outputs(if(BOOL[][], FLOAT3[][], LONG4));
    __debug::outputs(members_if(BOOL2x2[][], FLOAT3[][], LONG4));

    __debug::outputs(distance_float_ULP(FLOAT[][], DOUBLE));
    __debug::outputs(equivalent_float_ULP(FLOAT[], DOUBLE3, INT[]));

    __debug::outputs(expect_equal(FLOAT[], DOUBLE3, STRING));

    __debug::outputs(create_mesh_plane(length_segments=10i, width_segments=10i));

    AUTO sample = sample_property(geometry=OBJECT, locations=GEOLOCATION[], default=FLOAT3);
    __debug::outputs(sample);

    __debug::outputs(within_bounds(FLOAT, FLOAT, FLOAT3[]));


    ... = compound() => LONG[] x
    {
        using => foreach(=> LONG[] x) < 10 {};
//        LONG[] y = x+1;
    }
}