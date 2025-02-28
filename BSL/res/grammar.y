##############################
### define terminals first ###
##############################

NEWLINE = \n+

COMMENT_INLINE = //
# denote the start only, the process function will do the rest
COMMENT_BLOCK = /\*

# denote the start only, the process function will do the rest
STRING = ["']

FLOAT = -?([1-9][0-9_]*[0-9]*|0)(\.[0-9][0-9_]*[0-9]*(e(\+|-)?[1-9][0-9_]*[0-9]*)?|(e(\+|-)?[1-9][0-9_]*[0-9]*))[fF]
DOUBLE = -?([1-9][0-9_]*[0-9]*|0)(\.[0-9][0-9_]*[0-9]*(e(\+|-)?[1-9][0-9_]*[0-9]*)?|(e(\+|-)?[1-9][0-9_]*[0-9]*))[dD]
FRACTIONAL = -?([1-9][0-9_]*[0-9]*|0)(\.[0-9][0-9_]*[0-9]*(e(\+|-)?[1-9][0-9_]*[0-9]*)?|(e(\+|-)?[1-9][0-9_]*[0-9]*))

UNSIGNED_CHAR = -?([1-9][0-9_]*[0-9]*|0)[uU][cC]
UNSIGNED_SHORT = -?([1-9][0-9_]*[0-9]*|0)[uU][sS]
UNSIGNED_INT = -?([1-9][0-9_]*[0-9]*|0)[uU][iI]
UNSIGNED_LONG = -?([1-9][0-9_]*[0-9]*|0)[uU][lL]

UNSIGNED_NATURAL = -?([1-9][0-9_]*[0-9]*|0)[uU]

CHAR = ([0-9][0-9_]*[0-9]*|0)[cC]
SHORT = ([0-9][0-9_]*[0-9]*|0)[sS]
INT = ([0-9][0-9_]*[0-9]*|0)[iI]
LONG = ([0-9][0-9_]*[0-9]*|0)[lL]
NATURAL = ([0-9][0-9_]*[0-9]*|0)

IGNORE = \.\.\.

RESULT = =>
POINT_TO = ->

WALRUS = :=

POW = \*\*

ADD = \+
SUB = -
MUL = \*
DIV = /
MOD = %

EQ = ==
NE = !=
GE = >=
GT = >
LE = <=
LT = <

NOT = !

OR = \|\|
XOR = \^
AND = &&

INDEX = [#]
STATE = @

# (([a-zA-Z_][a-zA-Z0-9_]*::)+[a-zA-Z_][a-zA-Z0-9_]*)|(([a-zA-Z_][a-zA-Z0-9_]*\.)+[a-zA-Z_][a-zA-Z0-9_]*)
ENUM_VALUE = ({__ENUMS__})\.[a-zA-Z_][a-zA-Z0-9_]*
#ENUM = ({__ENUMS__})
#TYPE = ({__TYPES__})
#NAMESPACE = ([a-zA-Z_][a-zA-Z0-9_]*::)+
#NAME = \$?[a-zA-Z_][a-zA-Z0-9_]*
NAME = (([a-zA-Z_][a-zA-Z0-9_]*::)*[a-zA-Z_][a-zA-Z0-9_]*)|\$?[a-zA-Z_][a-zA-Z0-9_]*

FOR_EACH = "for_each"
FOREACH = "foreach"
ITERATE = "iterate"
NOLIMIT = "nolimit"
DO = "do"
WHILE = "while"
USING = "using"
FUNCTION = "function"
COMPOUND = "compound"
OVERLOAD = "overload"
IMPORT = "import"
AS = "as"
TRUE = "true"
FALSE = "false"
AUTO = "AUTO"
NODE = "NODE"

# multi string access for string vs array
# this will also be useful for type hints on
# matrices.
# R_BRACKET_S = ]s  # commenting this since I have moved things
# around and the function creating the nodes now has access to
# the incoming type

R_CURLY_BOOL = }[bB]
R_CURLY_FLOAT = }[fF]
R_CURLY_DOUBLE = }[dD]
R_CURLY_UNSIGNED_LONG = }[uU][lL]
R_CURLY_UNSIGNED_INT = }[uU][iI]
R_CURLY_UNSIGNED_SHORT = }[uU][sS]
R_CURLY_UNSIGNED_CHAR = }[uU][cC]
R_CURLY_UNSIGNED_NATURAL = }[uU]
R_CURLY_LONG = }[lL]
R_CURLY_INT = }[iI]
R_CURLY_SHORT = }[sS]
R_CURLY_CHAR = }[cC]

ARR_DIM_3 = \[]\[]\[]
ARR_DIM_2 = \[]\[]
ARR_DIM_1 = \[]

####################
### define rules ###
####################

program : execs
        | EMPTY

execs : execs exec
      | exec

exec : function
     | compound
     | overload
     | import

##################
### statements ###
##################

statement_list : statement_list statement
               | statement
               | EMPTY

statement : compound
          | loop
          | using
          | assignment
#          | atom ";"
          | call ";"
          | ";"
          | statement_BAD_1

@BAD_MESSAGE statement_BAD_1 Expression cannot stand by itself!
statement_BAD_1 : expression ";"

##############
### import ###
##############

import : IMPORT STRING ";"
       | IMPORT STRING AS namespace_name ";"
       | IMPORT STRING AS STRING ";"
       | import_BAD_1

@BAD_MESSAGE import_BAD_1 Missing ";"
import_BAD_1 : IMPORT STRING
             | IMPORT STRING AS namespace_name
             | IMPORT STRING AS STRING

#############
### using ###
#############

using : USING RESULT loop
      | USING RESULT compound

##################
### assignment ###
##################

assignment : assignment_lhs_list "=" loop
           | assignment_lhs_list "=" compound
           | assignment_lhs_list "=" expression ";"
           | assignment_lhs_list WALRUS loop
           | assignment_lhs_list WALRUS compound
           | assignment_lhs_list WALRUS expression ";"
           | assignment_BAD_1

# this is a conflict that arises if access_rhs stands as first element
# in a line. This could probably be fixed by creating an AST first that
# doesnt immediately try to convert itself into another representation.
# It may even be ok to just have the conflict (or even the entire assignment)
# as an expression. But I dont wanna do that atm so I'll make it a BAD rule
@BAD_MESSAGE assignment_BAD_1 Missing RHS of assignment. If this is meant to be an expression, use `... = {expression} ;`
assignment_BAD_1 : access_lhs

assignment_lhs_list : assignment_lhs_list "," assignment_lhs_one
                    | assignment_lhs_one

assignment_lhs_one : access_lhs
                   | type name
                   | name
                   | IGNORE

#############
### scope ###
#############

compound : COMPOUND name unnamed_scope ";"
         | COMPOUND name unnamed_scope
         | COMPOUND unnamed_scope ";"
         | COMPOUND unnamed_scope

unnamed_scope : terminal "(" scope_parameters scope_result ")" "{" statement_list "}"
              | terminal "(" scope_parameters ")" scope_result "{" statement_list "}"

scope_result : RESULT scope_result_list
             | EMPTY

scope_result_list : scope_result_list "," scope_result_one
                  | scope_result_one

scope_result_one : defined_port_type name feedback
                 | defined_port_type name
                 | scope_result_BAD_1
                 | scope_result_BAD_2
                 | scope_result_BAD_3

@BAD_MESSAGE scope_result_BAD_1 Iteration target only allowed in loops
scope_result_BAD_1 : defined_port_type name index
                   | name index

@BAD_MESSAGE scope_result_BAD_2 Scope results cannot be 'AUTO'
scope_result_BAD_2 : type_auto name

@BAD_MESSAGE scope_result_BAD_3 Passing variables of type 'NODE' to another scope is not allowed!
scope_result_BAD_3 : type_node name


scope_parameter_one : defined_port_type name "=" expression
                    | defined_port_type name
                    | scope_parameter_BAD_1
                    | scope_parameter_BAD_2

@BAD_MESSAGE scope_parameter_BAD_1 Passing variables of type 'NODE' to another scope is not allowed!
scope_parameter_BAD_1 : type_node name

@BAD_MESSAGE scope_parameter_BAD_2 Scope parameters cannot be 'AUTO'
scope_parameter_BAD_2 : type_auto name


scope_parameter_list : scope_parameter_list "," scope_parameter_one
                     | scope_parameter_one

scope_parameters : scope_parameter_list
                 | EMPTY

############################
### overload declaration ###
############################

overload_arr_dim : ARR_DIM_1
                 | "[" "1" "]"
                 | "[" "2" "]"
                 | "[" "3" "]"

overload_type : overload_type "|" defined_port_type
              | overload_type "|" MUL
              | overload_type "|" overload_arr_dim
              | defined_port_type
              | MUL
              | overload_arr_dim

overload_type_one : overload_type
                  | name "=" overload_type


overload_type_list : overload_type_list "," overload_type_one
                   | overload_type_one

overload_input : overload_type_list

overload_result : RESULT overload_type_list
                | EMPTY

overload : OVERLOAD terminal namespace_name "(" overload_input overload_result ")" ";"
         | OVERLOAD terminal namespace_name "(" overload_input ")" overload_result ";"
         | overload_BAD_1

@BAD_MESSAGE overload_BAD_1 Missing ";" at end of the line.
overload_BAD_1 : OVERLOAD terminal namespace_name "(" overload_input ")" overload_result

####################
### def/function ###
####################

function : FUNCTION namespace_name unnamed_scope

#############
### loops ###
#############

loop : for_each
     | for_each ";"
     | iterate
     | iterate ";"
     | do_while
     | do_while ";"

max_iterations : LT expression

current_index : index LT name GE expression
              | index "=" expression

safe_loop_settings : max_iterations "," current_index
                   | max_iterations

loop_settings : safe_loop_settings
              | "," current_index
              | current_index
              | EMPTY

loop_parameters : loop_parameter_list
                | EMPTY

loop_parameter_list : loop_parameter_list "," loop_parameter_one
                    | loop_parameter_one

loop_parameter_one : port_type name index "=" expression
                   | port_type name "=" expression
                   | name index
                   | name
                   | loop_parameter_BAD_1
                   | loop_parameter_BAD_2

@BAD_MESSAGE loop_parameter_BAD_1 Port state only allowed in result. Missing '=>'?
loop_parameter_BAD_1 : port_type name feedback
                     | name feedback

@BAD_MESSAGE loop_parameter_BAD_2 Passing variables of type 'NODE' to another scope is not allowed!
loop_parameter_BAD_2 : type_node name


for_each : _for_each terminal "(" loop_parameters for_each_result ")" loop_settings "{" statement_list "}"
         | _for_each terminal "(" loop_parameters ")" loop_settings for_each_result "{" statement_list "}"

_for_each : FOREACH
          | FOR_EACH

for_each_result : RESULT for_each_result_list
                | EMPTY

for_each_result_list : for_each_result_list "," for_each_result_one
                     | for_each_result_one

for_each_result_one : type_auto name index
                    | type_auto name
                    | type_array name index
                    | type_array name
                    | for_each_result_one_BAD_1
                    | for_each_result_one_BAD_2

@BAD_MESSAGE for_each_result_one_BAD_1 for_each results must be at least 1D arrays!
for_each_result_one_BAD_1 : type_base name

@BAD_MESSAGE for_each_result_one_BAD_2 Passing variables of type 'NODE' to another scope is not allowed!
for_each_result_one_BAD_2 : type_node name


iterate : ITERATE terminal "(" loop_parameters iterate_result ")" loop_settings "{" statement_list "}"
        | ITERATE terminal "(" loop_parameters ")" loop_settings iterate_result "{" statement_list "}"

iterate_result : RESULT iterate_result_list
               | EMPTY

iterate_result_list : iterate_result_list "," iterate_result_one
                    | iterate_result_one

iterate_result_one : port_type name index
                   | port_type name feedback
                   | iterate_result_one_BAD_1
                   | iterate_result_one_BAD_2

@BAD_MESSAGE iterate_result_one_BAD_1 Must be state port (@<port>) or iteration target (#)
iterate_result_one_BAD_1 : port_type name

@BAD_MESSAGE iterate_result_one_BAD_2 Passing variables of type 'NODE' to another scope is not allowed!
iterate_result_one_BAD_2 : type_node name

do_while : DO terminal "(" loop_parameters do_while_result ")" loop_settings "{" statement_list "}" WHILE "(" expression ")"
         | DO terminal "(" loop_parameters ")" loop_settings do_while_result "{" statement_list "}" WHILE "(" expression ")"
         | DO terminal "(" loop_parameters do_while_result ")" loop_settings "{" statement_list "}" WHILE "(" expression ";" ")"
         | DO terminal "(" loop_parameters ")" loop_settings do_while_result "{" statement_list "}" WHILE "(" expression ";" ")"
         | NOLIMIT DO terminal "(" loop_parameters do_while_result ")" loop_settings "{" statement_list "}" WHILE "(" expression ")"
         | NOLIMIT DO terminal "(" loop_parameters ")" loop_settings do_while_result "{" statement_list "}" WHILE "(" expression ")"
         | NOLIMIT DO terminal "(" loop_parameters do_while_result ")" loop_settings "{" statement_list "}" WHILE "(" expression ";" ")"
         | NOLIMIT DO terminal "(" loop_parameters ")" loop_settings do_while_result "{" statement_list "}" WHILE "(" expression ";" ")"

# disabling this until I have figured out how to correctly identify nested errors. This error
# is now being flagged during AST creation
#         | do_while_BAD_1
#
#@BAD_MESSAGE do_while_BAD_1 Missing nolimit keyword or max_iterations (<) expression
#do_while_BAD_1 : DO "(" loop_parameters do_while_result ")" loop_settings "{" statement_list "}" WHILE "(" expression ";" ")"
#               | DO "(" loop_parameters ")" loop_settings do_while_result "{" statement_list "}" WHILE "(" expression ";" ")"
#               | DO "(" loop_parameters do_while_result ")" loop_settings "{" statement_list "}" WHILE "(" expression ")"
#               | DO "(" loop_parameters ")" loop_settings do_while_result "{" statement_list "}" WHILE "(" expression ")"

do_while_result : RESULT do_while_result_list
                | EMPTY

do_while_result_list : do_while_result_list "," do_while_result_one
                     | do_while_result_one

do_while_result_one : port_type name feedback
                    | port_type name

############
### call ###
############

call : namespace_name terminal "(" call_arguments ")"
     | type_base "{" call_arguments "}"


call_arguments : call_argument_list
               | EMPTY

call_argument_list : call_argument_list "," call_argument_one
                   | call_argument_one

# todo:
#   - add BAD rules for node type
#   - add args/kwargs as separate rules
call_argument_one : name "=" expression
                  | name "=" defined_port_type
                  | expression
                  | defined_port_type

###################
### expressions ###
###################

expression : expression_logic

expression_logic : expression_logic AND expression_cmp
                 | expression_logic OR expression_cmp
                 | expression_logic XOR expression_cmp
                 | expression_cmp

expression_cmp : expression_cmp EQ expression_add
               | expression_cmp NE expression_add
               | expression_cmp GE expression_add
               | expression_cmp GT expression_add
               | expression_cmp LE expression_add
               | expression_cmp LT expression_add
               | expression_add

expression_add : expression_add ADD expression_mul
               | expression_add SUB expression_mul
               | expression_mul

expression_mul : expression_mul MUL expression_pow
               | expression_mul DIV expression_pow
               | expression_mul MOD expression_pow
               | expression_pow

expression_pow : expression_unary POW expression_pow
               | expression_unary

expression_unary : NOT expression_unary
                 | ADD expression_unary
                 | SUB expression_unary
                 | atom

############
### atom ###
############

atom : enum
     | access_port
     | access_rhs
     | atom_small

atom_small : call
           | name
           | value
           | "(" expression ")"

############
### enum ###
############

enum : ENUM_VALUE
     | enum_BAD_1

@BAD_MESSAGE enum_BAD_1 Not a valid enum
enum_BAD_1 : TYPE "." NAME


##############
### access ###
##############

# this could be "map[key]" or "array[::-1]" or "str[2]" or "matrix.c0"
# its important to differentiate between LHS and RHS access. LHS access
# means a value gets assigned and RHS means a value gets accessed ( LHS := RHS)

# this can used to access anything (strings, Objects, and arrays)
_access_expression : "[" expression "]"

# this can be used on strings and arrays
_access_rhs_slice : "[" expression ":" expression ":" expression "]"
                  | "[" expression ":" ":" expression "]"
                  | "[" expression ":" expression "]"
                  | "[" expression ":" "]"
                  | "[" ":" expression ":" expression "]"
                  | "[" ":" ":" expression "]"
                  | "[" ":" expression "]"
                  | _access_rhs_slice_BAD_1

@BAD_MESSAGE _access_rhs_slice_BAD_1 '[:]' expression is not supported since its redundant
_access_rhs_slice_BAD_1 : "[" ":" "]"


# this can only be used for Objects
_access_rhs_default : "[" expression "," expression "]"
                    | "[" expression "," type "]"

access_lhs : name _access_expression
           | name _access_lhs_dot
           | _access_lhs_BAD_1

@BAD_MESSAGE _access_lhs_BAD_1 Assigning to slice is not supported
_access_lhs_BAD_1 : name _access_rhs_slice

_access_lhs_dot : _access_lhs_dot "." name
                | "." name

# the methods currently look almost the same, but they are separated primarily
# make adjustments and identification easier. There is a significant difference
# between how data gets accessed and assigned and by keeping LHS and RHS separate
# I believe to make the most control
access_rhs : atom_small _access_rhs

_access_rhs : _access_rhs _access_rhs_default
            | _access_rhs _access_rhs_slice
            | _access_rhs _access_expression
            | _access_rhs _access_rhs_dot
            | _access_rhs_default
            | _access_rhs_slice
            | _access_expression
            | _access_rhs_dot


_access_rhs_dot : _access_rhs_dot "." name
                | "." name

# different from the above, this is for NODE types
access_port : call point_to_port
            | name point_to_port

point_to_port : point_to_port POINT_TO name
              | POINT_TO name

###################
### identifiers ###
###################

name : "$" NAME
     | NAME

namespace_name : NAMESPACE_NAME
               | NAME

######################
### state/feedback ###
######################

feedback : STATE NAME

################
### terminal ###
################

terminal : LT NAME GT
         | LT GT
         | EMPTY

#############
### types ###
#############

type : type_auto
     | type_array
     | type_node
     | type_base
     | type_enum

port_type : type_auto
          | type_array
          | type_base
          | type_enum

defined_port_type : type_array
                  | type_base
                  | type_enum

type_enum : ENUM

type_base : TYPE

type_array : type_base ARR_DIM_3
           | type_base ARR_DIM_2
           | type_base ARR_DIM_1
           | type_enum ARR_DIM_3
           | type_enum ARR_DIM_2
           | type_enum ARR_DIM_1

type_auto : AUTO

type_node : NODE

#####################
### simple values ###
#####################

value : string
      | index
      | bool
      | numeric
      | vector
      | matrix
      | object
      | array


string : STRING

index : INDEX

bool : TRUE
     | FALSE

numeric : some_float
        | some_int

some_float : float
           | double

float : FLOAT

double : DOUBLE
       | FRACTIONAL

some_int : ulong
         | uint
         | ushort
         | uchar
         | long
         | short
         | char
         | int

ulong : UNSIGNED_LONG
      | UNSIGNED_NATURAL

ushort : UNSIGNED_SHORT

uchar : UNSIGNED_CHAR

uint : UNSIGNED_INT

long : LONG
     | NATURAL

int : INT

short : SHORT

char : CHAR

vector : "{" _vector R_CURLY_BOOL
       | "{" _vector R_CURLY_FLOAT
       | "{" _vector R_CURLY_DOUBLE
       | "{" _vector R_CURLY_UNSIGNED_CHAR
       | "{" _vector R_CURLY_UNSIGNED_SHORT
       | "{" _vector R_CURLY_UNSIGNED_INT
       | "{" _vector R_CURLY_UNSIGNED_LONG
       | "{" _vector R_CURLY_UNSIGNED_NATURAL
       | "{" _vector R_CURLY_CHAR
       | "{" _vector R_CURLY_SHORT
       | "{" _vector R_CURLY_INT
       | "{" _vector R_CURLY_LONG
       | "{" _vector "}"

#       | vector_BAD_1
#@BAD_MESSAGE vector_BAD_1 Missing type hint
#vector_BAD_1 : "{" _vector "}"

_vector : expression "," expression "," expression "," expression
        | expression "," expression "," expression
        | expression "," expression

matrix : "{" _matrix R_CURLY_BOOL
       | "{" _matrix R_CURLY_FLOAT
       | "{" _matrix R_CURLY_DOUBLE
       | "{" _matrix R_CURLY_UNSIGNED_CHAR
       | "{" _matrix R_CURLY_UNSIGNED_SHORT
       | "{" _matrix R_CURLY_UNSIGNED_INT
       | "{" _matrix R_CURLY_UNSIGNED_LONG
       | "{" _matrix R_CURLY_UNSIGNED_NATURAL
       | "{" _matrix R_CURLY_CHAR
       | "{" _matrix R_CURLY_SHORT
       | "{" _matrix R_CURLY_INT
       | "{" _matrix R_CURLY_LONG
       | "{" _matrix "}"

#       | matrix_BAD_1
#@BAD_MESSAGE matrix_BAD_1 Missing type hint
#matrix_BAD_1 : "{" _matrix "}"

_matrix : _matrix_col "|" _matrix_col "|" _matrix_col "|" _matrix_col
        | _matrix_col "|" _matrix_col "|" _matrix_col
        | _matrix_col "|" _matrix_col

_matrix_col : expression "," expression "," expression "," expression
            | expression "," expression "," expression
            | expression "," expression
            | expression

# no node type array allowed
# maybe at a later point but that would have
# to be implemented in a different way
array : "[" port_type "," expression "]"
      | "[" port_type "]"
      | "[" _array "]"

_array : _array "," expression
       | expression

object : "{" _object "}"
       | "{" EMPTY "}"

_object : _object "," atom "=" expression
        | _object "," atom ":" expression
        | atom "=" expression
        | atom ":" expression
