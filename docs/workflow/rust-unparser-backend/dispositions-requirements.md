# Dispositions: Requirements Review — Rust Unparser Backend

Reviewer notes: `docs/workflow/rust-unparser-backend/notes-requirements-requirements-reviewer.md`
Refined request: `docs/workflow/rust-unparser-backend/requirements.md`

---

requirements-1:
- Disposition: Fixed
- Action: Softened prescriptive language throughout "What a generated Rust unparser does" and "Build system integration points" sections. Removed specific artifact names (`fltk-unparser-core`, `gen-rust-unparser`, `with_unparser`) that were stated as settled. Replaced with pattern-relative descriptions ("analogous to `fltk-parser-core`", "analogous CLI and Makefile integration", "will need to fit into this workspace structure") and explicit notes that exact names, boundaries, and decomposition are design decisions. The parser-backend artifacts remain as context for the pattern; what changed is that the unparser-specific artifact structure is no longer pinned.
- Severity assessment: Without the fix, a designer could treat crate names, crate boundaries, CLI subcommand surface, and lib.rs parameters as pre-decided and skip evaluating alternatives. The fix preserves the pattern context while leaving design space open.

requirements-2:
- Disposition: Fixed
- Action: In "What the user is asking for" section, changed "must produce equivalent Doc trees and include the full formatting pipeline in Rust" to "must reproduce all of this formatting behavior" with the Doc combinator tree, spacing resolution, and Wadler-Lindig renderer described as the Python reference rather than a mandated representation. Also softened "produces a Doc tree from it" to "produces formatting output from it" in the generated-code bullet. The formatting pipeline behavior requirement is preserved; the internal representation is explicitly left to design.
- Severity assessment: Minor — reproducing the formatting pipeline naturally wants a Doc-like IR, so in practice the representation would likely be similar regardless. The fix avoids the edge case where a designer feels locked into a literal enum mirroring every Python Doc subclass.

requirements-3:
- Disposition: Fixed
- Action: No additional changes needed. This is a positive overall assessment whose single specific concern (artifact naming crossing into design) is fully addressed by the requirements-1 fix. The reviewer confirmed the doc is "a faithful and intuitive framing" with no genuine user-intent questions left silently guessed.
- Severity assessment: None — this finding validates the doc rather than identifying a defect. The one weakness it flags is already resolved.
