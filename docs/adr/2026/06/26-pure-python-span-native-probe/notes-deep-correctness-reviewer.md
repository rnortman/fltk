# Deep correctness review — pure-python-span-native-probe (SpanProtocol delta)

Commit reviewed: `ab38ec777920f4761f124e56b3cedc995acee46a` (base `49e9701`)
Scope: code under `fltk/`, `src/`, `tests/` (ADR docs treated as design artifacts).

## Verdict

No findings.

Logic, control flow, and data flow of the changed code are correct. Every key invariant
named in the review brief was checked against the running system, not just read.

## What was traced / verified

- **Registry split is collision-free.** `context._register_builtin_types` repoints the shared
  `cname="Span"` entry to `span_protocol.SpanProtocol` and `cname="SourceText"` to
  `terminalsrc.SourceText`; `gsm2parser.__init__` registers a *distinct* key
  `cname="TerminalSpanConcrete"` → `terminalsrc.Span` and re-registers `SourceText`→`terminalsrc`
  (idempotent with context). No two `TypeInfo`s share a key with differing values, so
  `register_type`'s `ValueError("Conflicting type registration")` cannot fire. Parser annotations
  use the concrete key only; CST/protocol/unparser annotations use the shared `SpanProtocol` key.
  No path references the now-`SpanProtocol` `cname="Span"` from inside the parser.

- **Construction retarget is registry-independent.** `_make_span_expr` emits a fixed
  `fltk.fegen.pyrt.terminalsrc.Span.with_source(...)`; `_source_text` init emits a module-qualified
  `MethodAccess("SourceText", VarByName("fltk.fegen.pyrt.terminalsrc")).call(...)`. Committed
  `fltk_parser.py` confirms: returns `ApplyResult[int, terminalsrc.Span]`, constructs
  `terminalsrc.Span`/`terminalsrc.SourceText`, no `typing.cast`, no `span`/`_native` import.

- **`unparse/pyrt.is_span` dual-backend guard.** `isinstance(obj, terminalsrc.Span)` then a lazy
  `getattr(sys.modules.get("fltk._native"), "Span", None)` branch (defensive against the
  namespace-package-without-`Span` case). No false negative/positive for either backend; never
  imports `span.py` nor fires the probe. `gsm2unparser` branch `expected_type is self.span_type`
  correctly routes only Literal/Regex span children to the helper (identity holds —
  `_get_node_type_for_nonsequence_term` returns the same `self.span_type` object), keeping
  Identifier children on concrete `IsInstance`.

- **Empirical end-to-end checks (native built and importable):**
  - Importing committed `fltk_parser` + `fltk_cst` loads neither `fltk.fegen.pyrt.span` nor
    `span_protocol` (`sys.modules` inspected).
  - A generated pure-Python parser yields `node.span` and span children of type
    `fltk.fegen.pyrt.terminalsrc.Span` (the original bug: it used to yield `fltk._native.Span`).
  - With `fltk._native` forced into `sys.modules`, parse→unparse→render round-trips successfully
    (`is_span` recognizes the `terminalsrc.Span`) — the §2.1-exposed gap that previously raised
    `ValueError("Unparsing failed")`.

- **pyright stability (invariant #2).** Full-repo `pyright`: 0 errors. Generated pipeline triad
  (`fltk_parser.py`, `fltk_cst.py`, `fltk_cst_protocol.py`) re-checked with
  `fltk/_native/__init__.pyi` removed: still 0 errors and stable — the generated pipeline names
  neither `fltk._native` nor the `span` selector. (`span.py` / `span_protocol.AnySpan` remain
  stub-sensitive, but that is the explicitly-surfaced D8 open question, out of the pipeline, and
  pre-existing — not a regression.)

- **SpanProtocol conformance (invariant #4).** `Self`-typed `merge`/`intersect` + `kind` make
  `terminalsrc.Span` statically assignable to `SpanProtocol` (pyright-checked module-level slots in
  `test_span_protocol_assignability.py`); both backends conform at runtime via `runtime_checkable`
  `isinstance`. Rust `.pyi` span field/children → `SpanProtocol`, matching the protocol's invariant
  slot (swap-compatible); no dangling `terminalsrc`/`_native` references remain in `cst.pyi`.

- **Hybrid removal is clean.** No live references to `rust_cst_module` / `rust_fegen_cst_module` /
  `_load_rust_cst_classes` / `RustBackendUnavailableError` / `_load_fegen_grammar` /
  `_fegen_grammar_cache` remain; `importlib` import dropped.

- **No regen drift.** Re-ran the Python half of `make gencode` + `make fix`; `git status` clean.
  `ruff check` clean. Full suite: 2169 passed, 1 skipped.
