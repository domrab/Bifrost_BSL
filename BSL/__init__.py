from BSL._visitor_ast import Ast
from BSL._bifcmds import Graph
from BSL import _ui as ui
from BSL import _bifres
from BSL import _constants

from BSL._overlord import Overlord as _Overload


if _constants.PATH_BIFROST_NODES.exists():
    _Overload.init()


def collect_nodes_and_enums():
    _bifres.get_data(b_update=True)
