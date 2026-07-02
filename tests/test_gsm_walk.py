"""Direct unit tests for gsm.for_each_item — the structural Items walk.

These pin the public contract of the walk (name, visit order, index semantics,
and Sequence[Items] recursion) directly, rather than only via consumers such as
``regex_corpus.collect_regexes`` or the nullable-loop validators.
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
