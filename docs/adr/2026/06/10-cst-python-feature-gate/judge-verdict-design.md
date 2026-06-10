# Judge verdict — design review

Style: concise, precise, no padding. Audience: smart LLM/human.
Phase: design. Doc: `docs/adr/2026/06/10-cst-python-feature-gate/design.md`. Round 1.
Notes: 1 reviewer file; 3 findings. Dispositions: `dispositions-design.md`.

## Findings walk

### design-1 — Fixed
Claim: design §2.4 falsely said the out-of-tree guide "mirrors the fixture"; the guide template (`docs/rust-cst-extension-guide.md:41-57`) has no `fltk-cst-core` dependency and line 30 claims "depends on PyO3 only." Consequence: §2.7 as scoped ships a still-broken guide; OQ1 sign-off understates migration churn.
Source check: guide template confirmed pyo3-only, no `fltk-cst-core` entry; line-30 "depends on PyO3 only" claim present; `gsm2tree_rs.py` `_preamble` does emit `use fltk_cst_core::{...}`, so the guide is indeed stale at HEAD. Finding's premise sound.
Fix in doc: §2.4 now distinguishes the two baselines — fixture-pattern (feature block only) vs guide-following (dependency addition + feature block) — and states the guide is already stale at HEAD with the reason. §2.7 specifies adding the `fltk-cst-core` dependency (`default-features = false`, `features = ["python"]` or forwarding) and deleting/correcting the line-30 claim. OQ1 (§5) notes the guide staleness predates this change and folds dependency addition into the consumer migration.
Assessment: fix addresses claim and consequence at every named location. Accept.

### design-2 — Fixed
Claim: §3 missed the upgrade-without-regeneration failure mode — consumer with `default-features = false` upgrades fltk-cst-core, new default-on `python` feature resolves off, committed ungated `cst.rs` fails on gated imports with diagnostics pointing at generated code, not the manifest. Consequence: migration note omits the likely first-contact scenario; OQ1 adjudicated on an incomplete picture.
Source check: `crates/fltk-cst-core/Cargo.toml` comment confirms the documented `default-features = false` downstream pattern; fixture manifests match; the three gated symbols (`extract_span`/`get_span_type`/`span_to_pyobject`) and non-pyclass `Span` follow from §2.1's `lib.rs` sketch. Finding's mechanics sound.
Fix in doc: §3 now carries the case as its second bullet, including the diagnostics-don't-point-at-the-manifest detail and the required migration-note content ("manifest fix first, independent of regenerating"). §2.7 covers both paths. OQ1 reads "with or without regenerating."
Assessment: scenario fully incorporated where the reviewer asked. Accept.

### design-3 — Fixed
Claim: the §2.6 `check-no-pyo3` recipe passed vacuously when `cargo tree` fails (pipeline `if` takes grep's status; empty stdout → no match → green), defeating requirements §3's "automated, not eyeballed" exactly in the rot scenario.
Fix in doc: recipe rewritten — `set -e` with command-substitution assignment (`out="$(cargo tree ...)"`) propagates a `cargo tree` failure and aborts the recipe; positive control (`grep -q fltk-cst-core`) proves the tree was produced before the negative assertion; reviewer's optional suggestion adopted — the literal requirements-§1 acceptance command (`cargo tree -p fltk-cst-core --no-default-features`, asserted pyo3-free) runs directly with the spike-transitivity mapping stated in the explanatory paragraph.
Shell-semantics check of the new recipe: assignment-with-substitution under `set -e` does abort on `cargo tree` failure; the `! ... grep -q pyo3 || { ...; exit 1; }` guards fire on a pyo3 match and are inert otherwise; the recipe is one logical `;\`-joined line so `set -e` covers all of it. Sound.
Assessment: vacuous-pass hole closed, positive control present, acceptance command direct. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED
