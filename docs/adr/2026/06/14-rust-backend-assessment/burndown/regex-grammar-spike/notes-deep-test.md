test-1. tests/test_regex_grammar_adversarial.py:271 — wrong pattern: `r"A"` evaluates to the single character `A` (U+0041), not the 6-character string `A`.

Python interprets the raw-string literal `r"A"` as the single Unicode character `A` because `\u` is a Unicode escape in raw strings on CPython — the `r` prefix prevents `\\` interpretation but not `\u`. The resulting test passes `"A"` (1 char, a plain literal) to `classify_pattern`, which accepts it as an ordinary `literal_char`. The intended subject — the 6-char escape sequence `\uHHHH` admitted by `unicode_escape` — is never parsed.

Consequence: the `\uHHHH` 4-hex unicode escape, explicitly required as ACCEPT in design §4.2 ("Divergent escape sequences: `\xHH`/`\uHHHH`/`\UHHHHHHHH` (accept)"), has zero coverage. A grammar regression that broke `unicode_escape` for the `u`-lowercase 4-hex form would not be caught by any test.

Fix: replace the pattern literal with the explicit 6-character string: `"\\u0041"` (non-raw, double-backslash). Also add a second case with a different 4-hex value (e.g. `"\\u00E9"`) to confirm the rule fires on digit+letter hex sequences, not just all-digit ones.

---

test-2. tests/test_regex_grammar_corpus.py:163-178 — CLI smoke test exercises only `regex.fltkg`; the `_run_cli` error paths (wrong arg count → exit 2, nonexistent file → exit 2) are untested.

`_run_cli` has three distinct exit codes: 0 (all accepted), 1 (some rejected), 2 (bad invocation or unreadable file). The only test calls it with a valid path and asserts exit 0. The two exit-2 branches — `len(argv) != 1` and `not grammar_path.exists()` — are never exercised.

Consequence: a regression that silently swallowed argument-count errors (returning 0 instead of 2) or file-not-found errors would not be caught. Because `_run_cli` is the ad-hoc developer tool for clockwork verification, silent failure modes are high-stakes.

Fix: add two small tests — `_run_cli([])` asserts exit code 2; `_run_cli(["nonexistent_grammar.fltkg"])` asserts exit code 2.

---

test-3. tests/test_regex_grammar_adversarial.py — no test covers the `_run_cli` exit-1 (some-rejected) path end-to-end.

The CLI's exit-1 branch (`any_rejected = True` → `return 1`) is reachable only when `classify_pattern` returns False for at least one collected pattern. Neither the corpus test nor the adversarial test constructs an artificial grammar file containing a non-portable regex and passes it to `_run_cli` to confirm the nonzero exit.

Consequence: a regression where `_run_cli` printed REJECT output but returned 0 (e.g. an off-by-one in the `any_rejected` flag) would not be detected. The developer relying on the CLI as a nonzero-exit signal for clockwork validation would get a false all-clear.

Fix: add a test that creates a temporary `.fltkg` file containing one rejected pattern (e.g. `/(?=x)/`), calls `_run_cli` with its path, and asserts exit code 1.

---

test-4. tests/test_regex_grammar_corpus.py:88-160 — the six named risk-point pin tests (`test_fegen_block_comment_content`, etc.) duplicate coverage already provided by the parametric `test_corpus_pattern_is_accepted` sweep.

The parametric sweep at lines 63-76 already runs `classify_pattern` on every pattern collected from `fegen.fltkg`, which includes all six patterns the pins test individually. The pins add explaining comments and named failure messages — which has real maintenance value — but they assert the same boolean (`classify_pattern(pattern)`) with the same oracle on the same pattern string. If a grammar regression breaks one pattern, both the parametric case and the named pin will fail; neither provides coverage the other lacks.

Consequence: not a regression risk — no real behavior is left unchecked. The redundancy is benign but creates noise: a grammar change that makes the block-comment content pattern fail will produce two failing tests with slightly different messages, obscuring which is the authoritative one.

This is a quality observation, not a blocking gap. The named pins' documentation value likely outweighs the noise. No required fix; worth noting for the maintainer who adds new risk points.

---

Commit reviewed: 8828282
