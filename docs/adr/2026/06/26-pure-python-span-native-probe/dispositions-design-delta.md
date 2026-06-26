# Dispositions — delta design review (round 1)

Design under review: `./design-delta-python-rust-isolation.md`
Reviewer notes: `./notes-design-delta-design-reviewer.md`
Base design (reference only, not edited): `./design.md`

---

design-1:
- Disposition: Fixed
- Action: Corrected the false "verified by pyright" claim in D3.1 (the `merge`/`intersect`
  `Self` block, design-delta §D3.1). The sentence now states that only **`terminalsrc.Span`**
  values are statically assignable to a `SpanProtocol` slot; native `fltk._native.Span` is **not**
  statically assignable because `line_col()`/`line_col_or_raise()` return the native `LineColPos`
  (nominal-distinct from the protocol's `terminalsrc.LineColPos`, `span_protocol.py:6,67-79` vs
  `_native/__init__.pyi:67-68`), which the `Self` retyping does not close; native conforms by
  `.pyi` declaration + runtime `isinstance` per D5.2, with the residual gap tracked as
  `TODO(spanprotocol-native-linecol)`. Also softened the lead-in ("satisfied by both backends *at
  runtime* (and statically by `terminalsrc.Span`)") so the section no longer implies static native
  conformance. This removes the internal contradiction with D5.2/D4.
- Severity assessment: Medium. The build is unaffected (the Rust `.pyi` only *declares*
  `span: SpanProtocol` and no native value is assigned into a `SpanProtocol` slot inside pyright
  scope; D6's assignability test already pins only the `terminalsrc` side). But left uncorrected,
  the "fltk._native.Span values are assignable" prose would mislead an implementer into writing a
  native-side static assignability assertion that cannot pass, and it openly contradicted D5.2.
- Verification: confirmed against `span_protocol.py:6,67-79`, `_native/__init__.pyi:67-68`,
  `terminalsrc` `LineColPos`. The two `LineColPos` classes are distinct nominal types;
  method-return covariance fails, so the reviewer's pyright result is correct.

design-2:
- Disposition: Fixed
- Action: Amended D3.2's `SourceText` bullet (design-delta §D3.2) to call out **two**
  registration sites for the `cname="SourceText"` key — `context.py:125-132` and the re-registration
  at `gsm2parser.py:78-84` (`ParserGenerator.__init__`) — and to require both move to `terminalsrc`
  together (or delete the `gsm2parser.py:78-84` re-registration, since `context` now supplies the
  entry). Documented that repointing only `context.py` triggers
  `ValueError("Conflicting type registration")` (`context.py:19-25`) because `genparser.py:83` runs
  `create_default_context()` (terminalsrc) before constructing `ParserGenerator` (which would
  re-register span), crashing all Python-parser generation before the D6 regen can run.
- Severity assessment: High (hard blocker). A faithful literal implementation of the original
  D3.2 — repoint context only — raises `ValueError` at `ParserGenerator.__init__`, so `make gencode`
  (the D6 regen) cannot run and no Python parser can be generated.
- Verification: confirmed `gsm2parser.py:78-84` re-registers `self.SourceTextType`
  (`iir.Type.make(cname="SourceText")`, identical `TypeKey`) to `module=("fltk","fegen","pyrt","span")`;
  `context.py:19-25` raises on a differing `TypeInfo` for an existing key; `genparser.py:83`
  constructs the context (and its builtin SourceText registration) before `ParserGenerator`
  (`genparser.py:93`). Order and conflict reproduced by reading.

design-3:
- Disposition: Fixed
- Action: Added a D6 bullet (design-delta §D6, "Pre-existing union-surface tests must be
  retargeted") enumerating the prior-work suites that pin the old `terminalsrc.Span |
  fltk._native.Span` surface and giving each an explicit disposition contract:
  `tests/test_gsm2tree_rs.py` `test_imports_span_module` (`:1153`), `test_imports_fltk_native`
  (`:1156`), `test_span_annotation_exact_protocol_union` (`:1222`) → **retarget** to assert the
  `.pyi` imports `span_protocol`, imports neither `fltk._native` nor `span`, and annotates
  `span: …SpanProtocol`; and the `fltk/fegen/test_cst_protocol.py:487-614` "§4 item 8 — Protocol
  span additive-widening" suite (in-`make check`-pyright-scope, under `fltk/`) → **rework** into a
  `SpanProtocol`-conformance suite **or retire**, implementer's stated choice.
- Severity assessment: Medium. Without this, an implementer hits pre-existing test failures the
  design never named, with no retarget/delete guidance — risking either getting stuck or silently
  dropping the cross-backend span-surface coverage.
- Verification: confirmed `tests/test_gsm2tree_rs.py:1153,1156,1222` assert exactly those strings;
  confirmed `fltk/fegen/test_cst_protocol.py:487-614` is a dedicated union-widening suite asserting a
  `fltk._native.Span` value satisfies the protocol span field (e.g. `:536`); confirmed pyright scope
  `include = ["fltk", "*.py"]` (`pyproject.toml:50`) — so `fltk/fegen/test_cst_protocol.py` is gated,
  `tests/test_gsm2tree_rs.py` is pytest-only.

design-4:
- Disposition: Fixed
- Action: Enriched D8.1 (design-delta §D8) to make the repo-wide-vs-pipeline scope of R2 explicit,
  without resolving the open question. The question now distinguishes the pipeline-scoped reading of
  the directive (satisfied under keep-both) from R2's broader clause ("Pyright should produce the
  same results when analyzing Python code whether the Rust backend is importable or not"), which is
  **not** met repo-wide under keep-both because `span.py:8-14` and `span_protocol.py:89-94` (`AnySpan`)
  remain stub-sensitive inside `make check` pyright scope (`fltk/`). The default (keep both) and the
  user-judgment nature of the question are preserved; the delta now surfaces the tradeoff rather than
  deciding it.
- Severity assessment: Low/informational. The reviewer flagged this as "input to D8.1, not a
  defect"; the delta's reasoning is sound and D5.1 (pipeline stub-stability) is verified TRUE. The
  edit ensures the user's D8.1 decision is made with the scope of R2 explicit. The open question
  remains open per instructions (no finding resolves it).
- Verification: confirmed `span.py:8-14` (try/except selector) and `span_protocol.py:89-94`
  (`AnySpan = _pymod.Span | _RustSpan` ↔ `_pymod.Span`) are stub-sensitive and live under `fltk/`,
  thus in pyright scope; D5.1's pipeline-only stub-stability holds because the generated modules name
  neither `fltk._native` nor `span`.
