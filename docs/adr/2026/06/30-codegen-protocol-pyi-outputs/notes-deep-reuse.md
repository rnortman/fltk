## reuse-1

**File:line**: `fltk/fegen/genparser.py:253` and `fltk/fegen/gsm2tree_rs.py:454`

**What is duplicated**: The protocol-text rendering expression `"# ruff: noqa: N802\n" + ast.unparse(protocol_mod)` appears in both locations. The `generate` command (Python path) builds it at `genparser.py:246-253`; `RustCstGenerator.generate_protocol()` builds it at `gsm2tree_rs.py:451-454`. The two expressions are textually identical.

**Existing function/utility**: There is no shared helper. The design (§2.2) explicitly identified this as a risk and named a potential shared `render_protocol_text(grammar) -> str` helper in `genparser.py`, but the implementation chose not to create it, relying on the cross-path byte-identity test as the sole guardrail. The accompanying rationale comment explaining what NOT to add (E501, F821 — `genparser.py:247-252`) lives only in the Python path; the Rust path (`gsm2tree_rs.py:452-453`) carries only a brief mirror note, so the reasoning is split across two files.

**Consequence**: Any future change to the file-level ruff suppressions — adding a new `noqa` code, altering the comment format — must be applied to both locations independently. The byte-identity test (`test_gen_rust_cst_protocol_output_matches_python_protocol`) catches output divergence after the fact but does not prevent one-site-only edits from silently producing a mis-annotated file that linters then complain about. As the suppression rationale grows more nuanced (already three codes considered — N802 kept, E501 and F821 explicitly rejected), keeping the reasoning in one place becomes more valuable.
