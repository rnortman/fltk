"""Cross-backend parser parity helpers.

Imported by test_rust_parser_parity_fegen.py and test_rust_parser_parity_fixture.py.
Not a test module itself.
"""

from __future__ import annotations


def assert_cst_equal(py_node, rust_node, path: str = "") -> None:
    """Recursively assert structural CST equality between Python and Rust nodes."""
    # kind equality
    assert py_node.kind == rust_node.kind, f"[{path}] kind mismatch: {py_node.kind!r} vs {rust_node.kind!r}"
    # span equality
    assert py_node.span.start == rust_node.span.start, (
        f"[{path}] span.start: {py_node.span.start} vs {rust_node.span.start}"
    )
    assert py_node.span.end == rust_node.span.end, f"[{path}] span.end: {py_node.span.end} vs {rust_node.span.end}"
    # children
    py_children = py_node.children
    rust_children = rust_node.children
    assert len(py_children) == len(rust_children), f"[{path}] children len: {len(py_children)} vs {len(rust_children)}"
    for i, (py_pair, rust_pair) in enumerate(zip(py_children, rust_children, strict=True)):
        py_label, py_child = py_pair
        rust_label, rust_child = rust_pair
        child_path = f"{path}.children[{i}]"
        # label equality
        assert py_label == rust_label, f"[{child_path}] label: {py_label!r} vs {rust_label!r}"
        # species: span vs node — discriminate by hasattr(child, "children")
        py_is_node = hasattr(py_child, "children")
        rust_is_node = hasattr(rust_child, "children")
        assert py_is_node == rust_is_node, (
            f"[{child_path}] child species mismatch: py_is_node={py_is_node} rust_is_node={rust_is_node}"
        )
        if py_is_node:
            assert_cst_equal(py_child, rust_child, child_path)
        else:
            # span child: compare start/end
            assert py_child.start == rust_child.start, (
                f"[{child_path}] span child start: {py_child.start} vs {rust_child.start}"
            )
            assert py_child.end == rust_child.end, f"[{child_path}] span child end: {py_child.end} vs {rust_child.end}"


def _parse_error_message(msg: str):
    """Parse an error message into (header_lines, {rule_name: set(token_lines)}).

    Assumes 'From rule "..."' lines are indented with exactly two leading spaces and
    token lines with exactly four.

    Validates that indentation assumptions hold: if any line in the message contains
    'From rule "' (anywhere in the line), the parsed rule_sections must be non-empty.
    The no-failure stub form ('Syntax error at line 1 col 0:\\n\\n^\\nExpected:\\n') has
    no 'From rule "' lines and legitimately produces empty rule_sections.
    """
    lines = msg.splitlines()
    header_lines = []
    rule_sections = {}
    current_rule = None
    current_tokens = set()
    for line in lines:
        if line.startswith('  From rule "'):
            if current_rule is not None:
                rule_sections[current_rule] = current_tokens
            current_rule = line.strip()
            current_tokens = set()
        elif current_rule is not None and line.startswith("    "):
            current_tokens.add(line.strip())
        else:
            if current_rule is not None:
                rule_sections[current_rule] = current_tokens
                current_rule = None
                current_tokens = set()
            header_lines.append(line)
    if current_rule is not None:
        rule_sections[current_rule] = current_tokens

    # Validate indentation assumption: if any line contains 'From rule "', the
    # two-space-indent pattern must have matched all of them.
    from_rule_count = sum(1 for line in lines if 'From rule "' in line)
    assert from_rule_count == len(rule_sections), (
        f"_parse_error_message indentation assumption violated: found {from_rule_count} "
        f"'From rule' line(s) in message but parsed {len(rule_sections)} rule section(s). "
        f"Check that 'From rule \"...\"' lines use exactly two leading spaces.\nMessage:\n{msg}"
    )

    return header_lines, rule_sections


def assert_messages_equiv(msg_a: str, msg_b: str) -> None:
    """Assert structural equivalence of two error message strings.

    Public wrapper around _assert_messages_equiv for callers that have raw message
    strings and do not need to supply parsed intermediate representations.
    """
    _assert_messages_equiv(*_parse_error_message(msg_a), *_parse_error_message(msg_b))


def _assert_messages_equiv(py_header, py_rules, rust_header, rust_rules) -> None:
    """Assert structural equivalence of two parsed error messages.

    Accepts the output of two _parse_error_message calls (header list + rule dict each).
    Separated from assert_error_equiv so header/group-order/token-set logic can be
    negatively tested with hand-built inputs without requiring live parser objects.
    """
    # Header lines byte-equal
    assert py_header == rust_header, f"Error message header mismatch:\nPython: {py_header}\nRust: {rust_header}"
    # Same rule names in order
    assert list(py_rules.keys()) == list(rust_rules.keys()), (
        f"Error rule group keys differ:\nPython: {list(py_rules.keys())}\nRust: {list(rust_rules.keys())}"
    )
    # Within each rule, token sets equal (unordered — Python iterates a set, Rust first-occurrence)
    for rule_name in py_rules:
        assert py_rules[rule_name] == rust_rules[rule_name], (
            f"Token set for rule {rule_name!r} differs:\nPython: {py_rules[rule_name]}\nRust: {rust_rules[rule_name]}"
        )


def assert_error_equiv(py_parser, rust_parser, terminals) -> None:
    """Assert error parity between Python and Rust parsers.

    py_parser: Python parser with .error_tracker attribute
    rust_parser: Rust PyParser with .error_position() and .error_message()
    terminals: the TerminalSource or text used for Python error formatting
    """
    from fltk.fegen.pyrt import errors as py_errors  # noqa: PLC0415

    py_pos = py_parser.error_tracker.longest_parse_len
    rust_pos = rust_parser.error_position()
    if py_pos == -1:
        assert rust_pos is None, f"Error position: Python=-1 (no error) but Rust={rust_pos}"
    else:
        assert rust_pos is not None, f"Error position: Python={py_pos} but Rust=None"
        assert py_pos == rust_pos, f"Error position: Python={py_pos} vs Rust={rust_pos}"

    # Compare messages structurally
    if py_pos == -1:
        # No error recorded; verify Rust emits the same no-failure form as Python.
        rule_name_fn = lambda rid: py_parser.rule_names[rid]  # noqa: E731
        py_msg = py_errors.format_error_message(py_parser.error_tracker, terminals, rule_name_fn)
        rust_msg = rust_parser.error_message()
        _assert_messages_equiv(*_parse_error_message(py_msg), *_parse_error_message(rust_msg))
        return

    py_msg = py_errors.format_error_message(py_parser.error_tracker, terminals, lambda rid: py_parser.rule_names[rid])
    rust_msg = rust_parser.error_message()

    _assert_messages_equiv(*_parse_error_message(py_msg), *_parse_error_message(rust_msg))


def run_parity_corpus_entry(py_p, rust_p, ts, *, rule: str, text: str, expected) -> None:
    """Shared corpus-entry dispatch body for parity test suites.

    Dispatches on expected outcome (SUCCESS / PARTIAL / FAIL), asserts both backends
    agree, and compares CST trees or error state as appropriate.

    py_p: Python parser instance (has .apply__parse_<rule> and .error_tracker)
    rust_p: Rust PyParser instance (has .apply__parse_<rule>, .error_message(), .error_position())
    ts: TerminalSource for the input text (used by assert_error_equiv)
    rule: grammar rule name (method suffix after 'apply__parse_')
    text: input text
    expected: SUCCESS, PARTIAL(pos), or FAIL sentinel
    """
    py_method = getattr(py_p, f"apply__parse_{rule}")
    rust_method = getattr(rust_p, f"apply__parse_{rule}")

    py_result = py_method(pos=0)
    rust_result = rust_method(0)

    if expected is SUCCESS:
        assert py_result is not None, f"Python parser failed: {py_p.error_tracker}"
        assert rust_result is not None, f"Rust parser failed: {rust_p.error_message()}"
        assert py_result.pos == len(text), f"Python pos {py_result.pos} != len {len(text)}"
        assert rust_result.pos == len(text), f"Rust pos {rust_result.pos} != len {len(text)}"
        assert_cst_equal(py_result.result, rust_result.result)
    elif isinstance(expected, PARTIAL):
        assert py_result is not None, f"Python parser failed unexpectedly on PARTIAL(pos={expected.pos}) input"
        assert rust_result is not None, f"Rust parser failed unexpectedly on PARTIAL(pos={expected.pos}) input"
        assert py_result.pos == expected.pos, f"Python pos {py_result.pos} != expected {expected.pos}"
        assert rust_result.pos == expected.pos, f"Rust pos {rust_result.pos} != expected {expected.pos}"
        assert_cst_equal(py_result.result, rust_result.result)
    else:  # FAIL
        assert py_result is None or py_result.pos < len(text), "Python unexpectedly succeeded"
        assert rust_result is None or rust_result.pos < len(text), "Rust unexpectedly succeeded"
        assert (py_result is None) == (rust_result is None), (
            f"Backends disagree on outcome: py={py_result!r} rust={rust_result!r}"
        )
        if py_result is not None and rust_result is not None:
            assert py_result.pos == rust_result.pos, (
                f"FAIL backends partial at different positions: py={py_result.pos} rust={rust_result.pos}"
            )
        assert_error_equiv(py_p, rust_p, ts)


# Outcome sentinels for declarative corpus entries
SUCCESS = "SUCCESS"


class PARTIAL:
    def __init__(self, pos: int):
        self.pos = pos

    def __repr__(self):
        return f"PARTIAL({self.pos})"


FAIL = "FAIL"
