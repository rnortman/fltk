# Judge verdict — interim review (rust-cst-native-span)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: interim (intermediate; project deliberately unfinished). Base 6fd32e7..HEAD a320715. Round 1.
Notes: 7 interim + 2 checkpoint files; 18 dispositioned findings.
Note: reviewers reviewed 767315f/f2bf59b; dispositions and verdict are against the fix commit a320715. All claimed fixes verified to have landed at a320715.

## Added TODOs walk

Dispositions referencing a `TODO(slug)`. The TODO-system convention (CLAUDE.md §"TODO System") requires BOTH a `TODO.md` entry AND a `TODO(slug)` code comment; the slug is the join key.

### test-1 / scope-5 — TODO(rust-cst-node-pub-ctor) at gsm2tree_rs.py:435 (_node_block)
Disposition: Fixed (partial) + TODO. Code comment present (`gsm2tree_rs.py:435`); TODO.md entry present (`rust-cst-node-pub-ctor`). Join key intact.
Q1 (worth doing): yes — §4 item-1 is a stated acceptance criterion (pure-Rust GIL-free node-subtree construct/walk/compare). The partial Span-level GIL-free tests landed (`crates/fltk-cst-core/src/lib.rs:15-53`); the node-level test is the remaining gap.
Q2 (design/owner input required): yes — the block is the §2.1-vs-§2.8 tension the design itself left unresolved (node structs in cdylib vs `fltk-cst-core`; generated-output path vs cross-crate `pub`). scope-5 reviewer documents the contradiction explicitly; resolving it (move generated files, build-script `include!`, or `pub` fields + logged deviation) is a design call, not a mechanical edit.
Assessment: TODO acceptable. Both pieces of the convention present; both rubric answers yes.

### reuse-1 — TODO(extract-rule-name-to-class-name) at gsm2tree_rs.py:18
Disposition: confirms pre-existing TODO; no new action. Verified: TODO.md entry present, code comment present (`gsm2tree_rs.py:18`). Finding is the same 4-copy transform the TODO already tracks.
Q1: yes — 4 divergent copies of one transform. Q2: no design cycle, but the work is already a tracked TODO from a prior phase, not created/worsened this iteration; the finding is a confirmation, not a new defer.
Assessment: acceptable — finding correctly maps to an existing, properly-formed TODO. Not this iteration's obligation.

### errhandling-3 / quality-2 — DISPOSITIONED "TODO(rust-cst-span-getter-source-loss)" — NO TODO EXISTS
File: span getter + `<Name>Child::to_pyobject` Span arm (`gsm2tree_rs.py` ~512, ~371); generated in all four `.rs`.
Claim: getter/`to_pyobject` reconstruct `fltk._native.Span(start, end)` sourceless even when the stored native `Span` carries source; `.text()`/`.has_source()` silently return None/False through the Python boundary.
Disposition mechanics — FAIL: grep of the entire tree for `rust-cst-span-getter-source-loss` returns hits ONLY in `dispositions-interim.md`. No `TODO.md` entry; no `TODO(rust-cst-span-getter-source-loss)` code comment. The disposition explicitly declines to add a TODO.md entry, relying on the increment-2 implementation-log deviation note (`implementation-log.md:28`) — but that note is prose and does NOT carry the slug. This is a fabricated `TODO(slug)` disposition: the join key exists nowhere in the codebase. Fails CLAUDE.md §"TODO System" (both pieces required).
Q1 (worth doing): yes — without it, §2.6 `fltk2gsm` `text_or_raise()` reads through child accessors return None even after §2.5 attaches source (quality-2 traces this; the source is stripped at every boundary crossing, not gated on §2.5).
Q2 (design/owner input required): no — the fix is mechanical: add `pub fn source_text(&self) -> Option<SourceText>` to `fltk-cst-core`'s `Span` and have the getter/`to_pyobject` call `with_source` when source is present. quality-2 gives the exact patch. No design cycle.
Furthermore: this iteration WORSENED the behavior. At base (`src/cst_generated.rs@6fd32e7:112`) `span: PyObject` stored the set object and the getter returned that same object, source intact. The new getter reconstructs sourceless every call. Per rubric: a problem this iteration created/worsened cannot be silently deferred — must be fixed or ESCALATED for visibility. A disposition that invents a slug present in no TODO and no comment is precisely "silently deferred."
Assessment: disposition wrong on two counts — (a) no real TODO (fabricated slug), (b) iteration worsened the surface so deferral must be visible. Disputed.

### checkpoint-correctness-1 — DISPOSITIONED "TODO(backend-with-source-signature continuation)" — NO TODO EXISTS; red test not surfaced
File: parser still emits `terminalsrc.Span` into the now-strict native setter; Rust backend cannot parse (TypeError at first node construction). AC9 test `test_fltk2gsm_behavioral_equivalence` (`tests/test_clean_protocol_consumer_api.py:334`) is live-red on the Rust arm.
Disposition mechanics — FAIL: slug `backend-with-source-signature continuation` exists in no TODO.md entry and no code comment (the `backend-with-source-signature` entry was *removed* from TODO.md in increment 5, log:58). The disposition names a TODO that does not exist.
Q1 (worth doing): yes — §2.5 source-bearing parse path is committed, in-scope, future work.
Q2 (design/owner input required): no — it is sequenced implementation work, not a design call. So strictly this is "do it later in the planned sequence," which the USER DECISION (design §5: "implementers can sequence this in whatever way works") explicitly permits.
Furthermore: this iteration CREATED the regression — increment 2 tightened the setter while the parser still feeds the old type; at base the Rust parse path worked (checkpoint-correctness-1 establishes this as a regression relative to base). Per rubric, a regression this iteration created cannot be silently deferred; it must be surfaced. The checkpoint reviewer's own sanctioned remedy — "mark `test_fltk2gsm_behavioral_equivalence`'s Rust-backend arm xfail with a `TODO(backend-with-source-signature)` reference so the suite reflects the documented deferral rather than a silent red" — was NOT applied. The test remains red with no xfail marker and no live TODO.
Assessment: the *deferral* is legitimate under the incremental USER DECISION; the *surfacing* is absent. A live-red AC test with no xfail and a disposition pointing at a non-existent TODO is a silent regression, not a visible one. Disputed — needs a real surfacing mechanism (xfail marker + a real TODO entry/comment, or fold into the `rust-cst-node-pub-ctor`-style tracked work).

## Other findings walk

### correctness-1 / errhandling-2 / checkpoint-correctness-2 — Fixed
Claim: generic `append`/`extend` silently drop an unrecognized/wrong-rule label (no-label node, or label not extractable to the node's enum) → child stored unlabeled, invisible to label accessors; cross-backend divergence (Python stores label verbatim).
Diff (`gsm2tree_rs.py:589-613`): no-label arm now `Some(lbl) => return Err(PyTypeError::new_err(...))`; labeled arm `else` branch now returns `PyTypeError` naming the rule and enum instead of `None`. Regenerated all four `.rs`.
Assessment: fix addresses the consequence at the named site — loud failure replaces silent label-drop, matching the §3 "fail loudly" stance. Accept.

### correctness-2 — Fixed
Claim: `child_<label>` error message undercounts (caps at 2) for 3+ matches due to early `break`.
Diff (`gsm2tree_rs.py:737-749`): loop now `count += 1` unconditionally and only sets `found` on `count == 1`; no `break`; message reads `{count}` (true total). `maybe_<label>` unchanged (its "at least 2" phrasing was already accurate).
Assessment: count accumulates fully; message accurate. Cosmetic severity, correctly Fixed. Accept.

### errhandling-1 — Fixed
Claim: `self.source.as_ref().unwrap()` at `span.rs:217` is a fragile local invariant; a future guard reorder makes it a silent panic.
Diff (`crates/fltk-cst-core/src/span.rs:218`): `.expect("invariant: source is Some — is_none() guard above returned Err already")`.
Assessment: invariant now documented at the call site; matches the reviewer's sanctioned remedy. Accept.

### errhandling-4 — Won't-Do (sound)
Claim: `_child_enum_block` degenerate path (`not has_span and not child_classes`) emits a node that can't store children, with no generation-time diagnostic.
Rationale: `_rule_info()` (`gsm2tree_rs.py:85-91`) already raises `RuntimeError` for any rule with an empty model (`not model.types`), a superset of the degenerate condition; the `_child_enum_block` path is unreachable, so a second diagnostic is dead code.
Verification: confirmed the guard precedes node emission and covers the superset. Rationale argues active harm (unreachable dead code). 
Assessment: Won't-Do correct — finding's concern is already addressed upstream. Accept.

### security-1 — Won't-Do (sound)
No findings reported by the security reviewer; disposition is a no-op acknowledgment. Security notes independently cleared the untrusted-offset slice path and the `downcast_unchecked` guard. Accept.

### reuse-2 / quality-1 / efficiency-1 — Fixed
Claim: `FLTK_NATIVE_SPAN_TYPE` 6-line init block duplicated ~10×/file (231 copies in `cst_fegen.rs`); per-accessor overhead + 10-site maintenance.
Diff (`gsm2tree_rs.py:180-191`): added preamble free fn `get_span_type(py)`; all ~10 inline blocks replaced with `let span_type = get_span_type(py)?;`. Generator test `test_get_span_type_helper_emitted` (`tests/test_gsm2tree_rs.py:335`) added. Confirmed by the fix-commit diff (~2300-line shrink in `cst_fegen.rs`).
Assessment: duplication centralized; emission test pins it. Accept.

### efficiency-3 — Won't-Do (sound)
Claim: cross-backend enum `__hash__` allocates a `PyString` per call.
Rationale: design comment (`gsm2tree_rs.py:204-206`) explicitly defers GILOnceCell amortization; the CPython salted-string-hash AC4 forces the `PyString` today; changing it now requires a hash-protocol design change and invalidates AC4 tests. No regression introduced.
Verification: the efficiency reviewer itself flagged this "Status: known, accepted cost — not a new regression." Both sides agree.
Assessment: Won't-Do correct — pre-existing, AC-forced, design-deferred. Accept.

### test-2 — Fixed
Claim: `extend_children` emission untested at generator level.
Diff: `test_extend_children_emitted` added (`tests/test_gsm2tree_rs.py:330`). Accept.

### test-3 — Fixed
Claim: `gsm2parser.py` extend_children call-site change untested.
Diff: `test_gsm2parser_extend_children_call_site` added (`fltk/fegen/test_genparser.py:133`); asserts `extend_children` present and `.children.extend(` absent. Accept.

### test-4 — Fixed
Claim: `test_span.py` doesn't test the new `SourceText` form of `with_source`.
Diff: `test_with_source_text_object` added (`tests/test_span.py:66`). Accept.

### quality-3 — Fixed
Claim: `extend_children` called by generated parsers but absent from the protocol.
Diff (`gsm2tree.py:579-581`): `extend_children_fn` added to `_protocol_class_for_model`; protocol modules regenerated (`fltk_cst_protocol.py` +28, others). Accept.

### scope-1 / scope-2 / scope-3 / scope-4 — Fixed (log + fixture regen)
scope-1 (commit hash TBD→ee4a59b), scope-2 (chronological reorder), scope-3 (count aligned to 121) verified in `implementation-log.md` diff. scope-4 (fixture regenerated from `phase4_roundtrip.fltkg`) verified: `tests/rust_cst_fixture/src/cst.rs` +1989 lines now exposing `Config`/`Entry`/`Operator`/`Literal`. Accept all four.

## Disputed items

1. **errhandling-3 / quality-2** — dispositioned `TODO(rust-cst-span-getter-source-loss)` but the slug exists in no `TODO.md` entry and no code comment (fabricated join key). The getter/`to_pyobject` source-drop is a surface this iteration WORSENED relative to base (base preserved the stored span object through the getter). Needed: either (a) implement the mechanical fix (`pub fn source_text` + `with_source` on present source — quality-2 supplies the patch), or (b) create a real TODO — both a `TODO.md` entry AND a `TODO(rust-cst-span-getter-source-loss)` code comment at the getter/`to_pyobject` sites — so the worsened surface is visibly tracked, not silently deferred.

2. **checkpoint-correctness-1** — dispositioned `TODO(backend-with-source-signature continuation)`, a slug that exists nowhere (the `backend-with-source-signature` TODO was removed in increment 5). The Rust parse path is a regression this iteration created; the AC9 test `test_fltk2gsm_behavioral_equivalence` is live-red with no xfail. The deferral is legitimate under the USER DECISION (incremental sequencing), but the regression is not surfaced. Needed: the checkpoint reviewer's sanctioned remedy — mark the Rust-backend arm `xfail` referencing a REAL TODO (entry + comment) for the §2.5 parse-path work — so the suite reflects a documented deferral rather than a silent red.

## Approved

16 findings accepted: 11 Fixed verified (correctness-1/2, errhandling-1/2, reuse-2/quality-1/efficiency-1, quality-3, test-2/3/4, scope-1/2/3/4, checkpoint-correctness-2), 3 Won't-Do sound (errhandling-4, security-1, efficiency-3), 2 TODOs acceptable (rust-cst-node-pub-ctor for test-1/scope-5; extract-rule-name-to-class-name for reuse-1).

---

## Verdict: REWORK

Two dispositions wrong, both the same lazy-responder failure mode (dispositioned `TODO(slug)` where the slug exists in neither `TODO.md` nor any code comment — no join key), compounded by the rubric rule that a surface this iteration created/worsened cannot be silently deferred:

- **errhandling-3 / quality-2** — fabricated `TODO(rust-cst-span-getter-source-loss)`; getter source-drop worsened vs base.
- **checkpoint-correctness-1** — fabricated `TODO(backend-with-source-signature continuation)`; live-red AC9 test unsurfaced (no xfail), regression created this iteration.

Round 1, so REWORK (not ESCALATE): the remedy is mechanical and well-specified for both — create real TODO pairs (and/or apply the supplied fix / xfail marker). Neither is a fundamental design disagreement; the deferrals themselves are legitimate under the incremental USER DECISION, only their surfacing is missing.
