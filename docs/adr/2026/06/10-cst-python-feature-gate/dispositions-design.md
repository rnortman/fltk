# Dispositions: design review round 1 — cst-python-feature-gate

Style: concise, precise, no padding. Audience: smart LLM/human.
Notes: `notes-design-design-reviewer.md`. All findings fact-checked against source at HEAD.

design-1:
- Disposition: Fixed
- Action: Verified against `docs/rust-cst-extension-guide.md` — template (lines 41-57) has only a `pyo3` dependency, no `fltk-cst-core`; line 30 claims "depends on PyO3 only," stale since the generated preamble began importing `fltk_cst_core` (`gsm2tree_rs.py:246`). Design §2.4 rewritten: the false "mirrors the fixture" claim replaced with the two real baselines (fixture-pattern vs guide-following) and their distinct migrations (feature block vs dependency addition + feature block). §2.7 now specifies adding the `fltk-cst-core` dependency to the template and correcting the stale line-30 claim. Open question 1 updated to state the guide is already stale at HEAD and dependency addition is part of the consumer migration.
- Severity assessment: Without the fix, the implementer following §2.7 ships a guide whose template still cannot compile generated code, and the user adjudicates the breaking-change open question against an understated migration. High-value finding.

design-2:
- Disposition: Fixed
- Action: New failure-mode bullet added as the second item in design §3: consumer upgrades fltk-cst-core without regenerating; `default-features = false` resolves the new `python` feature off; their committed ungated `cst.rs` fails on gated imports (`extract_span`/`get_span_type`/`span_to_pyobject`) and non-pyclass `Span`, with diagnostics pointing at generated code rather than the manifest. §2.7 migration-note scope now explicitly covers both paths (upgrade-then-regenerate, upgrade-without-regenerating; manifest fix first, independent of regeneration). Open question 1 wording updated ("with or without regenerating").
- Severity assessment: This is plausibly the first scenario existing consumers hit (dependency upgrades precede regeneration); omitting it from the migration note leaves the loudest failure undocumented and the OQ1 sign-off incomplete.

design-3:
- Disposition: Fixed
- Action: Verified the shell semantics: in `make`'s default `/bin/sh`, `if cargo tree | grep -q pyo3` takes grep's exit status, so a failing `cargo tree` (empty stdout) passes the gate vacuously. §2.6 `check-no-pyo3` recipe rewritten: `set -e` with command-substitution assignment fails the recipe if `cargo tree` fails; positive control (`grep -q fltk-cst-core`) proves the tree was produced before the negative assertion; reviewer's optional suggestion also adopted — the literal requirements-§1 acceptance command (`cargo tree -p fltk-cst-core --no-default-features`, no pyo3) is now run directly, with the spike-transitivity mapping stated. Explanatory paragraph added after the recipe.
- Severity assessment: The unfixed gate goes green exactly in the rot scenario it exists to catch (renamed package, manifest/lock breakage), silently voiding requirements §3's mechanical no-pyo3 guarantee and §5's rot prevention.
