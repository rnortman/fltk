Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: d442f56. Fixes applied in: de56edb.

---

errhandling-1:
- Disposition: Fixed
- Action: Added `# Panic and PanicException safety` section to `PackratState` doc (memo.rs:72-86). Explains that panic inside `apply_inner` skips depth decrement; pyo3 converts Rust panics to `PanicException` (distinct from `RecursionError`); any `PanicException` from a parser call means the instance is spent.
- Severity assessment: Post-panic instance reuse would give a stale depth counter, silently triggering `RecursionError` on shallow inputs. Without the doc, Python callers catching `PanicException` have no signal that the instance is corrupted.

errhandling-2:
- Disposition: Fixed
- Action: Generated `Parser::error_message()` now checks `self.packrat.depth_exceeded()` first and returns `"parse aborted: depth limit exceeded (max_depth = N)"` when set (gsm2parser_rs.py:377-390). Regenerated fixture parsers pick this up. Added generator test `test_python_bindings_error_message_depth_check`.
- Severity assessment: Without this, any diagnostic path calling `error_message()` after a depth-exceeded parse gets the stale error-tracker state — a confusing match-failure message at an arbitrary interior position, with no indication of the true cause.

errhandling-3:
- Disposition: Fixed
- Action: Added `test_depth_limit_t5_zero_max_depth` in memo_toy.rs (same finding as test-2).
- Severity assessment: `>=` → `>` regression would silently allow one apply with max_depth=0, violating the documented degenerate semantics.

security-1:
- Disposition: Fixed
- Action: Qualified both `DEFAULT_MAX_DEPTH` doc (memo.rs:64-70) and generated header template (gsm2parser_rs.py:258-270): "The default limit is sized for an ~8 MiB stack and ~5-7 native frames per rule application. Callers on smaller thread stacks … must lower max_depth proportionally or size the stack accordingly."
- Severity assessment: The overclaim was an implicit false assurance — consumers on 2 MiB spawned threads or fat-rule grammars could still SIGSEGV while believing the limit protects them.

security-2:
- Disposition: Won't-Do
- Action: No change.
- Severity assessment: A Rust-native caller who omits the depth_exceeded() check silently accepts a wrong parse tree on attacker-crafted deep inputs. Real, but explicitly dispositioned as residual risk in the design (§2): Python bindings enforce it; Rust-native callers must read the docs. A checked-wrapper return type is out of this change's scope and would be additive — it can be added later without breaking existing callers.
- Rationale (Won't-Do): The design explicitly named this residual risk and accepted it. Adding a checked entry point is a new design decision, not a fix to a finding. It would not remove the raw `apply__parse_X` methods (backward compat), so both paths would coexist. The correct place to make this call is in a follow-on design, not in a respond-mode patch.

test-1:
- Disposition: Fixed
- Action: Added five generator tests to test_gsm2parser_rs.py: `test_python_bindings_has_recursion_error_import`, `test_python_bindings_has_depth_exceeded_guard`, `test_python_bindings_has_max_depth_getter`, `test_python_bindings_constructor_has_max_depth_param`, `test_python_bindings_error_message_depth_check`. All five assert against the generated source string scoped to the bindings block.
- Severity assessment: Without these, a regression dropping the PyRecursionError import, the depth_exceeded guard, or the getters would only surface when the fixture extension is rebuilt — a slower, less reliable signal.

test-2:
- Disposition: Fixed
- Action: Same fix as errhandling-3 (they are the same test gap).

test-3:
- Disposition: Fixed
- Action: Added `("nest", "(42", FAIL)` and `("nest_sum", "+42", FAIL)` to the parity corpus in test_rust_parser_parity_fixture.py.
- Severity assessment: The failure paths of the right-recursive `nest` alt functions were unparity-tested. A generator bug accepting malformed input would be undetected.

test-4:
- Disposition: Fixed
- Action: `test_t5_spent_instance_raises_on_subsequent_call` now calls `apply__parse_nest_sum` (different rule, cold cache) on the second call. Comment explains the T3 cargo test is the definitive stickiness proof; this test pins the binding-layer observable contract independently of cache state.
- Severity assessment: Low — T3 already proves stickiness. But the revised test is a stronger binding-layer proof and the comment removes the subtle ambiguity.

reuse-1:
- Disposition: Fixed
- Action: T1-T4 in memo_toy.rs now use `tokens()` helper (e.g. `tokens("(((1)))")`) instead of inline `vec![...].into_iter().map(|s| s.to_owned()).collect()`.
- Severity assessment: Minor consistency issue; if the token representation ever changes, the depth tests would silently diverge from the rest of the test infrastructure.

quality-1:
- Disposition: Fixed
- Action: `PackratState::max_depth` is now private. Added `set_max_depth(&mut self, max_depth: u32)`, `max_depth(&self) -> u32`, and `with_max_depth(max_depth: u32) -> Self` methods on `PackratState` (memo.rs:107-131). `DepthParser::new` in memo_toy.rs uses `with_max_depth`.
- Severity assessment: The `pub` field created an inconsistency — two fields private, one public, no obvious reason for the asymmetry. Mid-parse mutation of max_depth would be undetectable. Making it private with an accessor enforces the "set before parsing" contract at the API level.

quality-2:
- Disposition: Fixed
- Action: Subsumed by quality-1 fix. `DepthParser::new` now uses `PackratState::with_max_depth(max_depth)` directly.

quality-3:
- Disposition: Fixed
- Action: Generator template updated: `set_max_depth` calls `self.packrat.set_max_depth(max_depth)` and `max_depth()` calls `self.packrat.max_depth()` (gsm2parser_rs.py:391,395). Regenerated fixture parsers reflect this.
- Severity assessment: The field-access coupling would silently break any regenerated parser when max_depth's storage layout changes — the breakage would only surface at cargo build of the downstream consumer, not at generator run time.
