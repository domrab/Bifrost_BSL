/*
Expressions are similar to other languages but there are no bitwise operations
implemented yet. Operators support common auto loops and auto type promotions.
Result types are calculated based on Bifrost type promotion rules.

Operations like (1+2+3) are split into two nodes ((1+2)+3) for simplicity in
parsing and converting the code. Generally, I am not making any optimizations
here (eg precomputing constant values) and instead cross my fingers and hope
the Amino compiler takes care of that.


 (binary)
 operator | function
----------+----------
     +    |  add
          |
     -    |  subtract
          |
     *    |  multiply (scalar multiplication, multiplying matrices with
          |  this method will multiply the members
          |
     /    |  divide
          |
     %    |  modulo
          |
     **   |  power
          |
     ==   |  equal
          |
     !=   |  not equal
          |
     >=   |  greater or equal
          |
     <=   |  less or equal
          |
     >    |  greater
          |
     <    |  less
          |
     ||   |  or
          |
     &&   |  and
          |
     ^    |  xor
          |

  (unary)
 operator | function
----------+----------
     -    |  negate
          |
     !    |  not
          |

*/

compound expressions1_SIMPLE(){
    INT x = 20i;
    INT y = 30i;

    // math operators
    INT x_plus_y = x + y;
    INT x_minus_y = x - y;
    INT x_times_y = x * y;
    INT x_divided_by_y = x / y;
    INT x_power_y = x ** y;
    INT x_mod_y = x % y;

    // also works with vectors
    FLOAT3 vecA = {1, 2, 3}f;
    LONG3 vecB = {4, 5, 6}l;
    DOUBLE3 vecC = vecA + vecB;

    // comparison operators
    BOOL x_equal_y = x == y;
    BOOL x_not_equal_y = x != y;
    BOOL x_greater_than_y = x > y;
    BOOL x_less_than_y = x < y;
    BOOL x_greater_or_equal_y = x >= y;
    BOOL x_less_or_equal_than_y = x <= y;
    BOOL a_equal_to_not_b = x_equal_y == !x_not_equal_y;

    // logic operators only supported for bool types
    BOOL result_or = x_equal_y || x_not_equal_y;
    BOOL result_and = x_equal_y && x_not_equal_y;
    BOOL result_xor = x_equal_y ^ x_not_equal_y;

}

compound expressions1_PROMOTIONS(){
    // float and long -> double
    LONG x = 10;
    FLOAT y = 3.0f;
    DOUBLE z = x * y;

    // float and int -> int
    INT x_int = 10i;
    FLOAT z_float = x_int * y;

    // unlike bifrost, the code automatically promotes
    // booleans in math operations to char
    BOOL a = true;
    BOOL b = false;
    CHAR c = a + b;

    // vectors and non vectors
    DOUBLE scale = 2.5;
    FLOAT3 vec = {1.2, 3.4, 5.6}f;
    DOUBLE3 result = scale * vec;

}

compound expressions1_AUTO_LOOPS(){
    // auto loops also follow the same promotion rules
    LONG[] samples = [80, 90, 100, 110, 120];
    FLOAT pi = 3.14f;
    DOUBLE[] results = samples * pi;

    // nested arrays
    LONG[][] nested_arrays = [[0], [1, 2], [3, 4, 5]];
    LONG[][] negated_nested_arrays = -nested_arrays;

    // mixing different array dimensions is not allowed
    // ... = nested_arrays + samples;

    BOOL[] filterA = [true, false, false, true, false, true];
    BOOL[] filterB = [true, true, false, false, true, true];
    BOOL[] both = filterA && filterB;
    BOOL[] either = filterA || filterB;
}

compound expressions1_MORE_PROMOTIONS(){
    // mixing more types. You can use "AUTO" as type and the tool
    // will happily assign the type it sees fit, but I dont have
    // an IDE for you that'll tell you the type when hovering over
    // it. I was confused about type promotions in the beginning
    // but once you get the hang of it, its pretty easy.
    USHORT[] s = [4s];
    LONG i = 3;
    FLOAT3 v = {10, 20, 30}f;

    DOUBLE3[] arr = s + i / v;
}

compound expressions1_STRINGS(){
    // strings have limited support at this point. The only operator
    // currently supported is "+" between strings.
    STRING concat = "string1" + " " + "string2";

    // like with numeric arrays, if you add a single string to and
    // array of strings, the result is an array of strings
    STRING[] suffixes = ["A", "B", "C"];
    STRING[] names = "name_" + suffixes;
}