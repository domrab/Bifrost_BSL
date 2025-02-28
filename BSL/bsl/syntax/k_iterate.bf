/*
ITERATE (iterate)
- if no max_iterations are given, at least one port has to be a port iteration target

- output ports have to be either iteration targets OR state ports. State ports are defined
like feedback ports on compounds using '@<port>'
*/

compound loops_ITERATE(){
    // loop settings for max_iterations and current_index still apply from the
    // foreach example.

    // calculating the cumulative sum of an array
    AUTO arr = [1, 3, 5, 10, 12, 30];
    using => iterate(arr#, LONG _last=0) => LONG sum@_last {
        sum = _last + arr;
    }

    // calculating the cumulative array sum of an array at each step
    using => iterate(arr#, LONG _last=0) => LONG sum@_last, LONG[] steps# {
        steps = _last + arr;
        sum = _last + arr;
    }

    // calculate the N-th number in the fibonacci sequence
    // p is the fibonacci number
    // _p/pp is the previous fibonacci number
    // _pp is the previous previous fibonacci number
    // fib is a an array to which each p gets added
    AUTO N = 10;
    LONG last, ..., LONG[] fib = iterate(LONG _p=0, LONG _pp=0 => LONG p@_p, LONG pp@_pp, LONG[] fib#) <N, #=0 {
		LONG temp := if(# < 2, #, _p + _pp);
		fib = temp;
		pp = _p;
		p = temp;
	}
}