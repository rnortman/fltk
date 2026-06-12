# Dispositions: design review r2 (`notes-design-design-reviewer-r2.md`)

Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

design-1:
- Disposition: Fixed
- Action: Adopted reviewer option (a). Design now specifies the **child-class union** rule: `DropWorklistItem` variants (and `drain_into` arms) only for classes appearing as a node-typed variant in any child enum; never-child classes get no variant (their own `impl Drop` seeds the worklist directly). Secondary effect handled: `into_drop_item` emitted only when the class has a `Drop` impl or a worklist variant (its only two call sites), so span-only never-child classes get neither. Degenerate empty-union case (flat grammar): `_drop_block` skipped entirely, consistent because no `Drop` impls or `into_drop_item` methods exist then either. Edits: "Drop: iterative worklist teardown" pieces 2-3 (variant-set paragraph, `into_drop_item` gating, code comments), generator-changes summary items 3-4 (including the `generate()` pre-pass to compute the union), new "Never-child root classes" edge-case bullet.
- Severity assessment: Verified real — `Items` appears in `src/cst_generated.rs` only in `__repr__` text, never as a child-enum variant, and Makefile:51-54 runs `cargo clippy -- -D warnings` on workspace + both fixture crates; the uniform-variant design as written would fail `make check` on `dead_code` (unconstructed private-enum variants) and force an unreviewed mid-implementation workaround.

design-2:
- Disposition: Fixed
- Action: Root-cause section now cites the left-recursion mechanism and `evaluation-drop-depth-reachability.md` §2, explicitly noting it supersedes the flawed `exploration.md` §5 bound (post-limit depth ≈ `max_depth` is false; depth scales with input length). Also adopted the evaluation §4 optional test rather than noting non-adoption: new test 5 (parser-produced deep tree — parse `"1" + "+1"*100_000` at default `max_depth`, assert success + bounded Debug + clean drop), pinning reachability-via-parsing in CI; tests renumbered.
- Severity assessment: Verified — evaluation §4 states the §5 claim is false and recommends the citation swap. Leaving the stale citation would let a future reader re-derive a ~1000-depth bound from `DEFAULT_MAX_DEPTH` and weaken the 100 000-depth tests or re-litigate the Drop fix; the ADR would record a wrong argument under a load-bearing security claim.

No Won't-Do or TODO dispositions. Substantial edits → cleanup-editor pass re-run (fixed one stale code comment: "uniform arm per node class" → "per worklist variant").
