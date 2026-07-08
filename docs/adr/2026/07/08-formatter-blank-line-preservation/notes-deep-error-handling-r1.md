# Error-handling deep review — formatter blank-line preservation (r1)

Range reviewed: `ef8f727..5864ae1` (HEAD 5864ae1).
Scope: error observability and response on the changed paths only.

## errhandling-1

- **File:line:** `crates/fegen-rust/src/unparser.rs:44-58` (new `BlockComment`/`LineComment`
  node arms in `_count_newlines_in_trivia`), vs `fltk/unparse/pyrt.py:80-98`
  (`count_whitespace_newlines`).
- **The broken error path:** The new Rust node arms treat `guard.span().text_str() == None`
  as "contributes 0" — `if let Some(t) = ... { ... }` with no `else`. `text_str()`
  (`crates/fltk-cst-core/src/span.rs:430-439`) returns `None` not only for a sourceless span
  but also for *invalid* offsets on a source-bearing span (negative indices, `start > end`,
  out-of-range). The mirrored Python helper routes a node child through `extract_span_text`
  (`pyrt.py:34-50`), which **raises `ValueError`** for exactly that source-bearing-but-invalid
  case ("codepoint offsets may be out of range"). So an identical corrupt span makes the
  Python formatter crash loud and the Rust formatter silently return 0.
- **Why:** An invalid span on a node inside a successfully-parsed CST is an invariant
  violation, not expected input. Python treats it as such (fail loud, named diagnostic); the
  Rust node arms swallow it. The `None` is discarded with no log, no panic, no counter.
- **Consequence:** In the Rust backend, a corrupt/invalid trivia-node span produces
  *silently dropped blank lines* (the exact user-visible symptom this whole change exists to
  fix) with zero diagnostic. On-call sees "Rust formatter collapses blank lines on file X"
  and has nothing to correlate — no log line, no panic, no divergence signal — while the
  Python backend on the same CST would have crashed with a pointed message. The two backends
  disagree on whether this is even an error, so cross-backend parity tests over *valid* input
  won't surface it either.
- **What must change:** Make the two backends agree on the invariant-violation response.
  Either (a) have the Rust node arms distinguish sourceless (→ 0, expected) from
  source-bearing-invalid (→ panic/diagnostic, matching Python's `extract_span_text` raise), or
  (b) if the deliberate cross-backend contract is "silently degrade to 0," relax the Python
  helper so a node child with an invalid source-bearing span also returns 0 instead of
  raising — and state that choice in the design's "identical in both backends" claim (§2
  Component B), which currently asserts an equivalence the `None`/raise split does not hold.
  Note this is the same silent-`0` convention as the pre-existing `Span` arm
  (`unwrap_or(0)`); the diff propagates it to the new node arms rather than introducing it,
  but the new arms are where the Python side newly *raises*, so the asymmetry is now live.

## Reviewed and clean

- `fltk/unparse/fmt_config.py:508-512` (in-place mutate of `trivia_config`): no error path;
  `None` guard is correct, no swallowing.
- `fltk/unparse/pyrt.py:90-98`: the `span is None` guard is dead-but-harmless (generated nodes
  default `.span` to `UnknownSpan`, never `None`); `text.isspace()` correctly rejects empty
  text; the `is_span`→`extract_span_text` raise on a genuinely invalid span is intentional
  fail-loud and acceptable.
- `fltk/unparse/gsm2unparser_rs.py:1520-1552`: emitted `match` is exhaustive (one arm per
  `TriviaChild` variant, no wildcard) — a future enum variant fails the generated code at
  `rustc` compile time (loud), not silently. `has_span` computation is sound.
- `gsm2unparser.py` / `gsm2unparser_rs.py` `TODO(rule-preserve-blanks)` comments: deferral is
  documented, no error path.
