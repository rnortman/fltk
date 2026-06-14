# Requirements Review — Clockwork consumes FLTK+Rust under Bazel

Reviewed: requirements.md against request + exploration-fltk.md + exploration-clockwork.md.
Overall: the doc faithfully captures the spirit of the request and is well-grounded in the
exploration. It correctly identifies this as a "prove it out + decide the how" task and keeps the
strategic decisions as open questions for the user to ratify. Findings below are mostly about
design-leakage into a requirements doc and a few scope-bar ambiguities.

---

## requirements-1 — Design/implementation detail leaks into acceptance criteria and surface

Section: "In scope" (lines 21-24), "User-visible surface" (lines 99-106), "System behavior" #2 (lines 56-58).

What's wrong: The doc names concrete implementation artifacts that the designer should be free to
choose: specific Starlark rule/macro names (`generate_rust_parser`, `fltk_pyo3_cdylib`,
`gen-rust-cst`/`gen-rust-parser` as rule names), file names the action must emit (`cst.rs`,
`parser.rs`, `lib.rs`), the requirement to write a consumer `lib.rs` "wiring `#[pymodule]`", and
"new/updated Bazel rules for gen-rust-cst / gen-rust-parser, a cdylib-build macro." These are *how*,
not *what*.

Why: Per CLAUDE.md and the requirements-doc contract, acceptance criteria should be "observable
behavior and surfaces, not how-it's-built." The request delegated the "how" ("How will we do this?
... Finding/suggesting answers is your job") — pinning macro names and file layout pre-empts the
designer. Note these names *are* real CLI subcommands per exploration (`gen-rust-cst`,
`gen-rust-parser` exist at genparser.py:265/368), so citing them as the existing CLI surface is
fine; inventing *new rule/macro names* (`generate_rust_parser`, `fltk_pyo3_cdylib`) is the leak.

Consequence: Designer may treat the invented names as mandated, or reviewers may flag deviation from
them as scope drift. Over-constrains an implementation that should be free to e.g. emit a single
combined rule, a different macro shape, or different intermediate file names.

Suggested fix: State the behavior — "FLTK exposes a Bazel-visible way to run Rust codegen and build
the resulting sources into an importable PyO3 cdylib" — and move concrete rule/macro/file names into
a non-normative "implementation notes / likely shape" appendix, clearly marked as designer's choice.

---

## requirements-2 — Acceptance criterion 3 over-specifies the failure mechanism (white-box)

Section: "System behavior" #3 (lines 60-63).

What's wrong: Criterion 3 phrases "bindings import" in terms of internal mechanics: "without the
pure-Python span fallback firing (no `warnings.warn` from `fltk/fegen/pyrt/span.py`)" and the exact
error string `RuntimeError: cross-cdylib Span type lookup failed (fltk._native.Span)`. These are
implementation-internal signals, not the user-facing outcome.

Why: The observable requirement is "the Rust span path is actually exercised, not silently replaced
by the pure-Python fallback." Tying acceptance to a specific `warnings.warn` call site and a verbatim
error string couples the test to current internals that the designer/implementer might legitimately
change (e.g. the fallback could be made an error, or the message reworded). The contract says
criteria should be observable behavior.

Consequence: A correct implementation that changes the fallback signaling (or that the team decides
should *hard-fail* rather than warn) would spuriously fail this criterion; or the test gets written
to grep for a brittle internal string.

Suggested fix: Re-state as observable behavior: "the generated Rust span path is used (the canonical
`fltk._native.Span` is resolved), confirmed by a positive assertion on Rust-backed behavior, not by
absence of a specific warning." Keep the internal signals as diagnostic hints, not pass/fail gates.

---

## requirements-3 — Criterion 5 (cross-backend equivalence) bar is left genuinely undefined, not just "to be pinned"

Section: "System behavior" #5 (lines 73-77) + open question TODO(equivalence-surface) (lines 232-238).

What's wrong: Criterion 5 is simultaneously listed as a "done" criterion and explicitly deferred
("Exact equivalence surface to be pinned during implementation"), and the same question is also an
open question for the user. So a hard acceptance criterion depends on an unresolved user decision.

Why: The request asks to "prove that the bindings work in context of bazel." Equivalence to the
Python parser is the doc's own invention of how to prove "works in context" — it is a reasonable
proxy, but the request never asked for Rust-vs-Python CST equivalence. Making it acceptance criterion
#5 risks over-scoping: full structural/byte-exact equivalence across a corpus is a large effort the
user may not want for a POC.

Consequence: If the implementer reads the strong end of the range, this balloons into building a
cross-backend differential test harness — well beyond "prove the bindings work." If the weak end,
criterion 5 is nearly identical to criterion 4 and adds little.

Suggested fix: Either (a) demote equivalence to an explicit "minimal" bar baked into criterion 4
(same parse success + top-level rule for one input) and drop the open-ended range, or (b) keep it as
a pure open question and remove it from the numbered acceptance criteria until the user picks a bar.
Don't have a "done" gate whose definition is itself an unresolved question.

---

## requirements-4 — TODO(grammar-regex-subset): a discovered blocker could change Clockwork source, which the request did not anticipate

Section: Constraints "Regex subset" (lines 138-140) + TODO(grammar-regex-subset) (lines 224-230).

What's wrong: The doc correctly flags that if `clockwork.fltkg` uses regex features incompatible with
`regex-automata`, the grammar must be edited — a Clockwork *source* change. This is surfaced well,
but it sits as an open question rather than being called out as a potential hard blocker on the
whole deliverable.

Why: The request frames this as a packaging/proof exercise; the user did not anticipate having to
modify the grammar. Per the doc's own constraint, incompatibility is "a blocking finding to surface,
not something to work around silently" (good). But acceptance criterion 1 ("Codegen under Bazel ...
produces cst.rs and parser.rs") silently assumes the grammar *is* compatible.

Consequence: If incompatible, criteria 1-6 are all unreachable without a grammar change the user
hasn't approved — the project could stall mid-implementation. Better to verify this one fact up front
(it is the single cheapest derisking step) rather than discover it after the Bazel plumbing is built.

Suggested fix: Recommend resolving TODO(grammar-regex-subset) *first*, before any Bazel work, since
it can independently invalidate the approach and the check is cheap (run `gen-rust-parser` against
the grammar once). The contract allows a single essential file lookup, but this is for the
implementer to do early, not the reviewer.

---

## requirements-5 — "submodule vs pip" framing partially answered but answer not surfaced to the user as a correction

Section: TODO(dep-mechanism) (lines 161-188).

What's wrong: The request explicitly asks "Stick with submodule, or switch to pip packaging?" The doc
correctly notes (lines 163-166) that Clockwork uses `git_override` (a Bazel module source dep), not a
git submodule — so the request's premise is slightly mistaken. Good catch. But this correction is
buried in the open-question body; given the user asked a direct either/or, the corrected framing
("you're not actually on a submodule; the real choice is git_override-source vs wheel") deserves to be
the headline of the recommendation, since it changes what the user is choosing between.

Why: Spirit of the request: the user wants a clear answer to a decision they framed. The doc's
substance is right; the risk is the user's mental model ("submodule") goes uncorrected.

Consequence: Minor — risk the user approves under a wrong mental model. Low severity; substance is
present.

Suggested fix: Ensure the final written recommendation (the deliverable at lines 25-26) leads with the
premise correction, not just the option matrix.

---

## requirements-6 — Big picture: is this a good idea? — Yes, with one altitude note

Section: overall.

Assessment: The project is well-justified. CLAUDE.md states FLTK's primary purpose is out-of-tree
consumers and the Rust backend's explicit goal is a near-drop-in replacement; proving a real
representative consumer (Clockwork) can build it under Bazel is squarely the kind of derisking that
matters before declaring the Rust backend usable. Not a duplicate, not a non-problem. The
out-of-scope section is sensibly drawn (does not rewire Clockwork's production path; no perf tuning;
no mandated publishing).

One altitude note: the deliverable is two-headed — (a) a working POC in the Clockwork repo and (b)
FLTK-side product changes (new Bazel rules, rules_rust wiring, packaging `fltk._native` as a
Bazel-visible artifact). Item (b) is genuine FLTK *feature* work, not throwaway POC scaffolding —
e.g. fixing the `py_library` glob so `_native.abi3.so` ships (lines 115-121) is a real bug fix every
Bazel consumer needs. The doc treats POC and product work as one scope. That's defensible (you can't
prove the POC without the product changes), but the user should know that approving this approves
shipping new public FLTK Bazel surface (rule/macro names become API), not just a one-off experiment.
Worth stating explicitly so the FLTK-side surface gets the same "this is public API" care CLAUDE.md
demands of generated symbols.

---

## requirements-7 — Minor: criterion 7 (ABI mismatch diagnosable) may be untestable as stated within POC scope

Section: "System behavior" #7 (lines 84-87).

What's wrong: Criterion 7 requires that a *mismatched* `fltk-cst-core` version surfaces as the typed
error. But the doc's own dep-mechanism default (A, single git pin governing both cdylibs) is designed
to make a mismatch *impossible to produce* under the Bazel build. So there is no natural way to
exercise this criterion without artificially constructing a mismatch.

Why: The criterion's last sentence half-acknowledges this ("this criterion just records that the
guard must remain effective"), i.e. it's really an invariant note, not a testable acceptance gate.

Consequence: Implementer may waste effort trying to build a deliberate-mismatch test, or the
criterion is quietly ignored. Either way it's not a clean "done" gate.

Suggested fix: Move criterion 7 out of the numbered acceptance list into Constraints as "the ABI
guard must remain effective; the chosen build mechanism should make matched-version the default."
Don't list it as an observable test outcome unless a mismatch test is actually in scope.
