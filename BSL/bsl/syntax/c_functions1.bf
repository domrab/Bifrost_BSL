/*
You can call Bifrost native compounds and operators as long as
they are known in advance. Follow the setup steps to learn how
to create this library

In this file, I am only going over how to call a function and
specify overloads. I am not discussing capturing returned ports
yet.
*/

compound op_SIMPLE(){
    // calling operators with no auto ports is straight forward
    // Operators and compounds may be called either by their full name including
    // namespace, partial namespace, or just their name. Make sure your compounds
    // have unique names if you do though.
    ... = create_mesh_cube();

    // with arguments for length, width, and height. Argument names and types
    // correspond to the Bifrost ports
    ... = create_mesh_cube(1.0f, 2.0f, 3.0f);

    // or, more clearly, with keyword arguments
    ... = create_mesh_cube(length=1.0f, width=2.0f, height=3.0f, position={0, 0, 0}f);

    // python rules apply, you may mix args and kwargs, but args have to come before kwargs
    ... = create_mesh_cube(1.0f, 2.0f, 3.0f, position={0, 0, 0}f, create_tags=false);
}

// because none of this code calls Bifrost, I have to do type resolution myself. There
// should be flags in the vnnNode and vnnCompound commands according to the docs but I
// got word from Autodesk that those docs are wrong and those flags dont exist :(
// Because of this, operators and compounds with auto types and overloads are a bit
// harder to implement. I have a system called Overlord to deal with overloads. You can
// specify available type combinations for operators and compounds. This unfortunately
// is not enough to cover every case. There are limitations (and lots of bugs I am sure)
// specifically around the topic of auto looping nodes. I have not found a reliable method
// to test auto loops yet unfortunately.
// When adding a type declarations or modifications to the Overlord, it is your
// responsibility to ensure the types are actually correct!
// Below is an example adding a custom overload to Roland Reyer's Print::print() node:
// (I'll talk about return types in a bit)

overload Print::print(
    value_1=*,  // value_* may be of any type, AUTO is not used on purpose
    value_2=*,  // Instead of using a wildcard, you may also deliberately
    value_3=*,  // pick a specific type or types separated by a pipe character:
    value_4=*,  // value_1=FLOAT or value_1=FLOAT|DOUBLE|LONG
    array_1=[], // array_* must be of arrays. You could specify a proper type like STRING[],
    array_2=[], // but for this node, we can accept so many different types, that it would
    array_3=[], // not be feasible to specify them all individually. If you want to specify
    array_4=[]  // an arbitrary array of a very specific dimension, use [1] or [2] or [3]
);

// Now you may be thinking, this looks fragile. But wait till you see the code, its much
// worse than you think!!
// I dont like how this works currently. I like my implementation even less as it grew and
// grew and grew and grew into the abomination it is.

// Lets look at another example to figure out return values: modulo (this does not affect
// the operator (%) but only when you call the function modulo(x, y)
// The type of the remainder depends on the input types:
//   +----------------------+
//   o- value    remainder -o
//   o- divisor             |
//   +----------------------+
// If value and divisor are of the same type, remainder will be as well, but if their types
// differ, Bifrost starts promoting types around. I do not have a mechanism that lets you
// specify relationships between ports to that extend. For now, you'll have to define these
// yourself. However, I dont recommend you do that. Primarily because it can throw off the
// type resolution. Imagine you define a modulo node with DOUBLE types on all 3 ports. Great,
// any numeric value will be able to connect and the script will assume the return value to
// be of type DOUBLE, but it Bifrost, that's not actually true. It may return a LONG or an INT.
// And there may be other downstream nodes that cant compile because of this.
// I have specified types and type resolutions to the best of my ability for all (most?) auto
// ports that I could find so this should not be a big concern for you on simple nodes, but
// it also applies to your own overloads. Be careful and make sure you get it right!

/*
Return values of functions/compounds or just the ports, there are two ways to specify them.
Within the parameter brackets, or after:
>> compound my_compound(FLOAT in => FLOAT out) {}
>> compound my_compound(FLOAT in) => FLOAT out {}
The same holds true for overloads
>> overload Core::Math::modulo(CHAR, CHAR => CHAR);
>> overload Core::Math::modulo(UCHAR, UCHAR) => UCHAR;
*/

// Unlike input overloads, output ports may not have variable types separated by |.
// Thats because the output port types are dependent on the input port types. If there
// are multiple output types for one port for the same inputs, I would not be able
// to tell which overload you'd like to call.
// Important note again, this has absolutely no effect on what happens in Bifrost,
// these overloads here only tell this tool not to freak out if it encounters a certain
// combination of input types.

// I have a growing collection of default nodes with overloads specified through
// the Overlord, primarily Core::Array nodes. But there is one node that has been
// making trouble: set_in_array(). The index port is of type long, not auto. However,
// there exists a version of the node that is capable of taking in an array<long>
// Because this is not an auto port, I have no been able to specify it through the
// Overlord, and because I need relationships between the ports, using overload
// declarations is suboptimal as well. This isnt that terrible because you can use
// square bracket access to set one or more values in an array (more in a later example),
// but its worth noting if you have compounds that have lots of type configurations

compound op_AUTO_PORTS(){
    // this would fail since based on the given overloads, module only takes
    // CHAR and UCHAR
    // ... = modulo(10i, 6i);

    FLOAT[] arr_f = [0.0f, 1.0f, 2.0f, 3.0f];
    LONG[] arr_l = [0, 2];
    LONG len_arr_f := array_size(arr_f);
    LONG len_arr_l := array_size(arr_l);
}

// A special case of operators are operators with associative ports. Namely:
//   min, max, build_array, add, subtract, multiply, divide, matrix_multiply

// Since these nodes dont have overloads to define, their input types are checked
// against each other. Similarly to the type resolution in expressions. Build
// array can take numeric values of different types, but those may not be combined
// with strings or other non numeric values.

compound op_TYPES() {
    // function arguments dont have to be values but can also be types
    ... = identity(type=DOUBLE2x4);
    ... = identity(type=DOUBLE4x2);
    ... = default_value(ULONG3[]);
}

/*
Not all nodes have (complete) overload sets here. If you run into an
issue because an overload set is missing, you can easily define one
yourself. Lets imagine the Core::Logic::if function did not have an
overload to compare two strings with an array of bools as condition.
You could define the overload like this:
>> overload Core::Logic::if(BOOL[], STRING, STRING) => STRING[];
(in a previous version, this function did not have the necessary
overload, I have since added it which makes this overload redundant)
Personally, I dont like to work with auto ports except for some very
general functionality (eg push_stack and pop_stack). And for
specifying a handful overloads max, this is all fine. However, if you
make heavy use of overloads where types change somewhat unpredictably,
it might be better to define overload rules or an overload resolver
through python. I am purposefully not going into detail about that as
I dont have a public API
*/

compound op_IF() {
    LONG result := if(5 > 3, 5, 3);
    STRING[] result_s := if(0 == 0, "equal", ["not_equal", "NOT equal"]);

    BOOL[] conditions = [true, false, true];
    STRING[] filter := if(conditions, "yes", "no");
}

function func(){}

compound op_NESTED_FUNCTIONS(){
    // nested functions can be a bit tricky. Generally, functions can be used in
    // expressions without hassle if they only have a single output. Eg sin() or
    // cos()
    DOUBLE x = 1.2345;
    DOUBLE sin_plus_cos = sin(x) + cos(x);
    DOUBLE one = power(sin(x), 2) + power(cos(x), 2);

    // when dealing with nodes that have multiple outputs, you need to specify
    // the port you want to use in the expression
    ... = 1.0f - split_fraction(1.2f)->fraction;

    // if you dont remember the exact port names of a node, you can use a
    // special function __debug::outputs() that will print the outputs for a NODE
    // result. Like with the __debug::type() function, you can use any arguments or
    // keyword arguments.
    __debug::outputs(sin_node=sin(UCHAR));
    // > __debug::outputs(sin={sine: float})

    // it also works on NODE variables
    NODE frac = split_fraction(FLOAT);
    __debug::outputs(frac);
    // > __debug::outputs({fraction: float, integer: float})

    // there is also a function __debug::inputs(). This one only takes the function
    // name as string and returns the default input types.
    // Here, the kwarg name will be ignored and instead the function name will be printed
    __debug::inputs("sin", this_get_ignored="cos");
    // __debug::inputs(sin={value: auto}, cos={value: auto})
}
