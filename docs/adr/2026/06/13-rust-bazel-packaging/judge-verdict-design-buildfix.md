# Judge verdict — design review (build-fix follow-on)

Phase: design. Doc: `design-buildfix.md`. Round 1.
Notes: `notes-design-buildfix-design-reviewer.md` — 3 findings (design-1, design-2,
design-3), all dispositioned Fixed.
Ground-truth back-check: pyo3 0.29 `prelude.rs` (Bazel crate cache), `rust.bzl`,
`fltk/fegen/gsm2tree_rs.py`.

## Other findings walk

### design-1 — Fixed
Reviewer claim: §2.4's `object → PyObject` example is factually wrong — `PyObject`
is not in pyo3 0.29's prelude nor re-exported at the crate root, so a rule named
`object` does not collide. Consequence: the headline example for the design's only
Tier-1 REVISE verdict motivates a non-existent collision; an implementer following
§10.1's `object`/`err`/`result` test list writes a test asserting `object` is
rejected/qualified that corresponds to no real rustc error, and may trust the
analysis enough to skip the genuine gaps.

Ground truth: `prelude.rs:11-18` re-exports `PyErr`/`PyResult` (`:12`), `PyAny`/
`PyModule` (`:17`) — **no `PyObject`**. Reviewer is correct.

Disposition action verified against revised doc:
- §2.4 (design lines 142-151) now states `PyObject` is **not** in the prelude nor
  re-exported at the crate root (`lib.rs` re-exports only `FromPyObject`/
  `IntoPyObject`/`IntoPyObjectExt`), and explicitly: "a rule named `object` →
  `PyObject` does **not** collide — it is not an example of a gap."
- Keeps `err → PyErr` / `result → PyResult` (`prelude.rs:12`) as the genuine
  `Py`-prefixed gaps.
- §10.1 (lines 484-486) explicitly warns "Do **not** include `object`/`PyObject`
  ... so `object` does not collide and is not a valid test of the reservation."
- §9 table row 1 and §11 O1 updated to match.

Assessment: the wrong example is removed, the corrected re-export set matches
ground truth, and the test-plan trap the consequence warned about is closed with
an explicit anti-instruction. Fix addresses the comment completely. Accept.

### design-2 — Fixed
Reviewer claim: §2.4's collision model misses the non-`Py`-prefixed prelude
re-exports against the bare `{CN}` data struct, and the "qualify-everything-
`Py`-prefixed ⇒ structurally safe" completeness claim is false for its own goal —
rules named `bound`/`py`/`python`/`borrowed` collide via the bare `pub struct {CN}`
with prelude glob re-exports `Bound`/`Py`/`Python`/`Borrowed`, which qualifying
`Py`-prefixed handles does nothing for. Consequence: a user taking the "preferred"
path believing pyo3 collisions are structurally impossible still ships
`bound`/`py`/`python`/`borrowed` miscompiles (E0255) — the exact silent-narrowing
failure the Tier-1 analysis claims to close.

Ground truth: `prelude.rs:13-14` re-exports non-`Py`-prefixed `Borrowed`/`Bound`/
`Py` (`:13`), `Python` (`:14`). `gsm2tree_rs.py` emits a bare `pub struct
{class_name}` per rule and the claims check (`:144`+) compares generated idents
only against each other, not the pyo3 glob. Reviewer is correct on both the bare
struct and the false completeness claim.

Disposition action verified against revised doc:
- §2.4 (design lines 152-163) adds the bare `pub struct {CN}` bullet, names the
  `bound`/`py`/`python`/`borrowed` collisions against the non-`Py`-prefixed
  re-exports, and notes the cross-rule claims check does not compare against the glob.
- "Mandated robustness upgrade" (lines 173-202) splits the collision surface into
  two halves and **withdraws** the false claim: lines 187-192 state the
  "structurally cannot ship an unhandled pyo3 collision" property is "**not**
  achievable by qualifying `Py`-prefixed types alone."
- Makes **de-globbing** `pyo3::prelude::*` the load-bearing, mandatory step (lines
  194-202): the glob is unenumerable, so it must be replaced with an explicit import
  list before any check can cover half 2.
- §9 table row 1, §10.1 (added `bound`/`py`/`python`/`borrowed` cases + generator-
  load test), §11 O1 updated to match.

Assessment: the missing half of the collision surface is now documented, the false
completeness property is explicitly withdrawn, and the corrected mechanism (de-glob)
is the only one that can actually deliver the claimed robustness — directly closing
the consequence. Fix addresses the comment completely. Accept.

### design-3 — Fixed
Reviewer claim: §5.2 option (1) "the macro already synthesizes/owns the crate root
layout" overstates what the macro does — `_assemble_crate` `cp`s the consumer
`lib.rs` verbatim; the macro owns the directory layout, not lib.rs contents.
Consequence: an implementer looks for a synthesis hook that does not exist, or
prepends `#![recursion_limit]` without handling the inner-attribute-ordering
constraint, producing `error: an inner attribute is not permitted following an
outer attribute`.

Ground truth: `rust.bzl:207` is `cp $(location {lib_rs}) $$OUTDIR/lib.rs` —
verbatim copy; `crate_root` points at the copy (`:225`). Reviewer is correct.

Disposition action verified against revised doc:
- §5.2 option (1) (design lines 342-357) now states the macro "owns the crate
  *directory layout*, not the *contents* of `lib.rs`," quotes the verbatim
  `cp $(location {lib_rs}) $$OUTDIR/lib.rs`, restates the fix as "a genuine (small)
  behavioral change to that genrule" (prepend then copy), and calls out the
  inner-attribute-ordering constraint with the exact `error: an inner attribute is
  not permitted following an outer attribute` symptom and the requirement that the
  recursion-limit line be emitted first.
- §9 table row 4 and §5.2 recommendation adjusted from "hook existing synthesis" to
  "contained genrule change."

Assessment: the overstated framing is corrected to match `rust.bzl`, and both edges
the consequence named (missing hook, ordering error) are explicitly addressed. Fix
addresses the comment completely. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified (design-1, design-2, design-3). No TODOs, no Won't-Do.
Reviewer's "Notes (not findings)" block (Problems 2/3/5/6/7 + parser asymmetry)
required no disposition and is corroborated by the design and source; no action.

---

## Verdict: APPROVED

All three Fixed dispositions verified against the revised design text and
back-checked against ground truth (pyo3 0.29 `prelude.rs`, `rust.bzl`,
`gsm2tree_rs.py`). Each fix removes the wrong premise the reviewer identified and
closes the stated consequence. No disposition is wrong.
