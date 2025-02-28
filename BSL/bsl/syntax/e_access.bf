/*
There are different kinds of access and different types that can be accessed

In the return chapter, we accessed ports on a node using the -> operator.
In this section, I'll showcase every other kind of access that is supported.
*/

compound access_TYPE(){
    // port types have member access through "."
    DOUBLE4 quat = {0,0,0,1};
    AUTO x = quat.x;
    AUTO w = quat.w;
    quat.x = x;
    quat.w = w;

    AUTO transform := identity(MATRIX4);
    DOUBLE4 col1 = transform.c0;
    DOUBLE pos_x = transform.c3.x;
    transform.c0 = col1;
    transform.c3.x = pos_x;

    AUTO location = GEOLOCATION{};
    GEOTYPE location_type = location.type;
    location.type = location_type;
}

compound access_ARRAY(){
    // arrays can be accessed through square brackets
    LONG[] arr = [10, 20, 30, 40, 50];

    // arrays can be accessed by a single value
    LONG first = arr[0];

    LONG index = -1;
    AUTO last = arr[index];

    // or by a list of values
    LONG[] part1 = arr[[0,1,2]];

    LONG[] indices = [4, 3];
    LONG[] part2_rev = arr[indices];

    // or by slice. Slicing works the same way it does in python
    LONG[] even = arr[::2];
    LONG[] odd = arr[1::2];
    LONG[] without_last = arr[:-1];
    LONG[] without_first = arr[1:];
    LONG[] last_three = arr[-3:];
    LONG[] without_first_and_last_reverse = arr[-2:1:-1];
    LONG[] second_till_third = arr[2:3];

    // and more combinations. All also work with variables
    LONG start = -2;
    LONG end = -5;
    LONG stride = 3;
    LONG[] arr_dyn = arr[start:end:stride];
    LONG[] arr_trim_start = arr[start:];

    // you can assign one value to a single position in an array
    arr_dyn[0] = 0;

    // assigning to multiple values is currently not supported
}

compound access_STRING(){
    // strings can be accessed using slices as well
    STRING s = "Hello world.";
    STRING hello = s[:5];

    // like arrays, a value can be assigned to a single index in a string
    s[-1] = "!";
}

compound access_OBJECT(){
    // Objects can be accessed through square brackets as well, however,
    // they require a single STRING and a default value/type (get_property)
    // the default can bei either a value or a type.
    OBJECT constants = {"pi": 3.14, "e": 2.72};
    constants["g"] = 9.81;

    // the second value/types serves both as a fallback and as type hint for
    // what gets returned. Its up to you to validate the content of the returned
    // value if you question whether it was successful or not.
    DOUBLE pi = constants["pi", DOUBLE];

    // accessing a valid key with a wrong type will yield the fallback
    STRING e = constants["e", STRING];

    // accessing with default value
    STRING updated = constants["last_updated", "<unknown>"];
}

compound access_CONCAT(){
    // you can concatenate multiple types off access. Since the language is
    // statically typed, if all overloads are properly set and I didnt mess
    // up, you should get proper errors if you are trying to do access something
    // that doesnt exist or is not allowed (in theory^^)
    OBJECT versions = {"maya": [{2023, 3}s, {2024, 2}s, {2025, 3}s]};
    STRING software = "maya";
    SHORT latest_major = versions[software, [{-1, -1}s]][-1].y;

    // you cannot currently concatenate anything but nested port names
    // on the left side of an expression
}

compound access_ENUM(){
    // enum values are not access per se, but they can be used
    // to access the value of an enum
    AUTO rotate_order = ROTATE_ORDER.XYZ;

    // you cannot currently assign anything to enums
}
