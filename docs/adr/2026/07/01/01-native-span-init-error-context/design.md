# Design: `native-span-init-error-context` — generator drift fix + UnknownSpan init error context

Requirements: `request.md` (this directory). Exploration: `exploration.md` (this directory).

## Context / root cause

Two changes ride together (per `request.md`):

1. **Generator drift (the substance).** Committed `src/lib.rs` registers `LineColPos`
   (`src/lib.rs:6,13,16`) but `RustLibGenerator.generate()` in `fltk/fegen/gsm2lib_rs.py`
   does not know about it — the `register_span_types` block (lines 171-172, 193-196) emits
   only `Span` and `SourceText`. `LineColPos` exists and is exported: `src/span.rs:2`
   re-exports it from `fltk-cst-core` (`crates/fltk-cst-core/src/span.rs:167`). The next
   `make gencode` run (Makefile:275-276 writes `src/lib.rs` directly) would drop the
   `m.add_class::<LineColPos>()` registration, removing `LineColPos` from the module's
   attribute/import surface (`fltk._native.LineColPos`, declared in
   `fltk/_native/__init__.pyi:14`). Returned `LineColPos` instances from `Span.line_col`
   would still work — pyo3 creates `#[pyclass]` type objects lazily, independent of
   `add_class` — but `from fltk._native import LineColPos` would fail. The divergence
   itself is invisible until someone regenerates: `make check` (Makefile:39-77) has no
   gencode-drift step; drift detection today is "run `make gencode`, eyeball `git diff`"
   (Makefile:251-252) — which is exactly how this drift survived. Post-regen, the drop
   *would* be caught loudly — `make test` rebuilds `fltk._native` via
   `build-test-fixtures` → `build-native` (Makefile:94-97, 194-195) and
   `tests/test_rust_span.py:11` imports `LineColPos` at module scope — but only after a
   full native rebuild. The drift pin (§4) moves detection to a pure-Python unit test
   that needs no cargo and fires before regeneration is even attempted.

2. **The TODO (the rider).** `TODO(native-span-init-error-context)`
   (`fltk/fegen/gsm2lib_rs.py:199-201`, `TODO.md:21`): the emitted
   `Py::new(m.py(), Span::unknown())?` propagates a bare error (realistically
   `MemoryError` from CPython's allocator — see exploration for the pyo3 0.29 trace) with no
   indication the failure occurred during UnknownSpan sentinel creation. Wrap it with a
   structured message, following the established sibling pattern at
   `crates/fltk-cst-core/src/py_module.rs:155-159`.

## Proposed approach

All generator logic changes are in `RustLibGenerator.generate()`
(`fltk/fegen/gsm2lib_rs.py`). No structural changes to `LibSpec`, `Submodule`, the CLI
(`genparser.py gen-rust-lib`), or `rust.bzl` — the fixes apply unconditionally within the
existing `register_span_types` / `unknown_span_static` flags. Two one-line description
updates (a docstring and a CLI help string) ride along (§1).

### 1. Teach the generator about `LineColPos` (drift fix)

In the `register_span_types` paths:

- Emitted use line (currently line 172):
  `use span::{SourceText, Span};` → `use span::{LineColPos, SourceText, Span};`
- Emitted comment (line 194):
  `// Canonical Span/SourceText/UnknownSpan live at the top level.` →
  `// Canonical Span/SourceText/LineColPos/UnknownSpan live at the top level.`
- After `m.add_class::<SourceText>()?;` (line 196), emit `m.add_class::<LineColPos>()?;`
  — matching the committed `src/lib.rs` ordering (Span, SourceText, LineColPos).
- Two description surfaces that enumerate "Span/SourceText" get `LineColPos` added:
  the `LibSpec.register_span_types` docstring (`gsm2lib_rs.py:99`) and the
  `--register-span-types` CLI help text (`genparser.py:789`) — the help text is how an
  out-of-tree `gen-rust-lib` user learns their `mod span;` must export `LineColPos`.

This makes the generator match committed reality rather than the other way around;
`LineColPos` is public API of `fltk._native` already relied on by the span runtime.

### 2. Wrap the `Py::new` sentinel creation (the TODO)

Replace the emitted line (currently gsm2lib_rs.py:202)

```rust
    let unknown_span_obj = Py::new(m.py(), Span::unknown())?.into_any();
```

with (module name interpolated at generation time; `{e}` literal in the Rust source):

```rust
    let unknown_span_obj = Py::new(m.py(), Span::unknown())
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "<module_name> module init: failed to create UnknownSpan sentinel: {e}"
            ))
        })?
        .into_any();
```

Notes:

- Closure-block `map_err` shape and fully-qualified `pyo3::exceptions::PyRuntimeError`
  copy the sibling pattern (`py_module.rs:155-159`); no new `use` line needed — the
  emitted `use pyo3::prelude::*;` does not export `exceptions` (verified in exploration).
- The Python generator must escape braces so `{e}` survives into Rust
  (`f"...{{e}}..."` or plain-string appends); the module name substitutes at generation
  time, so for `fltk._native` the pinned message is
  `_native module init: failed to create UnknownSpan sentinel: {e}`.
- Delete the inline TODO comment (gsm2lib_rs.py:199-201) and the `TODO.md`
  `native-span-init-error-context` entry in the same change (TODO system: both halves
  stay in sync).

### 3. Regenerate `src/lib.rs`

Run the Makefile `gen-rust-lib` invocation (or full `make gencode`) → `make fix` → commit,
per the generated-code policy. Expected committed diff to `src/lib.rs`:

- `Py::new` line gains the `map_err` wrap (only functional change).
- The `UNKNOWN_SPAN` doc comment normalizes from the hand-edited
  `fltk._native.UnknownSpan` to the generator's `_native.UnknownSpan`
  (`{spec.module_name}.UnknownSpan`, gsm2lib_rs.py:182). This is a Rust comment with no
  API surface; we accept the normalization rather than adding a display-name knob to
  `LibSpec` for one comment. (Deliberate decision — see Edge cases.)
- `LineColPos` lines are already present and now survive regeneration.

`make fix` runs only ruff (Makefile:84-86); no rustfmt pass touches the emitted Rust, so
the emitted formatting is final and must compile clean under `cargo clippy` (it mirrors
already-clippy-clean code in `py_module.rs`).

### 4. Drift pin (prevent recurrence)

Add a regeneration-equality test to `fltk/fegen/test_gsm2lib_rs.py`: construct the
`LibSpec` matching the Makefile invocation
(`module_name="_native"`, `submodules=()`, `register_span_types=True`,
`unknown_span_static=True` — same spec as the existing `_span_only_spec()` helper) and
assert `RustLibGenerator(spec).generate()` equals the committed `src/lib.rs` byte-for-byte
(located via `Path(__file__).parents[2] / "src" / "lib.rs"`; `pytest.skip` if absent so the
test doesn't false-fail if the suite ever runs outside a repo checkout). This turns the
manual "eyeball `git diff` after gencode" convention into an automatic gate for the one
generated file that had already drifted. It runs in plain `make test` — no cargo, no regen
step needed.

The test duplicates the Makefile's flag choices by design: if the Makefile invocation
changes, the test must change with it, which is exactly the synchronization the drift bug
lacked.

## Edge cases / failure modes

- **Exception type changes from `MemoryError` to `RuntimeError`.** The realistic
  underlying failure (CPython allocator OOM) currently surfaces as `MemoryError`; after
  the wrap it surfaces as `RuntimeError` whose message embeds the original error text via
  `{e}`. This is import-time-only, OOM-only behavior; no out-of-tree consumer can
  meaningfully depend on the exception type of a failed `import fltk._native`, and the
  sibling submodule-registration path already made the same trade. Not a compatibility
  concern.
- **Double-wrap asymmetry.** The two following fallible calls in the block
  (`m.add("UnknownSpan", ...)?` and `UNKNOWN_SPAN.set(...).expect(...)`) stay as-is: the
  TODO scoped only the `Py::new` call, `m.add` failures are equally OOM-bound but were
  judged not worth wrapping originally, and `.expect` already carries a structured
  message.
- **Out-of-tree `--register-span-types` consumers.** Any consumer generating a lib.rs
  with `--register-span-types` must now have `LineColPos` exported from its `mod span;`.
  The documented pattern is re-exporting from `fltk-cst-core`
  (as `src/span.rs` does), which exports `LineColPos`
  (`crates/fltk-cst-core/src/span.rs:167`) — consumers tracking current fltk-cst-core get
  it for free. The only visible
  `gen-rust-lib` consumer besides fltk itself (`clockwork/dsl/BUILD.bazel:77-82`) does not
  use `register_span_types`. A consumer pinning an old fltk-cst-core *and* regenerating
  lib.rs with new fltk would get a Rust compile error (`LineColPos` unresolved) — loud,
  not silent, and inherent to mixing versions.
- **Comment normalization** (§3) restores the invariant that committed output is exactly
  what the generator produces — which is the point of this change.
- **Brace-escaping bug in the generator** (emitting a Python-interpolated `e` or a
  malformed `format!`) would fail to compile in Rust; the drift-pin test plus the
  message-text unit test catch it before cargo does.

## Test plan

Primarily in `fltk/fegen/test_gsm2lib_rs.py` (pure string-output unit tests, no cargo),
plus one CLI-level test in `fltk/fegen/test_genparser.py`:

New:
- `test_span_only_registers_line_col_pos` — span-only output contains
  `m.add_class::<LineColPos>()`.
- `test_span_only_wraps_unknown_span_creation_error` — span-only output contains
  `pyo3::exceptions::PyRuntimeError::new_err` and the exact pinned message
  `_native module init: failed to create UnknownSpan sentinel: {e}`, and does **not**
  contain the old unwrapped form `Span::unknown())?.into_any()`.
- `test_committed_lib_rs_matches_generator` — the drift pin (§4 above): generator output
  for the Makefile's spec equals committed `src/lib.rs` exactly.

Updated:
- `test_span_only_contains_span_module` — use line becomes
  `use span::{LineColPos, SourceText, Span};`.
- `test_span_types_without_unknown_span_emits_span_module_and_classes` — same use-line
  update, plus `m.add_class::<LineColPos>()` (the drift fix applies to
  `register_span_types` generally, not just the span-only combination).
- `test_standard_output_no_span_types` — add `assert "LineColPos" not in src`.
- `test_gen_rust_lib_span_only_output` (`fltk/fegen/test_genparser.py:1565`) — its
  assertion `use span::{SourceText, Span};` fails after the §1 drift fix; update to the
  new use line and add `m.add_class::<LineColPos>()`. Optionally add
  `assert "LineColPos" not in src` to `test_gen_rust_lib_standard_output` to mirror the
  `test_standard_output_no_span_types` update.

Remaining tests (`test_span_only_unknown_span_static`,
`test_span_only_adds_unknown_span_attribute`, once-init message, etc.) keep passing —
they assert substrings the change preserves.

TDD order: write the new/updated tests first (failing), change the generator, regenerate
`src/lib.rs`, confirm the drift-pin test goes green, then `make check`.

## Open questions

None. The one judgment call — accepting the `fltk._native.` → `_native.` comment
normalization instead of adding a `LibSpec` knob — is decided above (§3) and is trivially
reversible later if anyone cares about the comment text.
