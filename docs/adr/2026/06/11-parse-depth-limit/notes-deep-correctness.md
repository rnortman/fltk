# Correctness review — parse depth limit (ef315be..d442f56)

Style: concise, precise, complete, unambiguous. No padding.

No findings.

Verified: guard increment/decrement pairing (no underflow; panic-skip documented and unobservable); sticky check precedes cache lookup and all `apply_inner` panic sites (flag-set state cannot newly trigger memo-invariant panics); `>=` boundary permits exactly `max_depth` concurrent applies (T1/T4 traces re-derived by hand and match); depth-rejection writes no cache entry at the rejected (rule,pos); boundary-case missed left-recursion detection (poison never re-entered at the limit) yields wrong-but-flagged results, covered by the sticky contract; binding flag-check precedes result inspection in every per-rule method of both regenerated parsers (uniform template, spot-verified incl. `nest`/`nest_sum`/`_trivia`); rule-ID renumbering (`_trivia` 18→20) consistent with `RULE_NAMES`; `cargo test` in `fltk-parser-core` passes (12/12).
