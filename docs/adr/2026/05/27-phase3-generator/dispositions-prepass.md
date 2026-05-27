# Dispositions — prepass review (Phase 3 generator)

## slop-1

- Disposition: Fixed
- Action: Delete narrating inline comments in `generate()` and `_node_block()` in `fltk/fegen/gsm2tree_rs.py`. Specifically: `# Preamble` (line 48), `# Per-rule blocks` (line 51), `# register_classes function` (line 59), `# Constructor` (line 156), `# Label classattr (only if there are labels)` (line 159), `# Generic append/extend/child` (lines 163–165), `# Per-label methods` (line 168), `# __eq__, __hash__, __repr__` (line 172). Section-divider box comments (`# ------------------------------------------------------------------`) are retained as they provide skimmable structure without narrating individual calls. Comments inside `_per_label_methods` that label each sub-block (`# append_{label}`, `# extend_{label}`, etc.) are also noise but are already somewhat structural; applying same fix: delete them.
- Severity assessment: Cosmetic but meaningful — LLM-generated commentary signals low authorial intent to reviewers and degrades long-term maintainability. A real PR would get flagged.

---

## slop-2

- Disposition: Fixed
- Action: Delete the two `# Separator comment` lines (before `lines.append(f"// {'─' * 75}")`) at lines ~93 and ~136 in `fltk/fegen/gsm2tree_rs.py`. Verified present in source at lines 93 and 136.
- Severity assessment: Same LLM-tell as slop-1; pure restatement of what follows.

---

## slop-3

- Disposition: Fixed
- Action: In `tests/test_gsm2tree_rs.py`, delete docstrings that restate the test name verbatim (e.g., `"""Identifier node struct is emitted."""` on `test_identifier_struct_present`). Retain docstrings that add information the name cannot: AC references (`"""AC-5: pub fn register_classes is present."""`), edge-case explanations, or non-obvious intent. After review: retain AC-10 and AC-5 references, and the explanatory docstrings on `test_zero_label_rule_omits_label_classattr` (explains the nuance of _trivia having labels). Delete the rest.
- Severity assessment: Dozens of redundant docstrings inflate the file with noise; pattern signals auto-generated docs over authored ones. Reviewers notice.

---

## slop-4

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Reviewer correctly identified this block as clean — the `// PyO3's add_submodule` comment explains a genuine non-obvious platform limitation. No action needed.
- Rationale (Won't-Do): Reviewer's own assessment was "no findings here; this block is clean." The finding is a false positive by the reviewer's own conclusion.
