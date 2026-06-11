# Design review findings: Phase 3 — Python Bindings + Parity

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Reviewed: `design.md` against `request.md`, controlling design (`10-rust-parser-codegen/design.md`), Phase 1/2 designs, `exploration.md`, and source. Verification performed against code; claims checked include: `use super::cst` binding (parser.rs:17, generator header emission gsm2parser_rs.py:266-272), Phase 2 native `Parser` surface (parser.rs:31-115 — `new`/`from_source_text`/`terminals`/`capture_trivia`/`rule_names`/`error_message`/`error_position`/`apply__parse_<rule>` incl. `apply__parse__trivia`), `TerminalSource::len()` (terminalsrc.rs:88), `to_py_canonical` (cst.rs:432-439), `children` getter tuple shape (cst.rs:492+), `register_classes` (cst.rs:11055+), plumbing.py:134-141/161-162/291-322, errors.py:64-70 set iteration, errors.rs first-occurrence dedupe (errors.rs:148-157), Makefile lanes (cargo-check:40-42, no-python lanes:52-65, build-fegen-rust-cst:99-100, gencode parser targets:113-115,166), both fixture Cargo.tomls (no pyproject.toml in either crate; `rust-parser-fixture` lib name derivation), fixture grammar audit (rust_parser_fixture.fltkg: confirmed no sub-expression term, no leading separator), gsm2tree_rs.py identifier/label validation (~lines 56-79), `_fltk_canonical_name` machinery in fltk_cst.py and gsm2tree.py, phase-4 test importorskip + all-skipped-lane docstring, `Shared` = `Arc<RwLock<T>>`. All accurate except the findings below.

---

## design-1: comparator species discrimination via `hasattr(child, "kind")` is factually wrong — spans expose `kind` on both backends

**Section**: §2.4, `assert_cst_equal`: "then child species (span vs node — discriminate by `hasattr(child, "kind")`, true only for nodes on both backends), then recurse / compare span endpoints."

**What's wrong**: "true only for nodes on both backends" is false on both backends.

- Python: `terminalsrc.Span` is a dataclass with a `kind` field defaulting to `SpanKind.SPAN` (`fltk/fegen/pyrt/terminalsrc.py:55`: `kind: Literal[SpanKind.SPAN] = field(default=SpanKind.SPAN, ...)`).
- Rust: the `Span` pyclass exposes a `#[getter] fn kind` returning the *same* `SpanKind.SPAN` Python object (`crates/fltk-cst-core/src/span.rs`, getter near line 563, with docstring: "Returns the *same* Python object as the pure-Python `terminalsrc.Span.kind` field"). The adjacent `get_start` docstring explicitly states spans expose these attributes so "hasattr/getattr checks against child spans must find it on both backends" — the attribute exists by deliberate design for protocol narrowing.

**Consequence**: the comparator as specified classifies every span child as a node and recurses into it; spans have no `children` attribute, so every parity corpus entry whose tree contains a span child (i.e., essentially all of them — every terminal produces a span child) raises `AttributeError` instead of comparing. Best case the whole suite is red on a comparator bug, not a parity property; worst case a defensive implementation silently skips span comparison. The §4.4 negative self-tests as listed (kind/span/label/child-count/deep-child mismatches) would not necessarily expose the misdiscrimination since they may never construct a span-child/node-child confusion case.

**Suggested fix**: discriminate by `kind` *value* (`child.kind == SpanKind.SPAN`, which is identity-stable cross-backend per span.rs) or by `hasattr(child, "children")` (true only for nodes on both backends — Python dataclass field fltk_cst.py:82, Rust getter cst.rs:492). Add a §4.4 self-test for the span-vs-node discrimination itself.

---

## design-2: trailing-character parity coverage required by controlling design §4 is absent from the corpus

**Section**: §2.5 (corpus tables) and §2.4 (corpus entry forms).

**What's wrong**: controlling design §4 lists "`+` quantifier zero-progress check …, WS_REQUIRED failure …, leading separators, empty-nary, **trailing-character behavior**: each has an existing Python regression test whose inputs feed the parity corpus." The existing test is `fltk/fegen/test_trailing_character_bug.py` (inputs ending in a non-whitespace character historically stopped one position early: `"x+"` parsed to pos 1, `"x+ "` to completion). Phase 3's corpus covers the other four items explicitly (§2.5 fixture table rows), but no entry — fegen or fixture — names trailing-non-whitespace final-position behavior. The fegen "grammar snippets" bullets do not specify whether inputs end without trailing whitespace/newline, and the only PARTIAL-expectation entries are in the empty-nary row.

**Consequence**: a Rust-generator divergence in final-position handling at end-of-input (exactly the class of bug the Python backend historically had) would pass the parity suite, leaving a controlling-design §4 requirement unmapped. Because SUCCESS entries assert `result.pos == len(input)`, one deliberate corpus entry per grammar whose input ends in a non-whitespace terminal (plus the `"x+"`-style PARTIAL/SUCCESS pair adapted to the fixture grammar) closes it cheaply.

**Suggested fix**: add explicit corpus entries: input ending in a non-whitespace terminal with SUCCESS expectation, and the trailing-character pair (same input with and without trailing whitespace) from test_trailing_character_bug.py mapped onto the fixture grammar; cite the regression file in the §2.5 table.

---

No other findings. Requirements coverage otherwise complete: request.md's python-linkage isolation (cfg gate + empty default features, gated by existing no-python lanes), controlling §3.3 binding surface (verified signature-compatible with parser.rs as committed), §5 item 3 corpus (every `test_regression_*.py`, trivia, leading separators, fegen.fltkg, multibyte, both `capture_trivia` values), error-message structural comparison consistent with Phase 1 §2.4's ordering analysis and errors.rs's implemented first-occurrence dedupe. The fixture-grammar audit in §2.5 is accurate against the committed grammar. Internal consistency and scope discipline are sound; the §2.2B fixture-extension expansion is justified and its template-erosion risk is mitigated by verified existing lanes.
