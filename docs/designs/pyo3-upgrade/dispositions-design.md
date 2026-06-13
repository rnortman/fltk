# Dispositions — pyo3-upgrade design review, round 1

Style note (applies to this doc): concise, precise, complete, unambiguous; audience is a smart
LLM/human implementer.

Fact-check basis: counted pyclass attrs in committed generated files; inspected
`docs/rust-cst-extension-guide.md` version pins.

design-1:
- Disposition: Fixed
- Action: §2.G accounting restated as "2 NodeKinds + 17 label enums across `src/cst_fegen.rs`
  (1 NodeKind + 14 label enums) and `src/cst_generated.rs` (PoC grammar, 1 NodeKind + 3 label
  enums)", with an explicit step-5 verification note that warnings must clear in both files.
  Verified independently: grep counts 14 `name = "*_Label"` pyclass attrs + 1 NodeKind in
  `cst_fegen.rs`, 3 + 1 in `cst_generated.rs` — reviewer's breakdown is correct.
- Severity assessment: Low-moderate. The generator fix covers both files regardless, but the
  wrong breakdown would mislead step-5 verification — phantom-residual hunting, or missing
  surviving PoC-grammar warnings if a regen path were skipped.

design-2:
- Disposition: Fixed
- Action: §3 step 8 now includes updating `docs/rust-cst-extension-guide.md`:
  `fltk-cst-core = "0.1"` (line 59) → `"0.2"`, `pyo3 = "0.23"` (line 63) → `"0.29"`, plus a
  rebuild-requirement note for existing consumer extension crates. Verified independently: the
  guide's template pins both stale versions at the cited lines.
- Severity assessment: High for downstream consumers. A consumer following the published guide
  verbatim post-upgrade builds exactly the mixed-version extension the design's own 0.2.0 ABI
  marker exists to reject, with no documented remediation — a break in the surface CLAUDE.md
  designates as protected public API.
