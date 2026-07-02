# Design: `unparser-none-path-diagnostics`

Requirements: `request.md` (this directory). Exploration: `exploration.md` (this directory).
Base commit: `c03a8012`. TODO entry: `TODO.md:43-45`. (Exploration was written
against `8fd5ecf`, where the same entry sat at `TODO.md:85-87`; all line
references in this design are against `c03a8012`.)

## Context / root cause

The generated Rust unparser has two silent-`None` paths (the two
`TODO(unparser-none-path-diagnostics)` comments in `fltk/unparse/gsm2unparser_rs.py`):

- **Site 1 — dropped comment.** `_gen_non_trivia_rule_processing`
  (`gsm2unparser_rs.py:1366`) emits `if let Some(trivia_result) =
  self.unparse__trivia(&trivia_node) { ... }` with no `else`. When
  `_has_preservable_trivia` has already confirmed the trivia node contains
  preservable comments but `unparse__trivia` returns `None`, the comment is
  silently deleted from formatted output. The Python backend has the same gap:
  `gsm2unparser.py:1321` creates `if_trivia_success` with no `orelse`.
- **Site 2 — nulled result.** `_gen_regex_term_body` (`gsm2unparser_rs.py:1091`)
  emits `let text = span.text()?;`. `Span::text()`
  (`crates/fltk-cst-core/src/span.rs:418`, via `text_str` at `:430`) returns
  `None` both for a sourceless span and for a source-bearing span with invalid
  codepoint offsets; either way the whole `unparse_*` call becomes `None` with
  no record of which span failed. The Python backend already diverges here: its
  regex path calls `pyrt.extract_span_text` (`gsm2unparser.py:1764`,
  `fltk/unparse/pyrt.py:34-50`), which **raises `ValueError` naming the span**
  for the source-bearing bad-offset case and falls back to slicing `terminals`
  only for genuinely sourceless spans.

Both paths are invariant violations for a CST produced by the matching parser
(the `fltkfmt` pipeline always attaches source), but they are reachable through
hand-constructed or mutated CSTs — and a formatter that silently deletes
comments or silently returns `None` is the worst way to surface a broken
invariant.

## Decision: policy = halt with a diagnostic

Per the requirements, site 2's direction is already set by the Python backend's
established raise-with-context behavior; site 1 needs one policy call applied to
both backends. The policy for both sites is **halt loudly**:

- **Python-generated unparser:** `raise ValueError(...)` with a message naming
  the rule and the failure (the existing `extract_span_text` convention,
  `pyrt.py:48-49`; `terminalsrc.Span.text_or_raise`,
  `fltk/fegen/pyrt/terminalsrc.py:73-87`, confirms raise-on-invalid is the
  established Python-side pattern).
- **Rust-generated unparser:** `panic!(...)` with an equivalent message.
  Panicking on invariant violation is idiomatic Rust, and PyO3 converts a panic
  into a Python `pyo3_runtime.PanicException`, so a Python caller of the Rust
  backend still gets a raised exception carrying the message.

Rejected alternatives:

- **Log-and-continue** — produces exactly the failure this TODO exists to
  prevent: formatted output with user comments deleted (site 1) or a bare
  `None` result (site 2), now with a log line few callers will see. A formatter
  must never emit output that silently lost data.
- **`debug_assert!`** — release builds (the only builds downstream consumers
  run via `maturin develop --release` / published wheels) would keep the silent
  behavior, and Python has no `debug_assert` analog, so the backends could not
  be kept in parity.
- **Changing generated signatures to `Result` / raising a typed error class** —
  `Option<UnparseResult>` / `-> str | None` are public API for out-of-tree
  consumers (CLAUDE.md); `None` is also the in-band "this alternative does not
  match" signal driving alternative backtracking. A `Result` rework is a
  breaking change and is not needed to add a diagnostic to an
  invariant-violation path.

Accepted asymmetries (called out, not accidental):

- Exception **types** differ across backends (`ValueError` vs
  `PanicException`, which subclasses `BaseException`). Parity is at the policy
  level — both halt with a message identifying the failure — not the exception
  type. Making the Rust backend raise `ValueError` would require `Result`
  plumbing through every generated method (rejected above).
- For a **sourceless** span at site 2, Python falls back to slicing
  `self.terminals` (a normal path for the Python backend, `pyrt.py:43-50`);
  the Rust CST carries no `terminals`, so the Rust backend panics for both
  `None` causes. The panic message includes the span's `Debug` form, which
  reports `has_source` (`span.rs:295-300`, source text deliberately elided), so
  the two causes are distinguishable from the message.

## Proposed changes

### 1. Rust site 2 — `_gen_regex_term_body` (`gsm2unparser_rs.py:1086-1091`)

Replace the `TODO` comment + `let text = span.text()?;` with a `let-else` that
panics, e.g. emitted code of the shape:

```rust
let Some(text) = span.text() else {
    panic!(
        "unparse_<rule>: cannot extract text for regex term <item-desc> at child position {}: span.text() returned None for {:?}",
        pos, span
    );
};
```

`<rule>` and `<item-desc>` (``label `<label>` `` when the item is labeled,
`(unlabeled)` otherwise) are baked in at generation time; `pos` and the span's
`Debug` form (start/end/has_source) are runtime values. Update the
`_gen_regex_term_body` docstring paragraph that currently documents the
`None`-propagation as "a deliberate failure mode".

### 2. Rust site 1 — `_gen_non_trivia_rule_processing` (`gsm2unparser_rs.py:1360-1377`)

Add an `else` arm to the inner `if let Some(trivia_result)`:

```rust
} else {
    panic!(
        "unparse_<rule>: trivia at child position {} has preservable comments but unparse__trivia returned None; refusing to silently drop comments",
        pos
    );
}
```

Remove the `TODO` comment; update the docstring bullet that documents the
missing-`else` as "a faithful port of Python's `if_trivia_success` having no
`orelse`".

### 3. Python site 1 — `_gen_trivia_processing` (`gsm2unparser.py:1321`)

Change `if_has_preservable.block.if_(trivia_result_var.load())` to pass
`orelse=True`, and in the `orelse` block emit an `expr_stmt`
(`fltk/iir/model.py:153`) calling a new `pyrt` helper:

```python
if_trivia_success.orelse -> fltk.unparse.pyrt.raise_preserved_trivia_failure(
    "<rule_name>", current_pos
)
```

using the same `iir.VarByName("fltk.unparse.pyrt", ...)` module-reference
pattern as `_make_is_span_check` (`gsm2unparser.py:388`) and the
`extract_span_text` call (`:1764`), with the rule name as an
`iir.LiteralString` (`fltk/iir/model.py:353`) and the position from
`current_pos_var` (already in scope at the site).

### 4. New runtime helper — `fltk/unparse/pyrt.py`

```python
def raise_preserved_trivia_failure(rule_name: str, pos: int) -> NoReturn:
    msg = (
        f"unparse rule {rule_name!r}: trivia at child position {pos} has "
        f"preservable comments but unparse__trivia returned None; "
        f"refusing to silently drop comments"
    )
    raise ValueError(msg)
```

(Message wording and content — rule name plus child position — aligned with the
Rust panic in change 2; no node/span contents in the message, matching the Rust
`Span` `Debug` convention of eliding source text.)

Python site 2 is **unchanged**: `extract_span_text` already implements the
policy.

### 5. Bookkeeping

- Delete the `unparser-none-path-diagnostics` entry from `TODO.md` and both
  in-code `TODO(...)` comments (the only two in the tree, per exploration).
- Regenerate the committed generated Rust unparsers and run `make fix`:
  `tests/rust_parser_fixture/src/unparser.rs`,
  `tests/rust_parser_fixture/src/unparser_default.rs`,
  `crates/fegen-rust/src/unparser.rs`. (No Python-generated unparser is
  committed in-tree; Python unparsers are generated at test/consumer time.)

## Edge cases / failure modes

- **Backtracking interaction.** `None` from an alternative drives "try the next
  alternative"; a panic/raise instead aborts dispatch. This is intentional and
  safe: whether a span's text extracts (site 2) or a trivia node's comments
  unparse (site 1) is a property of the CST child itself, not of which
  alternative is being tried, so no alternative could have produced correct
  output containing that child's text. The one theoretical exception — another
  alternative that matches the same `Span` child without reading its text
  (e.g. a literal term, which only validates the variant) — is already aborted
  by the Python backend's `ValueError` today for source-bearing spans; the Rust
  backend adopting the same behavior is the parity this change exists to
  create.
- **Quantified loops / optional items.** The same reasoning applies: the panic
  fires inside the item/`__inner` body before the `None` reaches the
  loop-termination or optional-skip logic. A broken span cannot be "skipped
  into" a correct result.
- **Site 2 inside `unparse__trivia`.** Comment rules' regex terms go through
  `_gen_regex_term_body`, so a broken comment span now panics inside
  `unparse__trivia` (site 2) rather than surfacing as a site-1 `None`. Both
  sites halt, so the outcome is consistent; site 1 still catches
  non-span-related trivia unparse failures (e.g. structurally invalid trivia
  children).
- **Happy path unchanged.** For every CST produced by the matching parser with
  source attached (the entire `fltkfmt` pipeline and all parity tests), neither
  new branch executes; generated output for valid inputs is byte-identical.
- **Out of scope.** The `span.text_str().map(...).unwrap_or(0)` newline counts
  (`gsm2unparser_rs.py:1263`, `:1513`) still treat an unreadable whitespace
  span as zero newlines. That degrades blank-line preservation, not data
  fidelity, and is not one of the two paths this TODO names; it is deliberately
  left as-is.

## Test plan

TDD: these tests are written first and fail against base.

1. **Generator-output tests** (`tests/test_rust_unparser_generator.py`): the
   generated source contains the site-2 `let ... else { panic!(...) }` (and no
   bare `span.text()?`) and the site-1 `else { panic!(...) }` arm.
2. **Rust site-2 runtime test** (Python-level, against the committed fixture
   unparser in `tests/rust_parser_fixture`): construct a fixture-grammar node
   whose regex child is a sourceless `fltk._native.Span(start, end)` (the
   two-arg Python constructor, `span.rs:604-606`, attaches no source), using
   the CST constructors/`append_*` mutators exactly as
   `tests/test_cst_mutators_parity.py` does; assert `unparse_*` raises
   `PanicException` (`pytest.raises(BaseException, match=...)`) whose message
   names the rule, position, and span.
3. **Rust site-1 runtime test** in `crates/fegen-rust` (which already hosts
   Rust unit tests, `src/native_parser_tests.rs`). The
   `tests/rust_parser_fixture` unparsers are generated with default trivia
   config, so their `_has_preservable_trivia` is a constant `false` and site 1
   is unreachable there; the fegen-rust unparser preserves
   `BlockComment`/`LineComment` (`crates/fegen-rust/src/unparser.rs`,
   `_has_preservable_trivia`). Test: `#[should_panic(expected = ...)]` —
   construct a `Trivia` node containing a `LineComment::new(span)` with no
   children appended (its required content child is missing, so
   `unparse_line_comment`, and therefore `unparse__trivia`, returns `None`),
   embed it as a separator child of an otherwise-valid node, and unparse.
4. **Python site-1 runtime test** (alongside `fltk/unparse/test_unparser.py`,
   which already generates Python unparsers with trivia configs at test time):
   same construction against a Python-generated unparser with
   `preserve_node_names` set; assert `ValueError` with the
   refusing-to-drop-comments message.
5. **Helper unit test** (new `fltk/unparse/test_pyrt.py`, alongside the other
   `fltk.unparse` tests): `raise_preserved_trivia_failure` raises `ValueError`
   naming the rule. (Not `tests/test_pyrt_errors.py` — despite the name, that
   file is scoped to `fltk.fegen.pyrt.errors` and cross-pinned with the Rust
   escape tests.)
6. **Regression**: existing parity suites (`test_fltkfmt_parity.py`,
   `test_rust_unparser_parity_fixture.py`) pass unchanged, demonstrating the
   happy path is untouched.

## Open questions

None. The one judgment call — halt vs. log vs. `debug_assert` — is resolved
above with rationale; the site-2 direction was already fixed by the Python
backend's existing behavior.
