# Security review — fltk-parser-core runtime crate

Reviewed: d23d1df..1521372 (HEAD 1521372). Style: concise, precise, complete, unambiguous. No padding.

Threat model: this crate is the runtime under generated parsers; the source text being parsed is the untrusted input. Trust boundary: downstream applications feed arbitrary (potentially attacker-supplied) text into `TerminalSource` and the generated parser drives `consume_*` / `apply` / `format_error_message` over it. Checked: bounds/`as usize` conversions (all `i64` positions validated before cast — clean), unsafe code (none), secrets (none), dependency (`regex` 1.12.4 in Cargo.lock — current, linear-time engine, CVE-2022-24713 long fixed).

## security-1: `consume_regex` unanchored `find_at` scan — quadratic-time DoS on failed matches

- File: crates/fltk-parser-core/src/terminalsrc.rs:141-145
- Issue: `regex.find_at(text, byte_pos)` is not an anchored search. On a non-match at `byte_pos` it scans the entire remaining haystack looking for a later match, which line 142-145 then discards. Python's reference (`re.match(pos=...)`) anchors and fails without scanning — this is a behavioral and complexity divergence, not parity.
- Trust boundary / data flow: attacker-controlled source text → generated parser attempts regex terminals at many positions → each failed attempt costs O(remaining input) instead of O(match attempt at pos). Packrat memoization bounds rule applications to O(rules × positions), so worst case is O(rules × n²) scan work — quadratic in input length per grammar.
- Consequence: algorithmic-complexity DoS. An attacker submits an input crafted so regex terminals fail at most positions (trivially easy: any input the grammar rejects early and often); a service parsing untrusted input (the library's stated purpose) burns CPU quadratically. A few MB of input can turn into ~10¹² scan steps.
- Suggested fix: perform a truly anchored search. The high-level `regex::Regex` API doesn't expose anchoring at an offset, but `regex_automata::meta::Regex` (already in the dependency tree under `regex`) does: `Input::new(text).anchored(Anchored::Yes).span(byte_pos..text.len())` — preserves look-behind context (the reason slicing was rejected in design §2.3) and fails in O(1)-ish without scanning. Alternative: keep `find_at` but bound the search (no clean API for that) — prefer the regex-automata route. At minimum, document the complexity hazard if deferred.

## security-2: unbounded recursion in `apply` — stack-overflow abort on deeply nested untrusted input

- File: crates/fltk-parser-core/src/memo.rs:93-100 (`apply`, recursing via the `rule` callback)
- Issue: `apply` → `rule` → `apply` recursion depth is proportional to grammar-nesting depth of the input, with no depth limit. The Python reference hits `sys.setrecursionlimit` and raises a catchable `RecursionError`; Rust overflows the thread stack, which is a SIGSEGV/abort — process death, not a recoverable parse error.
- Trust boundary / data flow: attacker-controlled source text with deep nesting (e.g. ten thousand open parens for any grammar with parenthesized expressions) → recursive rule descent → stack exhaustion.
- Consequence: hard DoS — the embedding process (including a Python interpreter once Phase 3 binds this) is killed outright; in a multi-tenant service one malicious document takes down the worker. This is a strict failure-mode regression versus the Python backend it replaces (recoverable exception → unrecoverable abort), relevant to the cross-backend-equivalence goal.
- Suggested fix: the runtime is the natural chokepoint — add a depth counter to `PackratState`, increment/decrement in `apply`, and convert exceeding a configurable limit into a parse failure (or a dedicated error once Phase 3 grows an error channel). If deliberately deferred to Phase 2/3, record the decision and the limit's future home now; the current diff is silent on it.

## security-3: raw untrusted source text embedded in error messages — terminal/log escape injection

- File: crates/fltk-parser-core/src/errors.rs:108-130 (`format_error_message`, `line_text`)
- Issue: `line_text` is the raw failing line from the untrusted input, concatenated unescaped into the error string. `py_repr_str` escaping is applied only to grammar tokens (trusted), never to the input excerpt. Control characters (including ESC 0x1b — ANSI sequences) and `\r` pass through verbatim.
- Trust boundary / data flow: attacker-controlled source text → failing line → error message → downstream tools that print parse errors to terminals or write them to logs.
- Consequence: terminal escape-sequence injection (cursor manipulation, screen rewrite, title-set; historically RCE in vulnerable terminal emulators) and log-forging (`\r` line-splicing) against any downstream consumer that surfaces parse errors — the common case for a parser library. Mitigating context: this is byte-for-byte parity with the Python `format_error_message`, so the exposure is inherited, not introduced; severity is correspondingly low and a unilateral fix here would break the Phase 3 parity comparator.
- Suggested fix: don't change Phase 1 (parity governs). Record as a known shared weakness of both backends; if ever addressed, fix Python and Rust together (escape C0 controls except `\n`/`\t` in `line_text`) and update the comparator.

No other findings. Specifically clear: all `cp_to_byte` indexing is bounds-checked before `as usize` (no wraparound paths), the memo `assert!`s are not input-reachable per the algorithm (the one reachable `panic!` at memo.rs:117 is a documented, design-adjudicated parity decision — not re-raised), no secrets, no unsafe, no injection sinks beyond security-3.
