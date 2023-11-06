from fltk.fegen import gsm

rules = [
    # grammar := rule+;
    gsm.Rule(
        name="grammar",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        "rule",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("rule"),
                        gsm.ONE_OR_MORE,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    ),
    # rule := name:identifier , ":=" , alternatives , ";" ,;
    gsm.Rule(
        name="rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="name",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier(value="identifier"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.SUPPRESS,
                        term=gsm.Literal(value=":="),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label="alternatives",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier(value="alternatives"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.SUPPRESS,
                        term=gsm.Literal(value=";"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.WS_ALLOWED,
                ],
            )
        ],
    ),
    # alternatives := items , ("|" , items)* ;
    gsm.Rule(
        name="alternatives",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="items",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Identifier(value="items"),
                        quantifier=gsm.REQUIRED,
                    ),
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[
                            gsm.Items(
                                items=[
                                    gsm.Item(
                                        None,
                                        gsm.Disposition.SUPPRESS,
                                        gsm.Literal("|"),
                                        gsm.REQUIRED,
                                    ),
                                    gsm.Item(
                                        "items",
                                        gsm.Disposition.INCLUDE,
                                        gsm.Identifier("items"),
                                        gsm.REQUIRED,
                                    ),
                                ],
                                sep_after=[
                                    gsm.Separator.WS_ALLOWED,
                                    gsm.Separator.NO_WS,
                                ],
                            ),
                        ],
                        quantifier=gsm.ZERO_OR_MORE,
                    ),
                ],
                sep_after=[
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.NO_WS,
                ],
            )
        ],
    ),
    # items := item , ((no_ws:"." | ws:",") , item)* , (no_ws:"." | ws:",")? ,;
    gsm.Rule(
        name="items",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        "item",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("item"),
                        gsm.REQUIRED,
                    ),
                    gsm.Item(
                        None,
                        gsm.Disposition.INCLUDE,
                        [
                            gsm.Items(
                                items=[
                                    gsm.Item(
                                        None,
                                        gsm.Disposition.INCLUDE,
                                        [
                                            gsm.Items(
                                                items=[
                                                    gsm.Item(
                                                        "no_ws",
                                                        gsm.Disposition.INCLUDE,
                                                        gsm.Literal("."),
                                                        gsm.REQUIRED,
                                                    )
                                                ],
                                                sep_after=[gsm.Separator.NO_WS],
                                            ),
                                            gsm.Items(
                                                items=[
                                                    gsm.Item(
                                                        "ws",
                                                        gsm.Disposition.INCLUDE,
                                                        gsm.Literal(","),
                                                        gsm.REQUIRED,
                                                    )
                                                ],
                                                sep_after=[gsm.Separator.NO_WS],
                                            ),
                                        ],
                                        gsm.REQUIRED,
                                    ),
                                    gsm.Item(
                                        "item",
                                        gsm.Disposition.INCLUDE,
                                        gsm.Identifier("item"),
                                        gsm.REQUIRED,
                                    ),
                                ],
                                sep_after=[
                                    gsm.Separator.WS_ALLOWED,
                                    gsm.Separator.NO_WS,
                                ],
                            ),
                        ],
                        gsm.ZERO_OR_MORE,
                    ),
                    gsm.Item(
                        None,
                        gsm.Disposition.INCLUDE,
                        [
                            gsm.Items(
                                items=[
                                    gsm.Item(
                                        "no_ws",
                                        gsm.Disposition.INCLUDE,
                                        gsm.Literal("."),
                                        gsm.REQUIRED,
                                    )
                                ],
                                sep_after=[gsm.Separator.NO_WS],
                            ),
                            gsm.Items(
                                items=[
                                    gsm.Item(
                                        "ws",
                                        gsm.Disposition.INCLUDE,
                                        gsm.Literal(","),
                                        gsm.REQUIRED,
                                    )
                                ],
                                sep_after=[gsm.Separator.NO_WS],
                            ),
                        ],
                        gsm.NOT_REQUIRED,
                    ),
                ],
                sep_after=[
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.WS_ALLOWED,
                ],
            )
        ],
    ),
    # item := (label:identifier . ":")? . disposition? . term . quantifier? ,;
    gsm.Rule(
        name="item",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        None,
                        gsm.Disposition.INCLUDE,
                        [
                            gsm.Items(
                                items=[
                                    gsm.Item(
                                        "label",
                                        gsm.Disposition.INCLUDE,
                                        gsm.Identifier("identifier"),
                                        gsm.REQUIRED,
                                    ),
                                    gsm.Item(
                                        None,
                                        gsm.Disposition.SUPPRESS,
                                        gsm.Literal(":"),
                                        gsm.REQUIRED,
                                    ),
                                ],
                                sep_after=[gsm.Separator.NO_WS, gsm.Separator.NO_WS],
                            )
                        ],
                        gsm.NOT_REQUIRED,
                    ),
                    gsm.Item(
                        "disposition",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("disposition"),
                        gsm.NOT_REQUIRED,
                    ),
                    gsm.Item(
                        "term",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("term"),
                        gsm.REQUIRED,
                    ),
                    gsm.Item(
                        "quantifier",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("quantifier"),
                        gsm.NOT_REQUIRED,
                    ),
                ],
                sep_after=[
                    gsm.Separator.NO_WS,
                    gsm.Separator.NO_WS,
                    gsm.Separator.NO_WS,
                    gsm.Separator.WS_ALLOWED,
                ],
            )
        ],
    ),
    # term := identifier | literal | "/" . regex:raw_string . "/" | "(" , alternatives , ")";
    gsm.Rule(
        name="term",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        "identifier",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("identifier"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        "literal",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("literal"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(None, gsm.Disposition.SUPPRESS, gsm.Literal("/"), gsm.REQUIRED),
                    gsm.Item(
                        "regex",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("raw_string"),
                        gsm.REQUIRED,
                    ),
                    gsm.Item(None, gsm.Disposition.SUPPRESS, gsm.Literal("/"), gsm.REQUIRED),
                ],
                sep_after=[
                    gsm.Separator.NO_WS,
                    gsm.Separator.NO_WS,
                    gsm.Separator.NO_WS,
                ],
            ),
            gsm.Items(
                items=[
                    gsm.Item(None, gsm.Disposition.SUPPRESS, gsm.Literal("("), gsm.REQUIRED),
                    gsm.Item(
                        "alternatives",
                        gsm.Disposition.INCLUDE,
                        gsm.Identifier("alternatives"),
                        gsm.REQUIRED,
                    ),
                    gsm.Item(None, gsm.Disposition.SUPPRESS, gsm.Literal(")"), gsm.REQUIRED),
                ],
                sep_after=[
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.WS_ALLOWED,
                    gsm.Separator.NO_WS,
                ],
            ),
        ],
    ),
    # disposition := suppress:"%" | include:"$" | inline:"!"
    gsm.Rule(
        name="disposition",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        "suppress",
                        gsm.Disposition.INCLUDE,
                        gsm.Literal("%"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        "include",
                        gsm.Disposition.INCLUDE,
                        gsm.Literal("$"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        "inline",
                        gsm.Disposition.INCLUDE,
                        gsm.Literal("!"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    ),
    # quantifier := optional:"?" | one_or_more:"+" | zero_or_more:"*";
    gsm.Rule(
        name="quantifier",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        "optional",
                        gsm.Disposition.INCLUDE,
                        gsm.Literal("?"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        "one_or_more",
                        gsm.Disposition.INCLUDE,
                        gsm.Literal("+"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
            gsm.Items(
                items=[
                    gsm.Item(
                        "zero_or_more",
                        gsm.Disposition.INCLUDE,
                        gsm.Literal("*"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    ),
    # identifier := name:/[_a-z][_a-z0-9]*/
    gsm.Rule(
        name="identifier",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        "name",
                        gsm.Disposition.INCLUDE,
                        gsm.Regex("[_a-z][_a-z0-9]*"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    ),
    # raw_string := value:/([^\/\n\\]|\\.)+/
    gsm.Rule(
        name="raw_string",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        "value",
                        gsm.Disposition.INCLUDE,
                        gsm.Regex(r"([^\/\n\\]|\\.)+"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    ),
    # literal := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/
    gsm.Rule(
        name="literal",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        "value",
                        gsm.Disposition.INCLUDE,
                        gsm.Regex("(\"([^\"\\n\\\\]|\\\\.)+\"|'([^'\\n\\\\]|\\\\.)+')"),
                        gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    ),
]

grammar = gsm.Grammar(rules=rules, identifiers={rule.name: rule for rule in rules})

if __name__ == "__main__":
    import sys

    import astor  # type: ignore

    from fltk import pygen
    from fltk.fegen import gsm2parser, gsm2tree
    from fltk.iir.py import compiler
    from fltk.iir.py import reg as pyreg

    parser_filename, cst_filename, cst_module_name = sys.argv[1:]

    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module)
    pgen = gsm2parser.ParserGenerator(grammar=grammar, cstgen=cstgen)

    parser_ast = compiler.compile_class(pgen.parser_class)
    imports = [
        pyreg.Module(("collections", "abc")),
        pyreg.Module(("typing",)),
        pyreg.Module(("fltk", "fegen", "pyrt", "errors")),
        pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
        cst_module,
    ]

    parser_mod = pygen.module(module.import_path for module in imports)
    parser_mod.body.append(parser_ast)

    with open(parser_filename, "w") as parser_file:
        parser_file.write(astor.to_source(parser_mod))

    cst_mod = cstgen.gen_py_module()
    with open(cst_filename, "w") as cst_file:
        cst_file.write(astor.to_source(cst_mod))
