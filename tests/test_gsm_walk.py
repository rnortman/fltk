"""Direct unit tests for the structural Items walk and the predicates built on it.

``gsm.for_each_item``: the walk's public contract (name, visit order, index semantics, and
Sequence[Items] recursion), pinned directly rather than only via consumers such as
``regex_corpus.collect_regexes`` or the nullable-loop validators.

``gsm.rule_reads_trivia_at_gap``: the shape question both unparser backends ask, whose answer
is invisible in any formatter output.
"""

from fltk.fegen import gsm


def _item(label: str, quantifier: gsm.Quantifier = gsm.REQUIRED, term: gsm.Term | None = None) -> gsm.Item:
    """Build a leaf Item whose Literal value doubles as an identifying label."""
    return gsm.Item(
        label=label,
        disposition=gsm.Disposition.INCLUDE,
        term=term if term is not None else gsm.Literal(label),
        quantifier=quantifier,
    )


def _items(items: list[gsm.Item]) -> gsm.Items:
    return gsm.Items(items=items, sep_after=[gsm.Separator.NO_WS] * len(items))


def test_flat_items_visited_once_in_order() -> None:
    """Every Item in a flat Items is visited once, idx == position in items.items."""
    a, b, c = _item("a"), _item("b"), _item("c")
    seq = _items([a, b, c])

    visits: list[tuple[int, gsm.Item]] = []
    gsm.for_each_item(seq, lambda idx, item: visits.append((idx, item)))

    assert visits == [(0, a), (1, b), (2, c)]


def test_recurses_into_sequence_terms_with_enclosing_relative_index() -> None:
    """Sequence[Items] sub-expression items are visited, idx relative to enclosing Items."""
    inner_x, inner_y = _item("x"), _item("y")
    inner = _items([inner_x, inner_y])

    outer_a = _item("a")
    sub = _item("sub", term=[inner])  # Sequence[Items] term (a list of Items)
    outer_b = _item("b")
    seq = _items([outer_a, sub, outer_b])

    visits: list[tuple[int, gsm.Item]] = []
    gsm.for_each_item(seq, lambda idx, item: visits.append((idx, item)))

    # Depth-first: outer item, then (immediately after visiting it) its nested items,
    # then the next outer item. Nested idx is relative to the inner Items, not global.
    assert visits == [(0, outer_a), (1, sub), (0, inner_x), (1, inner_y), (2, outer_b)]


def test_recurses_regardless_of_outer_quantifier() -> None:
    """A ZERO_OR_MORE-quantified Sequence sub-expression is still entered."""
    inner_x = _item("x")
    inner = _items([inner_x])
    sub = _item("sub", quantifier=gsm.ZERO_OR_MORE, term=[inner])
    seq = _items([sub])

    visits: list[tuple[int, gsm.Item]] = []
    gsm.for_each_item(seq, lambda idx, item: visits.append((idx, item)))

    assert visits == [(0, sub), (0, inner_x)]


# ── rule_reads_trivia_at_gap ──────────────────────────────────────────────────
#
# Both unparser backends gate the dropped-comment check on this predicate, so a false negative
# silently removes the guard for a rule and a false positive emits a check that never fires.
# Neither shows up in a formatter's output, which is why the predicate is pinned here directly.


def _rule(name: str, alternatives: list[gsm.Items], *, is_trivia_rule: bool = False) -> gsm.Rule:
    return gsm.Rule(name=name, alternatives=alternatives, is_trivia_rule=is_trivia_rule)


def _items_with(seps: list[gsm.Separator], items: list[gsm.Item] | None = None) -> gsm.Items:
    """An Items whose ``sep_after`` is exactly ``seps`` (one item per separator)."""
    items = items if items is not None else [_item(f"i{idx}") for idx in range(len(seps))]
    return gsm.Items(items=items, sep_after=seps)


def test_a_top_level_ws_allowed_separator_reads_trivia() -> None:
    rule = _rule("stmt", [_items_with([gsm.Separator.WS_ALLOWED, gsm.Separator.WS_ALLOWED])])
    assert gsm.rule_reads_trivia_at_gap(rule) is True


def test_a_top_level_ws_required_separator_reads_trivia() -> None:
    rule = _rule("stmt", [_items_with([gsm.Separator.WS_REQUIRED])])
    assert gsm.rule_reads_trivia_at_gap(rule) is True


def test_a_glued_rule_reads_no_trivia() -> None:
    rule = _rule("glued", [_items_with([gsm.Separator.NO_WS, gsm.Separator.NO_WS])])
    assert gsm.rule_reads_trivia_at_gap(rule) is False


def test_an_initial_separator_alone_reads_trivia() -> None:
    items = gsm.Items(
        items=[_item("a")],
        sep_after=[gsm.Separator.NO_WS],
        initial_sep=gsm.Separator.WS_ALLOWED,
    )
    assert gsm.rule_reads_trivia_at_gap(_rule("leading", [items])) is True


def test_a_separator_inside_a_sub_expression_reads_trivia() -> None:
    """A sub-expression's children land on the enclosing rule's node, so its gaps are the
    enclosing rule's gaps."""
    inner = _items_with([gsm.Separator.WS_ALLOWED, gsm.Separator.NO_WS])
    sub = _item("sub", term=[inner])
    outer = gsm.Items(items=[_item("a"), sub], sep_after=[gsm.Separator.NO_WS] * 2)
    assert gsm.rule_reads_trivia_at_gap(_rule("outer", [outer])) is True


def test_a_separator_inside_a_quantified_sub_expression_reads_trivia() -> None:
    """The quantifier does not change where the children land."""
    inner = _items_with([gsm.Separator.WS_ALLOWED])
    sub = _item("sub", quantifier=gsm.ZERO_OR_MORE, term=[inner])
    outer = gsm.Items(items=[sub], sep_after=[gsm.Separator.NO_WS])
    assert gsm.rule_reads_trivia_at_gap(_rule("outer", [outer])) is True


def test_a_separator_in_any_alternative_reads_trivia() -> None:
    """The unparser picks an alternative by trial, so one gap anywhere arms the check."""
    glued = _items_with([gsm.Separator.NO_WS])
    spaced = _items_with([gsm.Separator.WS_ALLOWED])
    assert gsm.rule_reads_trivia_at_gap(_rule("either", [glued, spaced])) is True


def test_the_trivia_rule_itself_reads_no_trivia_gap() -> None:
    """Its whitespace children are consumed as spans, not as trivia gaps."""
    rule = _rule("_trivia", [_items_with([gsm.Separator.WS_ALLOWED])], is_trivia_rule=True)
    assert gsm.rule_reads_trivia_at_gap(rule) is False
