import pathlib


PATH_BASE = (pathlib.Path(__file__)/"..").absolute().resolve()

PATH_BIFROST_ENUMS = PATH_BASE/"res"/"bifrost"/"enums.json"
PATH_BIFROST_TYPES = PATH_BASE/"res"/"bifrost"/"types.json"
PATH_BIFROST_NODES = PATH_BASE/"res"/"bifrost"/"nodes.json"
PATH_FIXLIST = PATH_BASE/"res"/"fixlist.json"

FILE_URI_IN_STACKTRACE = False
