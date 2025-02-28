class _StaticMemory:
    DA_DATA = None
    DA_WRITE_ONLY = None


def init_static_memory():
    _StaticMemory.DA_DATA = [{}]
    _StaticMemory.DA_WRITE_ONLY = [{}]


def set_static_variable(s_name, value_type, value=None, b_write_only=False):
    if value_type.s == "__NODE" and value is None:
        raise Exception("NODE type values cannot be None")
    if b_write_only:
        _StaticMemory.DA_WRITE_ONLY[-1][s_name] = {"type": value_type, "value": value}
    else:
        _StaticMemory.DA_DATA[-1][s_name] = {"type": value_type, "value": value}


def get_static_variable_type(s_name):
    return _StaticMemory.DA_DATA[-1].get(s_name, _StaticMemory.DA_WRITE_ONLY[-1].get(s_name, {"type": None}))["type"]


def is_write_only(s_name):
    if s_name in _StaticMemory.DA_DATA[-1]:
        return False
    return s_name in _StaticMemory.DA_WRITE_ONLY[-1]


def get_static_variable_value(s_name):
    return _StaticMemory.DA_DATA[-1].get(s_name, {"value": None})["value"]


def push_scope():
    scope = {}
    _StaticMemory.DA_DATA.append(scope)
    _StaticMemory.DA_WRITE_ONLY.append({})
    return scope


def pop_scope():
    _StaticMemory.DA_WRITE_ONLY.pop(-1)
    return _StaticMemory.DA_DATA.pop(-1)


def print_all_scopes():
    for i, d_scope in enumerate(_StaticMemory.DA_DATA):
        print("+" + 20 * "-")
        for k, v in d_scope.items():
            print(f"| {i * '    '}{k}: {str(v['type'])}")
        for k, v in _StaticMemory.DA_WRITE_ONLY[i].items():
            print(f"| {i * '    '} (RESULT) {k}: {str(v['type'])}")

    print("+" + 20 * "-")
