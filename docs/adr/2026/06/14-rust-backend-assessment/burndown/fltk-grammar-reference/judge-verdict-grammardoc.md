# Judge verdict — grammar-reference design review

Phase: design (doc artifact). Artifact: `docs/fltk-grammar-reference.md`. Round 1.
Notes: 1 reviewer file (`notes-grammardoc-review.md`); 5 findings (design-1..design-5).
Doc phase → no Added-TODOs walk; findings walked below.

## Other findings walk

### design-1 — Fixed
Reviewer claim: §9.1 + §13 cite `test_regression_recursive_inlining.py:35-178` as pinning **left-associativity**, but the test parses single-`+` input (`"x+ "`) and asserts only `has_nested_expr`; for one `+` there is only one nesting shape, so it cannot distinguish left from right. Consequence: the doc's central credibility contract ("any claim can be checked against the code") is broken on its single most load-bearing behavioral claim — a maintainer verifying associativity against that test finds it unpinned and may weaken a true claim.
Source check: `test_regression_recursive_inlining.py` read in full — docstring (lines 1-15) states purpose is bug-#1 spurious-inlining regression; input is `"x+ "` (line 139); the only structural assertion is `has_nested_expr` (lines 162-176). Claim verified. Associativity property itself is real and follows from `_grow_seed`: the grow loop re-runs the head rule and writes back the longer wrapped result (`memo.py:251-252`, inside `_grow_seed` at 228-257), so nesting accretes leftward.
Disposition check: doc §9.1 (lines 548-556) now grounds associativity on `memo.py:228-257` (esp. `251-252`) and recasts the test citation to its actual content — "pins the related property that a recursive result is nested rather than spuriously inlined; it parses a single-`+` input, so it does not by itself distinguish left from right associativity." §13 row (line 739) code column changed to `memo.py:228-257 (esp. 251-252)`. The stale test citation no longer carries the associativity claim.
Assessment: real defect, severity should-fix (citation-accuracy on the doc's headline claim); fix landed and is correctly re-grounded on the algorithm. Accept.

### design-2 — Fixed
Reviewer claim: §3.2 cites `gsm2tree.py:425` for the "no `Node` suffix" name-derivation, but line 425 is unrelated mutator-dedup code; the real function is `class_name_for_rule_node` (`gsm2tree.py:46-47`). Consequence: points a verifier at irrelevant code on the public-API-stability guarantee the drop-in-replacement contract rests on.
Source check: `gsm2tree.py:423-426` read — it is the `for c in sorted(allowed_classes)` dedup loop inside the mutator-emission path, unrelated to naming. `class_name_for_rule_node` at `46-47` returns `naming.snake_to_upper_camel(rule_name)` verbatim, no suffix. Claim verified.
Disposition check: doc §3.2 (line 167) now cites `class_name_for_rule_node`, `gsm2tree.py:46-47`; the stray `:425` is gone. Matches §3.1's existing correct citation.
Assessment: real defect, should-fix; fix landed and is exact. Accept.

### design-3 — Fixed
Reviewer claim: §8.4 / §13 assert "both backends accept `pos == len`" but cite only the Rust file; the Python side is true-but-uncited, inconsistent with the doc's per-claim citation standard. Consequence: low (claim true) but a cross-backend equivalence assertion is exactly what a downstream consumer relies on for drop-in safety.
Source check: Python `consume_literal` (terminalsrc.py:168-175) fails only on `pos + literal_len > terminals_len`, so empty literal at `pos == len` succeeds; `consume_regex` (177-181) uses `re.match(..., pos=pos)`. Rust `consume_regex`/`consume_literal` guard `pos > self.len()` (terminalsrc.rs:142, 111) and document the `pos == len` case (line 139). Claim verified both sides.
Disposition check: doc §8.4 (lines 505-512) now adds the Python grounding (`terminalsrc.py:168-181`) alongside the Rust citation; §13 "Negative position" row (line 760) lists both `terminalsrc.rs:33-37, 139` and `terminalsrc.py:168-181`.
Assessment: real (minor) groundedness gap; fix landed. Accept.

### design-4 — Won't-Do
Reviewer claim: §1 omits that `bootstrap.fltkg:13` also defines (but never uses) `inline:"!"`, "mildly weakening the §6.3 argument." Reviewer's own text records this as a NON-finding / confirmation: "No defect in the claim ... Consequence: none. Recorded so the judge knows the [claim] was checked ... and holds."
Source check: the finding states no consequence — it is an affirmative verification, not a defect. Per the rubric, a finding with no stated consequence → responder wins by default. The §6.3 claim ("the live grammars define the glyph but never apply it to an item," doc lines 376-377) already covers both `fegen.fltkg` and `bootstrap.fltkg` without naming each.
Disposition check: responder declines; rationale notes a `bootstrap.fltkg` name-drop would lengthen an already-correct passage with no accuracy gain.
Assessment: Won't-Do is correct — there is nothing to fix; the reviewer agrees. Accept.

### design-5 — Fixed (optional clarity)
Reviewer claim: §2.1 omits that a *consumer* grammar may define a looser identifier regex (`unparsefmt.fltkg:87` uses `/[a-zA-Z_][a-zA-Z0-9_]*/`, allowing uppercase). Reviewer explicitly scopes this "very low / optional"; the §2.1 claim about the `.fltkg` meta-grammar's own identifiers is already correct.
Source check: `unparsefmt.fltkg:87` defines the looser regex; it is a consumer-language property, not the `.fltkg` meta-grammar's. Reviewer noted the exploration's `fltk.fltkg:87` mention was off; responder dropped it and cites only the confirmed `unparsefmt.fltkg:87`.
Disposition check: doc §2.1 (lines 98-101) adds one clause clarifying the lowercase-snake_case rule constrains rule/label names *in `.fltkg` itself*, and that a consumer grammar may use any regex — citing `unparsefmt.fltkg:87`.
Assessment: optional nit; fix is a no-harm clarity improvement that does not weaken the correct core claim. Accept.

## Disputed items

None.

## Approved

5 findings: 4 Fixed verified (design-1, design-2, design-3, design-5), 1 Won't-Do sound (design-4).

All citation/grounding corrections landed and are accurate to source (`memo.py`, `gsm2tree.py`, `terminalsrc.py`, `terminalsrc.rs`, `test_regression_recursive_inlining.py`, `unparsefmt.fltkg` all spot-checked). No finding had a consequence the disposition failed to address; no Won't-Do hid behind out-of-scope. The doc's per-claim citation contract is now consistent across the five flagged passages.

---

## Verdict: APPROVED

All five dispositions acceptable.
