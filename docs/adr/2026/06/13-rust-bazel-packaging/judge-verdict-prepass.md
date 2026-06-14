# Judge verdict — prepass (slop + scope)

Phase: prepass. fltk base fafa6d7..HEAD 36eda0d; clockwork base ece332ad..HEAD 45bc7fe. Round 1.
Notes: 2 reviewer files (slop, scope); 4 findings (slop-1, slop-2, slop-3, scope).
Note: reviewer notes were written against fltk 353d24c / clockwork 0bf463b; HEAD includes the respond commits (fltk 36eda0d, clockwork 45bc7fe). Verified dispositions against the respond diffs `0bf463b..45bc7fe` and `353d24c..36eda0d`.

## Added TODOs walk

No TODOs added in the respond diffs. (Section retained for structure; nothing to walk.)

## Other findings walk

### slop-1 — Fixed
Claim: warning-filter heuristic at `clockwork_rust_roundtrip_test.py` is fragile in two directions — (a) `str(w.message)` yields the warning object repr not its text, (b) `w.filename` matches any path containing "fltk". Consequence: filter may silently miss the fallback warning → false-green on a gate that is meant to prove the pure-Python span fallback is not active.
Disposition: Fixed. Responder also disputes half the severity: claims `str()` on a `Warning` instance returns the message text, not the repr.
Verification:
- Disposition's factual counter is correct. `warnings.warn("…")` stores a `UserWarning("…")` instance as `w.message`; `str(UserWarning("…"))` returns the message text. The reviewer's claim (a) is wrong; `w.message.args[0]` is not required.
- But this is moot — responder applied the fix regardless. Diff at lines 22-24 replaces the broad `or`-filter with `issubclass(w.category, UserWarning) and "fltk/fegen/pyrt/span" in w.filename`.
- Fix is sound against the actual fallback: `fltk/fegen/pyrt/span.py` emits `warnings.warn("fltk._native could not be loaded; …", stacklevel=1)`. `stacklevel=1` ⇒ `w.filename` is span.py's own path, which contains `fltk/fegen/pyrt/span`, and the default category is `UserWarning`. Filter now matches the real fallback precisely and no longer false-positives on unrelated fltk paths.
Assessment: fix addresses the reviewer's stated consequence (the false-green risk from the broad `w.filename` half, which the responder concedes was real). Tighter filter is strictly more correct. The responder's partial dispute of (a) does not undermine the Fixed claim. Accept.

### slop-2 — Fixed
Claim: module + function docstrings carry task-tracking / design-doc references (`design §5, AC #3 + #4`) and explain a module the test doesn't directly test. Consequence: reads as LLM process-narration; section numbers rot when the design doc is revised.
Disposition: Fixed. Severity: cosmetic/maintenance.
Verification: diff at lines 1-29 replaces the module docstring (which cited `design §5, AC #3 + #4` and stated "NOT a correctness test…") with one sentence on what the test validates, and replaces the function docstring's fltk-internals explanation with a single invariant sentence. Design-doc section references removed. Current file (lines 3-7, 16) confirms no `§` / `AC #` references remain.
Assessment: fix addresses the consequence — references removed, narration trimmed. Accept.

### slop-3 — Fixed
Claim: the load-bearing fixed-basename constraint appears verbatim twice — inline impl comment in `rust.bzl` and the rule `doc` string seven lines away. Consequence: duplicate comments diverge; adds to copy-paste signal.
Disposition: Fixed. Inline copy deleted; `doc` string left as canonical reference.
Verification: respond diff `353d24c..36eda0d` removes the 3-line inline comment above `cst_out`/`parser_out` (now `rust.bzl:38`). The canonical statement survives in the rule `doc` string at `rust.bzl:109-110` ("The fixed basenames (cst.rs / parser.rs) are load-bearing: a consumer lib.rs that contains `mod cst;` and `mod parser;` relies on these exact names."). Constraint now documented in exactly one authoritative place.
Assessment: fix addresses the consequence — duplication removed, constraint preserved. Accept.

### scope — Won't-Do
Claim: scope reviewer surveyed all design §3.1–§3.5, §5 items plus TODO.md annotation and found every design-scope item present; "No findings." One deviation (single `rs_srcs` attr instead of separate `cst_rs`/`parser_rs`) explicitly called out, documented, and accepted as a strictly-simpler interface with identical semantics.
Disposition: Won't-Do (no action needed) — no findings to address.
Verification: scope notes are item-by-item against the design and the diff; the only deviation is documented with rationale and is a cleaner consumer API realizing the same design intent (both generated files fed to the macro). No stated consequence to act on.
Assessment: a finding-free scope review has nothing to remediate; Won't-Do is the correct disposition. No active-harm bar to clear because there is no finding. Accept.

## Disputed items

None.

## Approved

4 findings: 3 Fixed verified (slop-1, slop-2, slop-3), 1 Won't-Do sound (scope, finding-free review).

---

## Verdict: APPROVED

All dispositions acceptable. Three slop fixes verified against the respond diffs and current sources; the scope review found nothing to remediate and its Won't-Do is correct. Respond commits: fltk 36eda0d, clockwork 45bc7fe.
