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

## `consume-regex-anchor`

`consume_regex` uses `regex::Regex::find_at` which is not anchored: on a non-match at the
target byte position it scans the remaining haystack before concluding no match. Python's
`re.match(pos=...)` anchors and fails without scanning. Worst case: O(rules × n²) CPU for
inputs that cause many terminal failures — a complexity DoS when parsing untrusted input.
Fix: switch to `regex_automata::meta::Regex` with `Input::new(text).anchored(Anchored::Yes)
.span(byte_pos..text.len())` to get truly anchored rejection without losing look-behind
context. Location: `crates/fltk-parser-core/src/terminalsrc.rs` (`consume_regex`).

## `apply-depth-limit`

`apply` recurses (`apply → rule → apply`) with depth proportional to grammar-nesting depth
of the input, with no limit. Python raises a catchable `RecursionError`; Rust overflows the
stack and aborts the process (a hard, unrecoverable DoS — stricter regression vs. Python).
Fix: add a depth counter to `PackratState`, increment/decrement in `apply`, and convert
exceeding a configurable limit into a parse failure (or a dedicated error channel in Phase 3).
Location: `crates/fltk-parser-core/src/memo.rs` (`apply`, `PackratState`).

## `error-msg-escape`

`format_error_message` embeds the raw failing line from untrusted input unescaped in the
error string. Control characters (ESC/ANSI, `\r`) pass through verbatim, enabling terminal
escape injection and log forging against consumers that surface parse errors. This matches
Python's `format_error_message` byte-for-byte, so it cannot be fixed unilaterally without
breaking the Phase 3 parity comparator. Fix Python and Rust together: escape C0 controls
(except `\n`/`\t`) in `line_text`, then update the comparator.
Location: `crates/fltk-parser-core/src/errors.rs` (`format_error_message`).

## `rust-cst-debug-depth`

`derive(Debug)` on generated node structs recurses through `Shared<T>` children with no depth bound and no cycle detection. For downstream apps that parse untrusted input (the design's primary use case via R4), tree depth is attacker-controlled; debug-logging a deeply-nested tree causes stack exhaustion → uncatchable process abort. The cycle case is design-accepted (§5); this TODO tracks the unbounded-depth DoS on acyclic attacker-controlled input, which is new exposure introduced by Phase 2's `derive(Debug)`. Fix: emit a manual depth-capped `Debug` (elide children past depth N or print child count beyond a cutoff — the existing non-recursive `__repr__` in gsm2tree_rs.py is the model) instead of `derive(Debug)`. Alternatively, extend Phase-3 docs to explicitly warn authors of parsers over untrusted input not to `{:?}` unbounded trees. Location: `fltk/fegen/gsm2tree_rs.py` (the `#[derive(Clone, Debug)]` emit on node data structs, ~line 638).

