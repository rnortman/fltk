# Design review findings: error-msg-bidi-escape

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Verification performed against HEAD b02cb8f (design says "verified at HEAD 5d94733"; tree content at the cited locations is identical — confirmed all citations against the working tree):

- `crates/fltk-parser-core/src/errors.rs`: `needs_escape` predicate, fast path, caret pad (l.167-168), `TODO(error-msg-bidi-escape)` comment (l.90-91), escape unit tests (l.335-361), `no_raw_controls` test (l.412-430) — all match the design's descriptions (cited line numbers drift by 1–3 lines; immaterial).
- `fltk/fegen/pyrt/errors.py`: predicate duplicated between fast-path `any(...)` (l.69) and loop (l.74) — the drift hazard the design names is real; TODO comment at l.66-67; pad at l.93.
- `crates/fltk-cst-core/src/cross_cdylib.rs`: `escape_control_chars_for_msg` at l.123-138; wrong comment at l.128-129 (claims single-`\xHH`-per-codepoint; code iterates UTF-8 bytes); exactly six direct call sites at l.148, 162, 198, 208, 231, 241 — matches the design exactly. TAB-inclusion divergence (`cp <= 0x1F` without `!= 0x09`) confirmed.
- `crates/fltk-parser-core/Cargo.toml:15`: `fltk-cst-core = { path = ..., default-features = false }` — existing edge, no new dependency; design's dedup respects the request's dependency-direction constraint.
- `crates/fltk-parser-core/src/lib.rs:25`: `pub use errors::{escape_control_chars, ...}` — both public paths the design promises to preserve exist today and survive a `pub use fltk_cst_core::escape::escape_control_chars;` in `errors.rs`.
- `crates/fltk-cst-core/src/lib.rs` + `Cargo.toml`: `cross_cdylib` is `#[cfg(feature = "python")]`-gated; an ungated `pub mod escape` with no pyo3 imports compiles under `default-features = false` (pure-string); fltk-cst-core already carries `#[cfg(test)]` tests, so hosting the moved escape tests there is precedented.
- `tests/parser_parity.py`: `splitlines()` at l.56, byte-equal header assert at l.107 — as cited.
- `tests/test_pyrt_errors.py`: header cross-pin comment (l.3-4) currently names `crates/fltk-parser-core/src/errors.rs`; design's header update is required and planned. `no_raw` test at l.101-111 as cited.
- `tests/test_rust_parser_parity_fixture.py`: existing `("num", "\x1b[31mabc", FAIL)` and `("stmt", "x\r=\r@", FAIL)` entries at l.115, 118 — the precedent the design mirrors.
- Fixture grammar (`fltk/fegen/test_data/rust_parser_fixture.fltkg`): `num := value:/[0-9]+/`, `name := value:/[a-z]+/`, `stmt := lhs:atom : "=" : rhs:atom`. Traced the three proposed corpus entries: `"‮123"` fails at pos 0; `"⁦​abc"` fails at pos 0; `"x = @"` — name matches `x`, WS_REQUIRED separators consume each U+2028, `rhs:atom` fails at pos 4 — matches the design's trace.
- WS separator regex: generated parsers use `\s+` (e.g. `fltk_parser.py:1158`); Python `re` `\s` matches U+2028/U+2029 (verified by execution); `fltk-parser-core/Cargo.toml` enables regex-automata's `unicode` feature, so Rust `\s` is Unicode White_Space. The design's "LS consumed as whitespace" claim holds.
- `tests/test_rust_span.py`: FakeSource ABI-mismatch pattern at l.344-358 and l.763+ as cited; `check_abi_pair`'s SourceText-path `subject_fn` is `py_type_obj_name` (cross_cdylib.rs:93), so test plan #5 exercises the real path it claims to.
- `TODO.md` l.19-21: `error-msg-bidi-escape` entry as cited.
- Prior ADR `docs/adr/2026/06/11-error-msg-escape/design.md:33`: "two digits always suffice" — the claim this design supersedes, as stated.
- Exactly three escape implementations exist in-tree (errors.py, errors.rs, cross_cdylib.rs) — the design misses none.
- Set arithmetic: table rows (U+061C; U+200B–U+200F; U+2028–U+202E; U+2060; U+2066–U+2069; U+FEFF) = 19 new codepoints = Bidi_Control ∪ {LS, PS} ∪ five zero-width — internally consistent. No set member lies in U+00A0–U+00FF or above U+FFFF, as claimed.
- Requirements coverage: parts (a) and (b), all three pin-point repins, the splitlines-hazard corpus entry, TAB/C1/new-set coverage for the consolidated bridge path, TODO removal at both code locations plus TODO.md, signature stability, `\xHH` preservation, and the gates — each maps to a design section or test-plan item. No gaps found.
- Scope: U+061C and U+2060 additions fall within the request's delegated membership decision ("exact zero-width set ... is a requirements/design decision; pick deliberately and document") and are argued, not incidental; the non-goal exclusions (U+00AD, U+2061–U+2064, U+202F/U+205F, etc.) are explicit. No bonus features.

## Findings

### design-1

- **Section:** Proposed approach → Set rationale: "the complete Unicode `Bidi_Control` property (9 codepoints: U+061C, U+200E, U+200F, U+202A–U+202E, U+2066–U+2069)"
- **What's wrong:** The count is wrong. The enumerated set is 1 + 2 + 5 + 4 = **12** codepoints, not 9. The enumeration itself is correct and complete — it exactly matches Unicode `Bidi_Control` (PropList.txt: 061C; 200E..200F; 202A..202E; 2066..2069) — only the cardinality is wrong.
- **Why:** Arithmetic on the design's own enumeration; verified against the Unicode property definition (12 codepoints, confirmed by computation).
- **Consequence:** The design directs that "doc comments in code restate" this spec and that the spec be "auditable and non-arbitrary." An implementer restating "9 codepoints" into the `escape.rs`/`errors.py` doc comments propagates a falsifiable error into the normative cross-pin documentation; an auditor cross-checking against UCD gets a count mismatch and must re-derive whether the set or the count is wrong, defeating the stated auditability purpose.
- **Suggested fix:** Change "9 codepoints" to "12 codepoints."

No other findings. All other substantive claims verified true against source; requirements coverage complete; internally consistent; scope disciplined.
