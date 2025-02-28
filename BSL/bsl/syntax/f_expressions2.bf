// functions calls and access can be used in expressions like you'd expect
compound expressions2_MIXED(){
    OBJECT map = {"key": 10};
    LONG[] arr = [1, 2, 3];
    DOUBLE[] x = (map["key", LONG] + split_fraction(12.34)->integer)**arr - arr[:3];
}