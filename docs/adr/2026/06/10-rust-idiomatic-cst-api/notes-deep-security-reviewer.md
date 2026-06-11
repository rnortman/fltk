# Security review — Phase 2 (idiomatic native CST surface)

Style: concise, precise, complete, unambiguous. No padding.

Reviewed: `7e39dfb..fb8852f`. Scope: Phase 2 only (per directive; Phases 0–1 merged in base, Phases 3–4 out of scope — their absence is not a finding).

Surveyed: `fltk/fegen/gsm2tree_rs.py` (full generator diff), `crates/fltk-cst-core/src/{error.rs,span.rs,lib.rs}`, `crates/fltk-cst-spike/{Cargo.toml,benches/traverse.rs}`, Cargo.lock dependency additions, hand-written test diffs (`spike_tests.rs`, `native_tests.rs`, `tests/test_gsm2tree_rs.py`, `fltk/fegen/test_genparser.py`), and the five generated-output diffs grepped for `unsafe`/`downcast_unchecked`/`transmute`/process ops (none introduced).

## Findings

### security-1

- **File:line**: `fltk/fegen/gsm2tree_rs.py:504` and `:638` (`#[derive(Clone, Debug)]` emitted on child enums and node data structs); manifests in all five regenerated outputs (e.g. `crates/fltk-cst-spike/src/cst.rs`).
- **Issue**: Phase 2 adds derived `Debug` that recurses through `Shared<T>` children (`Shared`'s `Debug` delegates through `read()`, base) with no depth bound and no cycle detection.
- **Trust boundary / data flow**: CST trees are parser output — in downstream apps (this library's primary purpose; explicit R4 target is generated parsers), parser input is frequently untrusted. Tree depth is attacker-controlled via input nesting; cycles are additionally user-creatable via shared ownership (`append` an ancestor into a descendant). Sink: any downstream `{:?}` / `format!` / log statement on a node.
- **Consequence**: Stack exhaustion → uncatchable process abort when Debug-formatting a deeply nested attacker-shaped tree; infinite recursion on a cyclic tree. DoS of any downstream service that debug-logs nodes built from untrusted input. The *cycle* case is design-accepted (design §5 "Reference cycles" names the new `Debug` explicitly); the unbounded-*depth* case on acyclic attacker-controlled input is not called out there and is the part newly exposed by this diff (derived `PartialEq` had the same property pre-Phase-2; `Debug` is new and is the typical logging path).
- **Suggested fix**: Acceptable as documented contract given the design's acceptance posture; to close, emit a manual depth-capped `Debug` (elide children past depth N or print child count beyond a cutoff — the existing non-recursive `__repr__`, gsm2tree_rs.py Python handle path, is the model) instead of `derive(Debug)`. At minimum extend the §5 / Phase-3 docs to cover depth (not just cycles) so authors of parsers over untrusted input know not to `{:?}` unbounded trees.

## Checked, no finding

- **Codegen injection (grammar → Rust source)**: Phase 2 interpolates labels into method names (`children_{label}`), `&'static str` literals (`label: "{label}"` in `CstError` construction), and rustdoc; and rule-derived class names into types and `#[pyclass(name = "...")]`. All inputs are gated by the pre-emission `_IDENTIFIER_RE` (`^[_a-z][_a-z0-9]*$`) validation of every rule name and item label (`gsm2tree_rs.py:56–80`, present at base) — no quote, backslash, newline, or non-ASCII can reach an emitted literal, identifier, or doc comment. Reserved-label check rejects `children` (the `extend_children` collision). Closed.
- **Info leak via new Debug/Display**: `Span`'s manual `Debug` (`crates/fltk-cst-core/src/span.rs:148`) deliberately elides source text — which can be the entire input — printing only `start`/`end`/`has_source`. Positive control: prevents whole-input leakage into logs through the derived node `Debug`. `CstError`'s `Display` carries only generator-emitted static label strings and counts — no runtime data leakage.
- **Unsafe / boundary code**: no new `unsafe`, `downcast_unchecked`, or `transmute` anywhere in the diff; Phase 0 cross-cdylib hardening is untouched base. `forbid(unsafe_code)` posture of the python-off spike holds (new accessors are safe code only).
- **Secrets**: none in the diff (grep + manual read of all non-generated changes).
- **New dependencies**: criterion 0.5 plus its transitive tree (clap, rayon, plotters, serde_json, regex, etc.) — `[dev-dependencies]` of the spike crate only, never compiled into shipped artifacts; no known-vulnerable versions noticed. `benches/traverse.rs` is self-contained: no I/O beyond criterion's own report output, no env/process access.
- **AuthZ / SSRF / path traversal / deserialization / CSRF / open redirect / crypto / timing**: no applicable surface in this change set (pure codegen plus in-process native accessors; no network, filesystem, auth, or crypto code touched).
