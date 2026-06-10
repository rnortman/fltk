# Dispositions: requirements review round 1 — cst-python-feature-gate

Style: concise, precise, no padding. Audience: smart LLM/human.

Notes source: `notes-requirements-requirements-reviewer.md`. Requirements doc updated in place: `requirements.md`.

requirements-1:
- Disposition: Fixed
- Action: Added a "Native surface is mode-independent" bullet to "System behavior > 1. Feature gate on fltk-cst-core": all native (non-pyo3) API, existing and new, is available identically in both feature modes; the feature gates only the pyo3 surface. Includes the roadmap rationale (request sequencing point (a); mode 3 runs the parser backend in python-on builds).
- Severity assessment: Highest-impact finding. Without it, a feature-off-only native API passes every acceptance criterion yet defeats the phase's stated purpose — the parser backend would face two divergent APIs by feature state, and unifying later would break whichever consumers adopted one. Fact-checked against request ("defines and stabilizes the native API contract the parser backend will code against") and roadmap mode 3: confirmed.

requirements-2:
- Disposition: Fixed
- Action: Rephrased the native-methods bullet in "System behavior > 1 > Feature off" to "**all** existing pure-Rust methods remain available", expanded the parenthetical to include `source_full_text_str`, marked the list illustrative-not-exhaustive, and noted `source_as_py` as inherently pyo3-bound (python-on only).
- Severity assessment: Moderate. The original parenthetical read as exhaustive and omitted `source_full_text_str` (exploration confirms it is a native method); a literal designer could silently drop a working native accessor from python-off builds — a regression this phase would itself introduce.

requirements-3:
- Disposition: Fixed
- Action: Retitled "System behavior > 5" to "CI / automated gate"; now requires (a) CI exercises the python-off build/test including spike and no-pyo3 check, and (b) the same check is invocable locally via the standard precommit check entrypoint or an equivalently documented single command. Replaced the "User-visible surface" bullet naming `.github/workflows/ci.yml` with a path-neutral "Automated checks" bullet.
- Severity assessment: Moderate. Fact-checked: request's intent is rot-prevention ("so the configuration can't rot"), and exploration confirms `make check` / `cargo-test` cover only the workspace today — a CI-only step developers can't run locally catches rot at push instead of preventing it. The file-path prescription was design leakage; removed.

requirements-4:
- Disposition: Fixed
- Action: Rewrote "Open questions > 4" to state the request delegates name/polarity to the designer; `python` default-on is the design default (per exploration's recommendation), not a requirements-level decision; designer may deviate with rationale while keeping default-on behavior. Public-API-from-day-one note retained.
- Severity assessment: Low. The prior wording ("settled-unless-redirected") shifted a decision the request explicitly placed in design ("designer picks final name/polarity") into requirements; a designer with a good reason to deviate could have felt bound.
