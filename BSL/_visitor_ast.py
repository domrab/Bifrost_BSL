# todo:
#   - add separate loop_parameters for the different loops
#   - add arg/kwarg as separate rule
#   - implement more BAD grammars
#   - optimizations
import itertools
import json
import os
import pathlib
import re

from BSL import _grammar, _node, _error, _constants, _special_types, _bifast, _type, _file_io
from BSL._overlord import Overlord

from BSL import _bifres

TYPES = _file_io.get_type_dict()
ENUMS = _bifres.ENUMS
# self._functions = _special_types.Namespaces()


class Ast(_node.NodeVisitor):
    @classmethod
    def run(cls, source, _imported=False):
        import time

        start = time.time()
        parser = _grammar.get_parser()
        # print(f"Grammar: {time.time()-start:.2f}s")

        inst = cls()
        inst._setup()
        _bifast.init_static_memory()

        start = time.time()

        source = str(source)
        if "\n" in source:
            inst._source_code = source
            result = inst.visit(parser.parse(source))
        else:
            inst._source_code = (_constants.PATH_BASE/source).resolve().read_text()
            result = inst.visit(parser.parse((_constants.PATH_BASE/source).resolve()))

        if _imported:
            return inst

        # print(f"AST: {time.time()-start:.2f}s")
        return result

    def _setup(self):
        self._functions = _special_types.Namespaces()

        self._feedback_lock = []

        self.VISIT_MAP = {
            "AND": self._visit_operator,
            "OR": self._visit_operator,
            "EQ": self._visit_operator,
            "NE": self._visit_operator,
            "GT": self._visit_operator,
            "GE": self._visit_operator,
            "LT": self._visit_operator,
            "LE": self._visit_operator,
            "ADD": self._visit_operator,
            "SUB": self._visit_operator,
            "MUL": self._visit_operator,
            "DIV": self._visit_operator,
            "POW": self._visit_operator,
            "NOT": self._visit_operator,
            "R_BRACKET_S": self._visit_operator,
            "R_CURLY_BOOL": self._visit_operator,
            "R_CURLY_FLOAT": self._visit_operator,
            "R_CURLY_DOUBLE": self._visit_operator,
            "R_CURLY_UNSIGNED_LONG": self._visit_operator,
            "R_CURLY_UNSIGNED_INT": self._visit_operator,
            "R_CURLY_UNSIGNED_SHORT": self._visit_operator,
            "R_CURLY_UNSIGNED_CHAR": self._visit_operator,
            "R_CURLY_LONG": self._visit_operator,
            "R_CURLY_INT": self._visit_operator,
            "R_CURLY_SHORT": self._visit_operator,
            "R_CURLY_CHAR": self._visit_operator,
        }

    def _get_source_location(self, node):
        _s_before = self._source_code[:node.start]
        nl = "\n"
        return f"line: {_s_before.count(nl)+1}:{len(_s_before.rpartition(nl)[2])+1}"

    def format_log(self, node, s_log):
        def _expand_node(node_):
            if isinstance(node_.children[0], _node.Node):
                return [n for child in node_.children for n in _expand_node(child)]
            return [node_]

        flat = _expand_node(node)
        i_line_start = flat[0].lineno
        i_line_end = flat[-1].lineno

        if _constants.FILE_URI_IN_STACKTRACE:
            s_path = "file:///" + node.filename.replace("\\", "/")
        else:
            s_path = node.filename

        if i_line_start == i_line_end:
            s_lines = f"L{i_line_start}"
        else:
            s_lines = f"L({i_line_start}-{i_line_end})"

        s_path = pathlib.Path(s_path).name
        return f"[{s_path} {s_lines}] {s_log}"

    def format_error(self, node, s_error):
        def _expand_node(node_):
            if isinstance(node_.children[0], _node.Node):
                return [n for child in node_.children for n in _expand_node(child)]
            return [node_]

        flat = _expand_node(node)
        i_line_start = flat[0].lineno
        i_line_end = flat[-1].lineno
        in_last_line = [node for node in flat if node.lineno == i_line_end]

        s_prev = self._source_code[:in_last_line[0].start].rpartition("\n")[2]
        s_line = self._source_code.split("\n")[i_line_end - 1]
        s_underline = "".join([(c if c == "\t" else " ") for c in s_prev])

        i_underline = in_last_line[-1].end - in_last_line[0].start

        if _constants.FILE_URI_IN_STACKTRACE:
            s_path = "file:///" + node.filename.replace("\\", "/")
        else:
            s_path = node.filename

        if i_line_start == i_line_end:
            s_line_info = f"line {i_line_start}"
        else:
            s_line_info = f"lines {i_line_start}-{i_line_end}"

        s_msg = f'File "{s_path}", {s_line_info}\n'
        s_msg += f"    {s_line}\n"
        # s_msg += f"    {s_underline}{i_underline * '^'}\n>> Error processing '{node.type}': {s_error} <<"
        s_msg += f"    {s_underline}{i_underline * '^'}\n>> {s_error} <<"

        return s_msg

    def resolve_port_type(self, node, s_type):
        i_dim = s_type.count("[")
        s_base = s_type.strip("[]")
        s_type = i_dim * "array<" + TYPES.get(s_base, s_base) + i_dim * ">"
        if s_type.count(">") > 3:
            s_msg = "Arrays are currently limited to 3 dimensions!"
            s_err = self.format_error(node, s_msg)
            raise _error.BfTypeError(s_err, b_stacktrace=False)
        return s_type

    @classmethod
    def type_hint_to_port_type(cls, s_type_hint):
        return {
            "l": "long",
            "ul": "ulong",
            "i": "int",
            "ui": "uint",
            "s": "short",
            "us": "ushort",
            "c": "char",
            "uc": "uchar",
            "f": "float",
            "d": "double",
            "u": "ulong",
            "b": "bool"
        }.get(s_type_hint, "double")


    # ==================== program ==========================


    def v_program(self, node):
        if node.children[0].type == "EMPTY":
            return []
        return self.visit(node.children[0])

    def v_execs(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return self.visit(node.children)

            previous = self.v_execs(node["execs"], b_collect_recursive=True)
            new = self.visit(node["exec"])
            return [p for p in previous + [new] if p]

        return self.v_execs(node, b_collect_recursive=True)

    def v_exec(self, node):
        visited_children = self.visit(node.children)
        return visited_children[0]

    def v_statement(self, node):
        c = self.visit(node.children[0])
        if c == ";":
            return None
        return c

    def v_statement_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if node.children[0].type == "EMPTY":
                return []

            if node.children[0].type == "statement":
                return [self.visit(node["statement"])]

            previous = self.v_statement_list(node["statement_list"], b_collect_recursive=True)
            new = self.visit(node["statement"])
            return [p for p in previous if p] + [new]

        return self.v_statement_list(node, b_collect_recursive=True)


    # ===================== import ==========================


    def v_import(self, node):
        s_path = self.visit(node.children[1])[1:-1]

        # absolute path
        if ":" in s_path or s_path.startswith("/"):
            path = pathlib.Path(s_path)

        else:
            # relative path
            _path_rel = pathlib.Path(f"{node.filename}/{s_path}").resolve()
            if _path_rel.exists():
                path = _path_rel

            else:
                path = None
                for s_env_path in os.environ.get("BSLPATH", "").split(os.pathsep):
                    path = pathlib.Path(f"{s_env_path}/{s_path}").resolve()
                    if path.exists():
                        break

        if not (path and path.exists()):
            s_err = self.format_error(node, f"Could not find a '{s_path}' to import")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        if len(node.children) == 3:
            s_namespace = pathlib.Path(s_path).name.partition(".")[0]

        elif len(node.children) == 5:
            s_namespace = self.visit(node.children[3])
            if node.children[3].type == "STRING":
                s_namespace = s_namespace[1:-1]
            pattern = re.compile(r"(([a-zA-Z_][a-zA-Z0-9_]*::)*[a-zA-Z_][a-zA-Z0-9_]*)|[a-zA-Z_][a-zA-Z0-9_]*")
            if not re.fullmatch(pattern, s_namespace):
                s_err = self.format_error(node, f"Invalid namespace name '{s_namespace}'")
                raise _error.BfNameError(s_err, b_stacktrace=False)

        else:
            raise NotImplementedError

        sub_graph = self.__class__.run(source=path, _imported=True)

        for s_name, scope in sub_graph._functions.items():
            self._functions[f"{s_namespace}::{s_name}"] = scope


    # ==================== overload =========================


    def v_overload_arr_dim(self, node):
        return self.visit(node.children[0])

    def v_overload_type(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node.children[0])]

            previous = self.v_overload_type(node=node["overload_type"])
            new = self.visit(node=node.children[2])
            return previous + [new]

        return self.v_overload_type(node, b_collect_recursive=True)

    def v_overload_type_one(self, node):
        if len(node.children) == 1:
            s_name = None
            sa_types = self.visit(node.children[0])

        elif len(node.children) == 3:
            s_name = self.visit(node["name"])
            sa_types = self.visit(node.children[2])

        else:
            raise NotImplementedError

        return _bifast.OverloadType(node, s_name, sa_types)

    def v_overload_type_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node.children[0])]

            previous = self.v_overload_type_list(node=node["overload_type_list"])
            new = self.visit(node=node["overload_type_one"])
            return previous + [new]

        return self.v_overload_type_list(node, b_collect_recursive=True)

    def v_overload_input(self, node):
        return self.visit(node.children[0])

    def v_overload_result(self, node):
        if node.children[0].type == "EMPTY":
            return []
        return self.visit(node.children[1])

    def v_overload(self, node):
        s_name = self.visit(node["namespace_name"])
        inputs = self.visit(node["overload_input"])
        outputs = self.visit(node["overload_result"])

        s_func = self._functions.resolves(s_name)

        b_is_custom = False
        if s_func:
            scope = self._functions[s_name]["scope"]  # type: _bifast.Scope
            sa_names_in = [p.name() for p in scope._parameters]
            sa_types_in = [p.value_type().s for p in scope._parameters]
            sa_names_out = scope.output_names()
            sa_types_out = scope.output_types()
            b_is_custom = True

        else:
            s_func = Overlord.function(s_name)
            if not s_func:
                s_err = self.format_error(node, f"No function '{s_name}' found")
                raise _error.BfNameError(s_err, b_stacktrace=False)

            sa_names_in, sa_names_out = Overlord.get_port_names(s_func)
            sa_types_in, sa_types_out = Overlord.get_port_types(s_func)

        # do outputs first since its only needed once
        if outputs and not sa_names_out:
            s_err = self.format_error(outputs[0]._parser_node,
                                      f"Operator/compound '{s_func}()' does not return anything")
            raise _error.Error(s_err, b_stacktrace=False)

        if len(inputs) > len(sa_names_in):
            s_err = self.format_error(node["overload_input"], f"Cant overload operator '{s_func}()' with different in port count: {len(sa_names_in)}")
            raise _error.Error(s_err, b_stacktrace=False)

        if len(outputs) > len(sa_names_out):
            s_err = self.format_error(node["overload_result"], f"Cant overload operator '{s_func}()' with different out port count: {len(sa_names_out)}")
            raise _error.Error(s_err, b_stacktrace=False)

        kwarg = False
        for i, arg in enumerate(outputs):
            if kwarg and arg.name() is None:
                s_error = "Python rules! Positional arguments cant follow keyword arguments"
                s_msg = self.format_error(node, s_error=s_error)
                raise _error.BfSyntaxError(s_msg, b_stacktrace=False)

            if arg.name() is not None:
                kwarg = True

                if arg.name() not in sa_names_out:
                    s = "\n    ".join(sa_names_out)
                    s_err = self.format_error(arg._parser_node,
                                              f"Unrecognized out port name '{arg.name()}'. Use one of: [\n    {s}\n]")
                    raise _error.Error(s_err, b_stacktrace=False)

                i = sa_names_out.index(arg.name())

            if len(arg.types()) > 1:
                s_err = self.format_error(arg._parser_node,
                                          f"Results must not be ambiguous for out port '{arg.name()}'")
                raise _error.Error(s_err, b_stacktrace=False)
            sa_types_out[i] = arg.types()[0]

        saa_arg_types = [arg.types() for arg in inputs]

        for sa_arg_types in itertools.product(*saa_arg_types):
            sa_arg_names = [arg.name() for arg in inputs]
            nodes = [arg._parser_node for arg in inputs]

            kwarg = False
            for i, (s_name, s_type, pnode) in enumerate(zip(sa_arg_names, sa_arg_types, nodes)):
                if kwarg and s_name is None:
                    s_error = "Python rules! Positional arguments cant follow keyword arguments"
                    s_msg = self.format_error(node, s_error=s_error)
                    raise _error.BfSyntaxError(s_msg, b_stacktrace=False)

                if s_name is not None:
                    kwarg = True

                    if s_name not in sa_names_in:
                        s = "\n    ".join(sa_names_in)
                        s_err = self.format_error(pnode, f"Unrecognized in port name '{s_name}'. Use one of: [\n    {s}\n]")
                        raise _error.Error(s_err, b_stacktrace=False)

                    i = sa_names_in.index(s_name)

                sa_types_in[i] = s_type

            if b_is_custom:
                self._functions[s_func]["overloads"][tuple(sa_types_in)] = [_type.Type(s) for s in sa_types_out]
            else:
                Overlord._d_operators[s_func]["overloads"]["-".join(sa_types_in)] = sa_types_out


    # ================ functions/scopes =====================


    def v_function(self, node):
        s_name = self.visit(node["namespace_name"])
        if s_name in self._functions:
            s_msg = f"Function '{s_name} already defined!"
            s_err = self.format_error(node["namespace_name"], s_msg)
            raise _error.BfNameError(s_err, b_stacktrace=False)

        scope = self.visit(node["unnamed_scope"])

        self._functions[s_name] = {
            "scope": scope,
            "overloads": {tuple([p.value_type().s for p in scope._parameters]): scope.output_types()}
        }

    def v_compound(self, node):
        # skipping the name for now and treating it as a coding only thing
        scope = self.visit(node["unnamed_scope"])
        if node.children[1].type == "name":
            scope.set_name(self.visit(node["name"]))
        return scope

    def v_unnamed_scope(self, node):
        sa_terminal = self.visit(node["terminal"])
        parameters = self.visit(node["scope_parameters"])
        results = self.visit(node["scope_result"])

        set_dupe_ports = {p.name() for p in parameters} & {r.name() for r in results}
        if set_dupe_ports:
            s_err = self.format_error(node["scope_result"], f"Results cannot have the same name as arguments: '{sorted(set_dupe_ports)[0]}'")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        # check feedback port types
        sa_feedback = []
        d_inputs = {p.name(): p.value_type().s for p in parameters}
        for i, r in enumerate(results):
            if not r.feedback():
                continue

            rt = r.value_type().s
            rn = r.name()
            pn = r.feedback()
            pt = d_inputs[pn]

            # ensure we dont use the same feedback port twice
            if pn in sa_feedback:
                s_err = self.format_error(node["scope_result"]["scope_result_list"].children[2*i], f"Duplicate feedback port: '{pn}'")
                raise _error.BfNameError(s_err, b_stacktrace=False)

            sa_feedback.append(pn)

            if pt != rt:
                s_err = self.format_error(node["scope_result"], f"Feedback port types dont match: '{pn}[{pt}]@{rn}[{rt}]")
                raise _error.BfNameError(s_err, b_stacktrace=False)

        _bifast.push_scope()
        [_bifast.set_static_variable(param.name(), param.value_type()) for param in parameters]
        [_bifast.set_static_variable(res.name(), res.value_type(), b_write_only=True) for res in results]
        code = self.visit(node["statement_list"])
        _bifast.pop_scope()

        return _bifast.Scope(node, parameters, results, code, sa_terminal)


    def v_scope_result_one(self, node):
        visited_children = self.visit(node.children)
        s_type = visited_children[0]
        s_name = visited_children[1]
        s_feedback = visited_children[2] if len(visited_children) == 3 else None

        if s_feedback and self._feedback_lock:
            s_err = self.format_error(node, "Feedback ports in looping constructs are not allowed")
            raise _error.Error(s_err, b_stacktrace=False)

        return _bifast.ScopeResult(node, s_name, s_type, s_feedback)

    def v_scope_result_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node.children[0])]

            previous = self.v_scope_result_list(node=node["scope_result_list"], b_collect_recursive=True)
            new = self.visit(node=node["scope_result_one"])
            return previous + [new]

        results = self.v_scope_result_list(node, b_collect_recursive=True)
        sa_results = [r.name() for r in results]
        if len(sa_results) != len(set(sa_results)):
            s_err = self.format_error(node, "Duplicate result names found")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        return results


    def v_scope_result(self, node):
        if len(node.children) == 1:
            return []
        return self.visit(node["scope_result_list"])


    def v_scope_parameter_one(self, node):
        visited_children = self.visit(node.children)

        s_type = visited_children[0]
        s_name = visited_children[1]
        value = visited_children[3] if len(visited_children) == 4 else None

        if value:
            _validate_type_cast(self, node, value.value_type(), type_target=s_type)

        return _bifast.ScopeParameter(node, s_name, s_type, value)

    def v_scope_parameter_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node["scope_parameter_one"])]
            previous = self.v_scope_parameter_list(node["scope_parameter_list"])
            new = self.visit(node["scope_parameter_one"])
            return previous + [new]

        parameters = self.v_scope_parameter_list(node, b_collect_recursive=True)
        sa_parameters = [parm.name() for parm in parameters]
        if len(sa_parameters) != len(set(sa_parameters)):
            s_err = self.format_error(node, "Duplicate parameter names found")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        return parameters

    def v_scope_parameters(self, node):
        if node.children[0].type == "EMPTY":
            return []
        return self.visit(node["scope_parameter_list"])


    # ===================== statement ========================


    # ==================== assignments =======================


    def v_assignment_lhs_one(self, node):
        s_rule = node.children[0].type

        if s_rule == "IGNORE":
            return None

        if s_rule == "access_lhs":
            return self.visit(node.children[0])

        if s_rule == "type":
            s_type, s_name = self.visit(node.children)

            if _bifast.get_static_variable_type(s_name) is not None:
                s_msg = f"Redefinition: '{s_name}' already exists!"
                s_err = self.format_error(node, s_msg)
                raise _error.BfNameError(s_err, b_stacktrace=False)

            s_enum_test = s_type[6*s_type.count("<"):-s_type.count(">")]
            if s_enum_test in ENUMS:
                s_msg = f"Bifrost currently crashes if your have enum arrays of more than one dimension"
                s_err = self.format_error(node["type"], s_msg)
                raise _error.BfTypeError(s_err, b_stacktrace=False)

            return _bifast.AssignLHS_TypeName(node, s_name, s_type)

        s_name = self.visit(node.children)[0]
        if _bifast.get_static_variable_type(s_name) is None:
            print(_bifast.print_all_scopes())
            s_msg = f"Unknown variable: '{s_name}'"
            s_err = self.format_error(node, s_msg)
            raise _error.BfNameError(s_err, b_stacktrace=False)

        return _bifast.Variable(node, s_name)

    def v_assignment_lhs_list(self, node, b_collect_recursive=False):
        if len(node.children) == 1:
            return [self.visit(node.children[0])]

        if b_collect_recursive:
            previous = self.v_assignment_lhs_list(node["assignment_lhs_list"], b_collect_recursive=True)
            new = self.visit(node["assignment_lhs_one"])
            return previous + [new]

        components = self.v_assignment_lhs_list(node, b_collect_recursive=True)
        return components

    def v_assignment(self, node):
        # reversing the order in which the rules get evaluated here
        # so that we evaluate the RHS before the LHS.
        visited_children = self.visit(node.children[::-1])[::-1]
        lhs = visited_children[0]
        rhs = visited_children[2]
        s_op = visited_children[1]

        # if isinstance(rhs, _bifast.Scope):
        #     rhs = rhs.copy()
        # todo: add scaling and transform controls to SDFs
        #   check if its easy enough to include operations
        lhs_ = [t for t in lhs if t is not None]
        type_rhs = rhs.value_type()

        if lhs_ and type_rhs.is_node() and rhs.output_count() == 0:
            s_msg = f"'{rhs._s_name}' does not return anything."
            s_err = self.format_error(node.children[2], s_msg)
            raise _error.BfTypeError(s_err, b_stacktrace=False)

        if type_rhs.is_node():
            # more than one receiver on the left or ':=' -> unpack the node

            if len(lhs) > 1 or s_op == ":=":
                rhs_types = list(type_rhs.node_data().values())

            # elif lhs[0]:
            #     lhs0t = lhs[0].value_type().s
            #
            #     if op == ":=" and len(type_rhs.node_data()) != 1:
            #         s_err = self.format_error(node.children[2], "Can only use ':=' if there is exactly one output port")
            #         raise _error.BfTypeError(s_err)
            #
            #     if lhs0t == "__NODE" or (op == "=" and lhs0t == "auto"):
            #         rhs_types = [type_rhs]
            #
            #     if op == ":=":
            #         rhs_types = type_rhs.node_data()
            #
            #     else:
            #         rhs_types = type_rhs.node_data()
            else:
                rhs_types = [type_rhs]
        else:
            rhs_types = len(lhs) * [type_rhs]

        for (lhs_target, type_rhs) in zip(lhs, rhs_types):
            if lhs_target is None:
                continue

            type_lhs = lhs_target.value_type()

            if isinstance(lhs_target, (_bifast.Variable, _bifast.AssignLHS_TypeName)):
                if type_lhs == "auto":
                    type_lhs = type_rhs
                    lhs_target.set_value_type(type_lhs)

                # for copying node data
                elif type_rhs.is_node() and type_lhs.is_node():
                    type_lhs = type_rhs
                    lhs_target.set_value_type(type_lhs)

                b_write_only = _bifast.is_write_only(lhs_target.name())

                if type_lhs.is_node():
                    _bifast.set_static_variable(lhs_target.name(), type_lhs, value=rhs, b_write_only=b_write_only)
                else:
                    _bifast.set_static_variable(lhs_target.name(), type_lhs, b_write_only=b_write_only)

            if isinstance(lhs_target, _bifast.AccessLHS):
                # basically anything can get assigned to an object
                if lhs_target.base_type() == "Object":
                    if type_rhs.is_node():
                        s_err = self.format_error(node.children[2], "Cant assign NODE to object")
                        raise _error.BfTypeError(s_err, b_stacktrace=False)
                    continue

                elif lhs_target.base_type() == "_member":
                    type_lhs = lhs_target.value_type()

                elif lhs_target.base_type().is_array():
                    type_lhs = lhs_target.value_type()

                elif lhs_target.base_type() == "string":
                    type_lhs = lhs_target.value_type()

                else:
                    raise NotImplementedError(lhs_target.base_type().s)

            # this raises the exceptions itself so its not returning anything.
            # this works since I am passing the graph instance. If I passed that to
            # the AST nodes, that would simplify this a lot
            _validate_type_cast(self, lhs_target._parser_node, type_value=type_rhs, type_target=type_lhs)

        return _bifast.Assignment(node, lhs, rhs, s_op)


    # ======================= loops ==========================


    def v_loop(self, node):
        return self.visit(node.children[0])

    def v_max_iterations(self, node):
        return self.visit(node["expression"])

    def v_current_index(self, node):
        s_name = "current_index" if len(node.children) == 3 else self.visit(node["name"])
        value = self.visit(node["expression"])
        return _bifast.LoopIndex(node, s_name, value)

    def v_safe_loop_settings(self, node):
        index = _bifast.LoopIndex(node, "current_index", _bifast.Value(node, 0, _type.Type("long")))
        if len(node.children) == 3:
            index = self.visit(node["current_index"])
        return self.visit(node["max_iterations"]), index

    def v_loop_settings(self, node):
        s_rule = node.children[0].type

        if s_rule == "EMPTY":
            return None, _bifast.LoopIndex(node, "current_index", _bifast.Value(node, 0, _type.Type("long")))

        elif s_rule == "safe_loop_settings":
            return self.visit(node["safe_loop_settings"])

        return None, self.visit(node["current_index"])

    def v_loop_parameter_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node["loop_parameter_one"])]

            previous = self.v_loop_parameter_list(node["loop_parameter_list"])
            new = self.visit(node["loop_parameter_one"])
            return previous + [new]

        parameters = self.v_loop_parameter_list(node, b_collect_recursive=True)
        sa_parameters = [parm.name() for parm in parameters]
        if len(sa_parameters) != len(set(sa_parameters)):
            s_err = self.format_error(node, "Duplicate parameter names found")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        return parameters

    def v_loop_parameters(self, node):
        if node.children[0].type == "EMPTY":
            return []
        return self.visit(node["loop_parameter_list"])

    def v_loop_parameter_one(self, node):
        i_rule_count = len(node.children)

        if i_rule_count in [4, 5]:
            s_name = self.visit(node["name"])
            s_type = self.visit(node["port_type"])
            value = self.visit(node["expression"])
            b_iterate = node.children[2].type == "index"

            if s_type == "auto":
                s_type = value.value_type().s

            # this will not catch something like AUTO x# = 10 but its a start
            # alternatively, I could forbid AUTO types to be iteration targets...
            # todo: make this more solid
            if b_iterate and not s_type.startswith("array<"):
                s_error = self.format_error(node, s_error="Iteration targets must be at least 1D arrays!")
                raise _error.Error(s_error, b_stacktrace=False)

            # validate value type
            value_type = value.value_type()
            if value_type.is_node() and len(value_type.node_data()) == 1:
                value_type = list(value_type.node_data().values())[0]
            _validate_type_cast(self, node, value_type, s_type, s_name)

            status, value = _bifast.LoopParameter.create(node, s_name, s_type, value, b_iterate)
            if not status:
                s_err = self.format_error(node, value)
                raise _error.BfTypeError(s_err, b_stacktrace=False)

            return value

        s_name = self.visit(node["name"])

        if _bifast.get_static_variable_type(s_name) is None:
            s_error = self.format_error(node, s_error=f"Variable '{s_name}' referenced before assignment!")
            raise _error.Error(s_error, b_stacktrace=False)

        s_type = _bifast.get_static_variable_type(s_name).s
        b_iterate = i_rule_count == 2

        if s_type == "__NODE" and len(_bifast.get_static_variable_type(s_name).node_data()) != 1:
            s_error = self.format_error(node, s_error="Can't pass NODE type variables through scopes!")
            raise _error.Error(s_error, b_stacktrace=False)

        if b_iterate and not s_type.startswith("array<"):
            s_error = self.format_error(node, s_error="Iteration targets must be at least 1D arrays!")
            raise _error.Error(s_error, b_stacktrace=False)

        if s_name in ["max_iterations", "current_index", "looping_condition"]:
            s_error = self.format_error(node, s_error=f"Invalid port name: '{s_name}'!")
            raise _error.Error(s_error, b_stacktrace=False)

        status, value = _bifast.LoopParameter.create(node, s_name, s_type, None, b_iterate)
        if not status:
            s_err = self.format_error(node, value)
            raise _error.BfTypeError(s_err, b_stacktrace=False)

        return value


    def v_for_each_result_one(self, node):
        visited_children = self.visit(node.children)
        # name, type, index, port_state
        return _bifast.LoopResult(node, visited_children[1], visited_children[0], True, None)

    def v_for_each_result_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node["for_each_result_one"])]

            previous = self.v_for_each_result_list(node["for_each_result_list"], b_collect_recursive=True)
            new = self.visit(node["for_each_result_one"])
            return previous + [new]

        results = self.v_for_each_result_list(node, b_collect_recursive=True)
        sa_results = [r.name() for r in results]
        if len(sa_results) != len(set(sa_results)):
            s_err = self.format_error(node, "Duplicate result names found")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        return results

    def v_for_each_result(self, node):
        if node.children[0].type == "EMPTY":
            return []
        return self.visit(node["for_each_result_list"])

    def v_for_each(self, node):
        sa_terminal = self.visit(node["terminal"])
        max_iterations, current_index = self.visit(node["loop_settings"])
        parameters = self.visit(node["loop_parameters"])
        results = self.visit(node["for_each_result"])

        set_dupe_ports = {p.name() for p in parameters} & {r.name() for r in results}
        if set_dupe_ports:
            s_err = self.format_error(node["for_each_result"], f"Results cannot have the same name as arguments: '{sorted(set_dupe_ports)[0]}'")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        # b_has_at_least_one_iteration_target checks if any input port is an
        # iteration target if there are no iteration targets, there must be a
        # max_iterations. If there is no max_iterations, an error will be raised
        b_has_at_least_one_iteration_target = any([parm.is_iteration_target() for parm in parameters])

        if max_iterations is None and not b_has_at_least_one_iteration_target:
            s_error = self.format_error(node.children[7], "Either max_iterations or an iteration target is required!")
            raise _error.Error(s_error, b_stacktrace=False)

        _bifast.push_scope()
        _bifast.set_static_variable("#", _type.Type("long"), )
        _bifast.set_static_variable(current_index.name(), _type.Type("long"))

        # add the settings
        if max_iterations is not None:
            _bifast.set_static_variable("max_iterations", _type.Type("long"))

        # add the inputs
        for parm in parameters:
            s_type = parm.value_type().s
            _bifast.set_static_variable(parm.name(), _type.Type(s_type[6:-1] if parm.is_iteration_target() else s_type))

        # add the result
        for res in results:
            _bifast.set_static_variable(res.name(), _type.Type(res.value_type().s[6:-1]), b_write_only=True)

        # run the body of the loop
        self._feedback_lock.append(None)
        code = self.visit(node["statement_list"])
        self._feedback_lock.pop()

        _bifast.pop_scope()

        return _bifast.LoopForEach(node, parameters, results, code, max_iterations, current_index, sa_terminal)


    def v_iterate_result_one(self, node):
        visited_children = self.visit(node.children)
        b_index = node.children[2].type == "index"
        s_state = visited_children[2] if not b_index else None

        # name, type, index, port_state
        return _bifast.LoopResult(node, visited_children[1], visited_children[0], b_index, s_state)

    def v_iterate_result_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node["iterate_result_one"])]

            previous = self.v_iterate_result_list(node["iterate_result_list"], b_collect_recursive=True)
            new = self.visit(node["iterate_result_one"])
            return previous + [new]

        results = self.v_iterate_result_list(node, b_collect_recursive=True)
        sa_results = [r.name() for r in results]
        if len(sa_results) != len(set(sa_results)):
            s_err = self.format_error(node, "Duplicate result names found")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        return results

    def v_iterate_result(self, node):
        if node.children[0].type == "EMPTY":
            return []
        return self.visit(node["iterate_result_list"])

    def v_iterate(self, node):
        sa_terminal = self.visit(node["terminal"])
        max_iterations, current_index = self.visit(node["loop_settings"])
        parameters = self.visit(node["loop_parameters"])
        results = self.visit(node["iterate_result"])

        set_dupe_ports = {p.name() for p in parameters} & {r.name() for r in results}
        if set_dupe_ports:
            s_err = self.format_error(node["iterate_result"], f"Results cannot have the same name as arguments: '{sorted(set_dupe_ports)[0]}'")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        # check that feedback port types
        d_inputs = {p.name(): p.value_type().s for p in parameters}
        sa_feedback = []
        for i, r in enumerate(results):
            if not r.state():
                continue

            rt = r.value_type().s
            rn = r.name()
            pn = r.state()
            pt = d_inputs[pn]

            # ensure we dont use the same feedback port twice
            if pn in sa_feedback:
                s_err = self.format_error(node["iterate_result"]["iterate_result_list"].children[2*i], f"Duplicate state port: '{pn}'")
                raise _error.BfNameError(s_err, b_stacktrace=False)

            sa_feedback.append(pn)

            if pt != rt:
                s_err = self.format_error(node["iterate_result"], f"State port types dont match: '{pn}[{pt}]@{rn}[{rt}]")
                raise _error.BfNameError(s_err, b_stacktrace=False)

        # b_has_at_least_one_iteration_target checks if any input port is an
        # iteration target if there are no iteration targets, there must be a
        # max_iterations. If there is no max_iterations, an error will be raised
        b_has_at_least_one_iteration_target = any([parm.is_iteration_target() for parm in parameters])

        if max_iterations is None and not b_has_at_least_one_iteration_target:
            s_error = self.format_error(node.children[7], "Either max_iterations or an iteration target is required!")
            raise _error.Error(s_error, b_stacktrace=False)

        _bifast.push_scope()
        _bifast.set_static_variable("#", _type.Type("long"))
        _bifast.set_static_variable(current_index.name(), _type.Type("long"))

        # add the settings
        if max_iterations is not None:
            _bifast.set_static_variable("max_iterations", _type.Type("long"))

        # add the inputs
        for parm in parameters:
            s_type = parm.value_type().s
            _bifast.set_static_variable(parm.name(), _type.Type(s_type[6:-1] if parm.is_iteration_target() else s_type))

        # add the result
        for res in results:
            s_type = res.value_type().s
            _bifast.set_static_variable(res.name(), _type.Type(s_type[6:-1] if res.is_iteration_target() else s_type), b_write_only=True)

        # run the body of the loop
        self._feedback_lock.append(None)
        code = self.visit(node["statement_list"])
        self._feedback_lock.pop()

        _bifast.pop_scope()

        return _bifast.LoopIterate(node, parameters, results, code, max_iterations, current_index, sa_terminal)


    def v_do_while_result_one(self, node):
        visited_children = self.visit(node.children)
        s_state = visited_children[2] if len(visited_children) == 3 else None

        # name, type, index, port_state
        return _bifast.LoopResult(node, visited_children[1], visited_children[0], False, s_state)

    def v_do_while_result_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node["do_while_result_one"])]

            previous = self.v_do_while_result_list(node["do_while_result_list"], b_collect_recursive=True)
            new = self.visit(node["do_while_result_one"])
            return previous + [new]

        results = self.v_do_while_result_list(node, b_collect_recursive=True)
        sa_results = [r.name() for r in results]
        if len(sa_results) != len(set(sa_results)):
            s_err = self.format_error(node, "Duplicate result names found")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        return results

    def v_do_while_result(self, node):
        if node.children[0].type == "EMPTY":
            return []
        return self.visit(node["do_while_result_list"])

    def v_do_while(self, node):
        b_nolimit = node.children[0].type == "NOLIMIT"
        sa_terminal = self.visit(node["terminal"])
        # max_iterations, current_index = self.visit(node["loop_settings" if b_nolimit else "safe_loop_settings"])
        max_iterations, current_index = self.visit(node["loop_settings"])
        parameters = self.visit(node["loop_parameters"])
        results = self.visit(node["do_while_result"])

        if not b_nolimit and max_iterations is None and (not any([parm.is_iteration_target() for parm in parameters])):
            s_err = self.format_error(node.children[0], "Missing max_iterations setting or 'nolimit' keyword")
            raise _error.BfSyntaxError(s_err, b_stacktrace=False)

        set_dupe_ports = {p.name() for p in parameters} & {r.name() for r in results}
        if set_dupe_ports:
            s_err = self.format_error(node["do_while_result"], f"Results cannot have the same name as arguments: '{sorted(set_dupe_ports)[0]}'")
            raise _error.BfNameError(s_err, b_stacktrace=False)

        # check that feedback port types
        d_inputs = {p.name(): p.value_type().s for p in parameters}
        sa_feedback = []
        for i, r in enumerate(results):
            if not r.state():
                continue

            rt = r.value_type().s
            rn = r.name()
            pn = r.state()
            pt = d_inputs[pn]

            # ensure we dont use the same feedback port twice
            if pn in sa_feedback:
                s_err = self.format_error(node["do_while_result"]["do_while_result_list"].children[2*i], f"Duplicate state port: '{pn}'")
                raise _error.BfNameError(s_err, b_stacktrace=False)

            sa_feedback.append(pn)

            if pt != rt:
                s_err = self.format_error(node["do_while_result"], f"State port types dont match: '{pn}[{pt}]@{rn}[{rt}]")
                raise _error.BfNameError(s_err, b_stacktrace=False)

        _bifast.push_scope()

        # add the settings
        _bifast.set_static_variable("#", _type.Type("long"))
        _bifast.set_static_variable(current_index.name(), _type.Type("long"))

        if max_iterations is not None:
            _bifast.set_static_variable("max_iterations", _type.Type("long"))

        # add the inputs
        for parm in parameters:
            s_type = parm.value_type().s
            _bifast.set_static_variable(parm.name(), _type.Type(s_type[6:-1] if parm.is_iteration_target() else s_type))

        # add the results
        for res in results:
            _bifast.set_static_variable(res.name(), res.value_type(), b_write_only=True)

        # run the body of the loop
        self._feedback_lock.append(None)
        code = self.visit(node["statement_list"])
        self._feedback_lock.pop()

        condition = self.visit(node["expression"])

        _bifast.pop_scope()

        status, result = _bifast.LoopDoWhile.create(node, parameters, results, code, condition, max_iterations, current_index, sa_terminal)

        if not status:
            s_err = self.format_error(node["do_while_result"], result)
            raise _error.BfNameError(s_err, b_stacktrace=False)
        return result

    # ======================= using ==========================


    def v_using(self, node):
        op = self.visit(node.children[2])

        for s_name, type_ in zip(op.output_names(), op.output_types()):
            type_current = _bifast.get_static_variable_type(s_name)

            if type_current is not None and type_current != type_:
                s_err = self.format_error(node["USING"], f"A variable named '{s_name}' of a different type already exists!")
                raise _error.BfNameError(s_err)

            if not _bifast.is_write_only(s_name):
                _bifast.set_static_variable(s_name, type_)

        return _bifast.Using(node, op)

    # ======================== expr ==========================


    def v_expression(self, node):
        result = self.visit(node.children[0])
        return result

    def v_expression_logic(self, node):
        visited_children = self.visit(node.children)

        if len(node.children) == 1:
            return visited_children[0]

        status, result = _bifast.Logic.create(node, visited_children[0], visited_children[2], visited_children[1])
        if not status:
            s_err = self.format_error(node, result)
            raise _error.BfTypeError(s_err, b_stacktrace=False)
        return result

    def v_expression_cmp(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node.children[0])]

            previous = self.v_expression_cmp(node["expression_cmp"], b_collect_recursive=True)
            op = self.visit(node.children[1])
            new = self.visit(node["expression_add"])
            return previous + [(op, new)]

        visited_children = self.v_expression_cmp(node, b_collect_recursive=True)
        if len(node.children) == 1:
            return visited_children[0]

        values = [visited_children[0]] + [v[1] for v in visited_children[1:]]
        ops = [v[0] for v in visited_children[1:]]
        pairs = []
        for i, op in enumerate(ops):
            pairs.append((values[i], values[i+1], op))

        status, result = _bifast.Compare.create(node, pairs)
        if not status:
            s_err = self.format_error(node, result)
            raise _error.BfTypeError(s_err, b_stacktrace=False)
        return result

    def v_expression_add(self, node):
        visited_children = self.visit(node.children)

        if len(node.children) == 1:
            return visited_children[0]

        status, result = _bifast.MathOp.create(node, visited_children[0], visited_children[2], visited_children[1])
        if not status:
            s_err = self.format_error(node, result)
            raise _error.BfTypeError(s_err, b_stacktrace=False)
        return result

    def v_expression_mul(self, node):
        visited_children = self.visit(node.children)

        if len(node.children) == 1:
            return visited_children[0]

        status, result = _bifast.MathOp.create(node, visited_children[0], visited_children[2], visited_children[1])
        if not status:
            s_err = self.format_error(node, result)
            raise _error.BfTypeError(s_err, b_stacktrace=False)
        return result

    def v_expression_pow(self, node):
        visited_children = self.visit(node.children)

        if len(visited_children) == 1:
            return visited_children[0]

        status, result = _bifast.Pow.create(node, visited_children[0], visited_children[2], visited_children[1])
        if not status:
            s_err = self.format_error(node, result)
            raise _error.BfTypeError(s_err, b_stacktrace=False)
        return result

    def v_expression_unary(self, node):
        visited_children = self.visit(node.children)

        if node.children[0].type == "atom":
            return visited_children[0]

        s_op = visited_children[0]
        value = visited_children[1]

        if s_op == "+":
            return value

        if s_op == "!":
            status, result = _bifast.Not.create(node, value)
            if not status:
                s_err = self.format_error(node, result)
                raise _error.BfTypeError(s_err, b_stacktrace=False)
            return result

        if s_op == "-":
            if value.value_type().base_type().base_type().is_numeric():
                if isinstance(value, _bifast.Value) and value.is_constant():
                    return _bifast.Value(node, -value._value, value.value_type())

            # else:
            #     s_err = self.format_error(node, f"Can't negate value of type '{value.value_type()}'")
            #     raise _error.BfTypeError(s_err, b_stacktrace=False)

            status, result = _bifast.Negate.create(node, value)
            if not status:
                s_err = self.format_error(node, result)
                raise _error.BfTypeError(s_err, b_stacktrace=False)
            return result

        raise NotImplementedError(f"Unknown operator: '{s_op}'")


    # ======================== atom ==========================


    def v_atom(self, node):
        s_rule = node.children[0].type
        visited_children = self.visit(node.children)

        if s_rule in ["atom_small", "access_rhs", "access_port", "enum"]:
            return visited_children[0]

        raise NotImplementedError(f"atom: {s_rule}")


    # ==================== function call =====================


    def v_call(self, node):
        if node.children[0].type == "type_base":
            return self._v_call_type(node)

        s_func_name = self.visit(node["namespace_name"])
        sa_terminal = self.visit(node["terminal"])
        args, kwargs = self.visit(node["call_arguments"])

        if s_func_name.startswith("__debug::"):
            sa_valid = ["type", "outputs", "inputs", "dir"]
            s_func_name = s_func_name.partition("::")[2]

            if s_func_name not in sa_valid:
                s_err = self.format_error(node, f"Unknown debug function: '{s_func_name}'. Chose from {sa_valid}")
                raise _error.BfNameError(s_err, b_stacktrace=False)

            s = f"__debug::{s_func_name}("
            if s_func_name == "type":
                s_args = ", ".join([arg.value_type().s for arg in args] + [f"{arg.name()}={arg.value_type().s}" for arg in kwargs])
                s = s + s_args + ")"
                print(self.format_log(node, s))

            elif s_func_name == "outputs":
                sa = []
                for arg in args:
                    if not arg.value_type().is_node():
                        sa.append("<not a NODE>")
                    else:
                        sa.append("{" + ", ".join([f"{k}: {v.s}" for k, v in arg.value_type().node_data().items()]) + "}")

                for arg in kwargs:
                    if not arg.value_type().is_node():
                        sa.append(f"{arg.name()}=<not a NODE>")
                    else:
                        sa.append(f"{arg.name()}={{" + ", ".join([f"{k}: {v.s}" for k, v in arg._value.outputs().items()]) + "}")

                s = s + ", ".join(sa) + ")"
                print(self.format_log(node, s))

            elif s_func_name == "inputs":
                sa = []
                for arg in args + kwargs:
                    if not (isinstance(arg._value, _bifast.Value) and arg.value_type().is_string()):
                        s_err = self.format_error(node, "Function name must be passed directly as string")
                        raise _error.BfTypeError(s_err, b_stacktrace=False)

                    if not arg.value_type().is_string():
                        sa.append("<not a function>")
                        continue

                    s_func_name = arg._value._value
                    if self._functions.resolves(s_func_name):
                        sa_names_and_types = [(p.name(), p.value_type().s) for p in self._functions[s_func_name]["scope"]._parameters]
                        sa.append(f"{s_func_name}={{" + ", ".join([f"{k}: {v}" for k, v in sa_names_and_types]) + "}")

                    elif Overlord.function(s_func_name):
                        sa_names_in, _ = Overlord.get_port_names(s_func_name)
                        sa_types_in, _ = Overlord.get_port_types(s_func_name)
                        sa.append(f"{s_func_name}={{" + ", ".join([f"{k}: {v}" for k, v in zip(sa_names_in, sa_types_in)]) + "}")

                    else:
                        sa.append(f"{s_func_name}=<not a known function>")

                s = s + ", ".join(sa) + ")"
                print(self.format_log(node, s))

            elif s_func_name == "dir":
                d_settings = {
                    "bifrost": True,
                    "custom": True,
                    "newline": True,
                    "nested": False,
                }

                for kwarg in kwargs:
                    if kwarg.name() not in ["bifrost", "custom", "newline", "nested"]:
                        s_err = self.format_error(node, f"Unknown kwarg: '{kwarg.name()}'")
                        raise _error.BfTypeError(s_err, b_stacktrace=False)

                    if not (isinstance(kwarg._value, _bifast.Value) and kwarg.value_type() == "bool"):
                        s_err = self.format_error(node, "Values must be passed directly as bool (true/false)")
                        raise _error.BfTypeError(s_err, b_stacktrace=False)

                    d_settings[kwarg.name()] = kwarg._value._value

                if not (d_settings["custom"] or d_settings["bifrost"]):
                    s_err = self.format_error(node, "Must query at least one of: ['custom', 'bifrost']")
                    raise _error.BfTypeError(s_err, b_stacktrace=False)

                for arg in args:
                    if not (isinstance(arg._value, _bifast.Value) and arg.value_type() == "string"):
                        s_err = self.format_error(node, "Namespace name must be passed directly as string")
                        raise _error.BfTypeError(s_err, b_stacktrace=False)

                    if not arg.value_type().is_string():
                        continue

                    s_namespace = arg._value._value

                    sa_contents = set()

                    if s_namespace == "*":
                        for s_key, data in (Overlord.functions() if d_settings["bifrost"] else {}).items():
                            if d_settings["nested"] or s_key.count("::") == s_namespace.count("::") + 1:
                                sa_names_in, sa_names_out = Overlord.get_port_names(s_key)
                                sa_types_in, sa_types_out = Overlord.get_port_types(s_key)
                                s_sig = (", ".join([f"{s}: {t}" for s, t in zip(sa_names_in, sa_types_in)]))
                                s_result = (", ".join([f"{s}: {t}" for s, t in zip(sa_names_out, sa_types_out)]))
                                s_result = f" => {s_result}" if s_result else ""
                                sa_contents.add(f"{s_key}({s_sig}{s_result}) (bifrost)")
                            else:
                                sa_contents.add(f"{s_key.split('::')[0]}::* (bifrost)")

                        for s_key, data in (self._functions if d_settings["custom"] else {}).items():
                            if d_settings["nested"] or s_key.count("::") == s_namespace.count("::") + 1:
                                s_sig = (", ".join([f"{p.name()}: {p.value_type()}" for p in data["scope"]._parameters]))
                                s_result = (", ".join([f"{r.name()}: {r.value_type()}" for r in data["scope"]._results]))
                                s_result = f" => {s_result}" if s_result else ""
                                sa_contents.add(s_key + f"({s_sig}{s_result}) (custom)")
                            else:
                                sa_contents.add(f"{s_key.split('::')[0]}::* (custom)")

                    else:
                        for s_key, data in (Overlord.functions() if d_settings["bifrost"] else {}).items():
                            if s_key.startswith(f"{s_namespace}::") or s_key == s_namespace:
                                if d_settings["nested"] or s_key.count("::") == s_namespace.count("::") + 1:
                                    sa_names_in, sa_names_out = Overlord.get_port_names(s_key)
                                    sa_types_in, sa_types_out = Overlord.get_port_types(s_key)
                                    s_sig = (", ".join([f"{s}: {t}" for s, t in zip(sa_names_in, sa_types_in)]))
                                    s_result = (", ".join([f"{s}: {t}" for s, t in zip(sa_names_out, sa_types_out)]))
                                    s_result = f" => {s_result}" if s_result else ""
                                    sa_contents.add(f"{s_key}({s_sig}{s_result}) (bifrost)")

                                else:
                                    sa_contents.add(f"{s_namespace}::{s_key.split('::')[1]}::* (bifrost)")

                        for s_key, data in (self._functions if d_settings["custom"] else {}).items():
                            if s_key.startswith(f"{s_namespace}::"):
                                if d_settings["nested"] or s_key.count("::") == s_namespace.count("::") + 1:
                                    s_sig = (", ".join([f"{p.name()}: {p.value_type()}" for p in data["scope"]._parameters]))
                                    s_result = (", ".join([f"{r.name()}: {r.value_type()}" for r in data["scope"]._results]))
                                    s_result = f" => {s_result}" if s_result else ""
                                    sa_contents.add(s_key + f"({s_sig}{s_result}) (custom)")
                                else:
                                    sa_contents.add(f"{s_namespace}::{s_key.split('::')[1]}::*")

                    sa_contents = sorted(sa_contents)
                    s_sep = ("\n    " if d_settings["newline"] else ", ")
                    s = s_namespace + s_sep + s_sep.join(sorted(sa_contents))
                    print(self.format_log(node, s))

            else:
                raise NotImplementedError(s_func_name)

            return _bifast.Value(node, s, _type.Type("string"))

        if self._functions.resolves(s_func_name):
            x_func = lambda v, t, n, inst=self, nd=node: _validate_type_cast(inst, nd, type_value=v, type_target=t, s_port=n)
            d_copy = self._functions[s_func_name]
            d_copy["scope"] = d_copy["scope"].copy({})
            status, result = _bifast.CallScope.create(node, s_func_name, d_copy, args, kwargs, sa_terminal, x_func)
            if not status:
                error, s_msg = result
                s_err = self.format_error(node, s_msg)
                raise error(s_err, b_stacktrace=False)

            parms = result._args + result._kwargs
            for i, (type_in, type_arg) in enumerate(zip(result._parm_types, result._arg_types)):
                _validate_type_cast(self, parms[i]._parser_node, type_target=type_in, type_value=type_arg)
            return result

        s_func_name_resolved = Overlord.function(s_func_name)

        if not s_func_name_resolved:
            s_msg = f"Unknown operator or compound: '{s_func_name}'"
            s_err = self.format_error(node["namespace_name"], s_msg)
            raise _error.BfNameError(s_err, b_stacktrace=False)

        s_func_name = s_func_name_resolved

        if Overlord.is_associative(s_func_name):
            status, result = _bifast.CallAssociative.create(node, s_func_name, args, kwargs, sa_terminal)
            if not status:
                s_err = self.format_error(node, result)
                raise _error.BfTypeError(s_err, b_stacktrace=False)
            return result

        status, result = _bifast.CallNative.create(node, s_func_name, args, kwargs, sa_terminal)
        if not status:
            error, s_msg = result
            s_err = self.format_error(node, s_msg)
            raise error(s_err, b_stacktrace=False)

        parms = result._args + result._kwargs
        for i, (type_in, type_arg) in enumerate(zip(result._parm_types, result._arg_types)):
            _validate_type_cast(self, parms[i]._parser_node, type_target=type_in, type_value=type_arg)
        return result

    def v_call_argument_one(self, node):
        visited_children = self.visit(node.children)

        if len(visited_children) == 3:
            arg = _bifast.Argument(node, visited_children[0], visited_children[2])

        elif len(visited_children) == 1:
            arg = _bifast.Argument(node, None, visited_children[0])

        else:
            raise NotImplementedError

        # cant do this here since the debug functions can indeed take on NODE types
        # if arg.value_type().is_node() and arg._value.output_count() != 1:
        #     s_error = self.format_error(node, s_error="Can't pass NODE type variables through scopes!")
        #     raise _error.Error(s_error, b_stacktrace=False)

        return arg

    def v_call_argument_list(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node.children[0])]

            previous = self.v_call_argument_list(node["call_argument_list"], b_collect_recursive=True)
            new = self.visit(node["call_argument_one"])
            return previous + [new]

        all_args = self.v_call_argument_list(node, b_collect_recursive=True)

        args = []
        kwargs = []

        # todo: this should really be a syntax check and I should split 1) call_argument_list
        #   into args and kwargs. And 2) create BAD rules to catch this error. Since its a
        #   SyntaxError, it should be caught by the parser. Not afterwards processing the tree...
        b_named = False
        for arg in all_args:
            if b_named and arg.name() is None:
                s_error = "Python rules! Positional arguments cant follow keyword arguments"
                s_msg = self.format_error(node, s_error=s_error)
                raise _error.BfSyntaxError(s_msg, b_stacktrace=False)

            b_named = b_named or (arg.name() is not None)

            if b_named:
                kwargs.append(arg)
            else:
                args.append(arg)

        return args, kwargs

    def v_call_arguments(self, node):
        if node.children[0].type == "EMPTY":
            return [], []
        return self.visit(node["call_argument_list"])


    def _v_call_type(self, node):
        args, kwargs = self.visit(node["call_arguments"])
        s_name = self.visit(node["type_base"])

        d_type_data = _bifres.TYPES[s_name]
        sa_port_names = list(d_type_data.keys())
        if not sa_port_names:
            s_err = self.format_error(node, "No members found for type. Use default assignment")
            raise _error.BfTypeError(s_err)

        x_func = lambda v, t, inst=self, nd=node: _validate_type_cast(inst, nd, type_value=v, type_target=t)
        return _bifast.CallType(node, s_name, args, kwargs, x_compat=x_func)

    # ==================== small atom ========================


    def v_atom_small(self, node):
        s_rule = node.children[0].type
        visited_children = self.visit(node.children)

        if s_rule in ["value"]:
            return visited_children[0]

        elif s_rule.strip("'\"") == "(":
            return visited_children[1]

        elif s_rule in ["name"]:
            s_name = visited_children[0]
            if _bifast.get_static_variable_type(s_name) is None:
                if visited_children[0] == "max_iterations":
                    s_error = f"Variable 'max_iterations' only available in loops with max iterations setting"
                else:
                    s_error = f"Variable '{visited_children[0]}' referenced before assignment"

                s_error = self.format_error(node.children[0], s_error=s_error)
                raise _error.Error(s_error, b_stacktrace=False)

            if _bifast.is_write_only(s_name):
                s_error = f"Cant read '{visited_children[0]}' output variable"
                s_error = self.format_error(node.children[0], s_error=s_error)
                raise _error.Error(s_error, b_stacktrace=False)

            return _bifast.Variable(node, s_name)

        elif s_rule in ["call"]:
            # logic got moved into the binops
            return visited_children[0]

        raise NotImplementedError(s_rule)


    # ==================== access ============================


    def v_access_port(self, node):
        value = self.visit(node.children[0])
        b_is_variable = node.children[0].type == "name"
        s_port = self.visit(node["point_to_port"])
        # print(f"access_port: {value}.{s_port}")
        status, result = _bifast.AccessPort.create(node, value, s_port, b_is_variable)
        if not status:
            error, s_message = result
            s_err = self.format_error(node, s_message)
            raise error(s_err, b_stacktrace=False)
        # if hasattr(result._real_value, "_scope"):
        #     print(f"    {result._real_value} {result._real_value._scope}")
        #     _bifast.print_all_scopes()
        return result

    def v_point_to_port(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 2:
                return self.visit(node.children[1])

            previous = self.v_point_to_port(node.children[0])
            new = self.visit(node.children[2])
            return f"{previous}.{new}"

        return self.v_point_to_port(node, b_collect_recursive=True)


    def v__access_expression(self, node):
        value = self.visit(node.children[1])
        # only return the index and figure out string/array/object above
        return _bifast.AccessByValue(node, value)

    def v__access_rhs_default(self, node):
        """
        create a `get_property` node and connect/set the `key` and `default_and_type` ports
        """
        _, key, _, value_or_type, _ = self.visit(node.children)

        if key.value_type().s != "string":
            s_message = f"Key must be of type 'string', not '{key.value_type()}'"
            s_error = self.format_error(node.children[0], s_message)
            raise _error.BfTypeError(s_error, b_stacktrace=False)

        if node.children[3].type != "expression":
            value_or_type = _type.Type(value_or_type)

        return _bifast.AccessRHS_Default(node, key, value_or_type)

    def _check_slice_is_integer(self, node, visited_children, ia_indices):
        for i in ia_indices:
            type_value = visited_children[i].value_type()
            if type_value.is_array():
                s_message = "Slice value cannot be array"
                s_error = self.format_error(node.children[i], s_message)
                raise _error.BfTypeError(s_error, b_stacktrace=False)

            if type_value.is_fraction() or type_value.is_vector() or type_value.is_matrix():
                s_message = "Slice value bust be integer scalar"
                s_error = self.format_error(node.children[i], s_message)
                raise _error.BfTypeError(s_error, b_stacktrace=False)


    def v__access_rhs_slice(self, node):
        visited_children = self.visit(node.children)

        # [start:stop:step]
        if len(node.children) == 7 and node.children[1].type == node.children[3].type == node.children[5].type == "expression":
            # print("[start:stop:step]")
            self._check_slice_is_integer(node, visited_children, [1, 3, 5])
            return _bifast.Slice(node, visited_children[1], visited_children[3], visited_children[5])

        # [start:stop]
        elif len(node.children) == 5 and node.children[1].type == node.children[3].type == "expression":
            # print("[start:stop]")
            self._check_slice_is_integer(node, visited_children, [1, 3])
            return _bifast.Slice(node, visited_children[1], visited_children[3], None)

        # [start::step]
        elif len(node.children) == 6 and node.children[1].type == node.children[4].type == "expression":
            # print("[start::step]")
            self._check_slice_is_integer(node, visited_children, [1, 4])
            return _bifast.Slice(node, visited_children[1], None, visited_children[4])

        # [start:]
        elif len(node.children) == 4 and node.children[1].type == "expression":
            # print("[start:]")
            self._check_slice_is_integer(node, visited_children, [1])
            return _bifast.Slice(node, visited_children[1], None, None)

        # [:stop:step]
        elif len(node.children) == 6 and node.children[2].type == node.children[4].type == "expression":
            # print("[:stop:step]")
            self._check_slice_is_integer(node, visited_children, [2, 4])
            return _bifast.Slice(node, None, visited_children[2], visited_children[4])

        # [:stop]
        elif len(node.children) == 4 and node.children[2].type == "expression":
            # print("[:stop]")
            self._check_slice_is_integer(node, visited_children, [2])
            return _bifast.Slice(node, None, visited_children[2], None)

        # [::step]
        elif len(node.children) == 5 and node.children[3].type == "expression":
            # print("[::step]")
            self._check_slice_is_integer(node, visited_children, [3])
            return _bifast.Slice(node, None, None, visited_children[3])

        raise NotImplementedError(f"{len(node.children)}")


    def v__access_rhs(self, node, b_collect_recursive=False):
        visited_children = self.visit(node.children)
        if len(visited_children) == 1:
            return [visited_children[0]]

        if b_collect_recursive:
            previous = self.v__access_rhs(node.children[0], b_collect_recursive=True)
            new = self.visit(node.children[1])
            return previous + [new]

        components = self.v__access_rhs(node, b_collect_recursive=True)
        return components

    def v_access_rhs(self, node):
        visited_children = self.visit(node.children)

        value = visited_children[0]

        for access in visited_children[1]:
            type_value = value.value_type()
            if type_value.is_node() and len(type_value.node_data()) == 1:
                type_value = list(type_value.node_data().values())[0]

            b_is_array = type_value.is_array()
            b_is_string = type_value == "string"

            if isinstance(access, (_bifast.AccessByValue, _bifast.Slice)):
                type_access = access.value_type()
                if type_access.is_node() and len(type_access.node_data()) == 1:
                    type_access = list(type_access.node_data().values())[0]

                if type_value == "Object":
                    s_error = self.format_error(node, "Use object[key, type_or_value] to access an Object!")
                    raise _error.BfRuntimeError(s_error, b_stacktrace=False)

                elif not (b_is_array or b_is_string):
                    s_error = self.format_error(node, "Can only access 'array<?>' or 'string' via expression!")
                    raise _error.BfRuntimeError(s_error, b_stacktrace=False)

                if not type_access.is_integer():
                    s_error = self.format_error(node, f"Index must be integer type. Got '{type_access}'")
                    raise _error.BfTypeError(s_error, b_stacktrace=False)

                value = _bifast.AccessRHS(node, value, access)

            elif isinstance(access, _bifast.AccessRHS_Default):
                if type_value != "Object":
                    s_error = self.format_error(node, "Can only access Object with default value/type")
                    raise _error.BfRuntimeError(s_error, b_stacktrace=False)

                value = _bifast.AccessRHS(node, value, access)

            elif isinstance(access, str):
                if not type_value.has_access(access):
                    type_value = type_value.base_type() if type_value.is_array() else type_value
                    s_error = self.format_error(node, f"Type '{type_value}' has no accessor '{access}'")
                    raise _error.BfTypeError(s_error, b_stacktrace=False)

                value = _bifast.AccessRHS(node, value, access)

            else:
                raise NotImplementedError

        return value

    def v__access_rhs_dot(self, node):
        s_port = ".".join([s for s in self.visit(node.children) if s != "."])
        return s_port

    def v_access_lhs(self, node):
        visited_children = self.visit(node.children)

        s_var_name = visited_children[0]
        type_var = _bifast.get_static_variable_type(s_var_name)
        index_or_key = visited_children[1]

        if type_var is None:
            s_error = f"Variable '{visited_children[0]}' referenced before assignment"
            s_error = self.format_error(node.children[0], s_error=s_error)
            raise _error.Error(s_error, b_stacktrace=False)

        if _bifast.is_write_only(s_var_name):
            s_error = f"Cant access result '{visited_children[0]}'"
            s_error = self.format_error(node.children[0], s_error=s_error)
            raise _error.Error(s_error, b_stacktrace=False)

        if node.children[1].type == "_access_lhs_dot":
            return _bifast.AccessLHS(node, _bifast.Variable(node.children[0], s_var_name), index_or_key)

        elif node.children[1].type == "_access_expression":
            type_expr = index_or_key.value_type()

            if type_var == "string" or type_var.is_array():
                if type_expr.is_array() or not type_expr.is_integer():
                    s_error = f"Must assign to string and array via single integer, not '{type_expr}'"
                    s_error = self.format_error(node.children[1], s_error=s_error)
                    raise _error.Error(s_error, b_stacktrace=False)

                return _bifast.AccessLHS(node, _bifast.Variable(node.children[0], s_var_name), index_or_key)

            if type_var == "Object":
                if type_expr.is_array() or not type_expr.is_string():
                    s_error = f"Must assign to object via single string, not '{type_expr}'"
                    s_error = self.format_error(node.children[1], s_error=s_error)
                    raise _error.Error(s_error, b_stacktrace=False)

                return _bifast.AccessLHS(node, _bifast.Variable(node.children[0], s_var_name), index_or_key)

            s_error = f"Cannot assign to '{type_var}' via '{type_expr}'"
            s_error = self.format_error(node, s_error=s_error)
            raise _error.Error(s_error, b_stacktrace=False)

        # we should never get to this point
        raise NotImplementedError

    def v__access_lhs_dot(self, node):
        s_port = "".join(self.visit(node.children)).strip(".")
        return s_port


    # ======================== value =========================


    def v_value(self, node):
        s_rule = node.children[0].type
        if s_rule in ["string", "numeric", "bool", "vector", "matrix", "array", "object"]:
            return self.visit(node.children)[0]

        if s_rule in ["index"]:
            if _bifast.get_static_variable_type("#") is None:
                s_error = f"'Current index' (#) only available within loop scopes"
                s_error = self.format_error(node.children[0], s_error=s_error)
                raise _error.Error(s_error, b_stacktrace=False)

            return _bifast.Variable(node, "#")

        raise NotImplementedError(f"value: {s_rule}")


    # ======================== array ========================


    def v_array(self, node):
        visited_children = self.visit(node.children)

        if node.children[1].type == "_array":
            return visited_children[1]
        #
        # elif len(node.children) == 3:
        #     return self.create_const_default_array_value(0, f"array<{visited_children[1]}>")

        s_component_type = visited_children[1]
        if s_component_type.count("<") > 2:
            raise _error.BfTypeError(self.format_error(node, "Max array dimension is 3"), b_stacktrace=False)

        type_value = _type.Type(visited_children[1])
        value_count = visited_children[3] if len(node.children) == 5 else _bifast.Value(node, 0, "long")
        return _bifast.EmptyArray(node, value_count, type_value)

    def v__array(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 1:
                return [self.visit(node.children[0])]

            previous = self.v__array(node.children[0], b_collect_recursive=True)
            new = self.visit(node.children[2])
            return previous + [new]

        # call itself to collect all components.
        values = self.v__array(node, b_collect_recursive=True)

        status, result = _bifast.Array.create(node, values)
        if not status:
            s_err = self.format_error(node, result)
            raise _error.BfTypeError(s_err, b_stacktrace=False)

        return result


    # ======================== vector ========================


    def v_vector(self, node):
        values = self.visit(node["_vector"])  # type: list[_bifast.Value]
        s_type_hint = self.visit(node.children[2])[1:].lower()
        type_target = _type.Type(self.type_hint_to_port_type(s_type_hint))
        status, result = _bifast.Vector.create(node, values, type_component=type_target)
        if not status:
            s_err = self.format_error(node, result)
            raise _error.BfTypeError(s_err, b_stacktrace=False)

        return result

    def v__vector(self, node):
        visited_children = self.visit(node.children)
        values = visited_children[0:7:2]
        return values


    # ======================== object ========================


    def v_object(self, node):
        if node.children[1].type == "EMPTY":
            return _bifast.Object(node)

        return self.visit(node.children[1])

    def v__object(self, node, b_collect_recursive=False):
        if b_collect_recursive:
            if len(node.children) == 3:
                key, _, value = self.visit(node.children)

                b_key_valid = True
                if key.value_type().is_node():
                    d_nd = key.value_type().node_data()
                    if len(d_nd) != 1 or list(d_nd.values())[0] != "string":
                        b_key_valid = False

                elif key.value_type().s != "string":
                    b_key_valid = False

                if not b_key_valid:
                    s_message = f"Key must be of type 'string', not '{key.value_type()}'"
                    s_error = self.format_error(node.children[0], s_message)
                    raise _error.BfTypeError(s_error, b_stacktrace=False)

                if value.value_type().is_node():
                    if len(value.value_type().node_data()) != 1:
                        s_message = f"Values of type 'NODE' cannot be used in OBJECTs"
                        s_error = self.format_error(node.children[2], s_message)
                        raise _error.BfTypeError(s_error, b_stacktrace=False)

                return [(key, value)]

            previous = self.v__object(node.children[0], b_collect_recursive=True)
            new_key, _, new_value = self.visit(node.children[2:5])

            b_key_valid = True
            if new_key.value_type().is_node():
                d_nd = new_key.value_type().node_data()
                if len(d_nd) != 1 or list(d_nd.values())[0] != "string":
                    b_key_valid = False

            elif new_key.value_type().s != "string":
                b_key_valid = False

            if not b_key_valid:
                s_message = f"Key must be of type 'string', not '{new_key.value_type()}'"
                s_error = self.format_error(node.children[0], s_message)
                raise _error.BfTypeError(s_error, b_stacktrace=False)

            if new_value.value_type().is_node():
                if len(new_value.value_type().node_data()) != 1:
                    s_message = f"Values of type 'NODE' cannot be used in OBJECTs"
                    s_error = self.format_error(node.children[2], s_message)
                    raise _error.BfTypeError(s_error, b_stacktrace=False)

            return previous + [(new_key, new_value)]

        # call itself to collect all components.
        keys_and_values = self.v__object(node, b_collect_recursive=True)
        return _bifast.Object(node, keys_and_values)


    # ======================== matrix ========================


    def v__matrix_col(self, node):
        return [self.visit(node.children[i]) for i in range(len(node.children)) if i % 2 == 0]

    def v__matrix(self, node):
        return [self.visit(node.children[i]) for i in range(len(node.children)) if i % 2 == 0]

    def v_matrix(self, node):
        values = self.visit(node["_matrix"])  # type: list[_bifast.Value]
        s_type_hint = self.visit(node.children[2])[1:].lower()
        type_target = _type.Type(self.type_hint_to_port_type(s_type_hint))
        status, result = _bifast.Matrix.create(node, values, type_component=type_target)
        if not status:
            s_err = self.format_error(node, result)
            raise _error.BfTypeError(s_err, b_stacktrace=False)

        return result


    # ======================== string ========================


    def v_STRING(self, node):
        s_text = self.visit(node.children[0])
        if s_text[0] != s_text[-1]:
            s_err = self.format_error(node, f"Missing end of string: {s_text[0]}")
            raise _error.BfSyntaxError(s_err)
        return s_text

    def v_string(self, node):
        s_text = self.visit(node.children[0])
        return _bifast.Value(node, s_text[1:-1], "string")


    # ======================== numeric =======================


    def v_bool(self, node):
        s_text = self.visit(node.children[0])
        return _bifast.Value(node, int(s_text == "true"), "bool")


    def v_numeric(self, node):
        s_numeric = self.visit(node.children)[0]
        return s_numeric


    def v_some_int(self, node):
        return self.visit(node.children)[0]

    def v_char(self, node):
        s_text = self.visit(node.children[0]).strip("cC")
        return _bifast.Value(node, int(s_text), "char")

    def v_uchar(self, node):
        s_text = self.visit(node.children[0]).strip("uUcC")
        return _bifast.Value(node, int(s_text), "uchar")


    def v_short(self, node):
        s_text = self.visit(node.children[0]).strip("sS")
        return _bifast.Value(node, int(s_text), "short")

    def v_ushort(self, node):
        s_text = self.visit(node.children[0]).strip("uUsS")
        return _bifast.Value(node, int(s_text), "ushort")


    def v_int(self, node):
        s_text = self.visit(node.children[0]).strip("iI")
        return _bifast.Value(node, int(s_text), "int")

    def v_uint(self, node):
        s_text = self.visit(node.children[0]).strip("uUiI")
        return _bifast.Value(node, int(s_text), "uint")


    def v_long(self, node):
        s_text = self.visit(node.children[0]).strip("lL")
        return _bifast.Value(node, int(s_text), "long")

    def v_ulong(self, node):
        s_text = self.visit(node.children[0]).strip("uUlL")
        return _bifast.Value(node, int(s_text), "ulong")


    def v_some_float(self, node):
        return self.visit(node.children)[0]

    def v_double(self, node):
        s_text = self.visit(node.children[0]).strip("dD")
        return _bifast.Value(node, float(s_text), "double")

    def v_float(self, node):
        s_text = self.visit(node.children[0]).strip("fF")
        return _bifast.Value(node, float(s_text), "float")


    # ======================== type ==========================


    def v_port_type(self, node):
        s_type = self.visit(node.children)[0]
        return s_type

    def v_defined_port_type(self, node):
        s_type = self.visit(node.children)[0]
        return s_type

    def v_type(self, node):
        s_type = self.visit(node.children)[0]
        return s_type

    def v_type_auto(self, node):
        return "auto"

    def v_type_array(self, node):
        s_text = "".join(self.visit(node.children))
        s_type = self.resolve_port_type(node, s_type=s_text)
        return s_type

    def v_type_node(self, node):
        return "__NODE"

    def v_type_base(self, node):
        s_text = self.visit(node.children)[0]
        s_type = self.resolve_port_type(node, s_type=s_text)
        return s_type

    def v_type_enum(self, node):
        return self.visit(node.children)[0]


    # ======================== enum ==========================


    def v_enum(self, node):
        s_type, _, s_value = self.visit(node["ENUM_VALUE"]).rpartition(".")
        if s_type in TYPES:
            s_type = TYPES[s_type]

        return _bifast.Enum(node, s_value, s_type=s_type)


    # ===================== port state =======================


    def v_feedback(self, node):
        return self.visit(node["NAME"])


    # ======================= names ==========================


    def v_name(self, node):
        return self.visit(node["NAME"])

    def v_namespace_name(self, node):
        text = "".join(self.visit(node.children))
        return text


    # ====================== terminal ========================


    def v_terminal(self, node):
        if len(node.children) == 1:
            return [None]

        if len(node.children) == 2:
            return []

        s_flags = self.visit(node["NAME"])
        sa_letters = set(s_flags.strip("<>").upper())
        if sa_letters - {"F", "P", "D"}:
            s_err = self.format_error(node, "Invalid terminal flags. Use any combination of F, P, and D")
            raise _error.BfTypeError(s_err, b_stacktrace=False)

        return list(sa_letters)


    # ====================== misc op =========================


    def _visit_operator(self, node):
        return self.visit(node.children)[0]


def _validate_type_cast(graph, node, type_value, type_target, s_port=None):
    """
    this function only exists atm because I wanna use it in assignments
    and calls. Once I figure out auto looping, both will have separate
    logic and this function can go away
    """
    i_compat = _type.compatibility(type_target=type_target, type_value=type_value)

    if i_compat == 0:
        return

    if s_port is None:
        s_port = ""
    else:
        s_port = f" [{s_port}]"

    if i_compat & _type.ARRAY_DIM_MISSMATCH:
        s_msg = f"Array dimension missmatch{s_port}: '{type_value}' <> '{type_target}'"
        s_err = graph.format_error(node, s_msg)
        raise _error.BfTypeError(s_err, b_stacktrace=False)

    if i_compat & _type.INCOMPATIBLE_TYPES:
        s_msg = f"Incompatible type assignment{s_port}: '{type_value}' -> '{type_target}'"
        s_err = graph.format_error(node, s_msg)
        raise _error.BfTypeError(s_err, b_stacktrace=False)

    # if i_compat & _type.NUMERIC_AUTO_CONVERSION:
    #     s_msg = f"Automatic conversion: '{type_rhs}' -> '{type_lhs}'"
    #     s_wrn = self.format_error(node, s_msg)
    #     print(s_wrn)

    if i_compat & _type.NUMERIC_LOSSY_CONVERSION:
        s_msg = f"Use explicit cast for lossy conversion{s_port}: '{type_value}' -> '{type_target}'"
        s_err = graph.format_error(node, s_msg)
        raise _error.BfTypeError(s_err, b_stacktrace=False)

    # if i_compat & _type.MATRIX_DIM_EXTENSION:
    #     s_msg = f"Automatic dimension extension: '{type_rhs}' -> '{type_lhs}'"
    #     s_wrn = self.format_error(node, s_msg)
    #     print(s_wrn)

    if i_compat & _type.MATRIX_DIM_INCOMPATIBLE:
        s_msg = f"Incompatible matrix dimensions{s_port}: '{type_value}' -> '{type_target}'"
        s_err = graph.format_error(node, s_msg)
        raise _error.BfTypeError(s_err, b_stacktrace=False)
