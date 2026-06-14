# Design review: design-buildfix.md

Reviewer posture: adversarial fact-check against fltk `fac3da5..11d8460`, Clockwork
`932320e..42fedc8`, the generator source, and pyo3 0.29's actual prelude.

Overall: the per-defect factual grounding is strong. All seven defects, the
implementer's fixes, the `_RESERVED_CLASS_NAMES` mechanism, the qualify-vs-reserve
split, the Bazel non-forwarding fact, the Starlark concat fix, the recursion-limit
placement, the `__test__` rename, the `Span.__module__ == "builtins"` PyO3 behavior,
and the `local_path_override` scaffolding all check out against the diffs and the
implementation-log Inc 5. The findings below are where the design's *robustness
analysis* (its load-bearing REVISE verdict on Problem 1) rests on a wrong example and
an incomplete collision model.

---

## design-1 — §2.4: `object → PyObject` collision example is factually wrong for pyo3 0.29

Section: §2.4, first bullet: "A rule named `object` → `PyObject` ... derives a `pub
struct PyObject` ... that collides with the prelude import (`E0255`)" and "(e.g. a
rule named `object`/`err`/`result`)" in the test plan §10.1.

What's wrong: `PyObject` is **not** in pyo3 0.29's prelude and **not** re-exported at
the pyo3 crate root. Verified directly:
- `pyo3-0.29.0/src/prelude.rs:11-18` re-exports from `types` only `PyAny, PyModule`
  (line 17). No `PyObject`.
- `pyo3-0.29.0/src/lib.rs:347` re-exports from `conversion` only `FromPyObject,
  IntoPyObject, IntoPyObjectExt` — no `PyObject`.

So a rule named `object` derives handle `PyObject`, and there is **no unqualified
`PyObject` in scope** in the generated cst.rs preamble to collide with. The example
the design uses to motivate "the reserved set is incomplete" does not actually
demonstrate an incomplete reservation.

Why it matters: §2.4 is the evidentiary core of the design's only Tier-1 REVISE
verdict. Using a non-colliding name as the headline example of an un-reserved
collision undercuts the argument and, if implemented literally, would lead someone to
reserve/qualify `object` for a collision that does not exist (wasted churn) while the
real gaps below stay open.

Consequence: the REVISE recommendation is built on a partly-wrong premise; an
implementer following §10.1's "`object`/`err`/`result`" test list would write a test
asserting `object` is rejected-or-qualified that does not correspond to any real
rustc error, and may trust the analysis enough to skip finding the genuine gaps.

Fix: drop `object`/`PyObject` from the examples. The real prelude-re-exported
`Py`-prefixed names that DO collide are `PyErr` (rule `err`) and `PyResult` (rule
`result`) — both at `prelude.rs:12`. Keep those; they are correct and sufficient to
make the "set is hand-audited and incomplete" point.

---

## design-2 — §2.4: collision model misses non-`Py`-prefixed prelude re-exports against the bare data struct `{CN}`

Section: §2.4, "Mandated robustness upgrade" — the whole analysis is framed as: "the
*only* generated identifiers that can collide with a `Py`-prefixed pyo3 name are the
rule-derived `PyX` handles" and the preferred fix is "stop importing any `Py`-prefixed
pyo3 type unqualified in `cst.rs`."

What's wrong: the generator emits, per rule, a **bare data struct named `{CN}`**
(`gsm2tree_rs.py:843 _node_block`, struct name = `class_name`, not `Py`-prefixed) in
addition to the `Py{CN}` handle. pyo3 0.29's prelude (`use pyo3::prelude::*`, emitted
unconditionally in the cst.rs preamble) re-exports several **non-`Py`-prefixed** names
into the type namespace: `Bound`, `Py`, `Python`, `Borrowed` (`prelude.rs:13-14`),
`PyRef`, `PyRefMut`, `PyClassInitializer`, `PyClassGuard`, `PyClassGuardMut`
(`:15-18`). Verified with the generator's own naming:
- rule `bound` → `snake_to_upper_camel` → `Bound` → `pub struct Bound` collides with
  prelude `Bound` (E0255).
- rule `py` → `Py`; rule `python` → `Python`; rule `borrowed` → `Borrowed` — all
  collide.

None of these are in `_RESERVED_CLASS_NAMES` (`gsm2tree_rs.py:43-71`), and the
cross-rule claims check (`:144`) only compares generated identifiers against each
other, not against pyo3 imports — so these reach rustc as a silent miscompile, exactly
the failure mode the design says the backstop prevents.

Why it matters: the design's preferred robustness upgrade ("qualify every `Py`-prefixed
pyo3 type, then the `Py*` half of `_RESERVED_CLASS_NAMES` collapses to empty and we
*structurally cannot ship an unhandled pyo3 collision*") is **false for its own stated
goal**. Qualifying `Py`-prefixed imports does nothing for `Bound`/`Py`/`Python`/
`Borrowed`, which collide via the bare `{CN}` struct, not a `Py{CN}` handle, and which
come from `pyo3::prelude::*` — a glob you cannot make "qualified" without abandoning
the prelude and qualifying every pervasive `Bound<...>`/`Py<...>`/`Python<...>` usage
in the generated code. The design asserts a completeness property the proposed
mechanism cannot deliver.

Consequence: if the user takes the "preferred" path believing it makes pyo3 collisions
structurally impossible, rules named `bound`/`py`/`python`/`borrowed`/`ref`/`ref_mut`
still miscompile downstream with a confusing rustc E0255 — the precise "silent
narrowing invisible until a real consumer grammar hits it" the whole Tier-1 analysis
claims to close. The "fallback (mechanized completeness check)" option is the only one
of the two that can actually cover this class, and only if it enumerates the prelude's
non-`Py`-prefixed re-exports too — which the design's description of the fallback
("parse the set of unqualified `Py`-prefixed names the preamble imports") explicitly
does not.

Fix: either (a) reframe the robustness bar as "mechanized check over the full set of
unqualified names the preamble brings into the type namespace (prelude glob included),
`Py`-prefixed or not," and reserve `Bound`/`Py`/`Python`/`Borrowed`/`PyRef`/`PyRefMut`/
etc.; or (b) acknowledge that `pyo3::prelude::*` is an unenumerable glob and the only
sound mechanization is to stop using the glob and import the handful of needed prelude
names explicitly (then the import list is data the check can read). The current
"qualify-everything-`Py`-prefixed ⇒ collapses to empty ⇒ structurally safe" claim
should be withdrawn; it is not achievable as stated.

---

## design-3 — §5.2 / §9 (Problem 4): "the macro synthesizes/owns the crate root layout" overstates what the macro does

Section: §5.2 option (1): "have `fltk_pyo3_cdylib` **inject the crate-root attribute**
when it assembles the synthesized crate directory (it already synthesizes/owns the
crate root layout per `design.md` §3.4)."

What's wrong: the macro does **not** synthesize lib.rs — it copies the
consumer-authored `lib_rs` verbatim. `rust.bzl` step 1 (`_assemble_crate` genrule)
runs `cp $(location {lib_rs}) $$OUTDIR/lib.rs` — a byte copy of the consumer's file,
then sets `crate_root` to that copy. The macro owns the *directory layout* (co-locating
the three files), not the *contents* of lib.rs. The recursion-limit attribute lives in
Clockwork's hand-authored `clockwork_native_lib.rs` (confirmed in the Clockwork diff:
`#![recursion_limit = "512"]` added to that consumer file).

Why it matters: the verdict's framing ("natural extension, not new surface") is
slightly too easy. Injecting a crate-root attribute means the macro must *rewrite* the
consumer's lib.rs (prepend a line) rather than copy it, OR prepend into the assembled
crate root via a separate generated file — a real, if small, change to the assembly
genrule's `cmd`, and one with an ordering subtlety: `#![recursion_limit]` is an inner
attribute and must precede all items, so a naive `cat attr.rs lib.rs` only works if the
consumer's lib.rs has no inner attributes of its own ahead of it. The design presents
this as already-owned territory; it is feasible but is a genuine behavioral change to
the macro, and the design should say "modify the copy step to prepend" rather than
imply the synthesis already exists.

Consequence: an implementer reading "the macro already synthesizes the crate root" may
look for a synthesis step to hook and not find one, or may prepend without handling the
inner-attribute-ordering constraint, producing `error: an inner attribute is not
permitted following an outer attribute`. Minor, but it is a real edge in the exact
mechanism the verdict mandates.

Fix: restate option (1) as "modify the `_assemble_crate` genrule to prepend
`#![recursion_limit = "..."]` to the copied lib.rs (it currently `cp`s lib.rs
verbatim), ensuring the attribute is emitted before any item in the consumer file." Or
accept a `recursion_limit` macro attr (per O2) and have the genrule write the attribute
line ahead of the copied content.

---

## Notes (not findings — verified correct)

- Problem 2 / §3.2: the `["extension-module", "python"]` non-forwarding fix is real and
  already present in BOTH `@fltk//:native` (BUILD.bazel diff) and the
  `fltk_pyo3_cdylib` macro (`rust.bzl`: `crate_features = ["extension-module",
  "python"] + crate_features`), so the design's "already handled on the macro path"
  claim is correct. The doc-only generalization is sound.
- §2.4's claim that parser.rs emits only fixed class names (`PyParser`,
  `PyApplyResult`) and never rule-derived `PyX`, so rule-name collisions cannot reach
  the parser preamble — consistent with `gsm2parser_rs.py:845-958`. The only parser-side
  fix needed was the `register_classes(module: ...PyModule)` qualification, which is in
  the diff. Correct.
- §7 / Problem 6: PyO3 0.29 `#[pyclass]` without `module=` reporting `__module__ ==
  "builtins"` is corroborated by impl-log Inc 5 and the test diff; the inverted
  assertion (`!= fltk.fegen.pyrt.terminalsrc`, allow-list `("builtins",
  "fltk._native")`) matches the committed test. RATIFY is justified.
- §3 Problem 3 (Starlark implicit concat) and §6 Problem 5 (`__test__` rename) match
  the diffs exactly; nothing to add.
- §8 Problem 7: the `LOCAL_PATH_OVERRIDE` + `TODO(fltk-pin-finalize)` is present in
  Clockwork's MODULE.bazel diff exactly as described; the finalization steps are sound.
- Scope: the design stays within "ratify or revise the build-fix delta" and does not
  invent new features. The two REVISE verdicts (Problem 1 robustness, Problem 4
  placement) are in-scope generalizations of real defects, not speculative generality.
  No over-engineering concern. The pyo3 robustness REVISE is the only one whose
  technical premise needs correction (design-1, design-2) before it can be acted on.
