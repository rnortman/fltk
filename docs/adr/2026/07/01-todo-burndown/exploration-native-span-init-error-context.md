# Exploration: TODO(native-span-init-error-context)

## TODO text, ground truth

`TODO.md:21`:

```
## `native-span-init-error-context`

When `Py::new(m.py(), Span::unknown())` fails during `fltk._native` module init, the Python import raises a generic pyo3 `RuntimeError` with no indication the failure was in UnknownSpan sentinel creation. Wrap with a structured message so on-call can distinguish this from submodule registration failures. Location: `fltk/fegen/gsm2lib_rs.py` (`RustLibGenerator.generate()`, body for `unknown_span_static`).
```

Matches the teammate-message quote verbatim.

Inline comment at `fltk/fegen/gsm2lib_rs.py:201-203`, inside `RustLibGenerator.generate()`, in the `if spec.unknown_span_static:` block (`generate()` spans lines 152-222; the block is lines 200-208):

```python
        if spec.unknown_span_static:
            # TODO(native-span-init-error-context): Py::new failure here surfaces as a generic
            # pyo3 RuntimeError with no indication that it occurred during UnknownSpan sentinel
            # creation.  Wrap with a structured message for on-call clarity.
            body.append("    let unknown_span_obj = Py::new(m.py(), Span::unknown())?.into_any();")
            body.append('    m.add("UnknownSpan", unknown_span_obj.clone_ref(m.py()))?;')
            body.append("    UNKNOWN_SPAN")
            body.append("        .set(m.py(), unknown_span_obj)")
            body.append('        .expect("UNKNOWN_SPAN already set; module initialized twice");')
```

Only one occurrence of the slug in code (`grep -rn "native-span-init-error-context"` over the whole tree, excluding docs/ADR prose): `fltk/fegen/gsm2lib_rs.py:201`. No stale worktree copy of `gsm2lib_rs.py` exists under `.claude/worktrees/agent-ab295be24eef6e7ce/` (that worktree has no `fltk/fegen/gsm2lib_rs.py` at all). No other `TODO(native-span-init-error-context)` code comment exists anywhere in the fltk tree or in the accessible `/home/rnortman/tps/clockwork` checkout.

The TODO's own comment text is the Python generator's `#`-comment, sitting *above* the `body.append(...)` calls — it is not itself emitted into the generated Rust source (confirmed by generating `src/lib.rs` fresh and diffing; see below).

## Does the code match the TODO's description?

Yes, structurally: the generator code is exactly as described — `RustLibGenerator.generate()`, in the `unknown_span_static` body block, emits an un-wrapped `Py::new(m.py(), Span::unknown())?` with no `.map_err`, immediately above the two other fallible calls in that block (`m.add("UnknownSpan", ...)` and `UNKNOWN_SPAN.set(...)`, the latter using `.expect(...)` which panics rather than returns `Err`).

However, the TODO's characterization of the *failure mode* is not fully accurate against pyo3 0.29.0 mechanics (`Cargo.lock:198` pins `pyo3 = "0.29.0"`; source consulted at `~/.cargo/registry/src/index.crates.io-*/pyo3-0.29.0/`):

- `Py::new(py, value)` (`pyo3-0.29.0/src/instance.rs:1530`) delegates to `Bound::new` (`instance.rs:98`) which delegates to `PyClassInitializer::create_class_object` (`pyclass_init.rs:135`).
- Because `Span` has no `#[pyclass(extends = ...)]` base, the initializer is `PyNativeTypeInitializer<PyAny>`, whose `into_new_object` (`internal/pyclass_init.rs:33-64`) calls the base type's `tp_new` slot (CPython's generic object allocator) and, only if that C call returns a null pointer, does `Err(PyErr::fetch(py))` (`internal/pyclass_init.rs:56-58`) — i.e. it propagates *whatever exception CPython's allocator actually set* (in practice `MemoryError` on allocation failure), not a "generic pyo3 `RuntimeError`."
- Tracing further up: `#[pymodule]` init errors are surfaced via `impl_/trampoline.rs::module_exec` → `trampoline()` → `panic_result_into_callback_output`, which restores whatever `PyErr` the body produced (`.restore(py)`) without rewrapping it as `RuntimeError`. There is no pyo3-side fallback that coerces arbitrary init errors into `RuntimeError`.
- So the realistic failure is CPython object allocation failure (OOM / corrupted heap) surfacing as `MemoryError` (or whatever exception `tp_new` set), not literally `RuntimeError`. The prior review's own judge-verdict already used the same "generic pyo3 RuntimeError" phrasing (see History below) — this is a repeated, not independently re-derived, characterization.
- The substantive part of the claim — "no indication the failure was in UnknownSpan sentinel creation" vs. submodule registration — is accurate regardless of exact exception type: the raw propagated error carries no context about which init step produced it.

## Is the failure reachable / worth fixing?

`Span::unknown()` itself (`crates/fltk-cst-core/src/span.rs:331-337`) is infallible — it just constructs a plain struct (`start: -1, end: -1, source: None`). The only way `Py::new(...)` can fail here is the underlying CPython allocation path failing, which requires OOM or a corrupted interpreter heap. This matches the original review's own assessment (`docs/adr/2026/06/14-rust-native-lib-shape/judge-verdict-deep.md:8`): "Reviewer's own consequence concedes 'OOM, or broken Python heap' — extremely rare, import-time only."

## Is the fix feasible in the generated-code context?

Yes, mechanically, and a near-identical pattern already exists elsewhere in the Rust workspace for the sibling TODO `native-submodule-error-context` (`crates/fltk-cst-core/src/py_module.rs:159-163`, e.g. `register(&sub).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("register_submodule: register fn for submodule {qualified_name:?} failed: {e}")))?;`). Applying the same shape here would change the generator's emitted line from:

```
    let unknown_span_obj = Py::new(m.py(), Span::unknown())?.into_any();
```

to something like:

```
    let unknown_span_obj = Py::new(m.py(), Span::unknown())
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("failed to create UnknownSpan sentinel: {e}")))?
        .into_any();
```

`pyo3::exceptions::PyRuntimeError` can be referenced by its fully-qualified path (as the sibling fix does) without adding a new `use` line to the generator's prologue (`generate()` currently emits `use pyo3::prelude::*;` at line 160, which does not re-export `pyo3::exceptions::*`, confirmed empty grep for `PyRuntimeError`/`exceptions` in `pyo3-0.29.0/src/prelude.rs`).

## Where does the generated output land, and what regen workflow applies?

`gsm2lib_rs.RustLibGenerator` is invoked by the `gen-rust-lib` Typer subcommand (`fltk/fegen/genparser.py:761-842`). For `fltk._native` specifically, `Makefile:275-276` (the `gencode` target) runs:

```
uv run python -m fltk.fegen.genparser gen-rust-lib src/lib.rs \
    --module-name _native --register-span-types --unknown-span-static --no-cst --no-parser
```

writing directly to the committed `src/lib.rs` at the repo root. Per `CLAUDE.md`'s generated-code policy, the intended workflow for any change to `gsm2lib_rs.py` is: run the generator (`make gencode`, or the specific `gen-rust-lib` invocation above) → `make fix` → commit — `make check` is the precommit gate that verifies committed generated code is clean/current.

**Committed `src/lib.rs` is currently drifted from what the generator produces.** Regenerating it fresh into a scratch file and diffing against the committed version shows three differences, all related to a `LineColPos` class that the committed file registers but the current generator does not know about:

```
< use span::{SourceText, Span};
---
> use span::{LineColPos, SourceText, Span};
...
< // Canonical Span/SourceText/UnknownSpan live at the top level.
---
> // Canonical Span/SourceText/LineColPos/UnknownSpan live at the top level.
...
>     m.add_class::<LineColPos>()?;
```

(A fourth, cosmetic difference — `` `_native.UnknownSpan` `` vs. `` `fltk._native.UnknownSpan` `` in a comment — comes from the `--module-name` value passed, `_native`, not matching the fully-qualified name used in the hand-edited comment.) This drift is pre-existing and orthogonal to the `native-span-init-error-context` TODO — it means `LineColPos` registration was added to `src/lib.rs` by hand (or by a generator version that has since regressed) without updating `gsm2lib_rs.py`'s `register_span_types` block, and `src/lib.rs` has not been regenerated since. Any fix to the `unknown_span_static` block would regenerate `src/lib.rs` and — unless the generator is also updated for `LineColPos` — would silently drop the `LineColPos` class registration from the committed file, which would be a regression independent of this TODO's scope. This is a fact worth surfacing to whoever picks up the fix; it is not evidence about the TODO's own validity.

## History: when was the TODO added, and by whom

- The TODO (both the `TODO.md` entry and the inline comment) was added in commit `c018206` ("rust-native-lib: codegen lib.rs boilerplate; refactor _native to runtime-only", 2026-06-14) — `git log -p -- fltk/fegen/gsm2lib_rs.py` shows the comment introduced as new code (`+ # TODO(native-span-init-error-context): ...`) in that commit, alongside the `unknown_span_static`/`register_span_types` machinery itself. This is the same commit that introduced the sibling `native-submodule-error-context` TODO in `crates/fltk-cst-core/src/py_module.rs`.
- Unlike the sibling TODO, this one was added *together with* the code it describes (the `Py::new(...)?` call is new in that commit, not pre-existing), so there is no "code already fixed, TODO now stale" gap here — the un-wrapped `?` and the TODO comment have coexisted since introduction.
- Per-file ADR record: `docs/adr/2026/06/14-rust-native-lib-shape/dispositions-deep.md:1-8` records the disposition explicitly: "Disposition: TODO(native-span-init-error-context)... Rationale: The reviewer's option (b) — document rather than fix — is appropriate here; the failure is OOM-level and extremely rare. A full structured wrap (option a) can be done later without blocking this change." The corresponding judge verdict (`judge-verdict-deep.md:8`) rated it "Q1 (worth doing): marginal-yes... Q2: no [design input required]... TODO acceptable" on the basis that the fix is mechanical (~3 lines) but not a one-liner because it is generated boilerplate requiring a pinning test, and the failure is OOM-only.
- `docs/adr/2026/06/14-rust-native-lib-shape/audit-native-path-removal.md:80-86` separately confirms this TODO is one of four live TODOs in the `gsm2lib_rs.py` area and classifies it (along with the other three) as "independent polish items surfaced during review," not residue of any prior bespoke/removed code path.
- `docs/adr/2026/06/14-rust-backend-assessment/u7-completeness-cruft.md:109` lists this slug alongside `submodule-register-fn-convention` and `rust-ident-dedup` in a burndown-tracking context (not independently re-examined there).

## Test coverage today

`fltk/fegen/test_gsm2lib_rs.py:241-252` (`test_span_only_unknown_span_static`) asserts `"UNKNOWN_SPAN" in src` and `"UNKNOWN_SPAN already set; module initialized twice" in src`, but does not pin the exact text of the `Py::new(...)?` line. No existing test would break if that line were changed to add `.map_err(...)`. A fix would need a new/extended test asserting the wrapped-error text is present, per the original judge verdict's own expectation ("a test added to pin the emitted text").
