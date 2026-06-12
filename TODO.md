# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `abi-gate-test-consolidation`

`TestSpanPathAbiGate` spawns three separate subprocesses (one per scenario: ABI-string mismatch, layout mismatch, control). Since `GILOnceCell` does not cache errors, all three could share one subprocess (failures first, success last), reducing startup cost. Deferred: current structure is readable and the savings are modest. Location: `tests/test_rust_span.py` (`TestSpanPathAbiGate`).

## `crosscdylib-abi-size-probe`

The `_fltk_cst_core_abi_layout` classattr probe compares `size_of::<PyClassObject<T>>()` across cdylibs. Equal size is consistent with — but does not prove — identical field layout: a pyo3 build that reorders internal fields while preserving total size passes the probe, after which `downcast_unchecked` reinterprets memory at wrong offsets. To close this residual, fold the resolved pyo3 version into `FLTK_CST_CORE_ABI` (via a build script reading the Cargo lock or `DEP_*` env var) so the string itself separates pyo3 resolutions. The size probe remains as defense-in-depth. Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`FLTK_CST_CORE_ABI` constant and SAFETY comments in `extract_source_text` / `extract_span`).

## `rust-cst-children-list-view`

The Rust-backend `node.children` getter returns a fresh snapshot list per call (a `PyList` rebuilt from `Vec` on each access); in-place mutation of the returned list is a silent no-op on the tree. The Python backend returns the node's actual internal list, so in-place list mutation edits the tree. Closing this divergence would require a live sequence-proxy pyclass. Deferred as additive; the Python-backend behavior is documented in the Phase 3 docs. Location: `fltk/fegen/gsm2tree_rs.py` (`_children_getter`, lines 682–700).

## `registry-unit-tests`

`crates/fltk-cst-core/src/registry.rs` has no Rust unit tests. The four public functions (`lookup`, `register_if_absent`, `force_register`, `get_or_insert_with`) are tested only indirectly through Python integration tests. Direct unit tests are blocked by the build setup: `cargo test` on an rlib with `pyo3` (feature="python") cannot link `libpython` in the default test binary. Options: (a) build a dedicated test cdylib that exports test entry points, (b) test via the Python test harness using `ctypes`/`cffi`, or (c) add a `cargo test --target` integration test crate that links as a cdylib. Deferred; Python identity/mutation tests provide adequate coverage today. Location: `crates/fltk-cst-core/src/registry.rs`.


## `rust-str-lit-shared`

`_rust_str_lit` is only defined in `fltk/fegen/gsm2parser_rs.py`. `gsm2tree_rs.py` embeds Rust string literals in f-strings without going through an escaping helper, meaning any rule name or label containing characters that require escaping (backslash, double-quote, control chars) would produce malformed Rust there. Extract to a shared utility so both generators use the same escaping path. Location: `fltk/fegen/gsm2parser_rs.py` (`_rust_str_lit`, module level).

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks).

## `regex-automata-features`

`fltk-parser-core/Cargo.toml` uses `regex-automata = "0.4"` with default features, which include `dfa-build`/`dfa-search` (full DFA determinizer). The `regex = "1"` crate (the prior dependency) did not enable those features, so this change adds compile time and binary size for `fltk-parser-core` and every downstream consumer crate. The DFA-build path is a search-speed win for small patterns (and is tightly size-capped), so the default was kept deliberately, but the cost was not formally weighed at the time of the change. Consider pinning to the feature subset actually used by `regex=1` if compile time or binary size becomes a concern. Location: `crates/fltk-parser-core/Cargo.toml`.

## `error-msg-bidi-escape`

`escape_control_chars` (both backends) stops at U+009F. Unicode bidi override characters (U+202A–U+202E, U+2066–U+2069), line/paragraph separators (U+2028, U+2029), and zero-width chars pass through unescaped into the quoted failing line. An attacker controlling parse input can use RLO/bidi embedding to visually reorder the rendered error line in bidi-aware terminals/UIs, or use U+2028/U+2029 to split log lines in viewers that treat them as line terminators. Lower impact than the closed ESC vector (no command execution), but the log-forging variant is the same asset class. Extending the escape set beyond C0+DEL+C1 requires a new representation spec (two-digit `\xHH` is insufficient) and cross-backend repinning. Accepted risk for the current scope; address as a follow-up if consumers surface bidi-aware display paths. Locations: `crates/fltk-parser-core/src/errors.rs` (`escape_control_chars`), `fltk/fegen/pyrt/errors.py` (`escape_control_chars`).

## `error-msg-escape-zero-copy`

`escape_control_chars` now has an early-return fast path for control-free input (scans once, returns `s.to_owned()` / `text` unchanged). The zero-copy variant — returning `Cow<'_, str>` on the Rust side so no allocation occurs at all for clean input — would eliminate the remaining copy but requires changing the public function signature. Deferred: the `to_owned()` fast path already recovers the common-case regression; `Cow` is an API-surface decision for a future cleanup. Location: `crates/fltk-parser-core/src/errors.rs` (`escape_control_chars`).

## `rust-cst-eq-depth`

`PartialEq` on generated node structs recurses through `Shared<T>` children with no depth bound; tree depth is attacker-controlled for parsers over untrusted input, so `assert_eq!` or any equality check on a deep parser-produced tree aborts the process (stack exhaustion, uncatchable). Same root cause as the fixed Debug/Drop paths — `Shared<T>::PartialEq` acquires a read lock and delegates to `T::eq`, which compares `children` recursively. Fix: emit iterative `impl PartialEq` on node structs following the same generator pattern used for `impl Drop`. Locations: `fltk/fegen/gsm2tree_rs.py` (`_node_block`, `_drop_block` pattern), `crates/fltk-cst-core/src/shared.rs` (`PartialEq` impl).


## `rust-generated-ident-collisions`

Pairwise Rust-identifier collisions between rule-derived names are not checked at generation time. Examples: a rule `foo_child` yields class `FooChild`, which collides with the generated `FooChild` enum for a rule `foo`'s child enum; `foo_label`/`Py`-prefix analogues exist as well. These require cross-rule analysis rather than a fixed reserved set, unlike the single-rule class-name checks in `_RESERVED_CLASS_NAMES`. Currently such grammars produce uncompilable Rust output with an opaque `cargo` error. Location: `fltk/fegen/gsm2tree_rs.py` (`RustCstGenerator.__init__`, after `_RESERVED_CLASS_NAMES` check).

