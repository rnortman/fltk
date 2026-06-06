# Deep correctness review — CST type annotations regression

Commit reviewed: 0903a36 (base a2822d5..HEAD). Concise. Precise. Audience: smart LLM/human.

Scope: does the code do what it appears to do — logic, control flow, data flow. Type-annotation correctness reviewed for runtime safety, not style.

## Verification performed

- `fltk/fegen/test_cst_protocol.py` + `fltk/test_plumbing.py`: 51 passed.
- `uv run pyright fltk/fegen/fltk_cst_protocol.py fltk/fegen/fltk2gsm.py`: 0 errors.
- `test_default_cst_is_fltk_cst` passes → `_DEFAULT_CST = cast("cstp.CstModule", _default_cst)` is a runtime identity (`cast` returns arg 2 unchanged); the module-level sentinel is the real `fltk_cst` module. No behavior change at the default-injection path.
- All restored `cstp.*` names are confined to annotation position (`__init__` param, `visit_*` params). `from __future__ import annotations` (fltk2gsm.py:1) defers them; `cstp` is `TYPE_CHECKING`-only and never referenced at runtime. No `NameError` risk under runtime injection. Confirmed no `cstp.*` in `isinstance`/value position — runtime CST access stays on `self.cst` throughout.
- Call-site `cast(...)` insertions (genparser.py:62, plumbing.py:147/176, unparse/genunparser.py:48) are `typing.cast` runtime no-ops passing `result.result` / `pr.cst_module` through unchanged. Control/data flow of `visit_*` bodies is byte-identical to base modulo annotations and two removed narration comments.
- `fltk_cst.py` diff is purely cosmetic: `for label, child in` → `for (label, child) in` (added parens) inside generator comprehensions. Same binding, same iteration, same filter. No semantic change.

## Findings

### correctness-1: committed protocol header diverges from generator output
File: `fltk/fegen/fltk_cst_protocol.py:1`
What: committed file begins `# ruff: noqa: N802`. The generator (`genparser.py:197-201`) now writes `# ruff: noqa: N802, F821`. The committed artifact predates the `F821` addition and was not regenerated.
Why: the two are supposed to be in lockstep (design "Grammar drift": protocol is GSM-derived, regenerated with the CST, no manual maintenance). The committed file is stale relative to its generator.
Consequence: not a runtime bug — this is a lint-suppression comment; the module typechecks and imports cleanly regardless. The concrete risk is process-level: a future `genparser generate` rewrites line 1, producing a spurious diff, and any consumer trusting "committed == generator output" is wrong today. If a generated node ever emits an annotation pyright/ruff would flag as F821 (forward-ref edge), the committed file lacks the suppression the generator intends. Verify by regenerating fegen artifacts and diffing.
Fix: regenerate `fltk_cst_protocol.py` from the current generator and commit, so header matches `# ruff: noqa: N802, F821`.

## No other findings

No off-by-one, wrong-operator, wrong-variable, control-flow, data-flow, mutation-during-iteration, or null-deref issues introduced by this diff. The change is annotation-only at runtime; the sole executable-logic delta (parenthesized tuple unpacking in `fltk_cst.py` comprehensions) is semantically inert. `_DEFAULT_CST` identity and the `TYPE_CHECKING`-only confinement of `cstp` both hold.
