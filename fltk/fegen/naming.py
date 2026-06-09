"""Shared naming utilities for fltk code generators.

Leaf module: no FLTK imports, no third-party imports.
"""


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
