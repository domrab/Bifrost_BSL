from BSL import _constants, _special_types


def read_file(f):
    return (_constants.PATH_BASE/f).absolute().read_text()


def read_lines(f):
    return [s for s in read_file(f).split("\n") if s]


_TYPE_DICT = None


def get_type_dict():
    global _TYPE_DICT
    if _TYPE_DICT is None:
        _TYPE_DICT = {s.split("=")[0].strip(): s.split("=")[1].strip() for s in read_lines("res/types.txt")}

        for value in list(_TYPE_DICT.values()):
            _TYPE_DICT[value] = value

        _TYPE_DICT = _special_types.Namespaces(_TYPE_DICT)

    return _TYPE_DICT


def get_type_string():
    return '"' + '"/"'.join(get_type_dict()) + '"'
