# Judge verdict — deep review

Phase: deep. Base 46a6639..HEAD ce786b0 (fix commit ce786b0 on top of reviewed c78a014). Round 1.
Notes: 7 reviewer files; 25 finding entries (several cross-lane duplicates). Dispositions: `dispositions-deep.md`.
Style: concise, precise, complete. Audience: smart LLM/human.

## Added TODOs walk

### test-6 — claimed TODO(poc-per-class-conformance) at tests/test_gsm2tree_rs.py:1167
The actual comment is a bare `# TODO: add test_poc_per_class_no_cast_zero_errors ...` — **no slug, no TODO.md entry** (disposition admits the latter, but also misstates that a slugged TODO was added). Violates the repo TODO convention (CLAUDE.md: slug + TODO.md entry, both).
Q1 (worth doing): dubious — responder's own rationale: PoC class names (`Identifier`, `Items`, `Trivia`) are a subset of the fegen grammar's, same emitter code path, per-class conformance already verified by `test_fegen_per_class_no_cast_zero_errors`.
Q2 (design/owner input required): no — the test is mechanical: `poc_pyi` fixture and `_run_pyright_in_tmpdir` harness already exist; it's a copy of the fegen per-class test (~15 lines).
Assessment: fails the rubric both ways — if Q1 yes, Q2 fails → do-now; if Q1 no → Won't-Do and delete the comment. A slugless TODO is the worst of the options. Disposition wrong.

### test-7 — claimed TODO(pyi-bare-upper-annotation-check) at tests/test_gsm2tree_rs.py:884
Actual comment is bare `# TODO: also check that bare (unquoted) uppercase names ...` — **no slug, no TODO.md entry**; disposition misstates the slug.
Q1 (worth doing): marginal — the reviewer's own fix offered option (b): "rely on the pyright conformance tests as the authoritative guard and document that this test is a fast pre-pyright lint only." The added comment *is* that documentation; the substance of option (b) is done.
Q2: no — nothing remains that needs design; the remaining regex idea is the part the reviewer said could be skipped.
Assessment: substance complete via reviewer's option (b); the residual "TODO:" framing is a convention violation and the disposition mislabels what was done. Correct state: plain comment (no TODO), disposition Fixed. Disposition wrong as written; trivial to correct.

### reuse-1 — TODO(pyi-node-kind-name-reuse) at fltk/fegen/gsm2tree_rs.py:342 + TODO.md entry
Properly registered (slug, comment, TODO.md entry — verified).
Q1: yes — single source of truth for NodeKind member naming across `.rs`/`.pyi`/protocol; divergence breaks conformance.
Q2: no — mechanical. `CstGenerator.node_kind_member_name(rule_name)` exists (`gsm2tree.py:95-97`); `_rule_info()` already returns `rule_name` alongside `class_name` (`gsm2tree_rs.py:90`), and both call sites (`generate_pyi` :154, `_node_kind_block` :394) have it in scope. The TODO.md entry itself spells out the exact change — proof no design cycle remains.
Assessment: fails Q2 → do-now. Disposition wrong.

### reuse-2 — TODO(pyi-label-quintet-reuse) at gsm2tree_rs.py:183 + TODO.md entry
Properly registered.
Q1: yes — `_emit_label_quintet` is the authoritative quintet definition; a sixth accessor would silently miss the stub (B4 test catches the runtime→stub direction, not method addition timing).
Q2: yes — the reviewer concedes the string-vs-AST boundary makes direct reuse impossible; the fix requires choosing between unparsing `ast.FunctionDef`s and extracting a shared lower-level signature helper — an emitter-architecture decision, not mechanical work.
Assessment: TODO acceptable.

### efficiency-1 — TODO(pyright-batch-tests) at tests/test_gsm2tree_rs.py:1010 (+ reuse at test_fltk_native_stub.py:54) + TODO.md entry
Properly registered.
Q1: yes — 4 cold `uv run pyright` subprocesses, 20-60 s added to every `pytest` run, serialized. **This cost was created this iteration** (all 4 tests are new); per rubric a problem this iteration created cannot be silently deferred.
Q2: no for the reviewer's stated minimum-viable: "merge the fegen self-check + whole-module + per-class fixtures into a single tmpdir/run (they already share `fegen_pyi`)" — mechanical. The TODO.md entry contains the complete plan (single module-scoped tmpdir, one pyright run, partition `generalDiagnostics` by path) — fully specified, no design cycle remains. Mitigating context: per-test `run_pyright` is established repo precedent (`test_cst_protocol.py`, 8+ call sites), so the *full* harness consolidation across files is a larger refactor — but the minimum-viable batching within the new tests is not.
Assessment: fails Q2 at minimum-viable scope and falls under "this iteration created" → do-now (minimum-viable), or escalate with a specific reason it cannot be done now. Disposition wrong.

### efficiency-2 — TODO(fegen-pyi-fixture-sharing) at tests/test_gsm2tree_rs.py:766 + TODO.md entry
Properly registered.
Q1: yes — `fegen_pyi` duplicates the full fegen.fltkg parse pipeline of `fegen_source`; the duplication was added this iteration.
Q2: no — one module-scoped `fegen_generator` fixture, derive both from it; ~15 mechanical lines, plan fully written in the TODO.md entry.
Assessment: fails Q2 → do-now. Disposition wrong.

### efficiency-3 — Fixed (partially) + TODO(pyright-batch-tests) at test_fltk_native_stub.py:54
Fixed part verified: the dead parent-annotation loop is gone with `_stub_class_names()` deletion (diff confirms).
Q1 (residual `_parse_stub` re-read): yes, trivially — pure waste per helper call, file is new this iteration.
Q2: no — the TODO comment itself names the fix: "cache this at module scope (or `functools.cache`)". A one-line decorator the responder described while declining to apply it.
Assessment: residual fails Q2 → do-now. Disposition wrong.

## Other findings walk

### correctness-1 / quality-1 — Fixed
Claim: regenerated CST modules contained a bare runtime `import fltk._native` + eagerly evaluated `fltk._native.Span` annotation → `ModuleNotFoundError`/`AttributeError` at import in any pure-Python install (Bazel path, documented fallback). Blocker.
Evidence: `gsm2tree.py` diff — `from __future__ import annotations` inserted at module top; `fltk._native` and `fltk.fegen.pyrt.span` imports moved under `if typing.TYPE_CHECKING:`, mirroring the protocol generator. All four artifacts regenerated (headers verified in `fltk_cst.py`, `toy_cst.py`; diff covers `bootstrap_cst.py`, `unparsefmt_cst.py`). Empirically verified: with a meta-path blocker raising `ModuleNotFoundError` for `fltk._native`, all four CST modules import and `fltk_cst.Grammar(span=UnknownSpan)` constructs.
Assessment: fix addresses the consequence at the root (generator) and in artifacts. Accept.

### correctness-2 / errhandling-3 / test-1 / quality-4 — Fixed
Claim: `_stub_class_names()` reads never-set `.parent` → latent `AttributeError`; misleading cross-function comment.
Evidence: diff deletes the function and the parent-annotation comment/loop; `_stub_classes_with_members` no longer runs the dead annotation pass.
Assessment: matches all four reviewers' preferred fix (delete). Accept.

### correctness-3 — Fixed
Claim: `--pyi-output` without `--protocol-module` silently writes nothing, exit 0 → stub-regeneration drift.
Evidence: `genparser.py:312-314` — guard emits `Error: --pyi-output requires --protocol-module` to stderr, `typer.Exit(1)`, before any work.
Assessment: accept.

### correctness-4 — Fixed
Claim: docstring claimed `__init__` included; filter excludes it.
Evidence: docstring now reads "dunder names (including `__init__`) are excluded" — the reviewer's offered alternative (correct the docstring).
Assessment: accept.

### correctness-5 / quality-3 — Fixed
Claim: dead `python_label = label.upper()` + misleading `del`.
Evidence: both lines removed in diff.
Assessment: accept.

### errhandling-1 — Fixed
Claim: `RustCstGenerator(...)`/`generate_pyi`/`generate` raise `ValueError`/`RuntimeError` as raw tracebacks from the CLI.
Evidence: `genparser.py` — constructor wrapped in `try/except ValueError`; both generate calls wrapped in `try/except (ValueError, RuntimeError)`; both emit `Error: {e}` to stderr and `raise typer.Exit(1) from e`. Matches the reviewer's prescribed pattern.
Assessment: accept.

### errhandling-2 — Fixed
Claim: `except Exception` in `_try_import_fegen_cst` silently skips B4 tests when the extension is present-but-broken.
Evidence: narrowed to `except (ImportError, ModuleNotFoundError)` (test_fltk_native_stub.py:35); a PyO3 init panic now propagates.
Assessment: accept.

### test-2 — Fixed
Claim: `or hasattr(runtime_cls(), member)` fallback would raise `TypeError` (PyO3 classes need args); false confidence in instance-level checking.
Evidence: fallback removed; assertion is `hasattr(runtime_cls, member)` only — `Label` is a classattr, reachable on the class object.
Assessment: accept. (Reviewer's optional explicit `Label` type-check not taken; the mandatory part of the fix is done and the B4 class-attr direction still covers `Label` presence.)

### test-3 — Fixed
Claim: CLI emit test uses mismatched grammar/protocol pair, never validates the stub.
Evidence: reviewer's option (b) implemented — docstring states the test verifies plumbing only and points to `TestGeneratePyiConformance` for the matched pair; `ast.parse(pyi_text)` added as syntax guard.
Assessment: accept.

### test-4 — Fixed
Claim: second `runner.invoke` exit code unchecked → vacuous `.rs` equality on dual failure.
Evidence: `result1`/`result2` captured; both `exit_code == 0` asserted with output in the failure message.
Assessment: accept.

### test-5 — Fixed
Claim: no determinism guard for `generate_pyi`.
Evidence: `test_pyi_two_calls_produce_identical_strings` and `test_pyi_two_generator_instances_produce_identical_strings` added in `TestDeterministicOutput`, mirroring the `.rs` pair.
Assessment: accept.

### quality-2 — Fixed
Claim: `model_types: object` + `# type: ignore[arg-type]` blinds the type system.
Evidence: `from collections.abc import Iterable`, `ModelType` imported from `gsm2tree`; parameter now `Iterable[ModelType]`; ignore removed; prose workaround note in docstring deleted.
Assessment: accept.

### security-1 — no findings
Reviewer examined and ruled out the injection/path/shadowing vectors; no disposition required.
Assessment: N/A, accept.

## Disputed items

- **test-6**: choose a real disposition. Either write `test_poc_per_class_no_cast_zero_errors` (mechanical; harness and `poc_pyi` fixture exist) or convert to Won't-Do per the responder's own already-stated rationale and delete the slugless comment. A bare `# TODO:` with a phantom slug in the dispositions doc satisfies neither the repo convention nor the rubric.
- **test-7**: substance is done (reviewer's option (b)). Drop the `# TODO:` prefix — keep the explanatory comment — and re-disposition as Fixed. No phantom slug.
- **reuse-1**: do it now — delegate to `self._py_gen.node_kind_member_name(rule_name)` (`rule_name` already flows through `_rule_info()` to both call sites); remove TODO comment + TODO.md entry.
- **efficiency-1**: do the reviewer's minimum-viable now — merge the fegen self-check + whole-module + per-class pyright fixtures into one tmpdir/run (they share `fegen_pyi`). If the full cross-file harness consolidation is deferred, narrow the TODO.md entry to that remainder. Blanket deferral of an iteration-created 20-60 s/`pytest` cost is not acceptable.
- **efficiency-2**: do it now — module-scoped `fegen_generator` fixture; derive `fegen_source` and `fegen_pyi` from it; remove TODO.md entry.
- **efficiency-3 (residual)**: do it now — `functools.cache` on `_parse_stub` (the fix is already named in the comment being left behind); drop the comment.

## Approved

18 finding entries acceptable: 17 Fixed verified (incl. cross-lane duplicates correctness-1/quality-1, correctness-2/errhandling-3/test-1/quality-4, correctness-5/quality-3), 1 no-finding (security). 1 TODO acceptable (reuse-2).

---

## Verdict: REWORK

Six dispositions wrong (test-6, test-7, reuse-1, efficiency-1, efficiency-2, efficiency-3): two slugless TODOs whose dispositions claim slugs that don't exist in code or TODO.md, and four deferrals that fail rubric Q2 — each TODO's own text contains a fully specified, mechanical fix, three of them for costs this iteration introduced. All substantive Fixed claims verified, including empirical confirmation of the correctness-1 pure-Python import regression fix. Round 1.
