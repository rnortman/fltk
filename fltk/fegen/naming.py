"""Shared naming utilities for fltk code generators.

Leaf module: no FLTK imports, no third-party imports.
"""


def protocol_module_name(cst_module_name: str) -> str:
    """CST module import name → its paired CST protocol module import name.

    The layout every generated pair uses: ``X_cst`` beside ``X_cst_protocol``.
    """
    return f"{cst_module_name}_protocol"


def protocol_module_path(cst_path: str) -> str:
    """Path of a written CST module file → path of its paired protocol module file.

    ``dir/X_cst.py`` → ``dir/X_cst_protocol.py``, the layout ``genparser generate`` writes.  The
    ``.py`` suffix is required; the stem is otherwise unconstrained.
    """
    if not cst_path.endswith(".py"):
        msg = f"CST module path {cst_path!r} does not end in '.py'"
        raise ValueError(msg)
    return f"{cst_path[: -len('.py')]}_protocol.py"


def snake_to_upper_camel(name: str) -> str:
    """Convert a snake_case name to UpperCamelCase.

    Uses the canonical form: apply .lower() to the whole string, split on '_',
    capitalize() each segment, join.

    Edge-case contract:
    - Consecutive underscores collapse: "a__b" -> "AB"
    - Leading underscore collapses: "_foo_bar" -> "FooBar"
    - Trailing underscore collapses: "foo_" -> "Foo"
    - Digits mid-segment unaffected: "rule1_test" -> "Rule1Test"; "a1b2c3" -> "A1b2c3"
    - Digit-leading segment: capitalize() leaves the digit as-is: "1starts" -> "1starts"
    - .lower() applied first: "MixedLabel" -> "Mixedlabel"
    - Empty string -> empty string
    """
    return "".join(part.capitalize() for part in name.lower().split("_"))
