"""Tests for the interval-resolution core of ``fltk.lsp.classify`` (private seams by design).

The resolution step turns the explicit/ref intervals and the default intervals into one token
stream. This module keeps a verbatim copy of the original quadratic resolution as an oracle and
diffs the production ``_resolve`` against it, pins the exact-key tie rule, checks the structural
facts the linear default clip rests on, and bounds the growth of ``classify`` with input size.
"""

from __future__ import annotations

import gc
import heapq
import itertools
import logging
import pathlib
import random
import time
import typing

import pytest

import fltk.fegen
from fltk import plumbing
from fltk.lsp import classify as classify_module
from fltk.lsp import lsp_config, symbols
from fltk.lsp.analysis import prepare_analysis_grammar
from fltk.lsp.classify import Token, classify, default_tokens
from fltk.lsp.conftest import HELLO_GRAMMAR as _PAINTER_GRAMMAR
from fltk.lsp.engine import AnalysisEngine

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

_LOGGER = logging.getLogger(__name__)

_Interval: typing.TypeAlias = "tuple[int, int, lsp_config.Paint, tuple[int, lsp_config.Tier]]"
_Default: typing.TypeAlias = "tuple[int, int, str]"


# --- Legacy oracle: the original resolution, kept verbatim ------------------------------------------


def _legacy_winner_segments(intervals: list[_Interval]) -> list[tuple[int, int, lsp_config.Paint]]:
    if not intervals:
        return []
    boundaries = sorted({b for start, end, _, _ in intervals for b in (start, end)})
    segments: list[tuple[int, int, lsp_config.Paint]] = []
    for a, b in itertools.pairwise(boundaries):
        best: tuple[tuple[int, lsp_config.Tier], lsp_config.Paint] | None = None
        for start, end, paint, key in intervals:
            if start <= a and b <= end and (best is None or key > best[0]):
                best = (key, paint)
        if best is not None:
            paint = best[1]
            if segments and segments[-1][2] == paint and segments[-1][1] == a:
                prev_start = segments[-1][0]
                segments[-1] = (prev_start, b, paint)
            else:
                segments.append((a, b, paint))
    return segments


def _legacy_merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _legacy_subtract(interval: tuple[int, int], covered: list[tuple[int, int]]) -> Iterator[tuple[int, int]]:
    start, end = interval
    cursor = start
    for cstart, cend in covered:
        if cend <= cursor:
            continue
        if cstart >= end:
            break
        if cstart > cursor:
            yield (cursor, min(cstart, end))
        cursor = max(cursor, cend)
        if cursor >= end:
            return
    if cursor < end:
        yield (cursor, end)


def _legacy_merge_tokens(tokens: list[Token]) -> list[Token]:
    tokens.sort(key=lambda t: (t.start, t.end))
    merged: list[Token] = []
    for token in tokens:
        if (
            merged
            and merged[-1].end == token.start
            and merged[-1].token_type == token.token_type
            and merged[-1].modifiers == token.modifiers
        ):
            prev = merged[-1]
            merged[-1] = Token(prev.start, token.end, prev.token_type, prev.modifiers)
        else:
            merged.append(token)
    return merged


def _legacy_resolve(explicit: list[_Interval], defaults: Iterable[_Default]) -> list[Token]:
    covered = _legacy_merge_ranges([(start, end) for start, end, _, _ in explicit])

    tokens: list[Token] = []
    for start, end, paint in _legacy_winner_segments(explicit):
        if paint.token != "none":
            tokens.append(Token(start, end, paint.token, paint.modifiers))

    for start, end, token_type in defaults:
        for dstart, dend in _legacy_subtract((start, end), covered):
            tokens.append(Token(dstart, dend, token_type, ()))

    return _legacy_merge_tokens(tokens)


_PAINTS = (
    lsp_config.Paint("keyword", ()),
    lsp_config.Paint("type", ()),
    lsp_config.Paint("type", ("declaration",)),
    lsp_config.Paint("string", ()),
    lsp_config.Paint("none", ()),
)
_DEFAULT_TYPES = ("keyword", "variable", "comment", "type", "string")


def _random_explicit(rng: random.Random, count: int, span: int) -> list[_Interval]:
    """Explicit intervals over ``[0, span]`` with frequent shared endpoints and duplicate keys.

    A key that has been drawn before is given a paint different from its earlier use about half the
    time, so equal keys with different paints overlap often.
    """
    paint_by_key: dict[tuple[int, lsp_config.Tier], lsp_config.Paint] = {}
    out: list[_Interval] = []
    for _ in range(count):
        start = rng.randint(0, span)
        end = start if rng.random() < 0.1 else rng.randint(start, span)
        key = (rng.randint(0, 2), lsp_config.Tier(rng.randint(1, 2), rng.randint(0, 1), 0, rng.randint(0, 1)))
        previous = paint_by_key.get(key)
        if previous is not None and rng.random() < 0.5:
            paint = rng.choice([p for p in _PAINTS if p != previous])
        else:
            paint = rng.choice(_PAINTS)
        paint_by_key[key] = paint
        out.append((start, end, paint, key))
    return out


def _random_defaults(rng: random.Random, span: int) -> list[_Default]:
    """Non-overlapping, non-empty default intervals with boundaries drawn from ``[0, span]``, shuffled."""
    cuts = sorted(set(rng.sample(range(span + 1), k=rng.randint(0, span + 1))))
    out = [(a, b, rng.choice(_DEFAULT_TYPES)) for a, b in itertools.pairwise(cuts) if rng.random() < 0.7]
    rng.shuffle(out)
    return out


@pytest.mark.parametrize(
    ("count", "span", "cases"), [(0, 12, 50), (1, 12, 100), (2, 12, 200), (8, 16, 300), (300, 60, 20)]
)
def test_resolve_matches_legacy_on_random_inputs(count: int, span: int, cases: int) -> None:
    rng = random.Random(f"classify-resolution-{count}-{span}")  # noqa: S311 -- seeded, reproducible test data
    for _ in range(cases):
        explicit = _random_explicit(rng, count, span)
        defaults = _random_defaults(rng, span)
        expected = _legacy_resolve(explicit, defaults)
        assert classify_module._resolve(explicit, list(defaults)) == expected, (explicit, defaults)


def test_random_inputs_reach_the_edge_cases() -> None:
    rng = random.Random("classify-resolution-witness")  # noqa: S311 -- seeded, reproducible test data
    zero_width = equal_key_diff_paint = none_meets_default = False
    for _ in range(300):
        explicit = _random_explicit(rng, 8, 16)
        defaults = _random_defaults(rng, 16)
        zero_width |= any(s == e for s, e, _, _ in explicit)
        for x, y in itertools.combinations(explicit, 2):
            if x[3] == y[3] and x[2] != y[2] and max(x[0], y[0]) < min(x[1], y[1]):
                equal_key_diff_paint = True
        none_ends = {e for s, e, p, _ in explicit if p.token == "none" and s < e}
        none_meets_default |= any(s in none_ends for s, _, _ in defaults)
    assert zero_width
    assert equal_key_diff_paint
    assert none_meets_default


_REF_GRAMMAR = r"""
program := , stmt* ;
stmt := decl | use ;
decl := kw:"let" , name:word , semi:";" , ;
use := kw:"use" , target:word , semi:";" , ;
word := /[a-z]+/ ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""

_NEST_GRAMMAR = r"""
program := , stmt* ;
stmt := decl | use ;
decl := kw:"let" , name:word , semi:";" , ;
use := kw:"use" , inner , semi:";" , ;
inner := target:word ;
word := /[a-z]+/ ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""

_DEFAULT_GRAMMAR = r"""
top := , row* ;
row := k:"let" , p:"(" , o:"=>" , s:/"[a-z]*"/ , n:/[0-9]+/ , v:/[a-z_]+/ , x:/@[a-z]+/ , ";" , ;
_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
"""

_DEFAULT_TEXTS = (
    'let ( => "ab" 12 foo @bar ;',
    '//hi there\nlet ( => "ab" 12 foo @bar ;',
    '//c\nlet ( => "ab" 12 foo @bar ;\nlet ( => "z" 7 bar @q ;',
)

_PAINTER_CASES = (
    ("rule greeting {\n  scope name: type;\n}\n", "hello world !"),
    ("rule greeting {\n  scope kw: none;\n}\n", "hello world !"),
    ("scope rule:greeting: keyword;\nrule greeting {\n  scope name: type;\n}\n", "hello world !"),
    ("scope label:name: type;\nrule greeting {\n  scope name: string;\n}\n", "hello world !"),
    ("rule greeting {\n  scope name: type;\n  scope rule:word: string;\n}\n", "hello world !"),
    ("scope label:name: type;\nscope label:name: string;\n", "hello world !"),
    ("rule greeting {\n  def name: type;\n  scope name: variable;\n}\n", "hello world !"),
    ('scope "!": operator;\n', "hello world !"),
    ("rule line_comment {\n  scope content: string;\n}\n", "//hi there\nhello world !"),
    (
        "scope rule:greeting: keyword;\nrule greeting {\n  scope name: type;\n  scope kw: none;\n}\n",
        "//c\nhello world !\nhello there !",
    ),
)

_REF_TEXT = "let x ;\nuse x ;\nuse y ;\nuse x ;\n"
_REF_CASES = (
    (_REF_GRAMMAR, "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n}\n"),
    (_REF_GRAMMAR, "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n  scope target: string;\n}\n"),
    (_REF_GRAMMAR, "rule decl {\n  def name: widget.thing;\n}\nrule use {\n  ref target: *;\n}\n"),
    (_REF_GRAMMAR, "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n  scope target: none;\n}\n"),
    (
        _NEST_GRAMMAR,
        (
            "rule decl {\n  def name: type;\n}\nrule use {\n  ref rule:inner: type;\n}\n"
            "rule inner {\n  scope target: string;\n}\n"
        ),
    ),
    (
        _NEST_GRAMMAR,
        "rule decl {\n  def name: type;\n}\nscope rule:inner: string;\nrule inner {\n  ref target: type;\n}\n",
    ),
)


class _Prepared(typing.NamedTuple):
    tree: typing.Any
    grammar: typing.Any
    resolved: lsp_config.ResolvedLspConfig
    tables: classify_module.GrammarTables
    symbol_table: symbols.SymbolTable | None
    text: str


def _prepare(grammar_text: str, config_text: str, text: str, start_rule: str, *, with_symbols: bool) -> _Prepared:
    grammar = plumbing.parse_grammar(grammar_text)
    resolved = lsp_config.load_lsp_config(config_text, grammar)
    parser = plumbing.generate_parser(prepare_analysis_grammar(grammar))
    parsed = plumbing.parse_text(parser, text, start_rule)
    assert parsed.success, parsed.error_message
    tables = classify_module.build_grammar_tables(parser.grammar)
    symbol_table = symbols.extract(parsed.cst, tables, resolved, text) if with_symbols else None
    return _Prepared(parsed.cst, parser.grammar, resolved, tables, symbol_table, text)


def _collect(
    tree: typing.Any,
    tables: classify_module.GrammarTables,
    resolved: lsp_config.ResolvedLspConfig,
    text: str,
    symbol_table: symbols.SymbolTable | None,
) -> tuple[list[_Interval], list[_Default]]:
    explicit: list[_Interval] = []
    classify_module._explicit_intervals(tree, 0, tables=tables, resolved=resolved, text=text, out=explicit)
    if symbol_table is not None:
        classify_module._ref_intervals(symbol_table, explicit)
    defaults = list(classify_module._default_intervals(tree, tables, text))
    return explicit, defaults


def _fixtures() -> list[_Prepared]:
    out = [_prepare(_PAINTER_GRAMMAR, config, text, "top", with_symbols=False) for config, text in _PAINTER_CASES]
    out.extend(_prepare(grammar, config, _REF_TEXT, "program", with_symbols=True) for grammar, config in _REF_CASES)
    out.extend(_prepare(_DEFAULT_GRAMMAR, "", text, "top", with_symbols=False) for text in _DEFAULT_TEXTS)
    return out


def _assert_non_overlapping(defaults: list[_Default]) -> None:
    ordered = sorted(defaults)
    for prev, nxt in itertools.pairwise(ordered):
        assert prev[1] <= nxt[0], (prev, nxt)


def test_classify_matches_legacy_on_fixture_trees() -> None:
    for prepared in _fixtures():
        explicit, defaults = _collect(
            prepared.tree, prepared.tables, prepared.resolved, prepared.text, prepared.symbol_table
        )
        tokens = classify(
            prepared.tree,
            prepared.grammar,
            prepared.resolved,
            prepared.text,
            tables=prepared.tables,
            symbol_table=prepared.symbol_table,
        )
        assert tokens == _legacy_resolve(explicit, defaults), prepared.text


def test_engine_prefix_outcome_matches_legacy() -> None:
    grammar = plumbing.parse_grammar(_REF_GRAMMAR)
    config = "rule decl {\n  def name: type;\n}\nrule use {\n  ref target: type;\n  scope kw: keyword;\n}\n"
    engine = AnalysisEngine(grammar, lsp_config.load_lsp_config(config, grammar), start_rule="program")
    text = "let a ;\n// note\nuse a ;\nuse b ;\nlet ;\nlet c ;\n"
    analysis = engine.analyze(text)
    assert analysis.prefix_end is not None
    assert analysis.tree is not None
    assert analysis.tokens is not None
    tables = classify_module.build_grammar_tables(engine._parser_result.grammar)
    resolved = engine._resolved_config
    explicit, defaults = _collect(analysis.tree, tables, resolved, text, analysis.symbols)
    assert explicit
    _assert_non_overlapping(defaults)
    assert analysis.tokens == _legacy_resolve(explicit, defaults)


def test_default_intervals_do_not_overlap_on_fixture_trees() -> None:
    for prepared in _fixtures():
        _, defaults = _collect(prepared.tree, prepared.tables, prepared.resolved, prepared.text, None)
        _assert_non_overlapping(defaults)


def test_exact_key_tie_first_listed_wins() -> None:
    key = (1, lsp_config.Tier(lsp_config.SOURCE_RANK_REF, 1, 1, 3))
    type_paint = lsp_config.Paint("type", ())
    string_paint = lsp_config.Paint("string", ())
    first: _Interval = (0, 6, type_paint, key)
    second: _Interval = (3, 9, string_paint, key)

    assert classify_module._winner_segments([first, second]) == [(0, 6, type_paint), (6, 9, string_paint)]
    assert classify_module._winner_segments([second, first]) == [(0, 3, type_paint), (3, 9, string_paint)]


def test_empty_config_matches_default_tokens_and_never_enters_sweep(monkeypatch: pytest.MonkeyPatch) -> None:
    pushes: list[int] = []
    real_heappush = heapq.heappush

    def _recording_heappush(heap: list[int], item: int) -> None:
        pushes.append(item)
        real_heappush(heap, item)

    class _RecordingHeapq:
        heappush = staticmethod(_recording_heappush)
        heappop = staticmethod(heapq.heappop)

    monkeypatch.setattr(classify_module, "heapq", _RecordingHeapq)

    for text in _DEFAULT_TEXTS:
        prepared = _prepare(_DEFAULT_GRAMMAR, "", text, "top", with_symbols=False)
        tokens = classify(prepared.tree, prepared.grammar, prepared.resolved, text, tables=prepared.tables)
        assert tokens == default_tokens(prepared.tree, prepared.grammar, text, tables=prepared.tables)
        comments = [t for t in tokens if t.token_type == "comment"]
        assert len(comments) == text.count("//")
    assert pushes == []

    # Control: a non-empty spec does push, so the zero above is not vacuous.
    prepared = _prepare(_PAINTER_GRAMMAR, *_PAINTER_CASES[0], "top", with_symbols=False)
    classify(prepared.tree, prepared.grammar, prepared.resolved, prepared.text, tables=prepared.tables)
    assert pushes


# Expected growth for 10x input is ~11-13x; a reintroduced per-boundary rescan is ~100x.
_MAX_RATIO = 40.0


def _min_time(fn: typing.Callable[[], object], repeats: int) -> float:
    best = float("inf")
    for _ in range(repeats):
        gc.disable()
        try:
            t0 = time.perf_counter()
            fn()
            elapsed = time.perf_counter() - t0
        finally:
            gc.enable()
        best = min(best, elapsed)
    return best


def _dense_inputs(count: int) -> tuple[list[_Interval], list[_Default]]:
    """``count`` nested/overlapping explicit intervals over a document ~4 chars per interval wide."""
    rng = random.Random(f"classify-scale-{count}")  # noqa: S311 -- seeded, reproducible test data
    span = 4 * count
    explicit: list[_Interval] = []
    for _ in range(count):
        start = rng.randrange(span)
        end = min(span, start + rng.randint(1, 24))
        key = (rng.randint(0, 6), lsp_config.Tier(rng.randint(1, 2), rng.randint(0, 1), rng.randint(0, 1), 0))
        explicit.append((start, end, rng.choice(_PAINTS), key))
    defaults = [(a, a + 2, rng.choice(_DEFAULT_TYPES)) for a in range(0, span, 3)]
    return explicit, defaults


def test_resolve_scales_near_linearly_on_synthetic_input() -> None:
    n = 5_000
    small = _dense_inputs(n)
    large = _dense_inputs(10 * n)
    t_small = _min_time(lambda: classify_module._resolve(*small), 5)
    t_large = _min_time(lambda: classify_module._resolve(*large), 5)
    _LOGGER.info("synthetic _resolve: n=%d %.2f ms, n=%d %.2f ms", n, t_small * 1e3, 10 * n, t_large * 1e3)
    assert t_large <= _MAX_RATIO * t_small


_T = typing.TypeVar("_T")


class _CountingList(list[_T]):
    """A list that counts every element read, by index or by iteration, into ``counter[0]``."""

    def __init__(self, items: Iterable[_T], counter: list[int]) -> None:
        super().__init__(items)
        self._counter = counter

    def __getitem__(self, index: typing.Any) -> typing.Any:
        self._counter[0] += 1
        return super().__getitem__(index)

    def __iter__(self) -> Iterator[_T]:
        for i in range(len(self)):
            self._counter[0] += 1
            yield super().__getitem__(i)


class _AccessCounts(typing.NamedTuple):
    explicit: int
    covered: int
    n_covered: int
    n_defaults: int


def _resolve_access_counts(
    monkeypatch: pytest.MonkeyPatch, explicit: list[_Interval], defaults: list[_Default]
) -> _AccessCounts:
    """Run ``_resolve`` counting element reads of the explicit list and of the merged coverage."""
    explicit_reads = [0]
    covered_reads = [0]
    n_covered = [0]
    real_merge_ranges = classify_module._merge_ranges

    def _counting_merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        merged = real_merge_ranges(ranges)
        n_covered[0] = len(merged)
        return _CountingList(merged, covered_reads)

    with monkeypatch.context() as patch:
        patch.setattr(classify_module, "_merge_ranges", _counting_merge_ranges)
        tokens = classify_module._resolve(_CountingList(explicit, explicit_reads), list(defaults))
    assert tokens == _legacy_resolve(explicit, defaults)
    return _AccessCounts(explicit_reads[0], covered_reads[0], n_covered[0], len(defaults))


def _sparse_inputs(count: int) -> tuple[list[_Interval], list[_Default]]:
    """``count`` disjoint explicit intervals, so the merged coverage has ``count`` ranges."""
    rng = random.Random(f"classify-sparse-{count}")  # noqa: S311 -- seeded, reproducible test data
    explicit: list[_Interval] = []
    for i in range(count):
        key = (rng.randint(0, 6), lsp_config.Tier(rng.randint(1, 2), rng.randint(0, 1), rng.randint(0, 1), 0))
        explicit.append((6 * i + 1, 6 * i + 3, rng.choice(_PAINTS), key))
    defaults = [(a, a + 2, rng.choice(_DEFAULT_TYPES)) for a in range(0, 6 * count, 3)]
    return explicit, defaults


def _commented_rows_inputs(rows: int) -> tuple[list[_Interval], list[_Default]]:
    """``rows`` code rows each preceded by a comment painted by a trivia-internal ``scope``.

    Each comment is its own trivia node, so defaults and coverage ranges both grow with ``rows``.
    """
    text = "".join(f'// comment {i}\nlet ( => "ab" 12 foo @bar ;\n' for i in range(rows))
    prepared = _prepare(
        _DEFAULT_GRAMMAR, "rule line_comment {\n  scope content: string;\n}\n", text, "top", with_symbols=False
    )
    return _collect(prepared.tree, prepared.tables, prepared.resolved, text, None)


# A linear or n-log-n resolution reads ~10-13x more elements for 10x input; a per-boundary rescan of
# the intervals or a per-default rescan of the coverage reads ~100x more.
_MAX_READ_RATIO = 20.0


@pytest.mark.parametrize(
    ("make_inputs", "n"),
    [(_dense_inputs, 400), (_sparse_inputs, 400), (_commented_rows_inputs, 100)],
    ids=["dense", "sparse", "commented-rows-trivia-scope"],
)
def test_resolve_element_reads_scale_near_linearly(
    monkeypatch: pytest.MonkeyPatch, make_inputs: typing.Callable[[int], tuple[list[_Interval], list[_Default]]], n: int
) -> None:
    small = _resolve_access_counts(monkeypatch, *make_inputs(n))
    large = _resolve_access_counts(monkeypatch, *make_inputs(10 * n))
    _LOGGER.info("element reads at n=%d: %s; at 10n: %s", n, small, large)
    # Coverage and defaults must both grow with n, or a per-default rescan of the coverage would not show.
    assert large.n_covered >= 8 * small.n_covered > 0
    assert large.n_defaults >= 8 * small.n_defaults > 0
    assert large.explicit <= _MAX_READ_RATIO * small.explicit
    assert large.covered <= _MAX_READ_RATIO * small.covered


def _fegen_document_inputs(repeat: int) -> tuple[typing.Callable[[], list[Token]], int]:
    fegen_dir = pathlib.Path(fltk.fegen.__file__).parent
    grammar = plumbing.parse_grammar_file(fegen_dir / "fegen.fltkg")
    resolved = lsp_config.load_lsp_config((fegen_dir / "fegen.fltklsp").read_text(), grammar)
    parser = plumbing.generate_parser(prepare_analysis_grammar(grammar))
    text = (fegen_dir / "regex.fltkg").read_text() * repeat
    parsed = plumbing.parse_text(parser, text, "grammar")
    assert parsed.success, parsed.error_message
    tables = classify_module.build_grammar_tables(parser.grammar)
    symbol_table = symbols.extract(parsed.cst, tables, resolved, text)
    explicit, defaults = _collect(parsed.cst, tables, resolved, text, symbol_table)
    _assert_non_overlapping(defaults)

    def run() -> list[Token]:
        return classify(parsed.cst, parser.grammar, resolved, text, tables=tables, symbol_table=symbol_table)

    return run, len(explicit)


def test_classify_scales_near_linearly_on_grammar_document() -> None:
    run_small, n_small = _fegen_document_inputs(1)
    run_large, n_large = _fegen_document_inputs(10)
    assert n_large == 10 * n_small
    t_small = _min_time(run_small, 3)
    t_large = _min_time(run_large, 3)
    _LOGGER.info(
        "regex.fltkg classify: %d explicit %.2f ms, x10 %d explicit %.2f ms",
        n_small,
        t_small * 1e3,
        n_large,
        t_large * 1e3,
    )
    assert t_large <= _MAX_RATIO * t_small


_COMMENT_HEAVY = "".join(f"// comment line {i} with words\n" for i in range(200)) + 'let ( => "ab" 12 foo @bar ;\n'


@pytest.mark.parametrize(
    ("grammar_text", "config_text", "text"),
    [
        (_PAINTER_GRAMMAR, "", "hello world !"),
        (_PAINTER_GRAMMAR, "rule line_comment {\n  scope content: string;\n}\n", "hello world !"),
        (_DEFAULT_GRAMMAR, "", _COMMENT_HEAVY),
        (_DEFAULT_GRAMMAR, "rule line_comment {\n  scope content: string;\n}\n", _COMMENT_HEAVY),
    ],
    ids=["sparse-empty", "sparse-trivia-scope", "comments-empty", "comments-trivia-scope"],
)
def test_sparse_and_comment_heavy_inputs_stay_cheap(grammar_text: str, config_text: str, text: str) -> None:
    prepared = _prepare(grammar_text, config_text, text, "top", with_symbols=False)
    _, defaults = _collect(prepared.tree, prepared.tables, prepared.resolved, text, None)
    _assert_non_overlapping(defaults)
    elapsed = _min_time(
        lambda: classify(prepared.tree, prepared.grammar, prepared.resolved, text, tables=prepared.tables), 5
    )
    _LOGGER.info("classify %d chars: %.1f us", len(text), elapsed * 1e6)
    assert elapsed < 1.0
