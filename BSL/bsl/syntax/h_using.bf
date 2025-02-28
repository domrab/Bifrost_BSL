/*
For loops and nested compounds, besides the discussed return methods, there is
one more. The 'using => ' statement loads the return ports as variables in the
enclosing scope. If variables of the precise type already exist, they get
assigned the new values. If they dont exist, new variables are created.
*/

compound using_EXAMPLE(){
    // two new variables pi and e are created in the current scope
    using => compound() => DOUBLE pi, DOUBLE e {
        pi = 3.14;
        e = 2.72;
    }

    // proof they exist
    DOUBLE pi_times_e = pi * e;

    // since the variables already exist they just get the new values assigned
    using => compound() => DOUBLE pi, DOUBLE e {
        pi = 3.14159;
        e = 2.71828;
    }

    // check they are different
    DOUBLE pi_times_e_better = pi * e;
    BOOL different = pi_times_e == pi_times_e_better;
}