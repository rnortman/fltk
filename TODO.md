# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

## `regex-automata-features`

`fltk-parser-core/Cargo.toml` uses `regex-automata = "0.4"` with default features, which include `dfa-build`/`dfa-search` (full DFA determinizer). The `regex = "1"` crate (the prior dependency) did not enable those features, so this change adds compile time and binary size for `fltk-parser-core` and every downstream consumer crate. The DFA-build path is a search-speed win for small patterns (and is tightly size-capped), so the default was kept deliberately, but the cost was not formally weighed at the time of the change. Consider pinning to the feature subset actually used by `regex=1` if compile time or binary size becomes a concern. Location: `crates/fltk-parser-core/Cargo.toml`.

## `error-msg-bidi-escape`

`escape_control_chars` (both backends) stops at U+009F. Unicode bidi override characters (U+202A–U+202E, U+2066–U+2069), line/paragraph separators (U+2028, U+2029), and zero-width chars pass through unescaped into the quoted failing line. An attacker controlling parse input can use RLO/bidi embedding to visually reorder the rendered error line in bidi-aware terminals/UIs, or use U+2028/U+2029 to split log lines in viewers that treat them as line terminators. Lower impact than the closed ESC vector (no command execution), but the log-forging variant is the same asset class. Extending the escape set beyond C0+DEL+C1 requires a new representation spec (two-digit `\xHH` is insufficient) and cross-backend repinning. Accepted risk for the current scope; address as a follow-up if consumers surface bidi-aware display paths. Locations: `crates/fltk-parser-core/src/errors.rs` (`escape_control_chars`), `fltk/fegen/pyrt/errors.py` (`escape_control_chars`).

## `error-msg-escape-zero-copy`

`escape_control_chars` now has an early-return fast path for control-free input (scans once, returns `s.to_owned()` / `text` unchanged). The zero-copy variant — returning `Cow<'_, str>` on the Rust side so no allocation occurs at all for clean input — would eliminate the remaining copy but requires changing the public function signature. Deferred: the `to_owned()` fast path already recovers the common-case regression; `Cow` is an API-surface decision for a future cleanup. Location: `crates/fltk-parser-core/src/errors.rs` (`escape_control_chars`).

## `rust-cst-eq-depth`

`PartialEq` on generated node structs recurses through `Shared<T>` children with no depth bound; tree depth is attacker-controlled for parsers over untrusted input, so `assert_eq!` or any equality check on a deep parser-produced tree aborts the process (stack exhaustion, uncatchable). Same root cause as the fixed Debug/Drop paths — `Shared<T>::PartialEq` acquires a read lock and delegates to `T::eq`, which compares `children` recursively. Fix: emit iterative `impl PartialEq` on node structs following the same generator pattern used for `impl Drop`. Locations: `fltk/fegen/gsm2tree_rs.py` (`_node_block`, `_drop_block` pattern), `crates/fltk-cst-core/src/shared.rs` (`PartialEq` impl).


## `mutator-remove-at-oob-atomicity`

`remove_at` on the Rust backend removes the child from the `Vec` under the write lock, then calls `to_pyobject` after releasing the guard. On OOM in `Py::new` inside `registry::get_or_insert_with`, the `?` propagates a `PyErr` to the caller, but the child is already removed and its `Arc` dropped if no other reference exists. The semantic contract ("atomic: either returns (label, child) or does nothing") is violated in this case. Fix: clone the Arc (read-lock snapshot) and attempt `to_pyobject` before acquiring the write lock for removal; only remove if wrap-out succeeds. Alternatively: remove, attempt wrap-out, re-insert on failure. OOM is effectively unreachable in practice. Location: `fltk/fegen/gsm2tree_rs.py` (`_generic_remove_at`).

## `mutator-rs-fast-path-int-index`

`_generic_insert`, `_generic_remove_at`, and `_generic_replace_at` call `operator.index` unconditionally via Python import+getattr+call. For the common case of exact `int` inputs, `index.extract::<i64>()` on the original object suffices (PyO3 calls `PyLong_AsLongLong` which invokes `__index__`), avoiding three Python round-trips per mutator call. Add fast-path: `if let Ok(i) = index.extract::<i64>() { use i directly }; else { call operator.index }`. Requires care around `orig_str` capture ordering for `remove_at`/`replace_at`. Location: `fltk/fegen/gsm2tree_rs.py` (`_generic_insert`, `_generic_remove_at`, `_generic_replace_at`).

## `rust-generated-ident-collisions`

Pairwise Rust-identifier collisions between rule-derived names are not checked at generation time. Examples: a rule `foo_child` yields class `FooChild`, which collides with the generated `FooChild` enum for a rule `foo`'s child enum; `foo_label`/`Py`-prefix analogues exist as well. These require cross-rule analysis rather than a fixed reserved set, unlike the single-rule class-name checks in `_RESERVED_CLASS_NAMES`. Currently such grammars produce uncompilable Rust output with an opaque `cargo` error. Location: `fltk/fegen/gsm2tree_rs.py` (`RustCstGenerator.__init__`, after `_RESERVED_CLASS_NAMES` check).

