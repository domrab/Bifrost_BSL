/*
The supported loops correspond to the three loop compounds in Bifrost.
They look like compounds with extra ports and port settings, and as
such, they look similar like previously discussed compounds as well.
For all loops, there is a max_iterations and current_index port. Like in
Bifrost, both are optional and dont have to be provided.

To define the start for the current_index, use '#=x' where x is the start
value. For max_iterations its '<N' where N is are the max iterations.
There is also a special variable '#' available within the scope of the
loop pointing to the current index. So accessing non iteration target arrays
is trivial 'arr[#]' or getting the next element is 'arr[#+1]'

All loops support port iteration targets. Those can be used either together or
instead of max_iterations. A port iteration target (both in and out) can be
specified by adding '#' to the name. Ensure it is at least a 1D array. The
variable is then available within the loop at reduced array dimensionality.
Eg 'FLOAT3[] pos#'. Within the loop, 'pos' will be of type 'FLOAT3'.

The port names 'max_iterations', 'current_index', and 'looping_condition' are not allowed
on any of the loops.

This is about it for the commonalities between the loops. From here on, each
loop has its own special requirements and permits different operations

The following chapters will give several examples of each loop

*/