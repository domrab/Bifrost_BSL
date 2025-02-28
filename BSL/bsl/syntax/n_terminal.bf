/*
Terminals can be set for any function call, native or custom. There is no
error checking done so its perfectly legal to set terminal flags on a node
without terminals inside.
Terminals can be defined upon function definition and later be later replaced
when calling the function
*/

// define a function that has all 3 terminal flags enabled by default
//   F - full
//   P - proxy
//   D - diagnostic
// The order is irrelevant
function with_terminal<FPD>(){
    // create a terminal that has only the diagnostic and proxy flags enabled
    // that means the F flag on this function will have no affect. Keep in mind
    // that the terminal flags will only be propagated up if the ports are
    // connected
    terminal<DP>(proxy=[{}], diagnostic=[{}]);
}

// no terminal is specified on this compound so it will have all flags
// that are set on the inside
compound terminal_AUTO(){
    // calling the function with default terminal flags
    with_terminal();

    // calling the function with no terminal flags
    with_terminal<>();

    // calling the function with the diagnostic flag
    with_terminal<D>();

    // terminals are applicable to any sort of scope. That includes compounds
    // and loops
    foreach<P>()<10 {
        with_terminal();
    }
}