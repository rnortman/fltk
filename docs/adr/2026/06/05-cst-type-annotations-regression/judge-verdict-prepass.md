# Judge verdict — slop prepass

Phase: prepass (slop + scope). Base a2822d5..HEAD 0903a36. Round 1.
Notes: notes-prepass-slop.md (8 findings), notes-prepass-scope.md (no findings).

Concise. Precise. Complete. Unambiguous. No padding.

## Added TODOs walk

No TODO-dispositioned findings. (One TODO exists in the diff — `TODO(rust-cst-pyi)` at genparser.py:274 — but it is not a finding disposition; it is a design-anticipated deferral, confirmed present by the scope reviewer with sound rationale. Not in scope for this prepass adjudication.)

## Other findings walk

All 8 slop findings dispositioned Fixed. Severities: slop-1..7 nits (narration/redundancy, no consequence beyond reviewer noise); slop-8 should-fix (`type: ignore` masking an underspecified return type). Each verified at HEAD.

### slop-1 — Fixed
Claim: self-explanatory docstring on `protocol_node_name` restating signature; consequence is narration noise.
HEAD (gsm2tree.py): docstring now `"Rule name → Protocol class name; must stay in sync with class_name_for_rule_node."` — the non-obvious sync constraint the reviewer suggested. Accept.

### slop-2 — Fixed
Claim: "Like X but Y" definition-by-diff docstring on `protocol_annotation_for_model_types`.
HEAD: replaced with direct contract — `"Return a Python annotation string for model_types."` + body describing `<Name>Node` for rule refs vs library types. Accept.

### slop-3 — Fixed
Claim: narration comment `# from __future__ import annotations (must be first...)` in `gen_protocol_module`.
HEAD: comment removed; the `pygen.stmt("from __future__ import annotations")` append stands alone. Accept.

### slop-4 — Fixed
Claim: `# span: ...` and `# children: list[...]` inline comments restating the following string literal.
HEAD (`_protocol_class_for_model`): both `span:` and `children:` appends carry no restating comment. Accept.

### slop-5 — Fixed
Claim: section comments `# append`, `# extend`, `# child`, `# Per-label methods` restating variable/method names.
HEAD: the four named comments are gone — `append_fn`/`extend_fn`/`child_fn` blocks and the per-label `for` loop have no top-level section captions. (Per-label inline comments `# append_<label>` etc. remain inside the loop; these are a distinct set the reviewer did not flag — out of scope for this disposition.) The four flagged items are removed. Accept.

### slop-6 — Fixed
Claim: `# Generate companion Protocol module` captioning a self-captioning block.
HEAD (genparser.py): comment removed; the block now carries a substantive multi-line comment explaining the `# ruff: noqa: N802, F821` file-level suppressions (real intent, not narration). Accept.

### slop-7 — Fixed
Claim: identical 3-line cast paragraph copy-pasted across five files; "same pattern as plumbing.py" cross-refs go stale.
HEAD: all five sites (genparser.py:61, plumbing.py:147 & 176, test_plumbing.py:580, unparse/genunparser.py:49) reduced to `# nominal nested-Label mismatch; see _DEFAULT_CST in fltk2gsm.py`. Canonical explanation verified present at fltk2gsm.py:13-18 (`_DEFAULT_CST`), so the one-liner pointer is live, not stale. Accept.

### slop-8 — Fixed
Claim: `list[dict]  # type: ignore[type-arg]` on `run_pyright` suppresses a missing-type-param error; consequence is `Any`-keyed dicts downstream with no type safety.
HEAD (test_cst_protocol.py): signature is `run_pyright(file_path, *, pyright_available: bool) -> list[dict[str, Any]]` with no `type: ignore`; `from typing import Any` imported at file top. The proper type replaces the suppression. Accept.

## Disputed items

None.

## Approved

8 findings: 8 Fixed verified. Scope reviewer: no findings (all design-scope items present; two logged deviations sound; `TODO(rust-cst-pyi)` correctly placed and matches design's deferral default).

---

## Verdict: APPROVED

All 8 slop dispositions verified Fixed at HEAD 0903a36. No scope findings. No TODO, Won't-Do, or contested disposition.
