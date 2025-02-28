import json

from BSL._vendor.ply import lex, yacc

from BSL import _error, _constants, _bifres
from BSL import _node


def _parse_grammar():
    """
    This method parses the grammar.y file
    There is a bunch of custom logic in here and most of it is build around PLY
    and the idea of Parsimonious Node class. PLY uses the function docstrings
    to define grammar rules. And I dont like it... Furthermore, its quite picky
    about the signatures of the p_* and t_* functions so I am working around that
    using decorators.

    The grammar.y syntax are loosely based on Bison. The order in which tokens
    get defined matters. Any line starting with '#' after removing whitespaces
    gets discarded as a comment.
    I should probably also mention that this method assumes the grammar is formatted
    properly. I should probably have a function to validate this, but I dont anticipate
    this being changed often

    To define terminals, write the token name in caps and the python re
    expression on the right side (indentation does not matter):
        <TOKEN> = <regex>
        AND = &&

    To define a keyword, replace the regex with a string literal (enclosed in `"`
    symbols):
        <TERMINAL> = "keyword"
        FOR_EACH = "for_each"

    To define tokens with more complex logic like strings or multiline comments,
    write the regex to match the start symbol, then, below, create a matching
    function called `_t_<TOKEN_NAME>` or `_t_ignore_<TOKEN_NAME>` and manually
    consume the text till you meet your end condition.

    Single character literals can get defined in the `literals` string below or as
    proper tokens in the grammar.
    Characters to be ignored by the tokenizer may be specified in the `t_ignore`
    string below.
    NEWLINE characters are also ignored but still get their own `_t_ignore_NEWLINE`
    function since we want to increment the lexer's lineno.

    To define rules, write lowercase rule names and their possible resolutions.
    You may put the first alternative into a new line, but you may not put more
    than 1 alternative per line. There is no need for a closing ";".
    Indentation again does not matter.
        <rule> : <alternative_1>
                 | <alternative_2>

        <rule>
            : <alternative_1>
            | <alternative_2>

    BAD rules can be defined by including `_BAD_` in the rule name. If no dedicated
    `_p_<rule>` method is defined, _p_BAD() will get called with file and line(s)
    information. An additional error message for this BAD rule can be defined with
    @BAD_MESSAGE line. If no @BAD_MESSAGE line is given, the rule gets passed as message.
        <rule> : <alternative_1>
               | rule_BAD_1

        @MESSAGE rule_BAD_1 Missing ";"
        rule_BAD_1 : <bad_alternative_1>
    """
    literals = "$|,.{}()[]=;:"
    t_ignore = " \t"

    def token_converter(fn):
        """
        despite my effort to document this as early as I felt comfortable, I can already
        no longer tell what this decorator does. I knew what it did in the beginning, but
        I am somewhat sure that I removed all the functionality. Nevertheless, removing
        this fails... (todo: fix this)
        """
        def inner(t):
            return fn(t)
        inner.__doc__ = fn.__doc__
        return inner


    def _t_STRING(t):
        """
        Method to parse string values. The closing single or double
        quote must be in the same line. Escape rules apply
        """
        source = t.lexer.lexdata
        i = t.lexer.lexpos
        s = t.value
        c = source[i]

        while c != t.value and i < len(source):
            # dont allow strings across multiple lines
            if c == "\n":
                t.value = s
                t.lexer.lineno += 1
                break

            if c == "\\":
                c_next = source[i+1]

                # support special characters
                if c_next == "n":
                    s += "\n"

                elif c_next == "t":
                    s += "\t"

                else:
                    s += source[i+1]

                i += 2
                c = source[i]
                continue
    
            s += c
            i += 1
            c = source[i]

        else:
            # if this breaks early, the closing quote wont
            # get added thus raising an error in the visitor
            # less hassle than the regex
            t.value = s + t.value

        t.lexer.lexpos = i + 1
        return t
    
    
    def _t_ignore_COMMENT_BLOCK(t):
        """
        Ignore block comments. Same logic as with strings just
        that we are matching the start pattern in reverse /* -> */
        When encountering a NEWLINE, increment the lexer's lineno
        """
        for i in range(t.lexer.lexpos, len(t.lexer.lexdata)-1):
            if t.lexer.lexdata[i:i+2] == t.value[::-1]:
                t.lexer.lexpos = i+2
                break
    
            elif t.lexer.lexdata[i] == "\n":
                t.lexer.lineno += 1
    
        else:
            raise SyntaxError("Block comment was never closed!")
    
    
    def _t_ignore_COMMENT_INLINE(t):
        """
        Simple inline comment ignoring everything until the next NEWLINE.
        Also ignored.
        """
        for i in range(t.lexer.lexpos, len(t.lexer.lexdata)-1):
            if t.lexer.lexdata[i] == "\n":
                t.lexer.lexpos = i+1
                t.lexer.lineno += 1
                break

        else:
            t.lexer.lexpos = len(t.lexer.lexdata)


    def _t_NAME(t):
        """
        Since base types and keywords all match NAME as well,
        filter them out here and patch the token type.
        """
        if t.value in d_reserved:
            t.type = d_reserved[t.value]
        elif t.value in sa_enums:
            t.type = "ENUM"
            if t.value in d_types:
                t.value = d_types[t.value]
        elif t.value in sa_types:
            t.type = "TYPE"
            # if "print" in t.value:
            #     print(t.value, sa_types)
            if t.value in d_types:
                t.value = d_types[t.value]
        elif "::" in t.value:
            t.type = "NAMESPACE_NAME"

        # print(f"name: '{t.value}' << {t.type}")
        # print(sa_types)

        return t

    def _t_ENUM(t):
        print(f"enum: '{t.value}'")
    
    def _t_ignore_NEWLINE(t):
        """
        Ignore NEWLINEs but still count them towards the lineno
        """
        t.lexer.lineno += t.value.count("\n")
    
    
    def t_error(t):
        """
        Default token error method. This gets called when an unexpected
        symbol is encountered. Meaning a symbol that doesnt match any token's
        regex. This prints a nicely formatted syntax error
        """
        s_prev = t.lexer.lexdata[:t.lexer.lexpos].rpartition("\n")[2]
        s_line = t.lexer.lexdata.split("\n")[t.lineno-1]
        s_underline = "".join([(c if c == "\t" else " ") for c in s_prev])
    
        if _constants.FILE_URI_IN_STACKTRACE:
            s_path = "file:///" + t.lexer.filename.replace("\\", "/")
        else:
            s_path = t.lexer.filename
    
        s_msg = f"File \"{s_path}\", line {t.lineno}:{len(s_prev)+1}\n"
        s_msg += f"    {s_line}\n"
        s_msg += f"    {s_underline}^\n>> Unexpected symbol '{t.value[0]}' <<"
        raise _error.BfSyntaxError(s_msg, b_stacktrace=False)

    def p_error(p):
        """
        Default error method if a bunch of tokens do not match a rule. This will
        print an unexpected token error. Ideally you catch as much as you can using
        _BAD_ expressions since you can provide custom error messages there.
        """
        lexer = _LEXER

        if p is None:
            s_prev = lexer.lexdata.rstrip().rpartition("\n")[2]
            s_line = lexer.lexdata.rstrip().split("\n")[-1]
            s_underline = "".join([(c if c == "\t" else " ") for c in s_prev])
            i_len = 1
            s_type = "EOF"
            s_value = ""
        else:
            s_prev = lexer.lexdata[:lexer.lexpos-p.len].rpartition("\n")[2]
            s_line = lexer.lexdata.split("\n")[p.lineno - 1]
            s_underline = "".join([(c if c == "\t" else " ") for c in s_prev])
            i_len = p.len
            s_type = p.type
            s_value = p.value

        if _constants.FILE_URI_IN_STACKTRACE:
            s_path = "file:///" + lexer.filename.replace("\\", "/")
        else:
            s_path = lexer.filename

        s_msg = f"File \"{s_path}\", line {lexer.lineno}:{len(s_prev) + 1}\n"
        s_msg += f"    {s_line}\n"
        s_msg += f"    {s_underline}{i_len * '^'}\n>> Unexpected token '{s_value}' (type:'{s_type}') <<"
        raise _error.BfSyntaxError(s_msg, b_stacktrace=False)

    def p_EMPTY(p):
        """EMPTY : """

    def _p_BAD(p, d_data=None):
        """
        The default method for _BAD_ rules. Notice this takes d_data as a second
        parameter. For any custom rules, I am passing a dict as the methods
        __doc__ string. This data always contains an 'expression' key and for
        _BAD_ methods it should also contain a 'error' key containing the error
        message to print
        """
        def _expand_node(node):
            if isinstance(node.children[0], _node.Node):
                return [n for child in node.children for n in _expand_node(child)]
            return [node]

        lexer = _LEXER

        s_rule, _, _ = d_data["expression"].partition(" ::= ")
        s_error = d_data["error"]

        flat = _expand_node(p[1])
        i_line_start = flat[0].lineno
        i_line_end = flat[-1].lineno
        in_last_line = [node for node in flat if node.lineno == i_line_end]

        s_prev = lexer.lexdata[:in_last_line[0].start].rpartition("\n")[2]
        s_line = lexer.lexdata.split("\n")[i_line_end - 1]
        s_underline = "".join([(c if c == "\t" else " ") for c in s_prev])

        i_underline = in_last_line[-1].end - in_last_line[0].start

        if _constants.FILE_URI_IN_STACKTRACE:
            s_path = "file:///" + lexer.filename.replace("\\", "/")
        else:
            s_path = lexer.filename

        if i_line_start == i_line_end:
            s_line_info = f"line {i_line_start}"
        else:
            s_line_info = f"lines {i_line_start}-{i_line_end}"

        s_msg = f'File "{s_path}", {s_line_info}\n'
        s_msg += f"    {s_line}\n"
        s_msg += f"    {s_underline}{i_underline * '^'}\n>> Error in rule '{s_rule}': {s_error} <<"
        raise _error.BfSyntaxError(s_msg, b_stacktrace=False)

    def _rule_default(p, d_data=None):
        """
        The default rule. Basically the current rule is a list containing all
        the tokens/rules it matched.
        """
        p[0] = p[1:]

    def _rule_annotator(fn):
        """
        Since we have access to the expression through d_data, this method turns the
        strings we get from PLY and convert's them to Parsimonious like Node objects.
        I am still figuring out the best way to pass data from the lexer without to
        the nodes without duplicating it a ridiculous amount of times.
        While SyntaxErrors are nicely formatted and point to where something is wrong,
        I'd like to have the same information available at a later point when semantic
        checks are performed.
        todo: figure this out
        """
        def inner(p, d_data=None):
            s_current_rule = d_data["expression"].split(" ::= ")[0]
            sa_expr_names = d_data["expression"].replace(" ::= ", " ").split(" ")[1:]

            children = []
            for i, (s_expr_name, value) in enumerate(zip(sa_expr_names, p[1:]), 1):
                if not isinstance(value, _node.Node):
                    value = _node.Node(
                        type=s_expr_name,
                        children=[value],
                        lineno=p.lineno(i),
                        start=p.lexpos(i),
                        end=p.lexpos(i)+(len(value) if value else 0),
                        filename=p.lexer.filename,
                        text=value
                        # text=p.lexer.lexdata[p.lexpos(i):p.lexpos(i)+len(value)] if value else ""
                    )

                # _node.Node(type=s_expr_name, children=[value]) if not isinstance(value, _node.Node) else value)
                children.append(value)

            fn(p, d_data=d_data)
            p[0] = _node.Node(
                    type=s_current_rule,
                    children=children,
                    lineno=children[-1].lineno,
                    start=children[0].start,
                    end=children[-1].end,
                    filename=p.lexer.filename
                    # text=p.lexer.lexdata[children[0].start:children[-1].end]
            )


        inner.__doc__ = fn.__doc__
        return inner

    def _rule_extractor(fn):
        """
        As mentioned in some of the previous methods, I recently had the idea of passing
        json strings through the __doc__ string. (todo: could I pass the dict directly??)
        Since this is also a decorator, I can fix the __doc__ string on the inner method.
        """
        # d_data = json.loads(fn.__doc__)
        d_data = fn.__doc__

        def inner(p):
            fn(p, d_data=d_data)

        inner.__doc__ = d_data["expression"]
        return inner

    # this is again some PLY stuff. PLY uses the local space so I am checking
    # for and populating in that space as well
    d_locals = locals()
    terminals = []
    d_reserved = {}
    tokens = []
    d_bad_rule_messages = {}

    # query and sort the types from types.txt
    # todo: clean this up... A LOT!
    sa_types = (_constants.PATH_BASE/"res"/"types.txt").absolute().read_text().strip().split("\n")
    d_types = {s.split(" = ")[0].strip(): s.split(" = ")[1].strip() for s in sa_types if s.strip()}
    sa_types = [s.partition("=")[0].strip() for s in sa_types if s.strip()]

    sa_all_types = list(_bifres.TYPES.keys())
    sa_types += [s for s in sa_all_types if s.upper() not in sa_types]

    sa_enums = list(_bifres.ENUMS.keys())

    for k, v in d_types.items():
        if v in sa_enums:
            sa_enums.append(k)
            sa_types.remove(k)

    # for i in range(3):
    #     sa_types += [f"{s}\[]" for s in sa_types]
    #     sa_enums += [f"{s}\[]" for s in sa_enums]

    sa_types.sort(key=lambda x: len(x), reverse=True)
    sa_enums.sort(key=lambda x: len(x), reverse=True)

    # for s_type in sa_types:
    #     d_reserved[s_type] = "TYPE"
    #
    # for s_enum in sa_enums:
    #     d_reserved[s_enum] = "ENUM"

    # parse the grammar file, replacing the {__TYPES__} and {__ENUMS__} with the actual
    # type
    s_grammar = (_constants.PATH_BASE/"res"/"grammar.y").absolute().read_text()
    s_grammar = s_grammar.replace("{__TYPES__}", "|".join(sa_types))
    s_grammar = s_grammar.replace("{__ENUMS__}", "|".join(sa_enums))
    # print(s_grammar)
    # remove comments
    sa_lines = [s for s in s_grammar.split("\n") if s.strip() and not s.strip().startswith("#")]

    # keep track of rules for later
    sa_rules = []

    for s in sa_lines:
        # keep track of the _BAD_ rule messages
        if s.strip().startswith("@BAD_MESSAGE"):
            s_rule, _, s_message = s.strip().partition(" ")[2].partition(" ")
            d_bad_rule_messages[s_rule] = s_message.strip()
            continue

        # assume that we have a token definition
        token_name, _, token_regex = s.strip().partition(" = ")
        token_name = token_name.strip()
        token_regex = token_regex.strip()
        
        # upper tokens define terminals, lower (or anything but upper) defines rules
        # so if we have a rule, bank it for later and go on
        if not token_name.isupper() or token_name.startswith("|"):
            sa_rules.append(s)
            continue

        # check for reserved words
        if token_regex.startswith('"') and token_regex.endswith('"'):
            d_reserved[token_regex.strip('"')] = token_name
            continue

        # check if there is a t_* function already (probably not)
        # next, check if there is a _t_* or _t_ignore_* function
        # if not, get lambda
        func = None
        key = f"t_{token_name}"
        if key in d_locals:
            func = d_locals[key]

        elif f"_{key}" in d_locals:
            func = d_locals[f"_{key}"]

        elif f"_t_ignore_{token_name}" in d_locals:
            key = f"t_ignore_{token_name}"
            func = d_locals[f"_{key}"]

        else:
            func = lambda t: t

        # this is how ply gets the regex from functions. Not a fan,
        # but I like how the lexing works so I'll stick with that for now
        func.__doc__ = token_regex

        # I have no idea why `... = func` breaks but ... = token_converter(func)
        # does not break.
        d_locals[key] = token_converter(func)

        # if this token is supposed to be ignored, never mind the rest
        if "_ignore_" in key:
            continue

        tokens.append(token_name)

        # check if adding this terminal broke the lexer
        # this is probably not performant, but its relatively easy to figure out
        # if a new regex rule broke it. Keep in mind, if something is off in regard
        # to the t_* methods, (eg, defining t_<TERMINAL>), will cause an error on the first
        # rule since <TERMINAL> is not yet defined. My workaround is to specify a _t_<TERMINAL>
        # method instead
        try:
            lexer = lex.lex()
        except SyntaxError as e:
            raise _error.BfSyntaxError(str(e) + f" after: {token_name} = '{token_regex}'")

    tokens += list(dict.fromkeys(d_reserved.values()).keys())
    tokens += ["TYPE", "ENUM", "NAMESPACE_NAME"]

    global _LEXER
    _LEXER = lex.lex()

    # now for the rules. We keep a dict with rules as keys and lists of alternatives as
    # the values. We keep track of the last rule we added for alternatives in new lines
    s_last = None
    d_rules = {}
    for s_rule in sa_rules:
        # first alternative (and possible rule)
        if " : " in s_rule:
            s_new_last, _, s_alt1 = s_rule.partition(" : ")
            s_new_last = s_new_last.strip()
            if s_new_last:
                s_last = s_new_last.strip()
            d_rules[s_last] = [s_alt1.strip()]
            continue

        elif "|" in s_rule:
            d_rules[s_last] += [s_rule.partition("|")[2].strip()]
            continue

        s_last = s_rule.strip()
        d_rules[s_last] = []

    # now, that we have the rules dict, we can set the functions
    # for all alternatives
    for k, v in d_rules.items():
        for i in range(len(v)):
            d_data = {}

            # an EMPTY returns an empty list
            if v[i] == "EMPTY":
                func = lambda p, d_data: []

            # a _BAD_ rule might either be defined here already
            # or if not, makes use of the generic _p_BAD
            elif "_BAD_" in v[i]:
                if f"_p_{v[i]}" in d_locals:
                    func = d_locals[f"_p_{v[i]}"]
                else:
                    func = _p_BAD
                    d_data["error"] = d_bad_rule_messages.get(v[i], f"'{v[i]}'")

            # or, you know, just use the default method
            else:
                func = lambda p, d_data: _rule_default(p, d_data)

            d_data["expression"] = f"{k} ::= {v[i]}"
            # func.__doc__ = json.dumps(d_data)
            func.__doc__ = d_data

            # add the function to the local space
            d_locals[f"p_{k}_{i}"] = _rule_extractor(_rule_annotator(func))

            # we also need to delete func as PLY finds this with its docstring
            # otherwise. Actually, since I changed __doc__ to be a dict, maybe
            # this isnt needed anymore. Better safe than sorry.
            del func

    global _PARSER
    _PARSER = yacc.yacc(start="program")


_LEXER = None
_PARSER = None


def get_lexer():
    global _LEXER
    if _LEXER is None:
        _parse_grammar()
    return _LEXER


def get_parser():
    global _PARSER
    if _PARSER is None:
        _parse_grammar()
    return _PARSER
