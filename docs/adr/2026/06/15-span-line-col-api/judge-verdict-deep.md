# Judge verdict — deep review

Phase: deep. Base `8cd6232`..HEAD `3a61b07` (fixes over reviewed commit `b6c0aac`). Branch `span-line-col-api`. Round 1.
Notes: 7 reviewer files; 23 dispositioned findings (efficiency-1, errhandling-1/2/3, correctness-1, security-1/2, test-1..8, reuse-1/2, quality-1/2).

---

## Added TODOs walk

Two TODO dispositions (reuse-1/quality-2 share `py-span-linecol-cache`; reuse-2 → `linecol-cache-consolidate`). Both pairings verified: `TODO.md` entries (lines 62-69) + matching `TODO(slug)` comments in code (`terminalsrc.py:133`, `terminalsrc.rs:167,178`, `span.rs:56`).

### reuse-2 — TODO(linecol-cache-consolidate) at `terminalsrc.rs:178`, `span.rs:56`
Q1 (worth doing): yes — after the move-down, `TerminalSource.line_ends` and `SourceInner.line_ends` are two independent `OnceLock<Vec<i64>>` over the same immutable text; consolidation removes a redundant O(N) scan and a `Vec<i64>` allocation per parsed source.
Q2 (design/owner input required): yes (marginally). The reuse reviewer frames the fix as a "one-line change," but it is not purely mechanical: `SourceInner.line_ends` is `pub(crate)` in `fltk-cst-core` (`span.rs:58`), so `fltk-parser-core` cannot reach it without a visibility change; the change also deletes a field from `TerminalSource` (touching the parse path) and is an explicit design-scoped follow-up (design §2.6.3, §7). A cross-crate visibility decision + hot-path field removal is a deliberate change, not an in-scope one-liner.
Furthermore: pre-existing/move-surfaced duplication, correctness preserved (both caches derive deterministically from immutable text) — not a defect this iteration created.
Assessment: TODO acceptable.

### reuse-1 / quality-2 — TODO(py-span-linecol-cache) at `terminalsrc.py:133`
Q1 (worth doing): yes — Python `Span.line_col()` recomputes the O(N) line-ends scan every call, and the bisect body is copy-pasted between `Span.line_col` (`terminalsrc.py:133-158`) and `TerminalSource.pos_to_line_col` (`terminalsrc.py:273-295`).
Q2 (design/owner input required): split. The **cache** portion is genuinely design-gated — the frozen+slots Python `Span` carries only a raw `str` and cannot reach a mutable cache without `with_source`-plumbing a `_line_ends` through `SourceText` (non-trivial). The **algorithm-dedup** portion (extract `_bisect_line_col(src, pos, line_ends)`) the quality/reuse reviewers explicitly note is "fixable now without the cache plumbing" — i.e. do-now. The disposition folds the do-now extraction into the design-gated cache TODO.
Weighing: this is pre-existing duplication (both copies predate this PR; both were updated correctly and identically in lockstep here — not worsened this iteration), the reviewers rate it "maintenance risk rather than a present defect," and the dominant motivation (amortizing the scan) genuinely requires the cache design. Folding a small quality extraction under a legitimately design-gated TODO is mild responder stretch but does not defer a present defect or a problem this PR created.
Assessment: TODO acceptable (borderline; no present defect, cache half is correctly design-gated).

Two TODOs total, both concrete and paired, both pre-existing acknowledged duplications with correctness preserved — not a "scope was wrong → escalate the pile" signal.

---

## Other findings walk

### efficiency-1 — Fixed  [focus item: verify O(N)-per-call scan eliminated, not just re-documented]
Claim: Rust warm `line_col()` was O(N) (three `chars().count()` scans around the O(log N_lines) bisect), voiding the design's O(log N_lines) amortization for any consumer resolving many spans over one large source.
Diff inspection (`span.rs`):
- `resolve_line_col` (`span.rs`): `let len = text.chars().count()` is now **inside** the `get_or_init` closure — skipped entirely on warm calls. (Confirmed in the diff: the `len` binding sits within the `line_ends.get_or_init(|| { ... })` body.)
- `SourceInner` gains `char_count: OnceLock<i64>`. `line_col_inner` reads `len` via `source.char_count.get_or_init(...)` — O(1) warm.
- `line_col_or_raise` reads its domain-check `len` via the same `char_count.get_or_init(...)` — O(1) warm — then delegates to `line_col_inner` (O(1) warm) → `resolve_line_col` (O(log) warm).
Result: every per-call `chars().count()` is gated behind a `OnceLock`; warm path is O(log N_lines). The scan was **eliminated**, not merely re-documented. ABI probe unaffected (`SourceText` still holds one `Arc<SourceInner>`; design §2.6.3 layout note). Accept.

### test-1 — Fixed  [focus item: verify added tests genuinely catch the last-line off-by-one class]
Claim: cross-backend equivalence tests only used `\n`-terminated sources, so a sentinel regression (`len`→`len-1`) on the unterminated final line would pass both backends identically.
Diff at `test_span_protocol.py` `test_no_trailing_newline_sentinel`: source `"hello\nworld"` (no trailing `\n`), queries pos 6 on the last line, asserts `py_lc.line_span.end == 11` **and** `rs_lc.line_span.end == 11` (pinned absolute value, not just `==`), plus `line_span.text() == "world"` on both. A regression to `sentinel=len-1` yields `end==10` / text `"worl"` and fails the absolute assertion. This genuinely catches the bug class in both directions (asymmetric and symmetric). Backed by Rust unit `resolve_last_char` (`lib.rs`: `text="hello\nworld"`, pos 10 → `line_span.end==11`). Accept.

### security-1 — Fixed  [focus item: verify escaping actually restored in format_source_line]
Claim: `format_source_line` rendered attacker-controlled `lc.line_span.text()` unescaped, regressing the Rust `format_error_message` control-char hardening (terminal-injection / log-spoofing).
Diff at `error_formatter.py`: new `_escape_for_display()` replaces C0/C1 controls (`cat == "Cc"`), DEL (`0x7F`), and bidi/invisible Cf codepoints (U+202A-202E, U+2066-2069, U+200B/C/D, U+FEFF) with `U+XXXX`. Applied to `line_text = _escape_for_display(lc.line_span.text() or "")` before interpolation. Caret indent recomputed from the **escaped** prefix (`escaped_prefix = _escape_for_display(raw_line[:col])`, `caret_indent = " " * len(escaped_prefix)`) so alignment survives escaping. Tests (`TestControlCharEscaping`) assert raw `\x1b` absent / `U+001B` present, CR→`U+000D`, RLO→`U+202E`, clean source passes through, and caret realignment. Escaping is genuinely restored at the sink. Accept.

### security-2 — Fixed  [focus item, filename arm]
Claim: `filename` interpolated raw into the `In <file>:L:C:` header (newline/control injection breaking the single-line header contract).
Diff: `raw_filename` (explicit arg or `span.filename()`) is routed through `_escape_for_display` before the `In {resolved_filename}:...` interpolation. Test `test_newline_in_filename_is_escaped` (`filename="file\nrm -rf ~"`) asserts the raw `\n` is gone and `U+000A` appears in the header line, keeping it single-line. Accept.

### errhandling-1 / quality-1 — Fixed (same fix)
Claim: `resolve_line_col` docstring stated a false `pos >= 0` precondition that both callers violate (`pos = -1` for empty-source EOF clamp and the `ErrorTracker.longest_parse_len` sentinel); a maintainer trusting it could add a `pos < 0 → None` guard and silently break the empty-source / parse-error path.
Diff: docstring now states `pos >= -1`, documents that `pos = -1` yields `LineColPos(line=0, col=-1)` for the two named callers, and that `pos < -1` is unsupported. Matches actual behavior; `resolve_empty_input` unit test (`lib.rs`) pins `resolve_line_col("", -1) → col=-1`. Maintainability-trap consequence addressed. Accept.

### errhandling-2 — Fixed
Claim: bare `.unwrap()` at the guarded-invariant site in `line_col_or_raise` (vs the `.expect(...)` pattern in `text_or_raise`) — diagnostic regression if a future refactor reorders guards.
Diff: `.expect("invariant: source is Some — is_none() guard above returned Err already")` now present at that site. Matches `text_or_raise`. Accept.

### errhandling-3 — Fixed
Claim: fallthrough `"could not resolve line/col"` names only the symptom; on-call gets no context if the (currently unreachable) arm fires.
Diff: replaced with `"line_col_inner returned None despite passing all guards — internal invariant violation; start={}, source_len={}"`, carrying both `start` and the computed `len`. Names the invariant and provides reconstruction data. Accept. (Note: the Python `line_col_or_raise` keeps the terser `"could not resolve line/col"` fallthrough, but errhandling-3 was scoped to the Rust path and that path is provably unreachable; not a defect.)

### correctness-1 / test-4 — Fixed (same fix)
Claim: `TestDriftAnchor` docstring asserted a phantom final-line sentinel divergence (`Span.line_col` len vs legacy `len-1`) that no longer exists — acting on it would reintroduce the off-by-one.
Diff: docstring now states both paths use `sentinel=len` and the only deliberate divergence is the negative-start guard (cross-referenced to `test_line_col_negative_diverges_from_pos_to_line_col`). Verified the Python legacy `pos_to_line_col` was in fact updated to `terminals_len if terminals_len > 0 else -1` (diff at `terminalsrc.py:271-283`), so the corrected docstring matches code. The sibling `test_line_col_parity_with_terminalsrc_pos_to_line_col` (asserts `line_span.end` equality) corroborates. Accept.

### test-2 — Fixed
Claim: empty source `""` untested at the Python/pyo3 `line_col()` level (documented `col=-1` corner).
Diff: `test_span.py::test_line_col_empty_source` asserts `lc.col == -1`; `test_span_protocol.py::test_empty_source_cross_backend` asserts `col == -1` on both backends. Accept.

### test-3 — Fixed
Claim: no cross-backend zero-width `Span(p,p)` `line_col()` case.
Diff: `test_zero_width_span_cross_backend` (pos 3,3 → line 0 col 3, not None) added; equivalence asserted. Accept.

### test-5 — Fixed
Claim: cross-backend formatter equivalence only used a `\n`-terminated source; a one-backend last-line truncation would slip through.
Diff: `test_error_formatter.py::TestCrossBackend.test_same_output_no_trailing_newline` (`"hello\nworld"`, last line) asserts `py_result == rs_result` and `"world" in` result. Accept.

### test-6 — Won't-Do
Claim: no single-backend absolute-literal formatter assertion for a Rust span (only the relative `py_result == rs_result`).
Rationale: the finding's own text states "weak concern … No critical gap; noted for completeness"; the Rust absolute value is established transitively (Python `test_full_string_literal` absolute + `test_same_output_both_backends` equivalence).
Inspection: confirmed both tests exist; together they pin the Rust output absolutely. The finding states no consequence beyond completeness.
Assessment: nit with no real consequence; responder wins by default (reviewer stated no critical gap). Accept Won't-Do.

### test-7 — Fixed
Claim: Rust `line_col_or_raise` error tests asserted `ValueError` type without pinning the message family (design §2.2).
Diff: `test_rust_span.py` now has `match="has no source"`, `match="negative"`, `match="out of bounds"` on the three tests (lines ~155-168). Matches the Python equivalents (`test_span.py`). Accept.

### test-8 — Fixed
Claim: the Python parser-filename test was gated on `skipif(not _rust_available)` (wrong condition); the Rust variant silently `pytest.skip`ped on a missing `.parser` attribute, letting a broken install masquerade as tested.
Diff: `test_parser_produced_span_filename_python` no longer carries the `skipif` (runs whenever fltk Python is importable); `test_parser_produced_span_filename_rust` keeps the outer `importorskip` for `fegen_rust_cst` but uses direct `fegen_rust_cst.parser` access — an importable-but-broken install now `AttributeError`-fails rather than skipping. Accept.

---

## Disputed items

None. All 21 Fixed dispositions verify against the diff; both Won't-Do/TODO dispositions meet the bar (test-6 is a no-consequence nit the reviewer conceded; both TODOs are design-gated, concrete, paired, and defer no present defect).

---

## Approved

23 findings: 19 Fixed verified (efficiency-1, errhandling-1/2/3, correctness-1, security-1/2, test-1/2/3/4/5/7/8, quality-1; correctness-1=test-4 and errhandling-1=quality-1 share fixes), 1 Won't-Do sound (test-6), 2 TODOs acceptable (py-span-linecol-cache covering reuse-1/quality-2; linecol-cache-consolidate covering reuse-2).

---

## Verdict: APPROVED

All dispositions acceptable. The four focus items all verify against the diff: efficiency-1's O(N) warm scan is genuinely eliminated via the `char_count` `OnceLock` plus moving `len` inside `get_or_init` (not merely re-documented); test-1's `test_no_trailing_newline_sentinel` pins `line_span.end==11` absolutely and catches the last-line off-by-one in both directions; security-1/2 restore control/bidi escaping at both formatter sinks (source line and filename) with caret realignment and direct anti-injection tests. The two deferred TODOs are concrete, correctly paired, design-gated, and defer no defect this iteration created.
