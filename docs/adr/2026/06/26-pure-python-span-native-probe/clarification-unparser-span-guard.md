# Clarification needed — §2.1 breaks the generated unparser in native-present processes

Increment 2 implements design §2.1 (Python parser always constructs `terminalsrc` types).
The §2.1 change itself is complete and correct, but it exposes a **design gap the design does
not account for**: the generated *unparser* rejects the parser's pure-Python spans whenever
`fltk._native` is importable. I am stopping rather than improvising an unscoped codegen change
to `gsm2unparser.py`.

## What the design says

- §2.5: "The `make gencode` drift check (`make check`) must stay clean." and the regen "produces
  no diff beyond the intended parser changes."
- §4 (test plan) enumerates the surviving suite and asserts "`make check` is clean"; it does not
  list any unparser test as affected.
- §2.4 (frozen surface) calls out that the **CST node** mutator isinstance logic is
  "`terminalsrc.Span` + lazy `_get_native_span_type()`" and is left **unchanged** — i.e. the CST
  mutators already accept *both* backends' span types.
- requirements.md: "all of the CST-consuming code remains agnostic to which backend was used."

The design addresses the CST node mutators but **never mentions the generated unparser**, and
assumes only parser files change.

## What actually happens

The generated unparser's span-type guards are **probe-bound**, not dual-backend like the CST
mutators. In `fltk/unparse/gsm2unparser.py` the span type is built as
`self.span_type = iir.Type.make(cname="Span")` (`:87`) and used in `iir.IsInstance(...)` at
`:328` (span child guard), `:1013-1014`, and `:1116-1117`. The IIR compiler resolves that type
through the registry to `fltk.fegen.pyrt.span.Span`. The committed/generated unparser therefore
emits:

```python
if not isinstance(child, fltk.fegen.pyrt.span.Span):
    ...            # span child is skipped / unparse fails
```

In a process where `fltk._native` is importable, the probe makes
`fltk.fegen.pyrt.span.Span is fltk._native.Span`. After §2.1 the parser produces
`terminalsrc.Span`, so `isinstance(terminalsrc_span, fltk._native.Span)` is **False** → the
unparser does not recognize the span children → `unparse_*` returns `None` →
`plumbing.unparse_cst` raises `ValueError("Unparsing failed")`.

### Reproduction (native present in this environment)

```
parse_grammar('expr := value:/[0-9]+/;')  → generate_parser(capture_trivia=True)
parse_text(pr, '123')          → cst.span is fltk.fegen.pyrt.terminalsrc.Span   (correct, §2.1)
generate_unparser(...)         → unparse_cst(...) raises ValueError: Unparsing failed
```

On the clean base commit (before §2.1) the in-memory parser produced `fltk._native.Span` via the
probe, matching the unparser's probe-bound guard, so unparsing succeeded. The §2.1 change makes
parser and unparser disagree.

### Tests this breaks (all pass on clean HEAD, native present)

- `fltk/test_plumbing.py::TestUnparsing::test_unparse_simple_expression`
- `fltk/test_plumbing.py::TestUnparsing::test_unparse_with_auto_rule`
- `fltk/test_plumbing.py::TestIntegration::test_full_pipeline`
- `fltk/test_plumbing.py::TestIntegration::test_pipeline_with_formatting`

Because the failure is environment-conditional (only when `_native` is importable), it is exactly
the configuration this design targets. After the §2.5 regen of the committed parsers, the
committed unparsers (`fltk/unparse/{toy,toy_trivia,unparsefmt,unparsefmt_trivia}_parser.py`) would
be similarly broken in any native-present process, and the final increment's `make check` would
fail. **No planned increment in the design fixes the unparser**, so the design as written cannot
reach a green `make check` in a native-present environment.

## Why I did not just fix it

Making the unparser backend-agnostic requires changing the unparser **code generator**
(`gsm2unparser.py`) — out of §2.1's scope and out of the design's stated "only parser files
change" — and regenerating the committed unparser files. That is a public generated-surface change
and a design decision (which dual-backend pattern, where), not a trivial, obviously-correct
improvisation. Per the workflow I am surfacing it rather than improvising.

## Proposed resolution (for the designer)

Extend the design to make the unparser's span guards backend-agnostic, mirroring the existing CST
mutator pattern that §2.4 already blesses:

1. In `fltk/unparse/gsm2unparser.py`, replace the probe-bound `isinstance(child, span.Span)`
   guards (`:328`, `:1013-1014`, `:1116-1117`) with a dual-backend check that accepts
   `fltk.fegen.pyrt.terminalsrc.Span` **and** the lazily-resolved native span type — the same
   `(... , terminalsrc.Span)` + `_get_native_span_type()` shape the CST mutators emit
   (see `fltk/fegen/regex_cst.py:744-750`). `fltk.unparse.pyrt.{extract_span_text,
   count_span_newlines}` already handle both backends (`gsm2unparser.py:917`), so only the guards
   need widening.
2. Regenerate the committed unparser files and add the regen of `fltk/unparse/*_parser.py` to the
   §2.5 step; update §4 to note the affected unparse tests now pass under both backends.
3. Add a regression test: in a native-present process, round-trip a generated Python parser CST
   through its generated unparser and assert success (the case that fails today).

Alternative the designer might prefer: have the unparser/`pyrt` helpers accept any
`SpanProtocol`-shaped object structurally instead of isinstance against concrete classes.

I have **not committed** anything; the working tree carries the §2.1 edit to
`fltk/fegen/gsm2parser.py` and the new test `tests/test_python_parser_span_backend.py` (which
pass), plus this file. Awaiting a design decision before proceeding.

---

## Resolution (designer)

Gap confirmed and design extended. The unparser is now scoped under the same two-config principle:
a Python-generated unparser is a backend-agnostic CST consumer that recognizes span children of
either backend structurally (no `span.py` probe). The hybrid path is **not** reintroduced.

Decision (design §2.6, §5):
- **Runtime guards → dual-backend, centralized in `fltk/unparse/pyrt.py`.** Add
  `is_span(obj) -> bool` that checks `terminalsrc.Span` and, lazily via
  `sys.modules.get("fltk._native")`, the native `Span` — mirroring `gsm2tree.py`'s
  `_get_native_span_type()`. The three probe-bound `gsm2unparser.py` guards
  (`_extract_and_validate_nonsequence_child` span branch, `_count_newlines_in_trivia`,
  `_gen_trivia_processing`) call `fltk.unparse.pyrt.is_span(child)` instead of
  `isinstance(child, fltk.fegen.pyrt.span.Span)`. Centralized in `pyrt.py` (which the unparser
  already imports and which already homes the dual-backend `extract_span_text` /
  `count_span_newlines`) rather than emitted as per-module boilerplate.
- **Annotations → lazy/agnostic.** Prepend `from __future__ import annotations` and move
  `import fltk.fegen.pyrt.span` under `TYPE_CHECKING` in the generated unparser, so its eager
  `span: fltk.fegen.pyrt.span.Span` annotation no longer depends on the probe being imported
  elsewhere (it doesn't import `span` today and only resolves by ambient side effect, which §2.5
  removes). The agnostic annotation name is preserved — no downstream churn.
- Rejected: structural `SpanProtocol` duck-typing (diverges from the §2.4-blessed concrete
  dual-backend pattern) and per-module `_get_native_span_type()` boilerplate.

Correction to this clarification's "Proposed resolution" step 2: **there are no committed unparser
files.** `make gencode` generates none (it emits CST/protocol/parser + Rust artifacts only) and
`genunparser.py` writes to stdout; every unparser is generated in-memory by
`plumbing.generate_unparser`. The named `fltk/unparse/{toy,toy_trivia,unparsefmt,unparsefmt_trivia}_parser.py`
are the committed *parsers*, already in the §2.5 regen list, not unparsers. The unparser fix is a
code-generator + runtime-helper source change with **no committed-artifact diff and no new
`make gencode` target**; design §2.5 was corrected accordingly, and the "make check stays clean"
claim now rests on §2.6 restoring the unparse tests (it does not claim the unparser is untouched).

Sections changed in `design.md`: §1.2 (unparser as second probe symptom), §2 intro (unparser as
downstream sibling), §2.4 (unparser guard is a non-frozen runtime surface), §2.5 (no committed
unparser; corrected regen scope and make-check claim), **§2.6 (new — the full unparser fix)**, §3
(edge cases 7–9), §4 (new native-present round-trip regression + restored unparse tests), §5 (new
decision + rejected alternatives). A cleanup-editor pass was run.
