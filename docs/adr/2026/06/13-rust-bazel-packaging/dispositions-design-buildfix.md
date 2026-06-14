# Dispositions: design-buildfix.md review (round 1)

Reviewer notes: `notes-design-buildfix-design-reviewer.md`.
Design under revision: `design-buildfix.md`.

All three findings were fact-checked against pyo3 0.29's actual prelude
(`prelude.rs:11–18`, located in the Bazel crate cache), the generator source
(`fltk/fegen/gsm2tree_rs.py`), and `rust.bzl`. All three are correct. All Fixed.

---

design-1:
- Disposition: Fixed
- Action: §2.4, first prelude bullet. Dropped the `object → PyObject` example and
  the bare `PyObject` from the prelude re-export list. Replaced with the verified
  pyo3 0.29 re-export set (`prelude.rs:11–18`), stated explicitly that `PyObject` is
  neither in the prelude nor re-exported at the crate root (`lib.rs` re-exports only
  `FromPyObject`/`IntoPyObject`/`IntoPyObjectExt` from `conversion`), and kept `err →
  PyErr` / `result → PyResult` (`prelude.rs:12`) as the genuine `Py`-prefixed gaps.
  Also removed `object` from the §10.1 test-plan list and explicitly warned against
  testing it (it does not collide). Updated §9 table row 1 and §11 O1 to match.
- Severity assessment: Medium. The example was the headline for the design's only
  Tier-1 REVISE verdict; an implementer following it would have written a test
  asserting `object` is rejected/qualified that corresponds to no real rustc error,
  and might have trusted the analysis enough to skip the genuine gaps. Verified
  directly: `prelude.rs` re-exports `PyErr`/`PyResult` (`:12`) but no `PyObject`.

design-2:
- Disposition: Fixed
- Action: §2.4. Added a second prelude bullet documenting that the generator emits a
  **bare `pub struct {class_name}`** per rule (`gsm2tree_rs.py:_node_block`, confirmed
  `pub struct {class_name}` at the node-block emission), so rules named
  `bound`/`py`/`python`/`borrowed` collide with the non-`Py`-prefixed prelude
  re-exports `Bound`/`Py`/`Python`/`Borrowed` (`prelude.rs:13–14`) — and that the
  cross-rule claims check (`:144`) does not compare against the pyo3 glob. Rewrote the
  "Mandated robustness upgrade" block: split the collision surface into the two halves
  (rule-derived `Py{CN}` handle vs. `Py`-prefixed imports; bare `{CN}` struct vs.
  non-`Py`-prefixed re-exports), **withdrew** the false "qualify-everything-`Py`-prefixed
  ⇒ structurally safe" completeness claim, and reframed the upgrade so the load-bearing
  step is **dropping `use pyo3::prelude::*;`** in favor of an explicit, enumerable import
  list (the only way the generator can see the non-`Py`-prefixed collisions), with the
  residual `Py`-prefixed-qualification being the one remaining genuine choice. Updated
  §2.5, §9 table, §10.1 test plan (added `bound`/`py`/`python`/`borrowed` cases plus a
  generator-load test over the full import set), and §11 O1.
- Severity assessment: High. As written the design asserted a completeness property
  the proposed mechanism could not deliver; a user taking the "preferred" path
  believing pyo3 collisions were structurally impossible would still ship rules named
  `bound`/`py`/`python`/`borrowed` that miscompile downstream with E0255 — the exact
  silent-narrowing failure the Tier-1 analysis claims to close.

design-3:
- Disposition: Fixed
- Action: §5.2 option (1). Corrected the overstated "the macro already
  synthesizes/owns the crate root layout" framing. Documented (verified in `rust.bzl`)
  that `_assemble_crate` copies the consumer `lib.rs` **verbatim**
  (`cp $(location {lib_rs}) $$OUTDIR/lib.rs`) and points `crate_root` at the copy — the
  macro owns the directory layout, not lib.rs contents. Restated option (1) as a real
  (small) behavioral change to the genrule: prepend `#![recursion_limit = "512"]` ahead
  of the copied content, with the inner-attribute-ordering constraint called out
  (`#![recursion_limit]` must be the first line, else `error: an inner attribute is not
  permitted following an outer attribute`). Adjusted the "natural extension, not new
  surface" recommendation to reflect that it is a contained genrule change rather than
  hooking an existing synthesis step.
- Severity assessment: Low/Medium. An implementer reading "the macro already
  synthesizes the crate root" would look for a synthesis hook that does not exist, or
  prepend without handling the inner-attribute ordering, producing a confusing build
  error in the exact mechanism the verdict mandates.

---

## Notes section (reviewer's verified-correct items)

The reviewer's "Notes (not findings)" block confirmed the remaining dispositions
(Problems 2, 3, 5, 6, 7 and the parser-side asymmetry in §2.4) are correctly grounded.
No action required.
