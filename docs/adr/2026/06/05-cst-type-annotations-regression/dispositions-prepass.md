## Dispositions — slop prepass (commit 0903a36)

slop-1:
- Disposition: Fixed
- Action: gsm2tree.py:285 — replaced "Return the Protocol class name for a CST node (e.g. 'grammar' -> 'GrammarNode')." with "Rule name → Protocol class name; must stay in sync with class_name_for_rule_node."
- Severity assessment: Cosmetic; no correctness risk.

slop-2:
- Disposition: Fixed
- Action: gsm2tree.py:289 — replaced "Like py_annotation_for_model_types but emits Protocol node names (<Name>Node) for rule refs." with a direct contract description split across two lines to respect line-length limits.
- Severity assessment: Cosmetic; no correctness risk.

slop-3:
- Disposition: Fixed
- Action: gsm2tree.py:310 — removed inline comment "# from __future__ import annotations (must be first; defers annotation evaluation)".
- Severity assessment: Cosmetic.

slop-4:
- Disposition: Fixed
- Action: gsm2tree.py — removed "# span: fltk.fegen.pyrt.terminalsrc.Span" and "# children: list[tuple[<Label> | None, <ChildType>]]" inline comments.
- Severity assessment: Cosmetic.

slop-5:
- Disposition: Fixed
- Action: gsm2tree.py — removed "# append", "# extend", "# child", "# Per-label methods" section comments.
- Severity assessment: Cosmetic.

slop-6:
- Disposition: Fixed
- Action: genparser.py:193 — removed "# Generate companion Protocol module" comment.
- Severity assessment: Cosmetic.

slop-7:
- Disposition: Fixed
- Action: Canonical explanation kept at fltk2gsm.py:13-18 (_DEFAULT_CST). Five call sites trimmed to "# nominal nested-Label mismatch; see _DEFAULT_CST in fltk2gsm.py" (or equivalent one-liner). Files changed: genparser.py:61, plumbing.py:147-149 and 176-182, test_plumbing.py:581-582, unparse/genunparser.py:49-51.
- Severity assessment: No functional change; eliminates stale cross-reference fragility.

slop-8:
- Disposition: Fixed
- Action: test_cst_protocol.py:52 — replaced `list[dict]  # type: ignore[type-arg]` with `list[dict[str, Any]]`; added `from typing import Any` at file top.
- Severity assessment: Return type was underspecified; callers accessed dict keys as Any. Now properly typed.
