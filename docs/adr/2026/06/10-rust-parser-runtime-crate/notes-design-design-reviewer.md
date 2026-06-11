# Design review findings — Phase 1 `fltk-parser-core` runtime crate

Reviewed: `design.md` against `request.md`, controlling `design.md` (rust-parser-codegen), `exploration.md`, and source. All cited line numbers spot-checked: memo.py, errors.py, terminalsrc.py (incl. lines 168-205), span.rs:48-50/161-165/204, Makefile:49-71, gsm2parser.py memoizer/consume_* regions, test_memo.py (five cases confirmed), root Cargo.toml members. Citations are accurate; the memo algorithm mapping (§2.5 steps 1-7) was walked against memo.py:82-257 and is observably equivalent, including the aliasing restructures. Verified claims not re-listed below.

## design-1: `PackratState` is not constructible by its own consumers as specified

§2.5: `pub struct PackratState { pub invocation_stack: Vec<u32>, recursions: HashMap<i64, RecursionInfo> }` — `recursions` is private, and no `new()`/`Default` is specified anywhere in the design. §4 item 1 specifies `tests/memo_toy.rs` (an external integration test using only the crate's public API) with a toy parser struct holding a `PackratState` field; Phase 2 generated parsers construct one in their constructor (controlling design §3.2: "`PackratState` ... is a field of the generated `Parser`"). Neither can build the struct: struct-literal construction fails on the private field outside the crate.

Same gap, weaker form, for `ErrorTracker`: fields are all `pub` so a literal works, but the `-1` initial value of `longest_parse_len` (errors.py:26) is a correctness invariant that every construction site must independently remember; the design specifies the invariant but no constructor that encodes it.

Consequence: Phase 1's own test plan does not compile as written; Phase 2's generated constructor is blocked or the implementer invents unspecified public surface ad hoc.

Suggested fix: specify `impl Default for PackratState` (empty stack/map) and `impl Default for ErrorTracker` (`longest_parse_len: -1`, empty context), or `new()` equivalents, and add them to the §2.1 re-export/API inventory.

## design-2: Golden-test plan contradicts the design's own nondeterminism analysis

§4 item 3: "`format_error_message` golden tests — expected strings captured by running the Python `format_error_message` on the same tracker states ... covering multi-rule grouping, dedup, regex tokens with backslashes". But §2.4 itself establishes that Python's within-rule line order is nondeterministic across processes (`defaultdict(set)` iteration, errors.py:64-70, PYTHONHASHSEED), and that Rust deliberately uses first-occurrence order instead. Therefore a Python-captured golden string is only byte-stable — and only guaranteed to match Rust's output — when each rule group contains at most one distinct token. The test plan states no such restriction, and the natural test for "dedup" or "multi-token rule" cases has ≥2 distinct tokens in one rule.

Consequence: golden expectations that are hash-seed-dependent at capture time and/or disagree with Rust's deterministic order — the test either flakes on recapture or fails against correct Rust output, exactly the trap §2.4 warns Phase 3 about.

Suggested fix: state the constraint in §4 item 3: golden byte-equality cases use ≤1 distinct token per rule group; multi-token-per-rule cases assert header + rule-group order byte-exactly and within-rule lines as an unordered set (mirroring the Phase 3 comparator rule §2.4 already defines), or capture with a fixed `PYTHONHASHSEED` and document that the captured order is arbitrary.

## design-3: §2.3 overstates Python parity of `consume_literal` for `pos < 0`; empty-literal sentence is ambiguous against the validity contract

§2.3: "Matches Python's per-codepoint comparison exactly, including the empty-literal case: `pos <= len` with empty literal yields `Some(empty span)`". Two problems, both at negative `pos`:

- Python's `consume_literal` (terminalsrc.py:168-175) indexes `self.terminals[pos + i]` — Python negative indexing wraps, so e.g. `consume_literal(-1, "<last char>")` succeeds in Python with `Span(-1, 0)`, and an empty literal at `pos = -5` returns `Span(-5, -5)`. The design's validity contract ("any `pos < 0` ... returns `None` — never wraps") is the right choice, but it is a deliberate divergence from Python, not an exact match.
- The empty-literal sentence ("`pos <= len` ... yields `Some`") taken literally includes negative `pos`, contradicting the contract sentence three lines earlier in the same section.

Consequence: implementer ambiguity over which sentence governs at `pos < 0` (Some vs None), and a parity-test author who validates against actual Python behavior at negative positions (e.g. fuzzing `consume_*` cross-backend) gets spurious mismatches the design claims cannot exist.

Suggested fix: change the sentence to "`0 <= pos <= len` with empty literal yields `Some(empty span)`; anything else yields `None`", and note explicitly that `pos < 0` behavior intentionally diverges from Python's negative-index wrapping (unreachable from generated code).
