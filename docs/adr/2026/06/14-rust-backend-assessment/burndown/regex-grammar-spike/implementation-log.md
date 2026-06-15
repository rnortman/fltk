## Increment 4b — Corrective Opus pass on adversarial suite (commit f8156ea)

Opus corrective pass over Inc-4's `tests/test_regex_grammar_adversarial.py` (the adversarial
increment had run on the default model). Grammar (`regex.fltkg`) deliberately NOT changed —
all findings are downstream regex-portability-lint go/no-go inputs.

- **`src/lib.rs` resolved: stray edit, REVERTED.** The uncommitted change was a comment-only
  edit (`fltk._native.UnknownSpan` -> `_native.UnknownSpan`, src/lib.rs:8). Confirmed stray,
  not spike work: (a) none of the four spike commits (0fea4f1/607400d/87a3fbc/8cde0c0) touch
  `src/lib.rs` — Inc 1 touched only `regex.fltkg`, the four `regex_*` artifacts, and the
  Makefile; (b) the edit degrades a correct comment — the module is imported everywhere as
  `fltk._native` (`fltk/fegen/bootstrap_cst.py`, `gsm2lib_rs.py:139`, and ~20 sites in
  `crates/fltk-cst-core/`), so the committed `fltk._native.UnknownSpan` is the consistent
  form. Reverted with `git checkout -- src/lib.rs`; tree clean.

- **Adversarial suite extended 116 -> 151 cases** (`tests/test_regex_grammar_adversarial.py`),
  all passing; `make check` green. Made the module docstring a raw string (line 2) to clear a
  `DeprecationWarning: invalid escape sequence '\z'` that `make check` would have flagged.

- **TWO NEW over-admission findings added** (grammar accepts; BOTH engines reject — the
  dangerous direction; pinned ACCEPT with `skip_re_check=True` + FINDING rationale):
  - **F4 — inverted bound `a{2,1}`** (min>max). `bounded` (regex.fltkg:93-95) is purely
    syntactic; Python re errors `min repeat greater than max`, Rust errors on out-of-order
    bound. Empirically verified.
  - **F5 — reversed class range `[z-a]`** (lo>hi). `class_range` (regex.fltkg:201) is purely
    syntactic; Python re errors `bad character range`, Rust errors. The class-range analogue
    of F4. Both gaps are intrinsic to a context-free recognizer (min<=max / lo<=hi are
    semantic predicates) and must be caught downstream — a material go/no-go input.

- **F1 (`\07`) generalized** to the whole `\0N` family: added `\00`, `\012` (octal-look,
  ACCEPTED as `\0`+literals; Python octal, Rust rejects) and the benign contrast `\0a`
  (`\0`+non-digit, genuinely portable). Also pinned the correct rejections `\7`, `\8`
  (bare-digit escapes) bounding the gap.

- **F2 (`(?U)`) generalized**: added `(?iU)` and `(?U:a)` showing the `U` over-admission
  reaches the combined-flag and scoped-flag-group forms, not just bare `(?U)`. F3 (`\z`)
  unchanged from Inc 4 (already pinned).

- **Coverage gaps filled with correct-disposition cases** (sharpened §4.2): dangling
  quantifiers `*`/`+`/`?`/`{2}` (reject, "nothing to repeat"); invalid/non-portable escapes
  `\q`/`\e`/`\c`/lone-`\` (reject; `\e` is a Rust-vs-Python divergence, others both-reject);
  full top-level `meta_escape` family `\.`/`\*`/`\(`/`\{`/`\}`/`\-`/`\/`/`\\` (accept);
  empty/degenerate classes `[]`/`[^]`/`[]a]`/`[[]` (reject, with the bracket-first and
  literal-`[` Python-vs-Rust divergences documented); shorthand-as-range-endpoint
  `[\d-z]`/`[a-\d]` (reject); open-min/empty/unterminated bounds `a{,3}`/`a{}`/`a{2`
  (reject, fail-closed on non-portable brace forms).

- **Findings index added to the module docstring** (F1–F5) so the suite header is a complete
  scope-boundary catalogue for the downstream lint.

- Observed (not a portability gap, noted for awareness): the generated Python recursive-descent
  parser overflows the interpreter stack (`RecursionError`) on very deeply nested input (~50
  nested groups at the default recursionlimit 1000); depth 20 is safe. This is a parser-impl
  limit, not a grammar semantic gap; the existing 5-deep nesting cases are well within bounds,
  so no extreme-depth ACCEPT case was added (it would crash CI).

**Full list of scope-boundary gaps the suite now documents (over-admissions; the grammar
admits something at least one engine rejects):** F1 `\0N` octal family (`\07`/`\00`/`\012`);
F2 `U` flag (`(?U)`/`(?iU)`/`(?U:a)`); F3 `\z` top-level anchor (grammar comment "verified on
both engines" wrong for Python>=3.6); F4 inverted bound `a{2,1}`; F5 reversed class range
`[z-a]`. No over-rejections of a portable construct were found — every other divergent shape
probed fails closed correctly.

## Increment 4 — Adversarial test suite (commit 8cde0c0)

- `tests/test_regex_grammar_adversarial.py` (new, 116 cases): table-driven `(pattern, expected, rationale[, skip_re_check])` covering all §4.2 categories:
  - Over-admission probes: POSIX look-alikes, set-op look-alikes, Unicode properties, lookaround/backrefs/named-groups, divergent escapes, bare-brace divergence, flag divergence, in-class escape divergence.
  - Over-rejection/boundary probes: empty/nilable shapes, PEG shadowing, deep nesting, whitespace-significance, pathological dashes/carets, quantifier-on-quantifier + lazy markers.
  - UTF-8/non-ASCII probes (required, §4.3): multi-byte literals, multi-byte at non-zero offsets, non-ASCII in classes, Unicode shorthands with cross-engine divergence rationale, NFC vs NFD combining marks, astral-plane codepoints, RTL bidi text.
  - Anchors, dot metacharacter.
- ACCEPT-direction cases cross-checked against Python `re.compile`; REJECT cases carry mandatory Rust-aware rationale strings. `skip_re_check=True` used for documented grammar over-admissions.
- Findings surfaced (§4.4):
  - **`\07` ACCEPTED as grammar gap**: grammar parses `\0` (control_escape null) + `7` (literal) rather than rejecting it as an octal sequence. Python re treats `\07` as octal chr(7); Rust rejects octal sequences. The grammar cannot distinguish without removing `\0` from `control_escape`. Documented in rationale; not fixed (would require design decision about control_escape `0`).
  - **`(?U)` ACCEPTED but Python re rejects it**: `flag_chars /[imsU]+/` admits `U` (Rust's greedy/lazy swap flag) but Python re raises `unknown extension ?U`. Over-admission relative to Python; design explicitly lists U as admitted. Documented in rationale; not changed (design decision).
  - **`\z` ACCEPTED but Python re rejects it**: `anchor_escape /[Az]/` admits `\z` (Rust end-of-text anchor) but Python re raises `bad escape \z`. Grammar comment says "verified on both engines" which appears incorrect for Python >= 3.6. Documented in rationale; not fixed (downstream lint increment's call).
- All 116 tests pass; `make check` passes.

## Increment 3 — General CLI entry point + documented ad-hoc clockwork run (commit 87a3fbc)

- `fltk/fegen/regex_corpus.py`: the `__main__` guard wiring `_run_cli` as the `python -m fltk.fegen.regex_corpus <path>` grammar-agnostic CLI was already present from Inc 2 (no change needed).
- `tests/test_regex_grammar_corpus.py:163-176`: added `test_cli_entry_point_accepts_in_tree_grammar`, calling `_run_cli([str(_REGEX_FLTKG)])` directly and asserting exit code 0. Docstring documents the developer ad-hoc usage for out-of-tree grammars (no clockwork path committed). 26 tests pass; `make check` passes.
- Deviation: the `__main__` guard was pre-shipped in Inc 2; Inc 3 was reduced to the unit test that pins it. The design's "document the ad-hoc clockwork command" is already in §3.4 (the design is committed); no additional documentation file was needed.

## Increment 2 — General extract + classify logic + corpus test (commit 607400d)

- `fltk/fegen/regex_corpus.py` (new): `collect_regexes(grammar: gsm.Grammar) -> list[str]` walks every rule/alternative via `gsm._for_each_item`, collecting distinct `gsm.Regex.value` strings in encounter order; `classify_pattern(pattern: str) -> bool` drives `regex_parser.Parser` directly and checks `result.pos == len(terminals.terminals)`; `_run_cli` wires the CLI entry point (grammar-agnostic; `python -m fltk.fegen.regex_corpus <path>`); `parse_grammar_file` imported at module top (no lazy import needed). Print calls use `# noqa: T201`.
- `tests/test_regex_grammar_corpus.py` (new): 18 parametric cases (6 from fegen.fltkg, 12 from regex.fltkg) — all ACCEPT; 7 named risk-point pin tests for §3.3 in-tree patterns (block-comment content/end, line-comment content, identifier, raw-string body, literal value, self-referential count assertion). All 25 tests pass; `make check` passes.

## Increment 1 — Copy grammar + wire codegen + commit generated artifacts (commit 0fea4f1)

- `fltk/fegen/regex.fltkg`: copied verbatim from `burndown/regex-portability-lint/regex.fltkg`; identical content confirmed with `diff`.
- `Makefile:265-268`: `generate` line for the regex grammar (after the `unparsefmt` block) was already present in the working tree; staged and committed.
- `fltk/fegen/regex_cst.py`, `regex_cst_protocol.py`, `regex_parser.py`, `regex_trivia_parser.py`: generated via `make gencode` + `make fix`; `git diff --stat` after regen showed zero drift.
- `make check` passes; `import fltk.fegen.regex_parser` succeeds.
