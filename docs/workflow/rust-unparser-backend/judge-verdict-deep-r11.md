# Judge verdict — deep review r11

Phase: deep. Base 0494f31..HEAD 1cda7da. Round 1.
Notes: 7 reviewer files (correctness + security: no findings); 9 dispositioned findings.
Fixes landed in commit 1cda7da (review was against fabdc5a).

## Added TODOs walk

### efficiency-1 — TODO(unparser-gencode-protocol-only) at Makefile:288 / TODO.md
Finding: the `gencode` protocol-module step runs `genparser generate` into a temp dir and keeps only `rust_parser_fixture_cst_protocol.py`, discarding the full `<base>_cst.py` + parser suite that `generate` always emits, purely to extract the one protocol module. Reviewer explicitly rates it "optional," cost "negligible," "the current approach is correct."

Q1 (worth doing): weak yes — it eliminates genuinely redundant CST/parser codegen on every `make gencode`; the protocol module is producible alone via `cstgen.gen_protocol_module()` (genparser.py:206).

Q2 (design cycle / owner input required): **no.** The fix is fully specified in the TODO.md entry itself — "add a `--protocol-only` flag (or a dedicated subcommand) to `generate` that emits just `<base>_cst_protocol.py`, then point the `gencode` step at it." That is a mechanical additive CLI flag + a one-line Makefile rewire. No design question, no product-owner call. The disposition's own stated rationale — "out of this design's file set" / "deferred rather than expanding scope into the CLI here" — is exactly the "out of scope / not now" rationale the rubric rejects.

Furthermore: this iteration introduced the temp-dir dance (the `gencode` protocol-module step is new in this work). A problem this iteration created that fails Q2 cannot be silently deferred via TODO — it must be fixed (do it now) or escalated for visibility.

Assessment: Q2 fails → do-now (or a properly-argued Won't-Do). TODO disposition wrong. The slug/comment/TODO.md form is correct, but acceptability fails: mechanical, fully-specified, doable-now work parked as a TODO for scope reasons.

## Other findings walk

### errhandling-1 / quality-3 — Fixed (same change, two reviewers)
Claim: `Makefile` gencode protocol step `;`-chains `mktemp`/`generate`/`cp`/`rm`; exit code is `rm`'s (always 0), so a generator or `cp` failure is masked and `make gencode` exits 0 with a stale/absent committed protocol module — pyright then type-checks the committed `.pyi` against an old protocol with no Make-level CI signal.
Diff at Makefile:292-298: replaced the `;`-chain with `set -e; tmpdir=$(mktemp -d); trap 'rm -rf "$tmpdir"' EXIT; <generate>; <cp>`. `cp` is now the final real command. Under `set -e`, a generate/cp failure exits the shell with that command's non-zero status; the EXIT trap runs `rm` for cleanup but does not execute an explicit `exit`, so the failing status is preserved and propagates to Make. POSIX-valid in both dash and bash; single shell invocation via backslash continuation.
Assessment: fix addresses the consequence — generator-fail and cp-fail now propagate non-zero; success still 0; temp dir cleaned on every path. Accept both.

### test-1 — Fixed
Claim: `_CONSUMER_OK` assigns `unparse_num`'s return into a `str | None` target, which accepts `str | None`, `str`, and `Any` alike, so `test_consumer_pyright_clean` cannot catch a stub that silently drops `| None`; downstream callers relying on `None` ("could not unparse") get wrong type info uncaught.
Diff at test_rust_unparser_pyi.py:79-89, 168-180: added `_CONSUMER_BAD_NARROWING` (`result: str = u.unparse_num(node)`) written to `consumer_bad_narrowing.py` in the existing batched fixture, plus `test_consumer_return_keeps_optional` asserting a `reportAssignmentType`/`reportArgumentType` error. This errors only if the stub keeps `| None`; narrowing to `str` (or `Any`) would silently pass. Exactly the fix the finding specified.
Assessment: addresses the gap at the named surface; batched into the single pyright run. Accept.

### test-2 — Fixed
Claim: in `_CONSUMER_OK`, `doc.render()` flows into a `-> str | None` return, which `Any` also satisfies, so no test proves `render()` is a constrained `str` rather than `Any`.
Diff at test_rust_unparser_pyi.py:93-105, 183-194: added `_CONSUMER_BAD_RENDER` (`result: int = doc.render()` under an `is not None` guard) written to `consumer_bad_render.py`, plus `test_consumer_render_returns_str` asserting `reportAssignmentType`. Errors only if `render()` is concrete `str`; an `Any` return would silently pass. Matches the finding.
Assessment: addresses the gap, parallel to test-1, same batched run. Accept.

### reuse-1 / quality-1 — Fixed (same redundant helper, opposite directions)
Claim: the new file added a fourth copy of the `pyright_available` probe (`shutil.which("uv")` + `pyright --version`), redundant with three existing inline copies; quality-1 separately objected to the single-call-site private `_pyright_available` wrapper diverging from the established inline pattern.
Diff: `tests/pyright_test_utils.py:22-37` gained shared `pyright_runnable()` (+ `import shutil`); `test_rust_unparser_pyi.py:30-35,108-110` removed its private helper and defines `pyright_available` as a one-line fixture delegating to `pyright_runnable()`. Consolidation removes the new duplication (reuse-1) and the redundant private wrapper (quality-1); the remaining one-line fixture is a genuine pytest-DI adapter (a plain function can't be a fixture dependency), which is what quality-1's objection was about. The three pre-existing inline copies are outside this diff and correctly left untouched.
Assessment: both findings resolved by one consolidation without conflict. Accept.

### reuse-2 / quality-2 — Fixed (same defect, two reviewers)
Claim: the new fixture inlined a `pyrightconfig.json` `json.dumps({...})` duplicating the three base keys `write_pyright_config` owns, plus `extraPaths`, because the helper had no `extra_paths` parameter — the limitation was in the helper and the call site worked around it.
Diff: `tests/pyright_test_utils.py:87-98` added keyword-only `extra_paths: list[str] | None = None`, emitted as `extraPaths` only when given (backward compatible — existing callers unaffected); `test_rust_unparser_pyi.py:126` now calls `write_pyright_config(tmpdir, extra_paths=[repo_root, fltk/_stubs])`. Fixes the helper rather than the call site, exactly as both findings specified.
Assessment: the inline duplication is gone; the convention now lives in one place. Accept.

## Disputed items

- **efficiency-1 / TODO(unparser-gencode-protocol-only)**: fails Q2 (no design cycle or product-owner input required — the fix is a mechanical, fully-specified `--protocol-only` flag + one-line Makefile rewire) and falls under "this iteration created it → cannot be silently deferred." Need: do it now (implement the flag per the TODO.md spec and drop the temp-dir dance), OR convert to a Won't-Do that argues the redundancy is genuinely not worth a new CLI surface given the negligible dev-only cost. A parked TODO for doable-now mechanical work is not an acceptable disposition.

## Approved

8 findings: errhandling-1, quality-3, test-1, test-2, reuse-1, quality-1, reuse-2, quality-2 — all Fixed and verified.

---

## Verdict: REWORK

One disposition wrong (efficiency-1: doable-now mechanical work deferred as a TODO for scope reasons, against the TODO acceptability rubric). Round 1.
