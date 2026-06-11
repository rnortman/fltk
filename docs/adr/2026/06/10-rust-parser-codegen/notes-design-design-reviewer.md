# Design review findings: Rust Parser Codegen

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Reviewed: `design.md` against `request.md`, `exploration.md`, and source at commit 5d05d7f.

Verified clean (no finding): gsm2parser.py citations (152, 171-180, 341, 374-375, 454-463, 581-585, 653-659, 682-683, 742-748); memo.py citations (82-156, 112-122, 181-187, 206-226); terminalsrc.py:183-205; plumbing.py:135; tests/rust_cst_fegen/src/cst.rs:403 (`append_rule(&mut self, child: impl Into<Shared<Rule>>)`); Span fields `i64` and `new_with_source(start, end, &SourceText)` (span.rs:143-144, 204); synthesis.md ~80 unparser call sites (line 207) and §5 `op="is"`; the cited parity-corpus test files all exist (under `fltk/fegen/`, not `tests/`); the single-parser/runtime-`capture_trivia` decision is compilable — generated Rust CST child enums already carry `Trivia` variants unconditionally (tests/rust_cst_fegen/src/cst.rs:187, 781, 1543, 2145, 3216, 4339, ...), so always-compiled trivia-append sites type-check. Requirements coverage is complete: Rust parser generation, pure-Rust use with no pyo3 linked, Python use, Python pipeline untouched, CST-style gating pattern chosen as request permits.

---

## design-1 — Duplicated ownership of the input text (`TerminalSource` vs `SourceText`)

**Where:** §3.1 "`TerminalSource`: owns the input `String` plus a codepoint-index table"; §3.2 "`pub struct Parser` holding `TerminalSource`, `SourceText`, ...".

**What's wrong:** The design has the parser hold the input text twice — a `String` inside `TerminalSource` and a separate `SourceText` (which is `Arc<SourceInner>` holding the text, crates/fltk-cst-core/src/span.rs:58-76). It never states the relationship between the two or that they must be the same text.

**Why:** Python avoids this only by string sharing (`SourceText(text=terminalsrc.terminals)`, gsm2parser.py:107-118). Rust `String` + `Arc<SourceInner>` are two allocations of the full input. Nothing in the design forces the spans' source (`SourceText`) to be the text actually parsed (`TerminalSource`'s `String`).

**Consequence:** Doubled peak memory for large inputs, and a constructible inconsistent state where every emitted `Span` carries a source that differs from the parsed text — `span.text()` would silently return wrong slices.

**Fix:** `TerminalSource` holds a `SourceText` (cheap Arc) and derives its codepoint table from it; the parser gets `&SourceText` from the `TerminalSource`. One owner, one constructor argument.

## design-2 — "Slice + match at offset 0" is not equivalent to Python `re.match(pos=...)`

**Where:** §3.1 "`consume_regex` slices at the byte offset and requires a match at offset 0 (equivalent to Python `re.match(pos=...)`)"; §4 "Regex semantics drift" bullet (covers only Unicode-class drift and compile failures).

**What's wrong:** The equivalence claim is false for context-sensitive constructs. Python `re.compile(regex).match(self.terminals, pos=pos)` (terminalsrc.py:177-181) anchors at `pos` but keeps full-string context: `\b`/`\B` see the character *before* `pos`. Slicing the haystack at `pos` makes the slice start a string boundary, so e.g. pattern `\bfoo` with a word character immediately before `pos` fails in Python but succeeds in the Rust design. This drift compiles cleanly — the generated regex-compile `#[test]` (§3.1) does not catch it — and §4's drift bullet doesn't mention it.

**Consequence:** Silent cross-backend parse divergence for any grammar whose regexes use `\b`/`\B` (or `(?m)^`). In-tree grammars don't, but out-of-tree grammars are the primary consumers (CLAUDE.md); the in-tree parity corpus cannot protect them.

**Fix:** Use `Regex::find_at(full_haystack, byte_pos)` and require `match.start() == byte_pos` — full-haystack context exactly reproduces Python's accept/reject results (worst-case it scans-and-rejects where Python anchors, a perf not correctness difference). Or explicitly document `\b`/`\B` as unsupported and make the generated test reject patterns containing them.

## design-3 — Generated code's `regex` dependency / version-coherence unaddressed

**Where:** §3.1 "the generated parser owns a static regex table (`OnceLock<Regex>` per distinct pattern); `TerminalSource::consume_regex` takes `&Regex`".

**What's wrong:** The generated parser file names the `regex::Regex` type, so every consumer crate (in-tree fixtures and out-of-tree) needs its own `regex` dependency — and it must resolve to the *same* `regex` version as `fltk-parser-core`'s, or `&Regex` at the `consume_regex` boundary is two distinct types and the generated code fails to compile (or works until a semver-major regex bump splits the graph). The design specifies the dep only for `fltk-parser-core`.

**Consequence:** Out-of-tree consumer crates (the primary audience per CLAUDE.md) get confusing type-mismatch compile errors or fragile version coupling that the design never decided.

**Fix:** `fltk-parser-core` does `pub use regex;` and the generated code references `fltk_parser_core::regex::Regex` exclusively. Consumers then need no direct `regex` dep and version coherence is structural.

## design-4 — No-panic posture contradicted by unvalidated `pos` in the pure-Rust entry points

**Where:** §4 "the parser must not panic on any *input*"; §4 "`i64` positions: ... parse entry validates `pos >= 0 && pos <= len` at the Python boundary".

**What's wrong:** Validation is specified only at the Python boundary, but the pure-Rust API is a first-class entry point (request.md; test plan item 2 calls `apply__parse_<rule>` from Rust directly). A negative or out-of-range `i64` pos reaching the codepoint→byte table (`Vec<usize>` indexing, §3.1) panics. The doc never says whether the native `apply__parse_<rule>(pos: i64)` validates, returns failure, or is documented as caller-must-validate.

**Consequence:** Panic in the pure-Rust API; for an out-of-tree consumer cdylib this can mean unwinding across FFI/abort. Internal inconsistency: the implementer cannot satisfy both stated rules without making an undesigned call.

**Fix:** State the contract: either native entry points treat out-of-range pos as parse failure (cheap bounds check in `consume_*`/`apply`), or narrow the no-panic posture to "valid `pos` + any text" and document it.

## design-5 — Parity test requires a farthest-failure position the designed API doesn't expose

**Where:** §5 item 3 "Failure cases assert both backends fail, at the same farthest position" vs §3.3 "The Python backend's `error_tracker` attribute is *not* replicated; consumers on the Rust parser use `error_message()`".

**What's wrong:** The only error surface on the Rust parser's Python bindings is a formatted `String`. The farthest failure position is not programmatically accessible, so the specified parity assertion can only be written by parsing the human-readable message — fragile, and exactly the "exposing tracker internals" the design wanted to avoid doing ad hoc.

**Consequence:** Test plan item 3 as written is unimplementable against the §3.3 API; the implementer will either string-scrape (brittle) or invent an API addition mid-implementation without a design decision.

**Fix:** Either add one scalar accessor (e.g. `error_position() -> int | None` or line/col pair) to `PyParser`, or weaken item 3 to "both fail and `error_message()` strings are equal" (which implies same position when `rule_names` match) and say so.

## design-6 — "Generation-time validation is impossible from Python" is overstated

**Where:** §3.1 regex-handling bullet: "(generation-time validation is impossible from Python)".

**What's wrong:** fltk already ships a Rust extension (`fltk._native`); a small binding that compiles a pattern with the `regex` crate would give generation-time validation. It's a cost/scope tradeoff (adds a `regex` dep to `_native`), not an impossibility. The chosen generated-`#[test]` mitigation is reasonable; the justification is wrong.

**Consequence:** The ADR records a cheap future improvement as impossible, deterring revisiting (ADRs are the durable decision record per CLAUDE.md).

**Fix:** Reword to "not available without adding a regex dependency and binding to `fltk._native`; deferred — the generated `#[test]` suffices."

## design-7 — `extend_children(&other)` does not "consume" the argument

**Where:** §3.2 "Non-memoized item/alternative parsers return nodes by value (`extend_children(&other)` consumes them)".

**What's wrong:** `extend_children(other: &Self)` borrows and Arc-clones children (exploration.md §2.5 item 5; tests/rust_cst_fegen/src/cst.rs). Nothing is consumed; the by-value local is simply dropped afterward. The by-value-return decision is fine; its stated rationale misdescribes the API.

**Consequence:** An implementer taking the parenthetical literally may design an `extend_children(self/Self)`-by-value variant or wrong ownership flow at the inline-to-parent sites.

**Fix:** Reword: "return nodes by value; the parent `extend_children(&result)` Arc-clones the children and the local is dropped."

## design-8 — Prior-ADR characterization: synthesis.md made no recommendation

**Where:** §2 "The 2026-05-25 synthesis ... favored Path 1 ... on the theory that ...".

**What's wrong:** synthesis.md is explicitly "No recommendations -- tradeoffs presented for human judgment" (synthesis.md:3); Path 1 was *Analysis 1's* recommendation, which synthesis reports (synthesis.md heading for Path 1). The LoC numbers the design quotes are accurate (3,280-4,580 vs 5,150-5,950).

**Consequence:** Minor record-accuracy defect in a document that will become the ADR rationale; misattributes a position to a prior decision-support doc.

**Fix:** "presented Path 1 (Analysis 1's recommendation) as the lowest-LoC option" or similar.
