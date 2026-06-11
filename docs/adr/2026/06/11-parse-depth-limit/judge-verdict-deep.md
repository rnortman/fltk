# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: deep. Base ef315be..HEAD de56edb (reviewed commit d442f56; fixes in de56edb). Round 1.
Notes: 7 reviewer files (correctness and efficiency: no findings). 13 findings, 12 Fixed + 1 Won't-Do.

## Added TODOs walk

No finding was dispositioned TODO. The diff adds `TODO(rust-cst-accessor-clone-efficiency)` comments only inside the newly regenerated `tests/rust_parser_fixture/src/cst.rs` — generator-template propagation of a pre-existing slug (entry at `TODO.md:27`, separate ADR dir exists), not a responder deferral. Not in scope for rubric scoring.

## Other findings walk

### errhandling-1 — Fixed
Claim: panic in `apply_inner` skips the `depth` decrement at `memo.rs:168`; a caller catching pyo3 `PanicException` and reusing the instance gets a corrupted counter with no diagnosable cause. Asked for (a) spent-on-panic guard or (b) docs at `apply` + `PyParser` level.
Evidence: de56edb adds a "# Panic and `PanicException` safety" section to the `PackratState` doc (memo.rs:80-89): pyo3 converts panics to `PanicException` (distinct from `RecursionError`); treat any `PanicException` as instance-spent.
Assessment: responder chose (b); substance delivered (the pyo3-conversion note the reviewer specifically required). Placement is `PackratState` rather than `apply`/`PyParser` — weaker than the literal ask, but the scenario presupposes a memo-invariant panic (an internal core bug; the panic sites are unreachable-by-design assertions) plus a caller that catches `PanicException` and continues. Severity nit/should-fix; cause is now documented and greppable. Accept.

### errhandling-2 — Fixed
Claim: `error_message()` on a depth-exceeded instance returns stale error-tracker state; on-call cannot distinguish no-match from depth-abort. Option (a): distinct string when flag set.
Evidence: generator template at `gsm2parser_rs.py:380-391` emits a `depth_exceeded()` check returning `"parse aborted: depth limit exceeded (max_depth = N)"`; both regenerated fixture parsers carry it (`tests/rust_parser_fixture/src/parser.rs:104-112`, `tests/rust_cst_fegen/src/parser.rs:89-97`); generator test `test_python_bindings_error_message_depth_check` pins it. Exactly option (a).
Assessment: accept.

### errhandling-3 — Fixed (same gap as test-2)
Claim: `max_depth = 0` degenerate semantics untested; `>=`→`>` regression would be silent.
Evidence: `test_depth_limit_t5_zero_max_depth` added at `memo_toy.rs:565-575` — asserts first apply returns `None` and flag set, exactly the reviewer's one-liner. Passes (cargo: 13/13).
Assessment: accept.

### security-1 — Fixed
Claim: generated header overclaims "instead of overflowing the native stack"; small-stack threads / fat-rule grammars can still SIGSEGV below `DEFAULT_MAX_DEPTH` — false assurance.
Evidence: both `DEFAULT_MAX_DEPTH` doc (memo.rs:64-72) and header template (`gsm2parser_rs.py:258-267`) now state the ~8 MiB / ~5-7 frames-per-level sizing assumption and instruct smaller-stack or deep-per-rule callers to lower `max_depth` proportionally or size the stack; propagated to both regenerated fixture headers. Matches the suggested one-sentence-in-template fix.
Assessment: accept.

### security-2 — Won't-Do
Claim: flag-outranks-result contract is documentation-only for Rust-native callers; truncated-`Some` silently accepted by `if let Some(r)` shape → parser-differential on attacker-chosen input. Suggested fix self-labeled "(future hardening, beyond this change's scope)": a checked `Result`-returning entry point; "at minimum keep the discard-on-flag sentence on every generated `apply__parse_X` doc".
Rationale: design §2 explicitly dispositioned this residual risk (bindings enforce; Rust-native callers read docs); a checked entry point is a new design decision, additive later without breakage.
Verification: design §2 and §4 confirm the explicit disposition ("The generated bindings enforce this (§4); the generated `Parser` docs state it for Rust-native callers"). Reviewer's own note records the finding as "residual risk, not a missed case". Generated surface carries the contract at the header and on `depth_exceeded()` ("the parse result (even if `Some`) must be discarded… instance is spent", `rust_parser_fixture/src/parser.rs:129-131`); the per-`apply__parse_X` doc sentence was not added, but that clause sat inside the reviewer's own out-of-scope framing.
Assessment: Won't-Do sound — the design (ground truth) made this call deliberately; the checked-wrapper is a follow-on design decision, correctly routed there. Accept.

### test-1 — Fixed
Claim: no generator-level coverage of the three new bindings codegen paths (PyRecursionError import, depth_exceeded guard, getters) or the constructor signature.
Evidence: five tests added in `test_gsm2parser_rs.py:1034-1089` asserting import, guard + `PyRecursionError::new_err`, both getters, `max_depth = None` + `Option<u32>` in the constructor signature — all scoped to the bindings block as the reviewer specified. All five pass.
Assessment: accept.

### test-2 — Fixed
Same gap as errhandling-3; same fix verified above. Reviewer's optional bindings-level mirror (`Parser("42", max_depth=0)`) not added — optional per the finding's own wording; cargo test covers the guard condition. Accept.

### test-3 — Fixed
Claim: parity corpus has no FAIL entries for `nest`/`nest_sum`; failure path of the new right-recursive alt functions unparity-covered.
Evidence: `("nest", "(42", FAIL)` and `("nest_sum", "+42", FAIL)` added at `test_rust_parser_parity_fixture.py:106-108` — the exact entries requested. Parity suite passes (86/86 incl. bindings file).
Assessment: accept.

### test-4 — Fixed
Claim: T5 spent-instance test re-calls the same rule at the same pos, so cached-`Failure` and sticky-flag are indistinguishable; reviewer offered (a) comment or (b) cold-cache different-rule second call.
Evidence: second call is now `apply__parse_nest_sum(0)` (cold cache) and the docstring states T3 is the definitive stickiness proof (`test_rust_parser_fixture_bindings.py:77-92`). Both (a) and (b) delivered.
Assessment: accept.

### reuse-1 — Fixed
Claim: T1-T4 inline `vec![…].map(to_owned)` duplicates the existing `tokens()` helper.
Evidence: all four sites now use `tokens("(((1)))")` / `tokens("(1)(1)")` / `tokens("1+(((9)))")` (memo_toy.rs diff in de56edb).
Assessment: accept.

### quality-1 — Fixed
Claim: `PackratState::max_depth` `pub` field is an asymmetric leaky abstraction; mid-parse mutation silent.
Evidence: field now private (memo.rs:99-100); `set_max_depth`/`max_depth()`/`with_max_depth` added (memo.rs:122-137) with "call before parsing" doc.
Assessment: accept.

### quality-2 — Fixed (subsumed by quality-1)
Claim: `DepthParser::new` two-step construct-then-mutate depends on the pub field; wanted `with_max_depth`.
Evidence: `DepthParser::new` now uses `PackratState::with_max_depth(max_depth)` (memo_toy.rs:233-241).
Assessment: accept.

### quality-3 — Fixed
Claim: generated `set_max_depth`/`max_depth` poke the field directly, coupling the generator to `PackratState` layout.
Evidence: generator now emits `self.packrat.set_max_depth(max_depth)` / `self.packrat.max_depth()` (`gsm2parser_rs.py:406,409`); both regenerated fixture parsers reflect it and compile (cargo tests pass against the now-private field, proving no stray field access remains).
Assessment: accept.

## Disputed items

None.

## Approved

13 findings: 12 Fixed verified (two pairs share a fix: errhandling-3/test-2, quality-1/quality-2), 1 Won't-Do sound.

---

## Verdict: APPROVED

All dispositions acceptable. Fixes verified against the de56edb diff; cargo (13/13 memo_toy) and pytest (5 new generator tests; 86 bindings+parity) pass.
