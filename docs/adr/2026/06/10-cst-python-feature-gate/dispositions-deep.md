Style: concise, precise, no padding. Audience: smart LLM/human.

Commit reviewed: 431ab53. Fixes committed: 08dcf9f.

---

errhandling-1:
- Disposition: Fixed
- Action: Rewrote `text_or_raise` to delegate to native `text()` after validating pre-conditions; the duplicate `char_indices` walk and the `unwrap_or(src.len())` both eliminated. span.rs:378-419.
- Severity assessment: The `unwrap_or` was only reachable in truly unreachable code paths (well-formed UTF-8 guarantees every codepoint has a unique start byte), so no observable wrong behavior existed. The fix closes the latent signal-destruction path and eliminates duplicated logic as a bonus.

errhandling-2:
- Disposition: Fixed
- Action: `py_merge` and `py_intersect` now use `map_err(|e| PyValueError::new_err(e.to_string()))` instead of discarding `e` with `|_|`. span.rs:445-458.
- Severity assessment: Current behavior is correct for the single `SourceMismatch` variant; the `#[non_exhaustive]` annotation means any future variant would have silently produced a misleading "cannot merge spans from different sources" message in Python. The fix uses `SpanError::Display` which was introduced in this diff for exactly this purpose.

errhandling-3:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Latent structural asymmetry in `text()` match arms; no current failure path. Reviewer noted no action required unless `text()` is changed.
- Rationale (Won't-Do): `text()` was refactored in this round (single forward pass); the new implementation does not have the described asymmetric match structure. The concern is resolved by the efficiency-1 rewrite.

correctness-1:
- Disposition: Fixed
- Action: Added path/git dep alternatives as comments alongside the version dep in the Cargo.toml template; fixed lint name `unexpected_cfg` → `unexpected_cfgs` in migration note. docs/rust-cst-extension-guide.md:58-62, line 145.
- Severity assessment: A consumer copying the template verbatim and using a local checkout would get a crates.io resolution error with no useful message. Low severity now (no Rust out-of-tree consumers), but the guide is the first artifact such a consumer would read.

test-1:
- Disposition: Fixed
- Action: Added assertions for `Items_Label` and `Trivia_Label` python-off blocks in `test_enum_python_off_block_present`. tests/test_gsm2tree_rs.py:464-482.
- Severity assessment: A generator regression dropping the python-off block for any multi-variant label enum other than `Identifier_Label` would have been undetected by this test.

test-2:
- Disposition: Fixed
- Action: Added `TriviaChild` to `test_child_enum_pyo3_impl_gated`; expanded `test_unconditional_child_enum_partialeq` to loop over both `IdentifierChild` and `TriviaChild`. tests/test_gsm2tree_rs.py:439-457.
- Severity assessment: `TriviaChild` is the span-only child enum (distinct code path through `_child_enum_block`); missing coverage meant a gating or PartialEq regression on that path would pass all generator tests.

test-3:
- Disposition: Fixed
- Action: Removed `test_fegen_register_classes_gated` from `TestRegisterClasses`; the identical assertion lives in `TestFegenGrammar.test_register_classes_present` where it belongs. tests/test_gsm2tree_rs.py:394-399 removed.
- Severity assessment: No regression risk — the assertion is preserved in the right class. The duplicate created false confidence that two independent things were being checked.

test-4:
- Disposition: Fixed
- Action: Added `assert_eq!(merged.text(), Some("hello world".to_string()))` to `span_merge_same_source_ok`; added `assert_eq!(inter.text(), Some("lo w".to_string()))` to `span_intersect_overlap_ok`. crates/fltk-cst-core/src/lib.rs:145, 175.
- Severity assessment: A bug dropping the source arc in merge/intersect result would pass the old coordinate-only assertions; `text()` returning `None` would have been undetected in the core unit tests (covered in spike, but not independently at the unit level).

test-5:
- Disposition: Fixed
- Action: Added `span_text_zero_to_zero` test for `Span::new_with_source(0, 0, &src)` asserting `text() == Some("")`. crates/fltk-cst-core/src/lib.rs:138-143.
- Severity assessment: The `end == 0` fast path in `text()` was real and untested. The efficiency-1 rewrite replaced the whole implementation; the new test pins the start=0,end=0 behavior in both old and new code.

reuse-1:
- Disposition: Fixed
- Action: Same fix as errhandling-2 — `e.to_string()` uses `SpanError::Display` which is the single source of truth for the message. span.rs:447, 457.
- Severity assessment: Three copies of the message string would diverge independently; `SpanError::Display` was introduced specifically to be authoritative.

reuse-2:
- Disposition: Fixed
- Action: Replaced the redundant `$(MAKE) gen-rust-cst` invocation for `crates/fltk-cst-spike/src/cst.rs` with `cp src/cst_generated.rs crates/fltk-cst-spike/src/cst.rs`; removed the TODO comment. Makefile:131-132.
- Severity assessment: The two outputs were byte-identical (same grammar, same generator); the separate subprocess per `make gencode` was pure overhead and the implicit identity invariant was invisible. The `cp` makes the identity explicit, reduces one `uv run python` subprocess per regen, and eliminates the dual-maintenance surface.

quality-1:
- Disposition: Fixed
- Action: Rewrote `text_or_raise` to delegate to `text()` after validating pre-conditions explicitly. Eliminates duplicated `char_indices` walk. span.rs:378-419. (Same fix as errhandling-1.)
- Severity assessment: Two copies of codepoint-to-byte translation logic with subtle asymmetry; any future change to one required manual replication in the other.

quality-2:
- Disposition: Fixed
- Action: Extracted `variant_names` (NodeKind) and `label_variants` (label enums) local variables before the dual-cfg loops; both loops iterate the shared variable. gsm2tree_rs.py:326-341, 392-410.
- Severity assessment: The two parallel loops over independent `rule_info` iterations shared data only by convention; a future generator change updating one loop silently would produce mismatched python-on/python-off enum variants that compile in one mode but differ in the other.

quality-3:
- Disposition: Fixed
- Action: Removed default value from `method_name` parameter of `_label_from_pyobject_match`; both call sites now pass `method_name` explicitly. gsm2tree_rs.py:708, 755.
- Severity assessment: A future call site omitting `method_name` would silently use `"append"` regardless of the actual method, producing misleading type error messages to downstream consumers.

efficiency-1:
- Disposition: Fixed
- Action: Rewrote `text()` to use a single forward `char_indices` loop that collects both byte offsets in one pass, breaking early after finding `byte_end`. Eliminates two separate `nth()` restarts from byte 0 and the third `chars().count()` scan for end-of-source spans. span.rs:237-285.
- Severity assessment: Previous implementation was O(start) + O(end) + O(src.len()) for root/trailing spans. The public native `text()` method is intended for use by a phase-2 Rust parser traversing all nodes; quadratic scaling on large inputs would dominate CST read cost. New implementation is O(end) worst case.

efficiency-2:
- Disposition: Fixed
- Action: Same fix as reuse-2 — `cp src/cst_generated.rs crates/fltk-cst-spike/src/cst.rs` replaces the second generator invocation. Makefile:131-132.
- Severity assessment: One redundant `uv run python` subprocess per `make gencode` invocation eliminated. Dev-time only; low individual impact but recurring on every regen cycle.
