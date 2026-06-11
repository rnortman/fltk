# Deep correctness review — Phase 2 (idiomatic native CST surface)

Style: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Reviewed: `7e39dfb..fb8852f` (HEAD fb8852f). Scope: Phase 2 only (per directive; Phases 0–1 are base, 3–4 out of scope).

## Verification performed (all passed)

- Regen identity: re-ran `gen-rust-cst` for poc, phase4_roundtrip, and fegen grammars — byte-identical to committed `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fegen/src/cst.rs`. `crates/fltk-cst-spike/src/cst.rs` byte-identical to `src/cst_generated.rs`. `.pyi` regen differs only by `make fix` formatting (intended flow per CLAUDE.md).
- `cargo test -p fltk-cst-core --no-default-features` (24 pass), `cargo test -p fltk-cst-spike` (37 pass), fixture crate `--features python` native tests (36 pass, linked against system libpython), both python-off clippy lanes clean, 133 generator pytest tests pass.
- Semantics audited against design §4.3: count-before-type precedence (`ChildCount` wins; `UnexpectedChildType` only at valid count, single-typed labels only) — implemented correctly in `child_<lbl>`/`maybe_<lbl>` for both node- and span-typed labels; `children_<lbl>` skips off-type variants (documented), union labels pure label-filter; `need_wildcard`/`need_unexpected_arm` (`total_variants > 1`) correctly omits unreachable arms exactly when the child enum is single-variant (off-type storage impossible there, so omission is sound, not lossy). Union `child_/maybe_` `(next(), next())` match arms cover all count cases ((None,_) → 0; (Some,None) → 1; recount in `_` arm correct).
- Python-visible surface provably unchanged: `_label_enum_python_name` (`ClassName_Label`) equals the pre-rename Rust enum-name string, so `#[pyclass(name=...)]`, label `__repr__` (`"{class_name}.Label.{NAME}"` — built from `class_name`, not the enum name), and pymethod error messages are string-identical to base.
- `impl Into<Shared<T>>` write side accepts both `T` (via `From<T> for Shared<T>`, shared.rs) and `Shared<T>` (reflexive `From`; no coherence overlap — target types differ); `append_lbl_node_adds_labeled_child` pins Arc preservation (`ptr_eq`).
- Reserved-label check (`children` → `extend_children`) still covers the only fixed-name collision after Phase 2's new fixed natives (`kind`, `set_span`, `child`, `extend_children`): all per-label names are prefixed (`children_/child_/maybe_/append_/extend_`), so no new collision pair exists.
- `Span` manual `Debug` (span.rs:148–158): no pre-existing derive conflict; elides source as designed.
- Fixture crate python-off compile failure (`cargo test --no-default-features` in `tests/rust_cst_fixture`) is pre-existing — `lib.rs` `#[pymodule]` is ungated and unchanged from base. Not a Phase 2 regression.
- Benchmark (`crates/fltk-cst-spike/benches/traverse.rs`): span indices stay within the 70-char source (`i % 60 + 5`); nested parent-read → child-read locking is distinct-lock, single-threaded — no re-entrancy hazard.

## Findings

### correctness-1: `_native_per_label_methods` re-derives `rule_name` through a lossy inverted map; miss/collision path silently emits wrong-shaped accessors

- File: `fltk/fegen/gsm2tree_rs.py:1086–1094` (call site `:728` in `_node_block`).
- What's wrong: `_node_block` has `rule_name` in scope but does not pass it; `_native_per_label_methods` reconstructs it via `{class_name_for_rule_node(rn): rn for rn in rule_models}` then `rule_name_map.get(class_name)`, with a silent fallback (`f"&{enum_name}", None, 2` — union-shaped accessors, assumed multi-variant) on lookup miss.
- Why: `naming.snake_to_upper_camel` is non-injective by documented contract (naming.py:13–15: `"a__b" → "AB"`, `"_foo_bar" → "FooBar"`), so distinct valid rule names (`foo_bar`, `foo__bar`, `_foo_bar`) map to one class name. The dict comprehension is last-wins; `_label_type_info(rule_name, label)` then reads the *other* rule's `model.labels[label]` — either a `KeyError` mid-generation (label absent from the wrong rule) or accessors typed by the wrong rule's model. The `None` fallback is currently unreachable (`_rule_info` guarantees every emitted class name appears in the map), but if ever reached it degrades single-typed labels to union-shaped accessors with no error.
- Consequence: bounded — a class-name collision also emits two `pub struct X` definitions, so the output fails `rustc` regardless; the realistic failure is a confusing generation-time `KeyError` (no diagnostic naming the colliding rules) rather than shipped wrong behavior. The underlying defect is data-flow: a value already in hand is re-derived through a lossy inversion, and the dead fallback masks invariant violations instead of failing loudly.
- Suggested fix: pass `rule_name` from `_node_block` (it is a parameter there); delete `rule_name_map`; replace the fallback branch with a raised `RuntimeError`. Optionally add a generation-time class-name uniqueness check so collisions fail with a named error instead of `rustc` duplicate-definition output.

### correctness-2: non-interpolated `{label}` placeholder in generated comments

- File: `fltk/fegen/gsm2tree_rs.py:1409,1439` (`_per_label_methods`, pymethod `child_<lbl>`/`maybe_<lbl>` bodies); visible in all committed outputs, e.g. `src/cst_generated.rs:558,582,1375,1399`.
- What's wrong: `"        // TODO(rust-cst-accessor-clone-efficiency): see children_{label} above."` is a plain string where `{label}` was intended to interpolate (adjacent lines in the same lists are f-strings; commit 70d8412 fixed this exact slop class elsewhere in the same file).
- Consequence: comment text only — generated output literally reads `see children_{label} above` instead of e.g. `see children_name above`. No behavioral effect; misleading to readers of generated code.
- Suggested fix: make both lines f-strings; regenerate (`make gencode` → `make fix`).

No other logic, control-flow, data-flow, locking, or off-by-one defects found in the Phase 2 diff.
