# Judge verdict — prepass (slop + scope)

Phase: prepass. fltk base 7200d9c..HEAD 7a7ca4d; clockwork base 6ede250..HEAD ea34388. Round 1.
Notes: 2 reviewer files (slop: 3 findings; scope: 0 findings). Dispositions cover slop-1..3 + scope.

(Doc-phase header form retained for the design context, but the dispositions resolve concrete code findings against the HEAD that contains the slop-fix commit `7a7ca4d`, so the walk verifies code, not the design doc.)

## Other findings walk

### slop-1 — Fixed
Claim: `TODO.md` carried a struck-through `fltk-pyo3-cdylib-smoke` entry with a "(Closed)" note; consequence is noise in the master TODO list, conflicting with the project convention that TODOs track concrete remaining work, not completed work.
Disposition: Fixed — section deleted.
Evidence: `git show 7a7ca4d` removes the entire `## fltk-pyo3-cdylib-smoke` block (6 lines) from `TODO.md`. Current `TODO.md` (read in full) has no such section; the surrounding `bazel-rules-rust` / `verify-pyo3-ext-module` entries are intact.
Assessment: Fix matches the requested action and the project convention (CLAUDE.md TODO system: completed work is removed, not struck through). Accept.

### slop-2 — Fixed
Claim: `LibSpec.validate` permits `unknown_span_static=True` with `register_span_types=False`; consequence is a spec that passes validation but generates Rust referencing `Span` without importing it (`Span::unknown()` in the UNKNOWN_SPAN init), failing the downstream build with a cryptic rustc error.
Disposition: Fixed — guard added + covering test.
Evidence: `gsm2lib_rs.py:84-90` now raises `ValueError` when `unknown_span_static and not register_span_types`, with a message naming the dependency. Cross-checked the generator body: `use span::{SourceText, Span}` is emitted only under `register_span_types` (line 121-122), while `Span::unknown()` is emitted under `unknown_span_static` (line 149) — so the finding's compile-failure scenario is real and the guard closes exactly it. Test `test_unknown_span_static_without_register_span_types_raises_value_error` (test_gsm2lib_rs.py:128-136) constructs the offending spec and asserts the raise with `match="register_span_types"`.
Assessment: Fix addresses the stated consequence at the right place; test pins it. Accept.

### slop-3 — Fixed (partial) + Won't-Do (pub mod parser)
Claim: in `crates/fegen-rust/src/lib.rs`, `mod native_parser_tests;` lacked a `#[cfg(test)]` gate (compiled into release), and `pub mod parser;` exposes an internal generated module as cdylib public API.
Disposition: Fixed the `#[cfg(test)]`; Won't-Do on `pub mod parser`.
Evidence (cfg part): lib.rs:16 now has `#[cfg(test)]` immediately above `mod native_parser_tests;`. Correct and matches the finding's first requested fix.
Evidence (Won't-Do part): responder claims removing `pub` breaks the `--no-default-features` clippy lane because, with `python` off, the `#[pymodule]` body (gated `#[cfg(feature = "python")]`, lib.rs:19-25) is the only reference to `parser`, so a private `parser` becomes dead-code; `pub` anchors it as public API. I verified empirically: toggled `pub mod parser;` → `mod parser;` and ran `cargo clippy --manifest-path crates/fegen-rust/Cargo.toml --no-default-features -- -D warnings` (the exact lane at Makefile:149) — it failed with exit 101 and `-D dead-code` errors on `NodeKind`, `GrammarLabel`, `Rule`, and dozens of CST items. Restored the file afterward. The `-D warnings` lane makes this a hard build break, i.e. active harm, which clears the Won't-Do bar. The "cdylib has no Rust public API surface for downstream consumers" point is also correct, so the finding's stated consequence (downstream Rust linking against it) does not apply.
Assessment: cfg fix correct; Won't-Do rationale argues active harm and is source-verified. Accept both.

### scope — Won't-Do (no finding to resolve)
Claim: scope reviewer found no omissions; explicitly confirmed clockwork §2.7's "no source change" was correctly realized as a build-wiring change (drop `lib_rs` from `fltk_pyo3_cdylib`, delete `clockwork_native_lib.rs`), functionally identical to the deleted hand-authored file via the generic `gen-rust-lib`/`LibSpec.standard` path.
Disposition: Won't-Do — no change; nothing to resolve.
Evidence: scope notes report zero findings; responder agrees. No consequence is asserted by the reviewer, so there is nothing requiring action.
Assessment: No finding → Won't-Do is the correct (vacuous) disposition. Accept.

## Disputed items

None.

## Approved

4 dispositioned items: 2 Fixed verified (slop-1, slop-2), 1 Fixed+Won't-Do verified (slop-3, with the Won't-Do source-checked empirically), 1 vacuous Won't-Do (scope, no finding).

---

## Verdict: APPROVED

All dispositions acceptable. Both Fixed claims verified at the named lines; the slop-3 `pub mod parser` Won't-Do was independently reproduced (private `mod parser` breaks the `-D warnings` no-python clippy lane with dead-code errors), so the rationale argues genuine active harm. No disputed items.
