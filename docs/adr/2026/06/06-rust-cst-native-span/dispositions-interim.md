Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

HEAD after fixes: a320715

---

correctness-1:
- Disposition: Fixed
- Action: `_label_from_pyobject_match` now raises `PyTypeError` on unrecognized label (wrong-rule label or label on no-label node) instead of coercing to `None`. `gsm2tree_rs.py:585-606`. Regenerated all 4 `.rs` files.
- Severity assessment: Silent cross-backend divergence on the `children` Python shape for any out-of-tree consumer calling `append`/`extend` with a wrong-rule label; label accessor then silently missed the child. No in-tree parser affected (they use typed `append_<label>`).

correctness-2:
- Disposition: Fixed
- Action: Dropped early `break` in `child_<label>` loop so `count` accumulates the true number of matching children. `gsm2tree_rs.py:752-768`. Regenerated all 4 `.rs` files.
- Severity assessment: Error was still raised correctly (just with an inaccurate count integer in the message for 3+ matches). Cosmetic divergence from Python backend's exact count, now aligned.

errhandling-1:
- Disposition: Fixed
- Action: `self.source.as_ref().unwrap()` → `.expect("invariant: source is Some — checked by is_none guard above")` at `crates/fltk-cst-core/src/span.rs:217`.
- Severity assessment: Currently unreachable; maintainability improvement — future refactors that reorder guards won't produce a silent panic.

errhandling-2:
- Disposition: Fixed
- Action: Same fix as correctness-1 — `_label_from_pyobject_match` raises `TypeError` on failed extraction; `gsm2tree_rs.py:585-606`. Generator is the single source; all generated files regenerated.
- Severity assessment: Mis-labelled `append` call would have stored child as unlabeled with no error; debuggable only with a debugger. Now fails loudly at the call site.

errhandling-3:
- Disposition: TODO(rust-cst-span-getter-source-loss)
- Action: Span getter and `to_pyobject` Span variant reconstruct `fltk._native.Span(start, end)` sourceless even when the stored native Span has source. This is an accepted limitation documented in increment-2 log ("Loses source info on round-trip through getter; acceptable since parse-path source-bearing spans are §2.5"). Added `TODO(rust-cst-span-getter-source-loss)` to the existing deviation note. Fix requires exposing `pub fn source_text(&self) -> Option<SourceText>` on `Span` in `fltk-cst-core` (design §2.5/§2.6 prereq). Not added to TODO.md because it is already logged in the implementation log as a known deviation; the §2.5/§2.6 work will address it.
- Severity assessment: Any Python consumer calling `.text()` on a node's Python-visible span or child span after construction with a source-bearing span gets `None`/`ValueError`. Practical impact is zero until §2.5 attaches source to spans — parse path does not yet produce source-bearing spans.

errhandling-4:
- Disposition: Won't-Do
- Action: No change.
- Severity assessment: A grammar with a rule whose model has no typed children already raises `RuntimeError` from `_rule_info()` at generator construction time (line 85-91). The `not has_span and not child_classes` path in `_child_enum_block` is therefore unreachable — `_rule_info()` guards it. Adding a second diagnostic would be unreachable dead code.
- Rationale: `_rule_info()` at `gsm2tree_rs.py:85-91` raises `RuntimeError` for any rule with an empty model (`not model.types`), which is the superset of `not has_span and not child_classes`. The reviewer's concern (no warning at generation time) is already addressed by the existing guard; adding code to the `_child_enum_block` path would never execute.

security-1 (no findings):
- Disposition: Won't-Do (no action needed; reviewer found no issues)

test-1:
- Disposition: Fixed (partial) / TODO(rust-cst-node-pub-ctor)
- Action: Added 5 GIL-free `#[cfg(test)]` tests to `crates/fltk-cst-core/src/lib.rs` covering `Span` construction, accessor reads, and value equality without `Python::with_gil`. These pass via `cargo test --workspace`. The full §4 item 1 node-subtree test (construct `Identifier` with `Box<IdentifierChild>`, walk, compare) is blocked: node struct fields are private and the only constructor requires `Python<'_>`. Added `TODO(rust-cst-node-pub-ctor)` to `TODO.md` with location `fltk/fegen/gsm2tree_rs.py` (`_node_block`).
- Severity assessment: Span-level GIL-free acceptance partially satisfied. Node-level traversal without GIL remains unverified by test; a regression re-introducing a GIL dependency in native traversal logic would be caught only via Python-level tests.

test-2:
- Disposition: Fixed
- Action: Added `test_extend_children_emitted` and `test_get_span_type_helper_emitted` to `TestNodeStructure` in `tests/test_gsm2tree_rs.py`.
- Severity assessment: Regression in `_generic_extend_children` emission would previously go undetected at the generator level.

test-3:
- Disposition: Fixed
- Action: Added `test_gsm2parser_extend_children_call_site` to `fltk/fegen/test_genparser.py`; generates a parser from a grammar with repeated terms and asserts `extend_children` is present and `.children.extend(` is absent.
- Severity assessment: A regression at either `inline_to_parent` emit site in `gsm2parser.py` would silently produce parsers that lose children on the Rust backend.

test-4:
- Disposition: Fixed
- Action: Added `test_with_source_text_object` to `tests/test_span.py`; moved `SourceText` to top-level import.
- Severity assessment: The `isinstance(source, SourceText)` branch of `terminalsrc.Span.with_source` had no test in its home file; coverage gap now closed.

scope-1:
- Disposition: Fixed
- Action: Replaced "commit TBD" with "commit ee4a59b" in increment 2 header of `implementation-log.md`.
- Severity assessment: Audit trail gap — reviewers could not `git show` increment 2.

scope-2:
- Disposition: Fixed
- Action: Reordered log sections to chronological order: inc 1 → 2 → 3 → 4 → 5 in `implementation-log.md`.
- Severity assessment: Confusing log; increment 4 appeared before increment 3 it depends on.

scope-3:
- Disposition: Fixed
- Action: Aligned both count references in increment 3 to 121 (the correct value from the `e850f48` state) in `implementation-log.md`.
- Severity assessment: Minor inconsistency; informational only.

scope-4:
- Disposition: Fixed
- Action: Regenerated `tests/rust_cst_fixture/src/cst.rs` from `fltk/fegen/test_data/phase4_roundtrip.fltkg` (not from the PoC grammar); now exposes `Config`, `Entry`, `Operator`, `Identifier`, `Literal`, `Trivia` as designed. Fixture crate builds clean.
- Severity assessment: `make build-test-user-ext && pytest` would have failed with `AttributeError: module has no attribute 'Config'` for all 71 phase4 fixture tests.

scope-5:
- Disposition: TODO(rust-cst-node-pub-ctor)
- Action: The design tension (§2.1 vs §2.8: node structs in cdylib vs fltk-cst-core) is a known architectural ambiguity not resolved in this respond round. Added `TODO(rust-cst-node-pub-ctor)` to `TODO.md` and `TODO(rust-cst-node-pub-ctor)` comment at `gsm2tree_rs.py` `_node_block` (line preceding the `#[pyclass]` emit). Resolution options logged in the TODO entry.
- Severity assessment: §4 item 1 acceptance criterion (pure-Rust node-subtree construction without GIL) remains partially unmet. Node struct fields and constructors are not accessible cross-crate; GIL-free node-level test cannot be written until the TODO is resolved.

reuse-1:
- Disposition: TODO(extract-rule-name-to-class-name)
- Action: Already tracked as `TODO(extract-rule-name-to-class-name)` in `TODO.md` and `gsm2tree_rs.py:18`. No new action needed; finding confirms the existing TODO.
- Severity assessment: 4 independent copies of the same transform; a behavioral change requires 4-site edit. Not blocking any current acceptance criterion.

reuse-2 / quality-1 / efficiency-1 (FLTK_NATIVE_SPAN_TYPE duplicate block):
- Disposition: Fixed
- Action: Added `get_span_type(py)` free function to the preamble in `gsm2tree_rs.py:_preamble`; replaced 10 inline `FLTK_NATIVE_SPAN_TYPE.get_or_try_init` blocks across all per-method generators with `let span_type = get_span_type(py)?;`. Regenerated all 4 `.rs` files. Test `test_get_span_type_helper_emitted` verifies absence of per-method inline blocks.
- Severity assessment: 10 duplicated 6-line blocks per generated file (231 copies in `cst_fegen.rs`); per-call overhead on every CST accessor; future bug in init logic requires 10-site fix. Now centralized.

quality-2 / efficiency-2 (span getter/to_pyobject drops source):
- Disposition: TODO(rust-cst-span-getter-source-loss) — same as errhandling-3.
- See errhandling-3 entry above.

quality-3:
- Disposition: Fixed
- Action: Added `extend_children_fn` to `_protocol_class_for_model` in `gsm2tree.py:577-580`; regenerated `fltk_cst_protocol.py`, `bootstrap_cst_protocol.py`, `toy_cst_protocol.py`, `unparsefmt_cst_protocol.py`.
- Severity assessment: `extend_children` is called by every generated parser's inline-to-parent paths but was absent from the protocol; static analysis against the protocol could not verify the call's validity.

efficiency-3 (cross-backend enum __hash__ allocates PyString):
- Disposition: Won't-Do
- Action: No change.
- Rationale: Design comment at `gsm2tree_rs.py:204-206` explicitly defers this: "amortizing this via GILOnceCell is deferred." The CPython salted-string-hash requirement (AC4) forces the `PyString` today. A `GILOnceCell<isize>` per variant would cache the computed hash; revisit if enum hashing appears on a profile. Active harm: changing it now requires design-level change to the hash protocol and would invalidate the existing AC4 tests. No regression introduced by current code.

checkpoint-correctness-1 (parse path TypeError regression):
- Disposition: TODO(backend-with-source-signature continuation)
- Action: The §2.5 parse-path work (parser emitting `fltk._native.Span` / `Span.with_source`) is the documented fix; it depends on `backend-with-source-signature` prerequisite which landed in increment 5. Until §2.5 is implemented, the Rust backend cannot parse. The `test_fltk2gsm_behavioral_equivalence` Rust-backend arm remains a live red test.
- Severity assessment: Rust backend cannot parse any input (regression from base 6fd32e7 where `span: PyObject` accepted `terminalsrc.Span`). Documented and expected per the incremental staging plan.

checkpoint-correctness-2:
- Disposition: Fixed — same as correctness-1/errhandling-2 above.

---

## Rework round (commit 622976c)

### errhandling-3 / quality-2 — TODO(rust-cst-span-getter-source-loss) [CORRECTED]

Prior disposition failed: slug existed only in `dispositions-interim.md`; no `TODO.md` entry and no code comment.

Actions taken:
- Added `## rust-cst-span-getter-source-loss` entry to `TODO.md` documenting the worsened surface, the fix path (`pub fn source_text()` on `fltk-cst-core Span` + `with_source` in getter/`to_pyobject`), and the §2.5 prerequisite.
- Added `// TODO(rust-cst-span-getter-source-loss)` comment in `_span_getter_setter` at `fltk/fegen/gsm2tree_rs.py` (the span getter emit).
- Added `// TODO(rust-cst-span-getter-source-loss)` comment in `_child_enum_block` at `fltk/fegen/gsm2tree_rs.py` (the `to_pyobject` Span arm emit).
- Regenerated all 4 `.rs` files; the TODO comment now appears in the emitted `to_pyobject` Span arms.
- Disposition: TODO(rust-cst-span-getter-source-loss) — both pieces of convention now present.

### checkpoint-correctness-1 — TODO(rust-cst-parse-path-native-span) [CORRECTED]

Prior disposition failed: slug `backend-with-source-signature continuation` existed nowhere (the `backend-with-source-signature` TODO was removed in increment 5); live-red AC9 test had no xfail.

Actions taken:
- Added `## rust-cst-parse-path-native-span` entry to `TODO.md` documenting the regression (parser emits `terminalsrc.Span`; Rust setter requires `fltk._native.Span`), the fix path (§2.5 parse-path source work), and noting `test_fltk2gsm_behavioral_equivalence` is xfail pending fix.
- Added `TODO(rust-cst-parse-path-native-span)` comment in the `rust_items` fixture docstring at `tests/test_clean_protocol_consumer_api.py`.
- Added `@pytest.mark.xfail(strict=True)` with `reason=TODO(rust-cst-parse-path-native-span)` reference to `test_fltk2gsm_behavioral_equivalence`.
- Added `@pytest.mark.xfail(strict=True)` to 5 `TestCrossBackendDualShapeDispatch` methods that depend on `rust_items` fixture and were ERRORing (pre-existing at a320715): `test_shape2_rust_backend_dispatches_correctly`, `test_shape2_python_and_rust_structurally_identical`, `test_shape1_rust_backend`, `test_shape1_python_and_rust_structurally_identical`, `test_span_kind_narrows_rust_backend_span_children`.
- Suite now: 47 passed, 6 xfailed — no errors, no silent reds.
- Disposition: TODO(rust-cst-parse-path-native-span) — both pieces of convention present; regression visibly surfaced.
