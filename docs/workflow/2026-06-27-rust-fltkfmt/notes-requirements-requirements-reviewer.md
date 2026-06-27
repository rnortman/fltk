# Requirements Review: notes-requirements-requirements-reviewer

Reviewer: requirements-reviewer
Target: docs/workflow/2026-06-27-rust-fltkfmt/requirements.md

## Summary

The refined request is faithful and well-grounded. The original request is quoted
verbatim. The most-intuitive reading is taken throughout (standalone Rust binary that
formats `.fltkg` = formats FLTK's own `fegen.fltkg`; zero-python pipeline; baked-in
format spec). Exploration facts are used to resolve the user's "I think" uncertainty
about `fegen.fltkfmt` and to fairly state the genuine tension around the "macro or
generic" bonus. The two open questions are real user-intent/scope matters. Crate
placement and the reuse mechanism are left open to design. One mild, borderline note
below; otherwise clean.

---

## requirements-1

**Section / quote:** "The bonus deliverable: reusable formatter scaffolding" — esp.
"Possible reuse approaches range from a shared library function that takes closures for
the grammar-specific parts, to a Rust procedural macro that generates a `main()`... to
simply providing a well-documented template..." (line 80), and the preceding
decomposition "What *can* be shared... is the `main()` scaffolding... The grammar-specific
parts are: which `apply__parse_{rule}` to call, which `unparse_{rule}` to call, and the
crate dependencies." (line 78).

**What's wrong (borderline):** Enumerating three concrete reuse mechanisms
(closure-taking library fn / proc-macro / copy template) edges into suggesting design
paths, which the enforcement says the refiner should avoid ("Nothing should even
*suggest* a design path directly; the designer is capable of seeing the solutions"). The
constraint that drives the tension — there is nothing to be generic *over* at the Rust
type level because the format spec is baked at generation time, so only the `main()`
scaffolding is shareable — is legitimate tension-explanation and grounded in exploration
(exploration-crates.md lines 156-179). The candidate-mechanism list goes one step
further than stating that constraint.

**Why this is only mild:** The user themselves opened the design-options door ("Maybe as
a Rust macro or generic"), so echoing "macro" is using the user's own word, and the
enumeration directly supports open question #2 (how much automation for the bonus). The
refiner also explicitly disclaims: "The right approach is a design decision, not a
requirements question."

**Consequence:** Low. Risk is anchoring the designer toward the three listed options
rather than letting them survey the full solution space. No mis-scoping of the build.

**Suggested fix (optional):** Keep the constraint ("the reuse mechanism must work within
the 'format spec baked at generation time' architecture; only the `main()`/CLI
scaffolding is grammar-independent") and drop the explicit menu of mechanisms, leaving
the choice wholly to design.

---

## Non-findings (checked, no action)

- **Verbatim restatement:** Original request quoted exactly. No drift.
- **CLI flag enumeration** (check mode, in-place, width, indent, output, exit codes):
  faithful expansion of "all the typical CLI flags you'd want for a code formatter."
  These are user-facing behavior (requirements), not internal design, and short
  spellings are grounded in the existing Python CLI convention from exploration. Not
  over-interpretation.
- **Open question #1 (in-place default spelling):** genuine likely-vs-likely product
  default (stdout-default like the Python CLI vs in-place-default like rustfmt/black);
  appropriate to ask, not noise, not code-answerable.
- **Open question #2 (scope of bonus):** the user flagged it "bonus points"; how far to
  invest is a legitimate user-intent/scope question.
- **Dropped `--rule` flag:** correctly omitted, with stated reasoning that the grammar
  and start rule are baked in — not a dropped requirement.
- **Crate placement** ("wire into `fegen-rust` ... or a new crate/binary target
  alongside it"): options offered, design not dictated.
- **Tension framing:** accurate and grounded; not invented; explains feasibility rather
  than telling the user to abandon the bonus.
