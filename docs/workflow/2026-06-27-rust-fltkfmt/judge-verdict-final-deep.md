# Judge verdict — final deep QA pass (rust-fltkfmt)

Phase: deep (final). Base 6f975ebf3e4e102c256397337a5d11a21cc1ab7f..HEAD 9ac3946033fe2500b237293184e288500dd23c89. Round 1.
Notes: 7 reviewer files (error-handling, correctness, security, test, reuse, quality, efficiency); 15 findings (correctness: none).
Note: dispositions doc reviewed HEAD f89c809; responder's fix commit 9ac3946 is HEAD. Walks below verify the fix commit.

## Added TODOs walk

### errhandling-2 — TODO(unparser-none-path-diagnostics) at gsm2unparser_rs.py:1365 (generated unparser.rs ~17 trivia sites)
Q1 (worth doing): yes — when `_has_preservable_trivia` returns true but `unparse__trivia` returns `None` (label mismatch / sourceless span), the comment is silently dropped with nothing on stderr; a diagnostic for that path is worth having. Reviewer states the consequence (silent comment deletion, exit 0).
Q2 (design/owner input required): yes — the right fix is a policy choice (log-and-continue vs `debug_assert!` vs halt) that must be applied to **both** the Rust generator and the Python unparser to preserve cross-backend behavioral equivalence (CLAUDE.md hard requirement; the parity suite asserts byte-identical output). The reviewer's own "what must change" offers the choice ("Or halt with `unreachable!()`/`debug_assert!` if the project philosophy is to crash") — confirming a policy decision, not a mechanical one-liner. A Rust-only `eprintln!` would diverge the backends.
Furthermore check (problem this iteration created/worsened cannot be silently deferred): the None-handling logic is pre-existing base behavior — correctness reviewer verified "this diff only added a TODO comment above it — no behavior change introduced here." The Python formatter already formats `fegen.fltkg` with identical None-handling; this iteration mirrors it (parity-verified), so it neither created nor worsened the gap. And it is not *silently* deferred: tracked in TODO.md:85 and at the code site with a full rationale. The escalation trigger (fails Q2) is not met — Q2 passes.
Assessment: invariant-violation path (spans always carry source under `capture_trivia=true`), should-fix diagnostic quality, legitimately design-gated. TODO acceptable.

### errhandling-3 — TODO(unparser-none-path-diagnostics) at gsm2unparser_rs.py:1091 (generated unparser.rs token-content sites)
Q1 (worth doing): yes — `let text = span.text()?;` propagates `None` to the public entry point, surfacing as a context-free "internal error: unparser returned None" naming the file but not the rule/label/span. Worth improving.
Q2 (design/owner input required): yes — same cross-backend policy decision as errhandling-2; the same TODO slug covers it (one coherent deferral, two sites). Embedding the label in a logged-then-propagate pattern must land in both backends to stay in parity.
Furthermore check: same as errhandling-2 — pre-existing generator pattern (base commit), mirrored to the new fegen unparser; not silent (tracked). Note this path is *not even silent at runtime* (it emits an error + filename and exits 2); the finding is purely diagnostic granularity. Q2 passes, so no escalation trigger.
Assessment: should-fix diagnostic quality on an invariant-violation path, design-gated, tracked. TODO acceptable.

### reuse-1 — TODO(unparser-pyi-doc-stub-shared) at gsm2unparser_rs.py:133 (generate_pyi)
Q1 (worth doing): yes — the grammar-independent 3-line `Doc` stub is emitted verbatim into every per-grammar `unparser.pyi` (currently 2 copies); a `Doc.render` signature change must be mirrored into each. Mild DRY win, grows linearly with grammar count.
Q2 (design/owner input required): yes — the `.pyi` stubs are generated public API consumed by out-of-tree apps (CLAUDE.md). Centralizing means each per-grammar stub *imports* a shared `Doc` module instead of defining it locally, changing the structure/import surface downstream consumers depend on. That is a deliberate public-API decision, not an incidental refactor; doing it blindly now would be wrong given the small payoff.
Furthermore check: this iteration added the second copy (`fltk/_stubs/fegen_rust_cst/unparser.pyi`), so it worsened the duplication — but the item passes Q2 (genuine public-API design decision) and is tracked in TODO.md:101 + the code site, so the "fixed or escalated if it fails Q2" clause does not bite. Not silent.
Assessment: TODO acceptable.

## Other findings walk

### errhandling-1 / quality-3 — Fixed (single change)
Claim: `_item_spacing_lines` assigns `spacing`/`ctor` only inside `if position=="before" / elif "after"`; the `Literal` is erased at runtime, so a subclass/untyped caller with another value hits unbound reads → `UnboundLocalError` naming neither rule nor position.
Diff at gsm2unparser_rs.py: added `else: ... raise ValueError(f"Internal error: unexpected position {position!r} for rule {rule_name!r} item {item_id}")` (line ~599), with `item_id` derived from label/term — mirrors the file's explicit-raise routing guards (verified consistent: raises at 329/344/362/561/694/880/962/1066/1196...). Reviewer suggested RuntimeError; ValueError is equally diagnosable and matches `_item_disposition_success_lines`. Generated `.rs` unchanged (branch unreachable; dispositions report regen byte-identical).
Assessment: addresses the consequence at the named site. Accept.

### security-1 — Fixed
Claim: `create_temp` opened the temp at process default (~0o644, world-readable); the source-mode copy is `let _ = set_permissions(...)` (result discarded) *before* write, so a failed copy widens a private (0o600) `.fltkg`'s contents to world-readable on `--in-place` (CWE-732).
Diff at crates/fltk-fmt-cli/src/lib.rs `create_temp`: temp now opened via `OpenOptions` with `#[cfg(unix)] opts.mode(0o600)` (`OpenOptionsExt`); `write_atomic` later widens to source mode. Matches the reviewer's suggested fix exactly — inverts the failure direction (failed widen leaves temp at 0o600).
Assessment: closes the consequence at the named line. Accept.

### test-1 — Fixed
Claim: six flag-conflict tests route through `run_args_only`, which discarded stderr; a silent exit-2 regression would pass. Design requires a usage message to stderr.
Diff: `run_args_only` now returns `(u8, String)` (exit + captured stderr); each conflict test asserts exit 2 AND `err.contains("--in-place"/"--check"/"--output")`. Matches the reviewer's fix.
Assessment: Accept.

### test-2 — Fixed
Claim: `--output` + stdin (zero file args, `count=1` branch) was untested; a `validate` count regression would silently break it.
Diff: `output_with_stdin_writes_to_file` — `-o <path>` with stdin "hi", asserts exit 0, stdout empty, output file contains "HI". Accept.

### test-3 — Fixed
Claim: `--check` over stdin had no coverage; a stdin-specific check regression would be silent.
Diff: `check_stdin_exits_1_when_input_would_change` (changing stub → exit 1, empty stdout, `<stdin>` on stderr) + `check_stdin_exits_0_when_already_formatted` (identity → exit 0, empty stdout/stderr). Matches the reviewer's fix. Accept.

### test-4 — Fixed
Claim: `--in-place` skip-when-unchanged guard (`formatted == content`) untested; removing it would silently churn mtimes.
Diff: `in_place_identity_skips_rewrite_and_leaves_no_temp` — identity stub, file unchanged ("abc"), dir entry count == 1 (no temp). Accept.

### test-5 — Fixed
Claim: `--in-place` with a format error — the atomicity guarantee (Err branch `continue`s, original untouched) had no test.
Diff: `in_place_format_error_leaves_original_and_no_temp` — fail stub → exit 2, file byte-identical, stderr names the path, dir entry count == 1. Accept.

### quality-1 — Fixed
Claim: `crates/fltkfmt/Cargo.toml` listed `fltk-unparser-core` as a direct dep though `src/main.rs` names no `fltk_unparser_core::` path (macro resolves render types via `fltk-fmt-cli` re-exports); it arrives transitively. The binary is the reference template consumers copy, so the redundant dep teaches false coupling.
Diff: line removed; comment updated to describe the minimal template (grammar CST crate + CLI scaffolding) and the transitive arrival. Deliberate, called-out deviation from the design's literal dep list, justified by the design's own rule ("add transitive crates explicitly only if a named type requires it (the macro names neither)"). Dispositions report binary still builds + 16-case parity passes. Not a public-symbol rename / not annotation churn; makes the template more correct. Accept.

### quality-2 — Fixed
Claim: the 5-line PyO3 unparse prelude was copy-pasted into both `unparse_{rule}` and `unparse_{rule}_doc` generators; a one-sided edit would not be caught.
Diff: extracted `_gen_py_unparse_prelude_lines(rule_name)`; both sites replaced with `lines.extend(...)`. Same five lines verbatim; regen byte-identical (dispositions). Accept.

### quality-4 — Fixed
Claim: `validate` dead branch — `count = if files.is_empty() {1} else {len}; if count > 1` where `1 > 1` is always false.
Diff: replaced with `if args.output.is_some() && args.files.len() > 1 { ... }`, behavior identical, "zero files = one implicit stdin input" documented in a comment. Accept.

### efficiency-1 — Won't-Do
Claim: multi-file formatting is sequential (`run_inner` `for source in sources`); N-file wall-clock is N × single-file.
Rationale: design §3 froze a single-threaded pipeline because `fltk_unparser_core::Doc` uses `Rc` (`!Send`); parallelizing would run each whole pipeline to `String` on a worker and reassemble by index — substantial change for marginal gain on ms-scale `.fltkg` files.
Inspection: the reviewer itself records this as "a conscious, documented design choice ... Recorded for completeness; not an action item given the accepted design and the tiny-file workload." Rationale argues active harm (contradicts accepted design, adds complexity for no payoff). Finding is a non-action-item by the reviewer's own admission.
Assessment: Won't-Do sound. Accept.

## Disputed items

None.

## Approved

15 findings: 11 Fixed verified (errhandling-1/quality-3 [one change], security-1, test-1..5, quality-1, quality-2, quality-4), 1 Won't-Do sound (efficiency-1), 3 TODOs acceptable across 2 slugs (errhandling-2 + errhandling-3 → `unparser-none-path-diagnostics`; reuse-1 → `unparser-pyi-doc-stub-shared`). Correctness reviewer reported no findings.

No `scope-N` findings; no pile of scope-cut TODOs (the 2 slugs are genuine design/public-API deferrals, both tracked in TODO.md and code).

---

## Verdict: APPROVED

All 15 dispositions acceptable. Fixes verified against the fix commit (9ac3946) diff; both TODOs pass the two-question rubric (worth doing + genuinely design/public-API-gated) and are properly tracked; the lone Won't-Do is endorsed by the originating reviewer.
