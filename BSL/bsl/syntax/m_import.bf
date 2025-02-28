/*
You may want to reuse code in the future, especially functions. It can be a good idea
to put them into their own file and then import them (like in any other language).
Here, imports are a mix of c and python logic. There is a plain
>> import "{file}";
a and
>> import "{file}" as {namespace_name};

The extensions dont matter, but I've been calling files that create compounds
immediately ".bf" and files that serve as libraries ".bfl".
*/

// Import the functions from "demo_lib.bfl" into the namespace "demo_lib". Be aware that
// if you have compounds in that file, they will NOT be executed. This is unlike
// Python or other languages. The reason is that "running" a BSL script doesnt
// actually run it, but instead builds an AST from it. When parsing an "import"
// directive, only the function definitions and overloads from the AST get imported.
// This might change in future versions.
// Since you can define functions with a namespace name, you may shoot yourself
// in the foot if you define a function, and later import something into the
// same namespace. As such, you should try to keep your imports in the beginning
// of the file
import "../../demo_lib.bfl";

// the same import, adding to/overwriting the demo_lib namespace from before, but this time
// it will attempt to load from the BSLPATH env var (if its set)
import "demo_lib.bfl";

// even if you are on windows, I recommend you use forward slashes in both absolute
// and relative paths to avoid issues with escape sequences
// import "C:/some/windows/path/demo_lib.bfl";

// Importing into a custom namespace. The target may be a string or a namespace name.
// If the target is given as a string, it must still match the rules for namespace names.
import "demo_lib.bfl" as "custom_namespace";
import "demo_lib.bfl" as nested::namespace;

// you can also create bfl files containing (only) overloads to complement your
// Bifrost compound libraries. In this case, I created a file containing an
// overload for Roland Reyer's Print::print() compound. If you have the print pack,
// uncomment this line:
// import "print_overloads.bfl";

compound import_LOAD_DUMMY(){
    // call the function by its full name
    demo_lib::dummy();

    // like with Bifrost nodes, you can also call the function by a minimal name
    // just make sure that there is only one "dummy()" function or compound to call
    dummy();

    // or creating from the custom namespaces
    nested::namespace::search_string("find the needle in the haystack", "needle");
    custom_namespace::fibonacci(10);

    // you can also use __debug::dir() to list whats available in a namespace. Unlike
    // other __debug methods, __debug::dir() only takes specific kwargs for settings:
    // nested (bool=false): if true, lists all nested namespace functions, else, only prints
    //      a nested namespace as "<NESTED>::*"
    // newline (bool=true): if false, lists everything in one line, if true, one line per
    //      entry
    // bifrost (bool=true): if false, skips over builtin compounds and operators
    // custom (bool=true): if false, skips over custom defined functions
    // For every printed function, the default signature is also included. Note that this
    // does not include default values!
    __debug::dir("demo_lib");

    // list evey node Bifrost provides in the Core::Array namespace
    __debug::dir("Core::Array", nested=true, custom=false);
}