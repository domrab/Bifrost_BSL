/*
In a previous chapter I showed how to invoke native compounds and operators.
Here I'll go into writing custom compounds/functions.

There are two keywords, "compound" and "function". A compound executes directly
almost like an IIFE. A function is more like a typical function that can be
invoked at a later point. The other difference is that a function may have a
namespace name (::) but compounds do not, in fact, compounds dont need to have a
name at all. Otherwise, they are identical.
There is no support for recursion and no forward declarations. Compounds may be
nested but functions cant be. When nesting compounds, keep in mind the scope of
variables. Since this language 'compiles' into a Bifrost graph, I am limited to
what I can recreate in Bifrost. As such, there is currently no support for
variables to be accessed across scope boundaries, neither up nor down. This also
means no global variables. To mimic a global variable, define a function that
returns the desired value.
*/

// create a simple function that calculates the hypotenuse of a triangle. Like
// with overload declarations, the return ports may be specified either in or
// after the parameter brackets. Overloading custom functions only works through
// 'overload' statements. If you define a second function with the same name but
// different parameters, it will overwrite the previous one.
function Math::hypotenuse(DOUBLE base, DOUBLE height => DOUBLE hypotenuse){
    hypotenuse = (base**2 + height**2)**0.5;
}

// an identical function with a different syntax:
function Math::hypotenuse_2(DOUBLE base, DOUBLE height) => DOUBLE hypotenuse {
    hypotenuse = (base**2 + height**2)**0.5;
}

// at this point, no Bifrost nodes will have been created but both functions
// are available
compound op2_FUNCTIONS(=> BOOL success){
    // like native operators and compounds, functions may be called with or without
    // namespace as long as they are uniquely identifiable
    DOUBLE h1 := hypotenuse(3, 4);
    DOUBLE h2 := Math::hypotenuse_2(3, 4);

    success = h1 == h2;
}

compound op2_NESTING(){
    // define a variable here
    LONG x = 1;

    NODE nested_scope1 = compound() => DOUBLE value {
        // this is a new scope, in here, we wont have access
        // to anything from the outer scope. Its perfectly
        // legal to create another variable name 'x' in here
        LONG x = 2;
        value = 0.5;
    }

    // to access a variable in a nested scope, it needs to be passed
    // in through the parameter list. It can be assigned the same name
    // or a different one
    NODE nested_scope2 = compound(LONG x=x, LONG also_x=x) => DOUBLE value {
        value := sin(x + also_x);
    }

    // before moving on, I need to mention that there is an important difference
    // between LHS and RHS variables. Both in terms of their meaning and what you
    // can do with them.
    // Consider the following compound. A 'var_in' port on the left and a 'var_out'
    // port on the right, both connected.
    ... = compound(LONG var_in=10) => LONG var_out {
        // Because var_out is an out port, it can only be used on the left side of an
        // expression. Even after it was assigned a value, it can currently not be
        // used on the right side of an expression.
        // Contrary, An in port is just an out port on the inside of the compound.
        // Therefore it may very well be reassigned. The variable will then just point
        // to another outgoing port on a node within the compound.
        var_out = var_in;
    }
}

compound op2_STATE(){
    // to define a state/feedback port, you add `@<port>` to the output port
    ... = compound(OBJECT current_state) => OBJECT next_state@current_state {
        next_state = current_state;
    }
}