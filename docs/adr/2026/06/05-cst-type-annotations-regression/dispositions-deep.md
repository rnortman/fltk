# Dispositions — deep review round 1

Commit reviewed: 0903a36. Fixes applied at: HEAD (see git log).

---

## errhandling-1
- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:312-315` — replaced bare `assert len(parts) > 0` with `raise ValueError(msg)` carrying rule context via `class_name` parameter threaded through all call sites.
- Severity assessment: A bare AssertionError on an empty-types node would surface with no context about the grammar rule; now produces a diagnostic message naming the rule.

## errhandling-2
- Disposition: Fixed
- Action: `fltk/fegen/genparser.py:184-210` — moved `gen_protocol_module()` and `ast.unparse()` calls to before `open()`, so any generation/AST error does not leave a partial file. Also added `newline="\n"` to both CST and protocol file opens (covers quality-5 simultaneously).
- Severity assessment: Previously a generation failure (e.g. ValueError from errhandling-1) would leave an empty open file; now it never touches the filesystem.

## errhandling-3
- Disposition: Won't-Do
- Action: no change
- Severity assessment: The existing guards (`result is None` and `result.pos != len(...)`) cover the meaningful gaps before the cast site. A logged diagnostic at the cast site for a wrong-type node would only matter for an internal parser bug, not a user-input error path.
- Rationale (Won't-Do): The design explicitly accepts this cast as a documented boundary for the known nested-Label mismatch (design.md "DI boundary"). Adding a runtime assertion here would be redundant with the guards already in place and adds noise without meaningful error-detection value for the actual failure modes.

---

## test-1
- Disposition: Fixed
- Action: `fltk/fegen/test_cst_protocol.py:409-413` — updated the `_STANDIN_FIXTURE` comment to explain that the cast mirrors production usage; the nested-Label nominal mismatch means a direct structural assignment is rejected by pyright for the same reason real modules require a cast. The member-access calls below the cast are the real T4 check.
- Severity assessment: The test does verify what it's supposed to (member access resolves on a non-dataclass class). The reviewer's suggested direct-assignment form would fail due to the same nominal nested-class limitation documented in the design, so it cannot serve as the "positive structural proof" without the cast pattern.

## test-2
- Disposition: Fixed
- Action: `fltk/fegen/test_cst_protocol.py:438-464` — replaced in-process `sys.modules` check with a subprocess call to guarantee collection-order isolation. Removed now-unused `sys` import.
- Severity assessment: Previous implementation would silently skip if another test imported the protocol first, making T5 unverifiable in certain collection orders.

## test-3
- Disposition: Fixed
- Action: `fltk/fegen/test_cst_protocol.py:173-178` — added explicit `assert required_name in prop_names` for `Items`, `Item`, `Disposition`, `Quantifier` with a comment naming them as Cst2Gsm runtime dependencies.
- Severity assessment: Without these, a grammar rule rename would pass T1 while silently breaking `fltk2gsm.py` at runtime.

## test-4
- Disposition: Fixed
- Action: `fltk/fegen/test_cst_protocol.py:230-271` — extended `_MEMBER_ACCESS_FIXTURE` with accessor calls for `RuleNode`, `TermNode`, `DispositionNode`, `QuantifierNode`, `LiteralNode`, `RawStringNode`.
- Severity assessment: Missing accessor coverage meant a misspelled member on those node types would not be caught by T2a; the boundary cast for those nodes was justified only by T2b (assignability), not member-resolution verification.

## test-5
- Disposition: Fixed
- Action: All five `cast("cstp.GrammarNode", result.result)` comment sites updated — `fltk/fegen/genparser.py:61`, `fltk/plumbing.py:147`, `fltk/plumbing.py:179`, `fltk/unparse/genunparser.py:49`, `fltk/test_plumbing.py:581` — replacing "nominal nested-Label mismatch" with accurate "result.result is typed Any (ParseResult.cst: Any); cast to satisfy visit_grammar's annotation" plus `TODO(parse-result-typed)`.
- Severity assessment: Misleading comments cause future engineers to misattribute the cast reason. The accurate comment prevents copy-paste of the wrong justification.

## test-6
- Disposition: Fixed
- Action: `fltk/fegen/test_cst_protocol.py:273-320` — added `_WRONG_LABEL_VALUE_FIXTURE` fixture string and `test_wrong_label_value_not_flagged` test asserting zero pyright errors on a valid-but-semantically-wrong label comparison, with a comment documenting the nominal-enum limitation.
- Severity assessment: Without this, consumers might over-trust the Protocol's label safety guarantees. The test documents the known boundary and serves as a regression guard if pyright's nominal-enum behavior changes.

---

## correctness-1
- Disposition: Fixed
- Action: Root cause identified: `ruff format` (run as part of `make fix`) strips `F821` from the noqa directive as RUF100 (unused noqa), because F821 does not actually fire on the generated protocol — nested Label forward refs resolve under `from __future__ import annotations` without ruff flagging them. Fix: updated `fltk/fegen/genparser.py:202` to emit `# ruff: noqa: N802` (dropping F821 from the template) with an explanatory comment. Regenerated `fltk/fegen/fltk_cst_protocol.py` from the updated generator and ran `make fix`; the committed header `# ruff: noqa: N802` now matches generator output stably (no spurious diff on future runs).
- Severity assessment: Generator and committed artifact now stay in sync: a future `genparser generate` + `make fix` produces the same header as already committed. The F821 suppression was not needed (F821 never fires), so removing it from the template is correct, not a loss.

---

## reuse-1
- Disposition: TODO(cst-protocol-generator-refactor)
- Action: Added `TODO(cst-protocol-generator-refactor)` comment at `fltk/fegen/gsm2tree.py:289` (above `protocol_annotation_for_model_types`); added `## cst-protocol-generator-refactor` entry to `TODO.md`.
- Severity assessment: The Union-building logic is duplicated; a Union syntax change (e.g. `X | Y`) must be applied in two places. Low immediate risk; grows as new per-label accessors are added.

## reuse-2
- Disposition: TODO(cst-protocol-generator-refactor)
- Action: Same TODO as reuse-1 — the same entry covers both `protocol_annotation_for_model_types`/`py_annotation_for_model_types` and `_protocol_class_for_model`/`py_class_for_model`.
- Severity assessment: Adding a new per-label accessor requires edits in both generators. Covered by the same TODO slug as reuse-1.

---

## quality-1
- Disposition: TODO(parse-result-typed)
- Action: Added `TODO(parse-result-typed)` comments at all five cast sites; added `## parse-result-typed` entry to `TODO.md`.
- Severity assessment: Scattered casts can be missed at new call sites, silently passing `Any` and bypassing the type checking the design enables. Root fix is making `ParseResult` generic; out of scope for this cycle.

## quality-2
- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:293-303` — added docstring explaining the quoting asymmetry (rule refs quoted as forward refs, library types unquoted as module paths) with rationale.
- Severity assessment: Without the comment, a future reader would "normalize" the quoting and break the generated module for any library-type annotation.

## quality-3
- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:311` — changed `parts = sorted(parts)` to `parts = sorted(set(parts))` for explicit deduplication + sort, with inline comment explaining the sort serves deterministic Union member order.
- Severity assessment: Low correctness risk but the sort was doing hidden deduplication; now both concerns are explicit.

## quality-4
- Disposition: TODO(cst-protocol-label-free)
- Action: Added `TODO(cst-protocol-label-free)` comment at `fltk/fegen/gsm2tree.py:362`; added `## cst-protocol-label-free` entry to `TODO.md`.
- Severity assessment: Generic code over arbitrary node `children` must case-split on label presence, which is not inferrable from the Protocol type. Low immediate impact (no such generic consumers today).

## quality-5
- Disposition: Fixed
- Action: `fltk/fegen/genparser.py:188,202` — added `newline="\n"` to both CST and protocol file opens.
- Severity assessment: On Windows, omitting `newline="\n"` produces `\r\n` endings in generated files, causing spurious `make check` failures. Fixed both the new protocol write and the existing CST write together.
