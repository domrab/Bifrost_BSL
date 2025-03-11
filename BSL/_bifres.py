import json
import time
import os
import pathlib

from BSL import _constants
from BSL import _special_types


_D_FIXLIST = json.loads(_constants.PATH_FIXLIST.read_text())


def _collect_nodes():
    from maya import cmds
    cmds.file(new=True, force=True)
    cmds.loadPlugin("bifrostGraph", qt=True)

    s_graph = cmds.createNode("bifrostGraphShape", name="bifrostGraphShape1")
    b_load_default_overload = True

    d_nodes = {}
    for s_lib in cmds.vnn(libraries="BifrostGraph"):
        sa_nodes = [s_node for s_node in cmds.vnn(nodes=("BifrostGraph", s_lib))]
        if not sa_nodes:
            continue
        d_nodes[s_lib] = sa_nodes

    d_node_data = {}

    cmds.vnnChangeBracket(s_graph, open=True)
    g_start = time.time()
    try:
        for s_lib in d_nodes:
            start = time.time()

            for s_type in d_nodes[s_lib]:
                s_full_name = s_lib + "::" + s_type
                d_data = d_node_data[s_full_name] = {}

                s_node = "/" + cmds.vnnCompound(s_graph, "/", addNode=f"BifrostGraph,{s_lib},{s_type}")[0]

                # get metadata since listPorts sometimes returns the ports in a different order from the node
                try:
                    sa_meta_keys = cmds.vnnCompound(s_graph, s_node, qms=True)
                    b_is_compound = True
                except:
                    b_is_compound = False
                    sa_meta_keys = cmds.vnnNode(s_graph, s_node, qms=True)

                # get the input port names
                sa_input_names = cmds.vnnNode(s_graph, s_node, listPorts=True, inputPort=True) or []

                # check the there is a UILayout that might be overriding the order
                if "UILayout" in sa_meta_keys:
                    da_ports = json.loads(cmds.vnnNode(s_graph, s_node, qmd="UILayout")[0])["NodeLayout"]["items"]

                    set_input_ports = set(sa_input_names)
                    sa_input_names = []

                    i = 1000
                    while da_ports and i > 0:
                        i -= 1
                        port = da_ports.pop(0)
                        if "port" in port and port["port"] in set_input_ports:
                            sa_input_names.append(port["port"])

                        if "items" in port:
                            da_ports = port["items"] + da_ports

                sa_input_types = []
                saa_input_suggestions = []
                i_ports_with_suggestions = 0

                sa_fan_in = []
                for s_port in sa_input_names:
                    s_port_type = cmds.vnnNode(s_graph, s_node, queryPortDataType=s_port)
                    s_suggested = cmds.vnnNode(s_graph, s_node, queryPortMetaDataValue=[s_port, "TypeWranglingSuggestedTypes"])

                    # there are some ports that have that metadata but are not actually auto ports
                    if s_full_name in _D_FIXLIST and s_port in _D_FIXLIST[s_full_name]:
                        s_suggested = ""

                    if s_suggested:
                        i_ports_with_suggestions += 1
                        saa_input_suggestions.append([s.strip() for s in s_suggested.split(",") if s.strip()])
                        sa_input_types.append("auto")
                        if s_port_type != "auto":
                            print("    ", s_type, s_port)

                    elif s_port_type == "auto":
                        saa_input_suggestions.append([])
                        sa_input_types.append(s_port_type)

                    else:
                        saa_input_suggestions.append([s_port_type])
                        sa_input_types.append(s_port_type)

                    # I dont think auto ports can be fan-ins (at least not by default)
                    if s_port_type != "auto":
                        flags = cmds.vnnPort(s_graph, f"{s_node}.{s_port}", 0, 1, qf=True)
                        if 2 & flags:
                            sa_fan_in.append(s_port)

                d_data["is_compound"] = b_is_compound
                d_data["inputs"] = sa_input_names
                d_data["fan-in"] = sa_fan_in
                d_data["has_auto_input"] = "auto" in sa_input_types
                d_data["suggestions"] = saa_input_suggestions

                # check output ports
                # I have not found evidence that output port might be jumbled as well. Although that doesnt
                # mean much since I stumbled across this by pure coincidence
                sa_output_names = cmds.vnnNode(s_graph, s_node, listPorts=True, outputPort=True) or []
                sa_output_types = []
                for s_port in sa_output_names:
                    s_port_type = cmds.vnnNode(s_graph, s_node, queryPortDataType=s_port)
                    sa_output_types.append(s_port_type)

                d_data["outputs"] = sa_output_names
                d_data["has_auto_output"] = "auto" in sa_output_types

                # if there are no auto inputs but auto outputs, its save to assume that
                # they wont change their type. So might as well get Bifrost to us what
                # type they actually are
                if d_data["has_auto_output"] and not d_data["has_auto_input"]:
                    cmds.vnnChangeBracket(s_graph, close=True)
                    sa_output_types = []
                    for s_port in sa_output_names:
                        s_port_type = cmds.vnnNode(s_graph, s_node, queryPortDataType=s_port)
                        sa_output_types.append(s_port_type)
                    cmds.vnnChangeBracket(s_graph, open=True)
                    d_data["has_auto_output"] = "auto" in sa_output_types

                # this is the 'plain' type
                d_data["overloads"] = {"-".join(sa_input_types): sa_output_types}

                # this will take a bit longer, but querying the default types for auto types
                # allows to at least superficially check the type engine later against this
                # default define
                if b_load_default_overload and d_data["has_auto_input"]:
                    cmds.vnnChangeBracket(s_graph, close=True)
                    sa_input_types = []
                    for s_port in sa_input_names:
                        s_port_type = cmds.vnnNode(s_graph, s_node, queryPortDataType=s_port)
                        sa_input_types.append(s_port_type)

                    sa_output_types = []
                    for s_port in sa_output_names:
                        s_port_type = cmds.vnnNode(s_graph, s_node, queryPortDataType=s_port)
                        sa_output_types.append(s_port_type)
                    cmds.vnnChangeBracket(s_graph, open=True)

                d_data["default_overload"] = (sa_input_types, sa_output_types)

                cmds.vnnCompound(s_graph, "/", removeNode=s_node.strip("/"))

            end = time.time()
            print(f"{s_lib} ({len(d_nodes[s_lib])}): {end-start:.02f}s")

    except Exception as e:
        raise e

    finally:
        cmds.vnnChangeBracket(s_graph, close=True)
        g_end = time.time()
        print(f"-> {g_end-g_start:.02f}s")

    _constants.PATH_BIFROST_NODES.parent.mkdir(parents=True, exist_ok=True)
    _constants.PATH_BIFROST_NODES.write_text(json.dumps(d_node_data, indent=4))


def _collect_enums():
    if "BIFROST_LIB_CONFIG_FILES" in os.environ:
        sa_paths = os.environ["BIFROST_LIB_CONFIG_FILES"].split(os.pathsep)

    # this is the fallback method currently hardcoded
    else:
        raise Exception("Missing BIFROST_LIB_CONFIG_FILES env var")

    sa_paths = [(0, s) for s in sa_paths]
    sa_libs = []

    i_max = 1000
    while i_max > 0 and sa_paths:
        i_max -= 1

        indent, path = sa_paths.pop(0)
        if not path:
            continue

        path = pathlib.Path(path)
        s_content = path.read_text()
        s_content = "\n".join([s for s in s_content.split("\n") if not s.strip().startswith("#")])
        d_data = json.loads(s_content)

        if "include" in d_data:
            sa_files_to_include = [s.split(":")[1].strip(" ,\"") for s in s_content.split("\n") if ":" in s]
            for s_file in sa_files_to_include:
                s_new_path = os.path.expandvars(str((path.parent/s_file).resolve().absolute()))
                if "${" in s_new_path:
                    # print(f"  skipping {s_new_path}")
                    continue
                sa_paths.insert(0, (indent+1, s_new_path))

        elif "AminoConfigurations" in d_data:
            da_configs = d_data["AminoConfigurations"]
            for d_config in da_configs:
                if "jsonLibs" in d_config:
                    for d_lib in d_config["jsonLibs"]:
                        s_lib_path = str(path.parent/d_lib["path"])
                        if s_lib_path not in sa_libs:
                            sa_libs.append(s_lib_path)

    d_enums = {}
    for s_lib in sa_libs:
        s_lib = pathlib.Path(s_lib)
        for path_json in s_lib.glob("*.json"):
            d_data = json.loads(path_json.read_text())
            for d_type in d_data.get("types", []):
                if "enumName" in d_type.keys():
                    d_enums[d_type["enumName"]] = {
                        "values": {d_kv["enumKey"]: int(d_kv["enumValue"]) for d_kv in d_type["enumMembers"]},
                        "__path": str(path_json)
                    }

    _constants.PATH_BIFROST_ENUMS.parent.mkdir(parents=True, exist_ok=True)
    _constants.PATH_BIFROST_ENUMS.write_text(json.dumps(d_enums, indent=4))
    # _constants.PATH_BIFROST_NODES.write_text(json.dumps(d_nodes, indent=4))


def _get_port_children(graph, s_node, s_port="value"):
    from maya import cmds
    sa_children = cmds.vnnNode(graph, s_node, listPortChildren=s_port) or []
    return sa_children + [f"{s}.{c}" for s in sa_children for c in _get_port_children(graph, s_node, s_port=f"{s_port}.{s}")]


def _collect_types():
    from maya import cmds
    cmds.file(new=True, force=True)
    cmds.loadPlugin("bifrostGraph", qt=True)

    s_graph = cmds.createNode("bifrostGraphShape", name="bifrostGraphShape1")

    sa_types = cmds.vnn(listPortTypes="BifrostGraph")
    sa_types.remove("auto")

    cmds.vnnChangeBracket(s_graph, open=True)
    d_types = {}
    for s_type in sa_types:
        if s_type.startswith("array<"):
            continue

        s_node = "/" + cmds.vnnCompound(s_graph, "/", addNode="BifrostGraph,Core::Constants,float")[0]
        cmds.vnnNode(s_graph, s_node, setMetaData=("valuenode_type", s_type))
        sa_children = _get_port_children(s_graph, s_node, "value")

        d_ports = {s: cmds.vnnNode(s_graph, s_node, queryPortDataType=f"value.{s}") for s in sa_children}

        cmds.vnnCompound(s_graph, "/", removeNode=s_node.strip("/"))
        d_types[s_type] = d_ports

    cmds.vnnChangeBracket(s_graph, close=True)

    _constants.PATH_BIFROST_TYPES.parent.mkdir(parents=True, exist_ok=True)
    _constants.PATH_BIFROST_TYPES.write_text(json.dumps(d_types, indent=4))


ENUMS = {}
NODES = {}
TYPES = {}


def get_data(b_update=False):
    if b_update:
        _collect_enums()
        _collect_nodes()
        _collect_types()

    global ENUMS
    global NODES
    global TYPES

    if _constants.PATH_BIFROST_ENUMS.exists():
        ENUMS = _special_types.Namespaces(json.loads(_constants.PATH_BIFROST_ENUMS.read_text()))

    if _constants.PATH_BIFROST_NODES.exists():
        NODES = _special_types.Namespaces(json.loads(_constants.PATH_BIFROST_NODES.read_text()))

    if _constants.PATH_BIFROST_TYPES.exists():
        TYPES = json.loads(_constants.PATH_BIFROST_TYPES.read_text())


get_data(b_update=__name__ == "__main__")
