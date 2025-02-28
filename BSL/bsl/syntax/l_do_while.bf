/* DO WHILE (do {} while {})
- Keep in mind that a do-while loop only checks the condition after the action.
That means it runs at least once.

- if no max_iterations are given, you need to use the 'nolimit' keyword before 'do'.

- outport ports cannot be iteration targets. They need to be either state ports or
regular output ports.

- the expression in the condition is actually in the scope of the loop and has access to
variables defined in there
*/

compound loops_DOWHILE(){
    // this has a slightly different syntax since the condition needs to be incorporated

    // calculate factorial of N (in practice, iterate would be better suited here but I want
    // to show the syntax)
    AUTO N = 5;

    // nolimit allows to not specify a max iterations
    LONG result, ... := nolimit do(LONG counter=N, LONG factorial_state=1)
        // putting the result in the next line to keep it shorter
        // when splitting statements like this across multiple lines, keep in mind
        // that errors only show the last line. They do, however, print the line
        // numbers of all lines in which the error might be
        => LONG factorial@factorial_state,
           LONG next_counter@counter
    {
        factorial = factorial_state * counter;
        next_counter = counter - 1;
    }
    while ( counter > 1 );
}

// lets try something more practical (although since we have sort_array, not that useful)
// quicksort! (source: https://www.geeksforgeeks.org/iterative-quick-sort)
function qs_partition(LONG[] arr, LONG low, LONG high) => LONG[] out_arr, LONG pivot {
    AUTO x = arr[high];
    AUTO i = low - 1;

    arr, i := iterate(arr, x, i => LONG[] out_arr@arr, LONG out_i@i) < high-low, #<j>=low {
        AUTO arr_j = arr[j];
        BOOL condition = arr_j <= x;

        // updated i
        AUTO i_inc := i+1;

        AUTO arr_i = arr[i_inc];

        // swap (or not)
        arr[j] := if(condition, arr_i, arr_j);
        arr[i_inc] := if(condition, arr_j, arr_i);

        out_i := if(condition, i_inc, i);
        out_arr = arr;
    }
    AUTO i_inc = i+1;

    // final swap
    AUTO arr_i = arr[i_inc];
    AUTO arr_h = arr[high];
    arr[i_inc] = arr_h;
    arr[high] = arr_i;

    pivot = i_inc;
    out_arr = arr;
}

// main quicksort function
function quicksort(LONG[] arr) => LONG[] sorted {
    AUTO arr_size := array_size(arr);

    // initial low and high
    AUTO low = 0;
    AUTO high = arr_size - 1;

    // create an array of sufficient length
    LONG[] stack = [LONG, arr_size];
    stack[0] = low;
    stack[1] = high;

    LONG top = 1;

    // no need for nolimit since we know the worst case scenario
    // "using" loads "sorted" automatically into the "sorted" variable
    using => do(arr, stack, top) < arr_size
                 => LONG[] _stack@stack, LONG[] sorted@arr, LONG _top@top
    {
        AUTO high = stack[top];
        stack[top] = -1;
        top = top - 1;

        AUTO low = stack[top];
        stack[top] = -1;
        top = top - 1;

        // out_arr already updated for the next iteration!
        sorted, LONG pivot = qs_partition(arr, low, high);

        // left update left side of the pivot. Since Bifrost has a pull
        // mechanism, its not sure if this code even executes. Implementing
        // algorithms here is a bit tricky since it looks like other languages
        // but at the same follows Bifrost rules
        NODE update_left = compound(LONG[] _stack=stack, LONG low=low, LONG _top=top, LONG pivot=pivot)
                               => LONG[] stack, LONG top
        {
            _top = _top + 1;
            _stack[_top] = low;
            _top = _top + 1;
            _stack[_top] = pivot - 1;

            top = _top;
            stack = _stack;
        }

        // determine if the left branch is needed
        stack := if(pivot - 1 > low, update_left->stack, stack);
        top := if(pivot - 1 > low, update_left->top, top);

        // left update right side of the pivot. Since Bifrost has a pull
        // mechanism, its not sure if this code even executes. Implementing
        // algorithms here is a bit tricky since it looks like other languages
        // but at the same follows Bifrost rules
        NODE update_right = compound(LONG[] _stack=stack, LONG high=high, LONG _top=top, LONG pivot=pivot)
                                => LONG[] stack, LONG top
        {
            _top = _top + 1;
            _stack[_top] = pivot + 1;
            _top = _top + 1;
            _stack[_top] = high;

            top = _top;
            stack = _stack;
        }

        // determine if the right branch is needed and update the output variables
        _stack := if(pivot + 1 < high, update_right->stack, stack);
        // the top variable here created since we cant use _top in the condition expression
        top := if(pivot + 1 < high, update_right->top, top);
        _top = top;

    } while (top > 0)
}

// testing quicksort
compound loop_QUICKSORT_TEST() => BOOL success {
    LONG[] arr = [10, -3, 5, 3, 2, 100, 56, 0, 0, 0, 0, -2, 16, 20, 15];

    LONG[] sorted := quicksort(arr);
    LONG[] control := sort_array(arr);

    success := all_true_in_array(sorted == control);
}