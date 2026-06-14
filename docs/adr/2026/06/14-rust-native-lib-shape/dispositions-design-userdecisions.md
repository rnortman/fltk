# Dispositions: user decisions on design open questions

Design: `design.md`
Decisions source: `notes-design-user.md` (authoritative user resolutions)

The three open questions in the draft's §5 have been resolved per the user's notes.
All open-question framing has been removed; the chosen paths are now stated as decided,
and consequences have been propagated through the design body.

user-decision-1 (OQ-1 — rename relocated fegen CST module):
- Disposition: Fixed (no rename)
- Action: Applied the user's "keep the existing import name" decision. §2 Proposed
  approach now states the three layout decisions as settled. §2.2 "Module name" bullet
  rewritten to drop the "Open question OQ-1 revisits…" hedge and assert the name is
  deliberately retained. §5 retitled "Decisions (formerly open questions)"; the OQ-1
  entry now records the keep-`fegen_rust_cst` decision rather than posing the question.
- Severity assessment: Cosmetic-only resolution; a rename would have churned
  `test_module_split.py` import sites (`tests/test_module_split.py:31-44`) for no
  principle-driven benefit. Keeping the name avoids that churn.

user-decision-2 (OQ-2 — promote fegen crate out of tests/):
- Disposition: Fixed (promote to `crates/fegen-rust/`)
- Action: Applied "move it out of tests/ into a real `crates/` crate." §2 now lists the
  crate-location decision as settled. §2.2 intro rewritten to drop the "Whether to promote
  … is OQ-2; the body assumes the recommended default" hedge and state the move directly.
  §5 OQ-2 entry records the promotion. The body already used `crates/fegen-rust` for all
  layout, Makefile (§2.5: build targets, gencode RS_OUT, clippy/test/no-pyo3 lanes,
  cargo-deny line), Bazel (§2.6), and pyright references, so those consequences were
  already consistent — verified no residual `tests/rust_cst_fegen` *destination* paths
  remain (only historical "move from `tests/rust_cst_fegen/`" source references kept).
- Severity assessment: Path-churn decision; choosing `crates/` signals the artifact is
  FLTK's first-class generated Rust grammar (peer of `fltk/fegen/fltk_cst.py`) rather than
  test scaffolding. Leaving it in `tests/` would have understated its canonical role.

user-decision-3 (OQ-3 — relocated fegen `.pyi` stub location):
- Disposition: Fixed (Option A)
- Action: Applied "Option A — route the codegenned CST `.pyi` to
  `fltk/_stubs/fegen_rust_cst/cst.pyi` and add the matching `stubPath`/`extraPaths`
  `[tool.pyright]` entry." §2.2 `.pyi` bullet rewritten to drop the "(OQ-3, option a)" /
  "OQ-3 decides between (a) and (b)" hedging and state the emit target + required
  `pyproject.toml` edit as decided. §2.5 gencode bullet now names the concrete
  `--pyi-output fltk/_stubs/fegen_rust_cst/cst.pyi` flag (was `<pyright-resolved stub path>`).
  §3 `.pyi`-resolution edge case and §4 gencode-drift-gate bullet updated to cite the
  concrete path instead of "(OQ-3)". §5 OQ-3 entry records Option A and that the
  `pyproject.toml` edit is part of acceptance.
- Severity assessment: Correctness-critical for the type-check gate: without the in-tree
  stub package plus the `[tool.pyright]` edit, the stub is unresolved and the
  `fltk.fegen.fltk_cst_protocol` conformance check silently stops running. Option A keeps
  stubs in the package tree where existing `fltk/_native/*.pyi` stubs already live.

Cleanup-editor: not re-invoked. The edits were targeted hedge-removal that converted
already-present recommended defaults (which the body had assumed) into stated decisions;
no structural rewrite or new contradictions were introduced.
