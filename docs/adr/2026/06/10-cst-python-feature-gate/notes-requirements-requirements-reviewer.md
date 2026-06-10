# Requirements review: cst-python-feature-gate

Style: concise, precise, no padding. Audience: smart LLM/human.

Overall: the doc is a faithful, well-scoped translation of the request; project premise is sound (settled roadmap phase 1, exploration confirms a clean pyo3/native split exists). Findings below are refinements, not direction changes.

## requirements-1

- **Section**: "System behavior > 1. Feature gate on fltk-cst-core", bullet "**Feature off:** ... The pure-Rust API additionally exposes ... span text access ... and `merge`/`intersect` equivalents." Also §2 "**Feature off:** ... providing at minimum: ...".
- **What's wrong**: The new native surface (span `text`, native `merge`/`intersect`) is specified only under the "Feature off" heading. The doc never states whether this surface also exists when the feature is **on**. A designer reading literally could gate the new native methods behind `#[cfg(not(feature = "python"))]`, producing a feature-dependent API.
- **Why**: The request's sequencing rationale (a): the gate "defines and stabilizes the native API contract the parser backend will code against." Roadmap mode 3 (do-not-relitigate) is "Python applications with a Rust parser" — i.e. the future parser backend runs in python-**on** builds and needs the same native API there. The requirements doc itself says "New pure-Rust surface is additive" (User-visible surface) but never says mode-independent.
- **Consequence**: A feature-off-only native API would compile and pass every acceptance criterion in this doc, yet fail the phase-2 purpose: the parser backend would face two different `fltk-cst-core` APIs depending on feature state, and stabilizing it later would be a breaking change to whichever consumers picked one up.
- **Fix**: State explicitly that all new native (non-pyo3) surface is available identically in both feature modes; the feature gates only the pyo3 surface.

## requirements-2

- **Section**: "System behavior > 1", bullet: "all native methods (`Span::unknown`, `new_sourceless`, `new_with_source`, `start`, `end`; `SourceText::from_str`) remain available".
- **What's wrong**: The parenthetical reads as an exhaustive enumeration but omits native methods the exploration lists: `Span::source_full_text_str` and (python-on-only by nature) `source_as_py` (exploration, span.rs notes: "all native methods on `Span` (`unknown`, `new_sourceless`, `new_with_source`, `start`, `end`, `source_as_py`, `source_full_text_str`)").
- **Why**: "all native methods (...)" with an incomplete list invites a designer to treat the list as the contract and drop `source_full_text_str` from the python-off build.
- **Consequence**: Silent loss of an existing native accessor in python-off mode; a parser backend reading source text via it hits a gap that the gaps report then has to record as a regression this phase introduced.
- **Fix**: Either complete the list or rephrase as "all existing pure-Rust methods (per exploration) remain available; the list is illustrative, not exhaustive" — and note `source_as_py` is inherently python-on.

## requirements-3

- **Section**: "System behavior > 5. CI" / "User-visible surface > CI config" ("new job/step(s) for python-off mode visible in `.github/workflows/ci.yml`").
- **What's wrong**: Coverage of python-off mode is required only in the CI workflow file; nothing requires the check to be runnable through the local precommit gate. Exploration: CI's substance is `make check`, and `cargo-test` covers only the workspace.
- **Why**: Request: "Add the python-feature-off build/test to CI so the configuration can't rot." The intent is rot-prevention; a CI-only step that developers can't reproduce locally (because `make check` skips it) catches rot late instead of preventing it. Naming the specific file (`ci.yml`) is also mild design leakage — the observable requirement is "the python-off configuration is exercised by the automated gate."
- **Consequence**: Designer satisfies the letter by adding a bespoke CI step outside `make check`; developers break python-off mode locally and only discover it on push.
- **Fix**: Require the python-off build/test to be invocable via the standard local check entrypoint (or an equivalently documented single command) and exercised in CI; drop the file-path-level prescription.

## requirements-4

- **Section**: "Open questions > 4. Feature name/polarity" — "Treated here as settled-unless-redirected".
- **What's wrong**: The request explicitly delegates this to the designer ("designer picks final name/polarity"); the requirements doc pre-settles it at the requirements stage. Minor over-specification of a delegated decision.
- **Why**: Request, Scope item 1: "working name `python`, default-on; designer picks final name/polarity."
- **Consequence**: Low — exploration recommends the same choice — but the doc shifts a decision the requester placed in design into requirements, and a designer with a good reason to deviate (e.g. `pyo3` to track the dependency name) may feel bound.
- **Fix**: Keep the recommendation but phrase as design default, not requirements-settled.
