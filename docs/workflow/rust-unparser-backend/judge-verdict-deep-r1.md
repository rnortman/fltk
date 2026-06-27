# Judge verdict — deep review

Phase: deep. Base 8a29f254..HEAD 8407c86b. Round 1.
Scope: `crates/fltk-unparser-core/src/{doc,accumulator,resolve}.rs` (batch 1 port).
Notes: 7 reviewer files (errhandling + security: no findings); 17 dispositioned findings.
Verification: `cargo test -p fltk-unparser-core --no-default-features` → 64 passed, 0 failed.

## Added TODOs walk

### efficiency-2 — TODO(unparser-join-sep-resolve) at resolve.rs:124 (inside `expand_joins`, the `Some(separator.clone())` site)
TODO hygiene: both pieces present and in sync — `TODO(unparser-join-sep-resolve)` comment at resolve.rs:124 marks the exact site, matching `TODO.md` entry `## unparser-join-sep-resolve` (added in this diff) with description + location. Slug joins correctly.

Q1 (worth doing): yes — `expand_joins` stores a clone of the same `separator` `Rc` as `preserved_trivia` in each of an M-element join's M-1 gaps, and resolution re-runs the full 4-pass pipeline on the byte-identical subtree once per gap (M-1 times). Each pass allocates `VecDeque`/`Vec` working buffers in `resolve_concat_patterns`, so for a `join from … to …` over thousands of elements this is O(M) redundant pipeline runs — a real, if bounded, per-render cost worth eliminating eventually.

Q2 (design/owner input required): yes — the fix has genuine design surface, not a mechanical one-liner. The two candidate approaches each carry parity-correctness stakes (cross-backend rendered-string parity is the project's whole contract here): (a) pre-resolve the separator once in `expand_joins` and store the resolved form — but `resolve_rc(trivia)` still runs again in `mutate_after_sep`/`mutate_sep_before`/`mutate_standalone_sep`/`resolve_spacing`, so this relies on resolution being idempotent on an already-resolved doc, which must be verified; (b) memoize `resolve_rc` on `Rc::as_ptr` — but the mutators are plain `fn` pointers (`type Mutator = fn(&VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>>`) that call `resolve_rc` internally, so threading a cache through them means changing the mutator-dispatch architecture or reintroducing a TLS/RefCell cache (the latter being exactly what correctness-1 just removed from `doc.rs`). Choosing the approach is a deliberate decision, not "just do it now."

Not iteration-created harm: the redundant resolution is faithful to the Python backend, which also calls `resolve_spacing_specs(sep_spec.preserved_trivia)` per gap (reviewer's own note). So the "problem this iteration created cannot be deferred" clause does not bite — it is a pre-existing inefficiency carried over, bounded because the generator rejects group/nest/join separators (each redundant run is small).

Assessment: YES to both → TODO acceptable. Single TODO in the phase (no pile).

## Other findings walk

### correctness-1 — Fixed
Claim: `Doc::drop` reaches `DROP_SENTINEL.with(...)` to swap single-`Rc<Doc>` child slots during iterative teardown; `LocalKey::with` panics if a `Doc` is dropped during TLS-destruction ordering after `DROP_SENTINEL` is gone, and a panic out of `drop` mid-unwind aborts the process. Consequence: uncatchable process abort.
Code: `thread_local!`/`DROP_SENTINEL` fully removed (grep confirms only a doc-comment mention survives, doc.rs:90). `take_children` (doc.rs:94-128) now swaps single-child slots with `std::mem::replace(content, Rc::new(Doc::Nil))` (lines 100, 107) and `.take()`s the `SeparatorSpec` Options. Comment (85-93) documents the hazard + no-TLS-in-drop CST precedent. `deep_{nest,afterspec,beforespec,group,concat,join}_chain` 200k-deep drop tests all pass.
Assessment: fix removes the TLS window entirely at the named site; matches the iterative-teardown precedent. Both sides agree; finding valid. Accept.

### test-1 — Fixed
Claim: `mutate_text_newline` (Text("\n") + SeparatorSpec spacing=Some → HardLine{0}) had no test. Consequence: wrong-field/string/index bug undetected.
Code: `text_newline_before_separator_becomes_hardline` (resolve.rs:1052-1057) drives `cat([text("\n"), sep(Some(line()),None,false), text("x")])` → asserts `cat([hardline(0), text("x")])`. Traced: ws[0]=Text("\n"), ws[1]=SeparatorSpec(Some) → mutator fires, both consumed, HardLine{0} emitted. Genuinely exercises the path. Test passes.
Assessment: fix addresses the gap at the named function. Accept.

### test-2 — Fixed
Claim: four `_extract_boundary_specs` edge cases (only-leading/only-trailing/all-specs/empty) unported.
Code: `extract_boundary_specs_only_leading` (1060), `_only_trailing` (1074), `_all_specs` (1088), `_empty_list` (1102) all present and passing; `_all_specs` correctly asserts remaining empty + trailing=[after(line)]. These pin exactly the boundaries the quality-2/efficiency-3 linearization touches.
Assessment: complete. Accept.

### test-3 — Fixed
Claim: the `resolve_spacing` "neither preserved trivia nor spacing" assert (only guard against silent corruption of a malformed triple) had no test.
Code: `#[should_panic(expected = "Separator has neither preserved trivia nor spacing")]` test `separator_without_trivia_or_spacing_in_triple_panics` (1112-1118) drives `after(line)/sep(None,None,false)/before(line)` → `mutate_after_sep_before` → `resolve_spacing` assert (640-643). Passes (should-panic confirmed in run).
Assessment: fix verifies the guard at the named site. Accept.

### test-4 — Fixed
Claim: symmetric `pop_nest` wrong-nesting guard untested (only pop_group/pop_join had `#[should_panic]`).
Code: `pop_nest_rejects_wrong_nesting` (accumulator.rs:399-402) — `push_group().pop_nest()` expects panic "Expected Nest". Passes.
Assessment: Accept.

### test-5 — Fixed
Claim: eight multi-level / consecutive-spec extraction tests unported; `consecutive_leading_specs_in_group` is the original regression target.
Code: all eight present (resolve.rs:1135, 1171, 1198, 1235, 1258, 1277, 1306, 1331), including the detailed `consecutive_leading_specs_in_group` scenario. All pass against the port.
Assessment: complete; confirms pass-ordering interactions are covered. Accept.

### test-6 — Fixed
Claim: `pick_spacing_with_blank_lines` "separator HardLine wins" branch unexercised.
Code: `separator_hardline_blank_lines_win_over_after_spec` (1120-1132) — `after(line)` + `sep(Some(hardline(2)),None,true)` → asserts `hardline(2)`. Traced: `mutate_after_sep` → `pick_spacing_with_blank_lines(line, hardline(2))`, sep_bl=2>0, primary=line not HardLine → primary_has_fewer → returns hardline(2). Exercises the branch. Passes.
Assessment: Accept.

### test-7 — Won't-Do
Claim: `add_trivia_sets_flag` reads private `last_was_trivia` directly — brittle, and (reviewer asserts) redundant with `pop_propagates_trivia_state_to_parent`. Consequence stated is purely brittleness (a safe enum refactor would break it) — a nit, no behavioral defect.
Rationale: same-module private access is idiomatic Rust `#[cfg(test)]`; the test uniquely covers `add_non_trivia` *clearing* the flag (`assert!(!acc.last_was_trivia)` at accumulator.rs:276), which the cited `pop_propagates_trivia_state_to_parent` (377-384) does not — that test only does `add_trivia` then `pop`. `last_was_trivia == false` is not observable through the rendered `Doc` by any other test.
Verification: walked the suite — `pop_propagates...` exercises only the add_trivia→true path; `add_accumulator_nil_keeps_self_trivia_state` observes true-preservation; no test observes the add_non_trivia→false reset behaviorally. Responder's redundancy rebuttal is correct.
Assessment: the reviewer's "delete it / redundant" premise is false (verified), and the consequence is a nit with no real harm. Won't-Do sound. Accept.

### reuse-1 — Won't-Do
Claim: `concat_rc` (resolve.rs:76-90) duplicates `doc::concat`'s (doc.rs:200-222) flatten/drop-Nil/collapse normalization; a future divergence would mean generated code and resolver normalize the same tree differently — a silent correctness gap.
Rationale: unifying pessimizes the public-API hot path — `concat` moves nested-`Concat` children via `&mut`/`append` (no clone), whereas `concat_rc` must `inner.iter().cloned()` each child `Rc` (can't move out of a shared `Rc<Doc>`); delegating either direction forces extra `Rc` allocs/clones on the per-rule `doc()` path. The two differ irreducibly in element/return type (`Doc` vs `Rc<Doc>`), so a shared body needs a generic trait abstraction for no behavioral gain. Divergence risk is controlled by bidirectional doc-comment cross-refs + the cross-backend parity suite.
Verification: confirmed `concat` uses move-based `append` (doc.rs:206), `concat_rc` uses `.cloned()` (resolve.rs:80) — the move/clone asymmetry is real; a generic unification of two ~15-line functions adds more complexity than the duplication. Responder argues concrete active harm (hot-path refcount churn) with a concrete mitigation, not "out of scope."
Assessment: sound engineering call on a reuse-should-fix. Accept.

### reuse-2 — Fixed
Claim: four test-local helpers (`line`/`softline`/`hardline`/`nil`) redefined verbatim, risking silent divergence from `doc.rs` constructors.
Code: replaced with `use crate::doc::{hardline, line, nil, softline, text};` (resolve.rs:699). Local bodies gone.
Assessment: Accept.

### quality-1 / efficiency-4 — Fixed (one change)
Claim: `resolve_spacing_specs(&Doc)` deep-clones the whole tree on entry (`Rc::new(doc.clone())`), transiently doubling Doc memory once per top-level unparse; the cloned top node is discarded immediately by `expand_joins`.
Code: signature now `pub fn resolve_spacing_specs(doc: Doc) -> Doc` with `Rc::new(doc)` (resolve.rs:39-43); all in-crate call sites pass by value. Deviation from design §2.1 (`&Doc`) recorded in implementation-log.md.
Public-API note: `fltk-unparser-core` is introduced in this very batch (absent at base 8a29f254), so no out-of-tree consumer can yet depend on the old signature — not a breaking change, and the reviewer recommended exactly this. Deep clone eliminated.
Assessment: fix addresses the consequence at the named site. Accept.

### quality-2 / efficiency-3 — Fixed (one change)
Claim: `extract_boundary_specs` used `insert(0, …)` (O(t²)) for trailing and `remove(0)` (O(n·l)) for leading — quadratic front-shifting on Concat levels with many consecutive trivia regions.
Code: trailing run now `push(docs.pop())` + one `reverse()` (resolve.rs:208-215); leading run `take_while().count()` + `drain(..k)` (218-222). Behavior byte-identical, pinned by test-2's edge cases (all pass).
Assessment: linear now, semantics preserved. Accept.

### efficiency-1 — Fixed
Claim: `doc()` clones an `Rc` per chain node (`self.head.clone()` + `node.tail.clone()` per node) just to traverse — ~2N redundant refcount ops on a hot path.
Code: chain now walked by borrow — `let mut current = &self.head; … current = &node.tail;` (accumulator.rs:245-248); only `node.doc.clone()` (required for `concat`) remains.
Assessment: Accept.

## Disputed items

None.

## Approved

17 findings: 14 Fixed (verified against diff + 64-test green run), 2 Won't-Do sound (test-7, reuse-1), 1 TODO acceptable (efficiency-2 / unparser-join-sep-resolve). errhandling + security reported no findings.

---

## Verdict: APPROVED

All dispositions acceptable. Every Fixed claim verified at its named site and corroborated by a clean `cargo test` run (64/64). Both Won't-Do rationales survive source-backed scrutiny (the redundancy/brittleness premises do not hold up). The single TODO answers YES to both rubric questions — a real-but-bounded, Python-faithful (not iteration-created) optimization whose fix carries genuine parity-correctness design surface — and has correct TODO.md/comment hygiene. Commit 8407c86b70c856df81b9634bc045098dfcf1afcd.
