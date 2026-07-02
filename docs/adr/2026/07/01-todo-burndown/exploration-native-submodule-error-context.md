# Exploration: TODO(native-submodule-error-context)

## TODO text, ground truth

`TODO.md:17-19`:

```
## `native-submodule-error-context`

`register_submodule` propagates errors from `register_classes` via `?` with no added context naming which submodule failed. A future improvement: annotate the error with the submodule name before propagating, so an `ImportError` at module import time names `"cst"` or `"parser"` as the culprit. Location: `crates/fltk-cst-core/src/py_module.rs` (`register_submodule` definition, line ~87).
```

Matches the teammate-message quote verbatim.

Inline comment at `crates/fltk-cst-core/src/py_module.rs:86-89`, immediately above the `register_submodule` function (function itself starts at line 91):

```rust
// TODO(native-submodule-error-context): register_submodule propagates errors from
// register_classes via `?` with no added context naming which submodule failed.
// A future improvement: annotate the error with the submodule name before propagating,
// so an ImportError at module initialization names "cst" or "parser" as the culprit.
```

Only one occurrence of the slug in code (`grep -rn "native-submodule-error-context"` over the whole tree, excluding docs/ADR prose): `crates/fltk-cst-core/src/py_module.rs:86`. No other `TODO(native-submodule-error-context)` code comment exists anywhere in the fltk tree or in the accessible `/home/rnortman/tps/clockwork` checkout.

## Does the code match the TODO's description?

No — for the specific call path the TODO names, the code already has the described fix.

`register_submodule` (`py_module.rs:91-109`) calls `register_submodule_impl` (`py_module.rs:147-185`). Every fallible call in that function that touches `register_classes` or the submodule pipeline already carries a `.map_err` that names the submodule:

- `py_module.rs:159-163` — `register(&sub).map_err(|e| PyRuntimeError::new_err(format!("register_submodule: register fn for submodule {qualified_name:?} failed: {e}")))?;` — `register` here is the caller-supplied closure that *is* `register_classes` (see call sites below). `qualified_name` is `"{parent_name}.{name}"`, e.g. `"fltk._native.cst"`.
- `py_module.rs:164-168` — same pattern for `parent.add_submodule(&sub)`.
- `py_module.rs:178-182` — same pattern for the `sys.modules.set_item` call.
- `py_module.rs:99-106` (in `register_submodule` itself) — `parent.name()` failure is wrapped with `"register_submodule({name:?}): failed to get parent module name: {e}"`, also naming the submodule being registered.

So the exact propagation the TODO calls out — errors from `register_classes` via `register(&sub)` — is not a bare `?`; it already carries submodule-identifying context via `qualified_name` in the wrapped `PyRuntimeError` message.

Call sites confirming `register` is literally the codegenned `register_classes` function, e.g.:
- `crates/fegen-rust/src/lib.rs:23-25`: `register_submodule(m, "cst", cst::register_classes)?;` (and `parser`, `unparser`)
- `tests/rust_parser_fixture/src/lib.rs:17-22`: six such calls with distinct submodule names, each passing `<mod>::register_classes`
- Generator template: `fltk/fegen/gsm2lib_rs.py:214` — `register_submodule(m, "{sub.submodule_name}", {sub.mod_name}::{sub.register_fn})?;` (`register_fn` defaults to `"register_classes"`, `gsm2lib_rs.py:73`)

### What actually lacks context

Three bare `?` calls exist in `register_submodule_impl` with no `.map_err` wrapping, none of which the TODO's text mentions:
- `py_module.rs:169` — `sub.setattr("__name__", &qualified_name)?;`
- `py_module.rs:175` — `py.import("sys")?`
- `py_module.rs:176` — `.getattr("modules")?`

These would surface as generic pyo3 errors with no indication of which submodule or operation failed. This is a narrower, different gap than the one the TODO describes (it's not on the `register_classes` path at all).

## History: when was context added vs. when was the TODO written

- `crates/fltk-cst-core/src/py_module.rs` was created in commit `cf3c54c` ("rust-bindings-module-split: per-rule submodules for generated CST bindings", 2026-06-11). That commit's version of `register_submodule_impl` already contains the `.map_err` wrapping for `register(&sub)`, `add_submodule`, and the `sys.modules` insertion (verified via `git show cf3c54c -- crates/fltk-cst-core/src/py_module.rs`).
- The inline `TODO(native-submodule-error-context)` comment was added three days later in commit `c0182064e2f6906fb5cf836b025980beca44cab3` ("rust-native-lib: codegen lib.rs boilerplate; refactor _native to runtime-only", 2026-06-14). The diff for `py_module.rs` in that commit is a pure 4-line comment insertion above the already-existing, already-`map_err`-wrapped `register_submodule` — no code in `register_submodule`/`register_submodule_impl` changed in that commit.
- The matching `TODO.md` entry was added in the same commit `c0182064` (confirmed by walking `git log -p -- TODO.md` and checking which commit introduces the `## \`native-submodule-error-context\`` heading). That commit's message lists its own deferred follow-ups explicitly ("Deferred follow-ups (see TODO.md): native-span-init-error-context, bazel-lib-rs-no-cst, submodule-register-fn-convention, rust-ident-dedup") and does not name `native-submodule-error-context` — it was added to `TODO.md` without being called out in the commit message, alongside the other three that are named.

So both halves of the TODO (code comment + `TODO.md` entry) were authored together on 2026-06-14, describing a "bare `?`, no context" state that the code had already moved away from on 2026-06-11, three days earlier, for the exact call (`register(&sub)`) the TODO names.

## ADR/design-doc cross-references (context, not verified against code)

Multiple ADR documents under `docs/adr/2026/06/13-rust-bazel-packaging/` and `docs/adr/2026/06/14-codegen-rust-lib-boilerplate/` discuss this TODO as a "bookkeeping" item (inline comment present without a `TODO.md` entry, needing relocation/pairing) rather than examining whether its technical claim is still accurate:

- `docs/adr/2026/06/13-rust-bazel-packaging/dispositions-final.md:24-25` claims: "Added a `TODO(native-submodule-error-context)` comment at the `register_submodule` call sites in `clockwork/dsl/clockwork_native_lib.rs` (Clockwork repo)." No `clockwork_native_lib.rs` file exists anywhere under the accessible `/home/rnortman/tps/clockwork` checkout (`find` and `grep -rn "native-submodule-error-context"` both come up empty there); this claimed action is not present in the accessible clockwork working directory.
- `docs/adr/2026/06/14-codegen-rust-lib-boilerplate/design.md:429-435`, `judge-verdict-design.md:39-42`, and `judge-verdict-deep.md:32-33` treat the finding purely as a TODO-convention compliance question (comment present, `TODO.md` entry missing → add the entry or delete the comment) and explicitly state the underlying technical content is out of scope for that review ("No change needed; noting here for completeness" — `notes-deep-error-handling-reviewer.md:74`). None of these documents re-derive or re-check the "bare `?`, no context" claim against the code as it stood.

## Feasibility of the fix as literally scoped (if the gap still existed)

Pattern is already established in the same file/function for the sibling calls: wrap the fallible call's `Result` in `.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("...{qualified_name}...: {e}")))?`. `PyResult<T>` = `Result<T, pyo3::PyErr>`, and `PyErr: Display`, so `{e}` interpolates the original error text into the new message; there is no error-chaining/`source()` mechanism used here, only string interpolation into a fresh `PyRuntimeError`. No blockers to applying this pattern to the three currently-bare `?` sites (`sub.setattr`, `py.import("sys")`, `.getattr("modules")`) were found — same crate, same imports (`pyo3::exceptions::PyRuntimeError`, `format!`), same `qualified_name` variable already in scope at each site.

## Other observations

- A stale/divergent worktree copy of this file exists at `.claude/worktrees/agent-ab295be24eef6e7ce/crates/fltk-cst-core/src/py_module.rs`; diffed against `HEAD:crates/fltk-cst-core/src/py_module.rs`, it is identical except missing the four-line TODO comment block (lines 86-89). Not part of the main tree; noted only because it surfaced during the search for all occurrences of the slug.
