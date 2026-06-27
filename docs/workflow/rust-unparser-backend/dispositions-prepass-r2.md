# Dispositions: rust-unparser-backend prepass r2

Scope notes (`notes-prepass-scope-r2.md`): no findings.

slop-1:
- Disposition: Fixed
- Action: Removed the "This module is built up incrementally … land in later increments" process-narration paragraph from the module docstring (`fltk/unparse/gsm2unparser_rs.py:19-22`). The opening paragraphs already state the module's purpose.
- Severity assessment: Cosmetic but genuine — "this revision …" describes development history and becomes false the moment a later increment lands.

slop-2:
- Disposition: Fixed
- Action: Removed the "This revision covers the generator scaffold only … rule-walking increments" sentences from the test-module docstring (`tests/test_rust_unparser_generator.py:7-8`).
- Severity assessment: Same staleness issue as slop-1; low impact, but the narration belongs in commit messages, not test docs.

slop-3:
- Disposition: Fixed
- Action: Reworded the `Output` struct doc comment (`crates/fltk-unparser-core/src/render.rs:46`) to state the Rust rationale (a shared struct so both helpers can mutate the same fields without borrow contention) instead of describing the Python closures it replaced.
- Severity assessment: Translator's note — meaningless to a reader not cross-referencing the Python original, and misleading as the codebases diverge.

slop-4:
- Disposition: Fixed
- Action: Reworded the `fits` doc comment (`crates/fltk-unparser-core/src/render.rs:200`) to describe actual behavior (flat measurement; `mode` carried but unconsulted; `indent` threaded for Nest; spacing specs/joins contribute zero width) rather than the "Python tuple shape"/"lack of an else branch" framing.
- Severity assessment: Translator's note; the Python tuple shape has no meaning in the standalone Rust crate.

slop-5:
- Disposition: Fixed
- Action: Removed the paragraph documenting absent `pyrt.py` helpers from the `result.rs` module docstring (`crates/fltk-unparser-core/src/result.rs:9-12`). The porting rationale already lives in design §1/§2.1.
- Severity assessment: Design archaeology — documents what is *not* present and would silently rot if `pyrt.py` is renamed; harmless but noise.
