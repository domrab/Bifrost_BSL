/*
FOR EACH (for_each or foreach)
- if no max_iterations are given, at least one port has to be a port iteration target

- foreach loops are required to have outgoing iteration targets, adding
the '#' is optional. However, output types have to be at least 1D arrays.
*/

compound loops_FOREACH(){
    // For loop that runs 10 times. The semicolon after a closing '}' is optional.
    for_each() < 10 {};
    foreach() < 10 {};  // also valid

    // For loop that runs N times
    AUTO N = 10;
    foreach() < N {}

    // For loop that runs 10 times but current index starts at -9
    // Inside of the loop scope, the current index can be referred to as '#'
    // This is not an issue for nested loops since the index of the enclosing loop
    // would get passed as a parameter.
    foreach() < 100, #=-9 {}

    // since referring to # can be useful in some instances but quite cumbersome in
    // others, '#' can be aliased. Within the loop body, both '#' and 'i' point to
    // the current_index port. I can be reassigned within the loop but '#' cant.
    foreach() < 100, #<i>=-9 {}

    // For loop that runs 10 times
    // with an input port 'value' of type FLOAT3 with values {1,2,3}
    foreach(FLOAT3 value={1,2,3}f) < 10 {}

    // For loop that takes in the whatever 'var' is pointing at currently
    // the resulting input port will also be called 'var' (or match whatever
    // variable name gets passed in)
    FLOAT var = 1.0f;
    foreach(var) < 10 {}

    // Nested for loops computing n*m for 0<n<= M and 0<m<=M
    AUTO M = 10l;
    foreach(M => LONG[][] result) < N, #=1 {
        result := foreach(LONG n=# => LONG[] result) < M, #=1{
            result = n*#;
        }
    }

    // this is one instance where # can get confusing and an alias might help
    foreach(M => LONG[][] result) < N, #<n>=1 {
        result := foreach(n => LONG[] result) < M, #<m>=1 {
            result = n*m;
        }
    }

    // A for loop without max iterations must have at least one iteration target as input.
    // FLOAT3[] position#=pos creates an input iteration target with the value of 'pos'
    // normal# creates an input iteration target called 'normal' from whatever 'normal'
    // is currently pointing at. Similar to envelope although envelope is not an
    // iteration target
    AUTO pos = [FLOAT3];
    AUTO normal = [FLOAT3];
    AUTO envelope = 1.0f;
    foreach(FLOAT3[] position#=pos, normal#, envelope) {}

    // Same as previous, but with max iterations set
    foreach(FLOAT3[] position#=pos, normal#, envelope) < 100 {}

    // A for loop running max 100 times with 'pos' and 'nrm' input iteration targets.
    // This for loop returns a an array of FLOAT3 values. Since this is a for loop,
    // its irrelevant if the output is specified as an iteration target or not. It
    // is always treated as such
    AUTO nrm = [FLOAT3];
    AUTO env = 1.0f;
    foreach(pos#, nrm#, env) < 100 => FLOAT3[] out_pos# {}
    foreach(pos#, nrm#, env) < 100 => FLOAT3[] out_pos {}

    // For loops can return zero, one, or multiple ports. Those output ports are
    // available within the for loop with one array dimension removed so values can
    // be assigned directly. ~After the loop, they are available as if they were assigned
    // their value~ Lets not do that anymore. Otherwise the variable space gets polluted.
    // Either assign the foreach to a NODE variable and use node->port_name, or just assign
    // them to new variables
    foreach(pos#, nrm#, env) < 100 => FLOAT3[] out_pos#, LONG[] id# {
        // out_pos should be an array, same with pos and nrm. Since they are
        // all iteration targets though, within the loop, they are available as
        // FLOAT3 (or whatever base type pos and nrm are in the outer scope)
        out_pos = pos + nrm * env;
        id = #;
    }

    // same as above only without explicitly marking 'out_pos' and 'id' explicitly as
    // iteration targets
    foreach(pos#, nrm#, env) < 100 => FLOAT3[] out_pos, LONG[] id {
        out_pos = pos + nrm * env;
        id = #;
    }
    
    // like with compounds and functions, results/output ports may be written either inside
    // of the parameter brackets or outside. In the case of loops, outside means after the
    // loop settings
}
