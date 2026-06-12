# Design: error-msg-bidi-escape — extend escape set to bidi/invisible chars; consolidate the divergent third copy

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md` (this dir). Exploration: `exploration.md` (this dir). Extends ADR `docs/adr/2026/06/11-error-msg-escape/design.md` (does not rewrite it); specifically supersedes its claim at l.33 that "two digits always suffice."

## Context / root cause

Two problems, verified at HEAD 5d94733 (exploration Claims 1–7):

1. **Escape set stops at U+009F.** Canonical `escape_control_chars` (Rust `crates/fltk-parser-core/src/errors.rs:94-113`, Python `fltk/fegen/pyrt/errors.py:59-79`) escapes C0-minus-TAB, DEL, C1 as `\xHH`. Bidi controls (U+202A–U+202E, U+2066–U+2069), LS/PS (U+2028/U+2029), and zero-width chars pass through into the quoted failing line. Attacker-controlled parse input can visually reorder the rendered error line (bidi) or split log lines (LS/PS). Both backends split source lines on `\n` only (`terminalsrc.py:190`, `terminalsrc.rs:198`), so these chars reach `escape_control_chars` inline.

2. **A third, private, divergent Rust copy.** `escape_control_chars_for_msg` (`crates/fltk-cst-core/src/cross_cdylib.rs:123-138`) escapes type/attribute names in CST-bridge `TypeError` messages. It diverges from canonical: escapes TAB (no `cp != 0x09` exclusion), encodes C1 per UTF-8 byte (`\xc2\x80` for U+0080 instead of `\x80`), carries a comment (l.128-129) falsely claiming single-`\xHH`-per-codepoint output, and has zero test coverage.

The cross-backend byte-identical pin is by duplicated literal strings: Rust unit tests (`errors.rs:338-362`), Python tests (`tests/test_pyrt_errors.py`), and the parity comparator's byte-equal header check (`tests/parser_parity.py:107`).

## Proposed approach

### Escape specification (the normative spec; doc comments in code restate it)

`escape_control_chars(text) -> str`: per-character mapping. Identical output, byte for byte, in both backends.

**Escape set** (codepoint predicate, exhaustive):

| Range | Class | Representation |
|---|---|---|
| U+0000–U+001F except U+0009 (TAB) | C0 controls | `\xHH` (unchanged) |
| U+007F | DEL | `\xHH` (unchanged) |
| U+0080–U+009F | C1 controls | `\xHH` (unchanged) |
| U+061C | ALM (Bidi_Control) | `\uXXXX` (new) |
| U+200B–U+200F | ZWSP, ZWNJ, ZWJ, LRM, RLM | `\uXXXX` (new) |
| U+2028–U+202E | LS, PS, LRE, RLE, PDF, LRO, RLO | `\uXXXX` (new) |
| U+2060 | Word Joiner | `\uXXXX` (new) |
| U+2066–U+2069 | LRI, RLI, FSI, PDI | `\uXXXX` (new) |
| U+FEFF | ZWNBSP/BOM | `\uXXXX` (new) |

Everything else (incl. TAB and all other printable/non-printable Unicode) passes through unchanged.

**Set rationale.** The new entries are exactly: the complete Unicode `Bidi_Control` property (12 codepoints: U+061C, U+200E, U+200F, U+202A–U+202E, U+2066–U+2069) ∪ line/paragraph separators {U+2028, U+2029} ∪ the five standard zero-width characters {U+200B, U+200C, U+200D, U+2060, U+FEFF}. The request names U+202A–U+202E/U+2066–U+2069 explicitly and suggests U+200B–U+200F + U+FEFF as the zero-width example; this design adds U+061C and U+2060 so each category is a *complete named set* (the full Bidi_Control property; all five conventional zero-width chars) rather than an ad-hoc subset — U+061C is an invisible bidi control with the same reordering capability as LRM/RLM, and U+2060 is ZWNBSP's successor with identical invisibility. Pinning to named closed sets makes the spec auditable and non-arbitrary.

**Deliberate exclusions** (per request non-goal "no new escaping for other Unicode ranges"): U+00AD (soft hyphen), U+2061–U+2064 (invisible math operators), U+202F/U+205F (narrow/math spaces — render visibly), U+180E (Mongolian vowel separator), variation selectors, and all other default-ignorable/confusable codepoints. These drift into the open-ended confusables space the request excludes; none is a bidi-reordering or line-splitting primitive.

**Representation:**
- cp ≤ U+009F → `\xHH`, lowercase, exactly 2 hex digits — byte-for-byte unchanged from today, so existing pinned literals and downstream-visible text for the current set do not churn (request constraint).
- cp > U+00FF in the escape set → `\uXXXX`, lowercase, exactly 4 hex digits (e.g. U+202E → `\u202e`, U+061C → `\u061c`).
- No set member lies in U+00A0–U+00FF or above U+FFFF, so the two spellings cover the set exactly. Spelling follows the Python string-literal/`repr` convention, consistent with the existing lowercase `\xHH` and the py_repr-formatted `Expected:` block; a future astral-plane addition would use `\UXXXXXXXX` (noted here as spec direction, not implemented).
- Backslash itself remains unescaped: output is not round-trippable (input text literally containing `\u202e` renders identically to an escaped U+202E). Preexisting property of the `\xHH` scheme; unchanged and acceptable — the message is a human-readable quote, not a serialization.

**Caret pad:** mechanism unchanged — pad = codepoint length of the escaped prefix (`errors.py:92-94`, `errors.rs:167-169`). A `\uXXXX` escape contributes 6 pad columns (vs 4 for `\xHH`); no code change needed beyond the escape function, but tests pin it.

### Part (a): consolidate the Rust copies

**Decision: deduplicate.** Move the canonical implementation into `fltk-cst-core`; delete `escape_control_chars_for_msg`.

- New module `crates/fltk-cst-core/src/escape.rs`, NOT gated on the `python` feature (pure `&str -> String`, no pyo3): `pub fn escape_control_chars(s: &str) -> String` — the canonical implementation (extended predicate per the spec above, fast-path scan preserved from `errors.rs:99-102`). `pub mod escape;` in `fltk-cst-core/src/lib.rs`.
- `fltk-parser-core` already depends on `fltk-cst-core` with `default-features = false` (`crates/fltk-parser-core/Cargo.toml`), so this respects the existing dependency direction and adds no new edge. `errors.rs` replaces its local definition with `pub use fltk_cst_core::escape::escape_control_chars;` — the public paths `fltk_parser_core::escape_control_chars` (via the existing `lib.rs` re-export) and `fltk_parser_core::errors::escape_control_chars` are preserved, so generated code and downstream Rust consumers see no path change.
- `cross_cdylib.rs`: delete `escape_control_chars_for_msg` (the wrong comment dies with it); all six call sites — `py_any_type_name` (l.148), `py_type_obj_name` (l.162), and the four `check_abi_pair` error branches escaping `e.to_string()` (l.198, 208, 231, 241) — call `crate::escape::escape_control_chars` instead.

Rejected alternative — keep a pinned-by-tests copy: the third copy already drifted (wrong comment, two behavioral divergences, zero tests). Cross-*language* duplication (Python/Rust) is forced; intra-Rust duplication is not, and the existing dependency edge makes dedup free.

**Behavioral change in CST-bridge error messages (deliberate, called out):** TAB in type/attribute names now passes through (was escaped); C1 codepoints render as one `\xHH` (was per-UTF-8-byte, e.g. `\x85` instead of `\xc2\x85`); the new bidi/zero-width set is escaped. These strings appear only in `TypeError` text on ABI-mismatch/wrong-type paths; no test pins the old divergent forms (zero coverage today), and aligning to canonical is the request's part (a).

### Part (b): extend both backends

- **`fltk/fegen/pyrt/errors.py`:** extract the escape predicate into a single module-level helper (today the condition is duplicated between the fast-path `any(...)` scan at l.70 and the loop at l.75 — a drift hazard the extension would double); extend per the spec; add the `\uXXXX` branch; update the docstring (escape table + both representations + cross-pin note); remove the `TODO(error-msg-bidi-escape)` comment.
- **`crates/fltk-cst-core/src/escape.rs`:** the moved implementation carries the extension; doc comment states the spec and the cross-pin to the Python implementation and to `tests/test_pyrt_errors.py`.
- **`crates/fltk-parser-core/src/errors.rs`:** re-export as above; update the doc comment to point at `fltk_cst_core::escape` as the implementation home; remove the `TODO(error-msg-bidi-escape)` comment.
- Signature unchanged in both backends (`&str -> String` / `str -> str`).

### Other file changes

- **`TODO.md`:** remove the `error-msg-bidi-escape` entry (l.19-21 region).
- **`tests/parser_parity.py`:** no code change. After (b), formatted messages contain no raw LS/PS, so the `str.splitlines()` hazard (request §constraints; exploration Claim 5) dissolves; a parity corpus entry pins it (test plan #4).
- **Tests:** see test plan. Rust escape unit tests move with the implementation to `escape.rs`; `errors.rs` keeps its `format_error_message`-level tests (which exercise the re-export).
- **Cross-pin doc headers:** `tests/test_pyrt_errors.py` header updated to name `crates/fltk-cst-core/src/escape.rs` as the Rust pin location.

### Observable output change (stated plainly)

Downstream-visible: parse-error messages whose failing line contains a newly-escaped codepoint now render it as `\uXXXX` and the caret shifts accordingly; CST-bridge `TypeError` text changes as called out in part (a). Messages free of the affected codepoints are byte-for-byte unchanged. This is the deliberate, user-approved change; nothing else about message format moves.

## Edge cases / failure modes

- **TAB:** stays literal in the canonical quoting path (preexisting, deliberate); newly literal in CST-bridge messages (alignment, called out above).
- **Caret pad with `\uXXXX`:** 6 columns per escape; computed automatically from the escaped prefix; pinned by an alignment test.
- **Caret at a newly-escaped char:** caret lands on the `\` of `\uXXXX` — same semantics as the existing `\xHH` case (`errors.rs` test `format_error_message_caret_at_control_char`).
- **LS/PS in the parity comparator:** before this change a raw LS in a message would be split by `splitlines()` (identically on both sides, so the assert passes but the line structure is distorted); after, no raw LS/PS exists in any message. Corpus entry covers it.
- **Whitespace separators consuming LS/PS:** U+2028/U+2029 are `White_Space=Yes`, so `\s` matches them in both Python `re` and `regex-automata` (Unicode mode) — they can be *consumed* before the failure point, putting `\uXXXX` escapes before the caret (the pad-from-escaped-prefix rule handles this; corpus entry exercises it). Zero-width chars (U+200B etc.) are not `White_Space` and are not consumed by `\s` — they cause failures instead; also fine.
- **Fast path:** the control-free fast path must use the same extended predicate as the escape loop in both backends (shared predicate in Rust today; Python gets one via the refactor above).
- **Rust capacity heuristic:** `String::with_capacity(s.len())` undershoots more when 3-byte chars become 6-char escapes; growth amortizes, correctness unaffected. No change.
- **`Expected:` block / `py_repr_str`:** untouched. Tokens are grammar-author-controlled, not the untrusted-input vector; preexisting documented divergence stands (prior ADR §Edge cases).
- **Feature gating:** `escape.rs` must compile without the `python` feature — `fltk-parser-core` consumes `fltk-cst-core` with `default-features = false`. Pure-string code; no pyo3 imports permitted in the module.
- **Round-trip ambiguity:** documented under Representation; preexisting, unchanged.
- **Lone surrogates / invalid UTF-8:** unchanged from prior ADR — Rust `&str` is valid UTF-8 by construction; out of scope.

## Test plan

TDD: every new assertion below is written first and fails against HEAD. After the change, the following exist and pass:

1. **Rust unit tests, `crates/fltk-cst-core/src/escape.rs` `#[cfg(test)]`** (existing `errors.rs` escape tests move here verbatim — their unchanged literals prove `\xHH` output is preserved — plus new rows):
   - New escaped rows, one per class: bidi embedding/override (`\u{202a}` → `\\u202a`, `\u{202e}` → `\\u202e`), bidi isolates (`\u{2066}`, `\u{2069}`), implicit marks (`\u{200e}`, `\u{200f}`, `\u{061c}`), LS/PS (`\u{2028}`, `\u{2029}`), zero-width (`\u{200b}`, `\u{200c}`, `\u{200d}`, `\u{2060}`, `\u{feff}`).
   - Boundary passthroughs: U+200A (hair space), U+2010, U+2027, U+202F, U+205F, U+2065, U+FFFD, an astral char (e.g. U+1F600), and TAB.
   - Mixed string combining `\xHH` and `\uXXXX` escapes.
2. **Python unit tests, `tests/test_pyrt_errors.py`:** mirror every Rust case with identical literals (the duplicated literals are the cross-language byte-identity pin, per existing convention). Header comment updated to the new Rust location.
3. **`format_error_message` tests (both backends, same expected strings):**
   - Golden: failing line containing a bidi override; assert exact escaped line + caret.
   - Caret alignment: newly-escaped char *before* the error column → 6 pad columns per escape; assert exact pad.
   - No-raw-output sweep: extend the existing `no_raw_controls_in_output` predicate (`errors.rs:415-432`, `test_pyrt_errors.py:101-111`) to assert no raw codepoint from the *full* extended escape set appears in a formatted message whose input contains all classes.
4. **Parity corpus (`tests/test_rust_parser_parity_fixture.py` `_CORPUS`),** new FAIL entries (traces verified against the fixture grammar during TDD, per the existing `\r` entry's precedent):
   - `("num", "\u202e123", FAIL)` — bidi override in the quoted line; fails at pos 0.
   - `("name", "\u2066\u200babc", FAIL)` — isolate + zero-width; fails at pos 0.
   - `("stmt", "x\u2028=\u2028@", FAIL)` — LS consumed as whitespace by the WS_REQUIRED separators (mirrors the existing `"x\r=\r@"` entry); two `\u2028` escapes before the caret; also pins that the comparator's `splitlines()` sees no raw LS.
5. **CST-bridge escaping (part a), `tests/test_rust_span.py`:** extend the existing FakeSource ABI-mismatch pattern (`test_rust_span.py:347-358`, `:763+`) with a dynamically-named class — `type("Fake\u202eSrc\t\x85", (), {...})` — passed to `Span._with_source_unchecked`; assert the `TypeError` text contains `\\u202e` and `\\x85` (single escape, not `\\xc2\\x85`), contains the raw TAB, and contains no raw U+202E/U+0085. This covers TAB-exclusion, C1-as-codepoint, and the new set through the real `py_type_obj_name` path.
6. **TODO hygiene:** `TODO.md` entry and both `TODO(error-msg-bidi-escape)` code comments gone; `make check` enforces sync.
7. **Gates:** `uv run --group dev maturin develop && uv run pytest`; `cargo test --workspace`; `make check` clean.

## Open questions

None. The three decisions the request delegated to design — exact zero-width/bidi membership, escape spelling for cp > 0xFF, and dedup-vs-pinned-copy — are decided and argued above (Set rationale; Representation; Part a).
