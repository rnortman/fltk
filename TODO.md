# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `crosscdylib-abi-check-helper`

`get_span_type` and `extract_source_text` both perform the same two-step ABI pair check (string marker then layout int), with only the type label and expected-layout constant varying. Extract a generic helper (e.g. `fn check_abi_pair<T: PyClass>(ty: &Bound<'_, PyType>, type_label: &str) -> PyResult<()>`) to eliminate the duplication and ensure uniform error messages. Currently the error-message wording diverges slightly between the two paths. Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`extract_source_text` lines 57–100, `get_span_type` lines ~255–300).

## `abi-gate-test-consolidation`

`TestSpanPathAbiGate` spawns three separate subprocesses (one per scenario: ABI-string mismatch, layout mismatch, control). Since `GILOnceCell` does not cache errors, all three could share one subprocess (failures first, success last), reducing startup cost. Deferred: current structure is readable and the savings are modest. Location: `tests/test_rust_span.py` (`TestSpanPathAbiGate`).

## `crosscdylib-abi-size-probe`

The `_fltk_cst_core_abi_layout` classattr probe compares `size_of::<PyClassObject<T>>()` across cdylibs. Equal size is consistent with — but does not prove — identical field layout: a pyo3 build that reorders internal fields while preserving total size passes the probe, after which `downcast_unchecked` reinterprets memory at wrong offsets. To close this residual, fold the resolved pyo3 version into `FLTK_CST_CORE_ABI` (via a build script reading the Cargo lock or `DEP_*` env var) so the string itself separates pyo3 resolutions. The size probe remains as defense-in-depth. Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`FLTK_CST_CORE_ABI` constant and SAFETY comments in `extract_source_text` / `extract_span`).

## `rust-cst-children-list-view`

The Rust-backend `node.children` getter returns a fresh snapshot list per call (a `PyList` rebuilt from `Vec` on each access); in-place mutation of the returned list is a silent no-op on the tree. The Python backend returns the node's actual internal list, so in-place list mutation edits the tree. Closing this divergence would require a live sequence-proxy pyclass. Deferred as additive; the Python-backend behavior is documented in the Phase 3 docs. Location: `fltk/fegen/gsm2tree_rs.py` (`_children_getter`, lines 682–700).

## `rust-cst-accessor-clone-efficiency`

Per-label child accessors (`children_<label>`, `child_<label>`, `maybe_<label>`) and the generic `child()` accessor each clone the full children `Vec` under the read guard then filter outside it — O(total-children) Arc/Span/label clones per call even when the matching subset is small. The fix is mechanical: filter inside the read guard, cloning only matching entries; `child()` can check `len` under the guard and clone only the single needed entry. The §6 item 8 benchmark (gate passed 2026-06-10) measured ~8 ns per uncontended read; fixing this accessor inefficiency is an independent cleanup not blocked by the gate result. Location: `fltk/fegen/gsm2tree_rs.py` (`_generic_child`, `_per_label_methods`).

## `registry-unit-tests`

`crates/fltk-cst-core/src/registry.rs` has no Rust unit tests. The four public functions (`lookup`, `register_if_absent`, `force_register`, `get_or_insert_with`) are tested only indirectly through Python integration tests. Direct unit tests are blocked by the build setup: `cargo test` on an rlib with `pyo3` (feature="python") cannot link `libpython` in the default test binary. Options: (a) build a dedicated test cdylib that exports test entry points, (b) test via the Python test harness using `ctypes`/`cffi`, or (c) add a `cargo test --target` integration test crate that links as a cdylib. Deferred; Python identity/mutation tests provide adequate coverage today. Location: `crates/fltk-cst-core/src/registry.rs`.


## `rust-str-lit-shared`

`_rust_str_lit` is only defined in `fltk/fegen/gsm2parser_rs.py`. `gsm2tree_rs.py` embeds Rust string literals in f-strings without going through an escaping helper, meaning any rule name or label containing characters that require escaping (backslash, double-quote, control chars) would produce malformed Rust there. Extract to a shared utility so both generators use the same escaping path. Location: `fltk/fegen/gsm2parser_rs.py` (`_rust_str_lit`, module level).

## `rust-naming-shared`

The `XChild` and `XLabel` naming conventions for generated Rust enums are encoded independently in `gsm2parser_rs.py` (`_child_enum_name`, `_class_name`) and `gsm2tree_rs.py` (`_label_enum_rust_name`, inline `f"{class_name}Child"` in `_child_enum_block`). A rename in one place without the other produces parser code that references non-existent CST enum names (caught only at `cargo` compile time). Extract naming helpers to `RustCstGenerator` so both generators read from a single source. Location: `fltk/fegen/gsm2parser_rs.py` (`_child_enum_name`), `fltk/fegen/gsm2tree_rs.py` (`_label_enum_rust_name`, `_child_enum_block`).

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks).

## `rust-cst-debug-depth`

`derive(Debug)` on generated node structs recurses through `Shared<T>` children with no depth bound and no cycle detection. For downstream apps that parse untrusted input (the design's primary use case via R4), tree depth is attacker-controlled; debug-logging a deeply-nested tree causes stack exhaustion → uncatchable process abort. The cycle case is design-accepted (§5); this TODO tracks the unbounded-depth DoS on acyclic attacker-controlled input, which is new exposure introduced by Phase 2's `derive(Debug)`. Fix: emit a manual depth-capped `Debug` (elide children past depth N or print child count beyond a cutoff — the existing non-recursive `__repr__` in gsm2tree_rs.py is the model) instead of `derive(Debug)`. Alternatively, extend Phase-3 docs to explicitly warn authors of parsers over untrusted input not to `{:?}` unbounded trees. Location: `fltk/fegen/gsm2tree_rs.py` (the `#[derive(Clone, Debug)]` emit on node data structs, ~line 638).

## `regex-automata-features`

`fltk-parser-core/Cargo.toml` uses `regex-automata = "0.4"` with default features, which include `dfa-build`/`dfa-search` (full DFA determinizer). The `regex = "1"` crate (the prior dependency) did not enable those features, so this change adds compile time and binary size for `fltk-parser-core` and every downstream consumer crate. The DFA-build path is a search-speed win for small patterns (and is tightly size-capped), so the default was kept deliberately, but the cost was not formally weighed at the time of the change. Consider pinning to the feature subset actually used by `regex=1` if compile time or binary size becomes a concern. Location: `crates/fltk-parser-core/Cargo.toml`.

## `error-msg-bidi-escape`

`escape_control_chars` (both backends) stops at U+009F. Unicode bidi override characters (U+202A–U+202E, U+2066–U+2069), line/paragraph separators (U+2028, U+2029), and zero-width chars pass through unescaped into the quoted failing line. An attacker controlling parse input can use RLO/bidi embedding to visually reorder the rendered error line in bidi-aware terminals/UIs, or use U+2028/U+2029 to split log lines in viewers that treat them as line terminators. Lower impact than the closed ESC vector (no command execution), but the log-forging variant is the same asset class. Extending the escape set beyond C0+DEL+C1 requires a new representation spec (two-digit `\xHH` is insufficient) and cross-backend repinning. Accepted risk for the current scope; address as a follow-up if consumers surface bidi-aware display paths. Locations: `crates/fltk-parser-core/src/errors.rs` (`escape_control_chars`), `fltk/fegen/pyrt/errors.py` (`escape_control_chars`).

## `error-msg-escape-zero-copy`

`escape_control_chars` now has an early-return fast path for control-free input (scans once, returns `s.to_owned()` / `text` unchanged). The zero-copy variant — returning `Cow<'_, str>` on the Rust side so no allocation occurs at all for clean input — would eliminate the remaining copy but requires changing the public function signature. Deferred: the `to_owned()` fast path already recovers the common-case regression; `Cow` is an API-surface decision for a future cleanup. Location: `crates/fltk-parser-core/src/errors.rs` (`escape_control_chars`).

## `parser-bindings-name-collision`

`_gen_python_bindings` registers `PyApplyResult` and `PyParser` as `"ApplyResult"` and `"Parser"` in the same module that registers one class per grammar rule. A grammar containing a rule named `parser` or `apply_result` generates a CST class with the same name (`Parser`/`ApplyResult`), and pyo3's `add_class` assignment silently shadows the first registration — the CST node class becomes unreachable as a module attribute. No generator-side check rejects or warns about the collision. Fix: in the generator (CST or parser side), raise an error at generation time when a rule's class name collides with the fixed names `Parser`, `ApplyResult`, `Span`, or `SourceText`. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_python_bindings`), `fltk/fegen/gsm2tree_rs.py` (class name validation).

