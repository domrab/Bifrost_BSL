from BSL import _error

def not_(sa_names_in, sa_names_out, sa_types_in, sa_types_out, input_types):
    if input_types[0].base_type().base_type() != "bool":
        return False, f"Cant invert value of type '{input_types[0]}'"
    return True, (input_types, [input_types[0].s])
