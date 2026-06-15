# Deep security review — regex-portability-lint

Commit reviewed: ba953c8 (base 034252d).

Scope note: this is a parser-*generation* library. The security-relevant trust boundary
here is the grammar-author-supplied regex pattern (`gsm.Regex.value`) reaching the Rust
regex engine. The whole purpose of the new validator (`check_regex_portable`) is to be a
fail-closed allowlist: a pattern it *accepts* but that is in fact non-portable is a
validator **bypass** — the exact hole this change exists to close. The findings below are
bypass cases (over-admission), evaluated against the design's own stated portability
contract and verified against the pinned engines (`regex-automata` 0.4 /
`regex-syntax-0.8.11`, octal disabled by default; Python `re`).

---

## security-1 — Validator admits `\0` (and `\0` + digits), which Rust rejects; over-admission bypass

**File:** `fltk/fegen/regex.fltkg:299` (`control_escape := value:/[nrtfv0a]/`); reached via
`escape` → `escape_body` → `char_escape` → `control_escape`. Same `control_escape` rule is
also used inside character classes (`class_escape_body` / `class_char_escape`).

**Issue.** `control_escape` admits `\0` as the NUL control character. The grammar comment
(`regex.fltkg:298`) asserts `\0` is "portable on both engines (verified)", and the design
(§4.1) lists `\0` among admitted control escapes while explicitly listing `\07` octal as an
*excluded, divergent* construct ("Python accepts, Rust rejects"). Both claims are wrong for
the pinned Rust engine. In `regex-syntax-0.8.11/src/ast/parse.rs:1490-1501`, an escape
whose char is in `'0'..='7'` is handled by the octal branch; octal defaults to **off**
(`parse.rs:142`, and `meta::Regex::new` uses the default builder), so the parser returns
`Err(UnsupportedBackreference)` for `\0`. Python `re` accepts `\0` as NUL. Verified by
execution:

- `check_regex_portable(r"\0")` → PORTABLE (accepted)
- `check_regex_portable(r"\07")` → PORTABLE (accepted)
- `check_regex_portable(r"\0a")` → PORTABLE (accepted)

So `\0`, `\07`, `\012`, `\08`, `\0a`, etc. all pass the lint. The grammar parses `\0` as
the control escape and any following digits as plain literal chars, which is why `\07`
sails through (the design assumed `\07` would be one octal token and excluded; the grammar
never had an octal token, so it decomposes to `\0` + `7` and is admitted).

**Trust boundary / data flow.** Untrusted input = a grammar author's regex term, stored
verbatim as `gsm.Regex.value` (`fltk2gsm.visit_regex`), reaching the Rust generator's
`gsm.Regex` branch in `gsm2parser_rs.py:786-796`. `check_regex_portable` is the only gate
on that path before the pattern is emitted into the Rust `REGEX_PATTERNS` table. A `\0`-
bearing pattern passes the gate.

**Consequence.** The lint is the contract that "anything the Rust generator accepts will
compile on the Rust engine, surfaced at generation time with a uniform message." A grammar
containing `\0` (a common, legitimate Python-`re` pattern — match a NUL byte) passes the
new generation-time check, then the emitted Rust parser **fails to compile** (the
`all_regex_patterns_compile` test / `meta::Regex::new` rejects it as
`UnsupportedBackreference`). The author gets a confusing Rust-toolchain compile error about
a "backreference" for a pattern the FLTK linter just blessed, instead of the clear
generation-time portability error this feature promises. This is a fail-*open* gap in a
checker whose entire justification (design §2) is fail-closed: a divergent construct the
allowlist was supposed to reject is admitted. It is lower-severity than a *silent*
divergence (Rust errors loudly rather than mis-parsing), but it still violates the stated
boundary and the "verified portable" comment is false. The corpus/unit tests do not catch
it because none of `_PORTABLE_PATTERNS` / `_NON_PORTABLE_PATTERNS` includes `\0`.

**Suggested fix.** Remove `0` from `control_escape` (make it `/[nrtfva]/`) so the validator
rejects `\0` / `\07` / `\0...` as non-portable, matching the design's stated exclusion of
octal-family escapes and the actual Rust behavior. Add `\0`, `\07`, `\012` to
`_NON_PORTABLE_PATTERNS`. Correct the `regex.fltkg:298` comment (drop the false "verified
portable" claim for `\0`). If a portable NUL escape is desired, `\x00` is already admitted
via `hex_escape` and works on both engines (verified PORTABLE), so authors lose nothing.

---

## Notes (not findings)

- The `genparser.py:386-391` `ValueError → typer.Exit(1)` handler is intact; the new
  `ValueError` from `gsm2parser_rs.py` propagates cleanly with no stack trace, and the
  message interpolates the pattern via `!r`, so there is no log/format-injection surface in
  the error path.
- Error-message construction in `regex_portability.py` uses `repr()` on the pattern and
  bounded slicing for the tail preview; no injection or unbounded-output concern.
- Spot-probed the admitted set for *silent* (both-engines-compile, different-match)
  divergence reaching the validator's accept path (`(?s).`, `(?U)a+`, `[^a]`, `\x00`,
  `$`-mid-pattern, etc.) — all genuinely portable; no silent-divergence bypass found beyond
  the `\0` case above. The documented non-ASCII `\d`/`\w`/`\s`/`\b`/`(?i)` residual (§6) is
  an accepted, called-out limit, not a finding.
- No secrets, auth, path, SSRF, deserialization, or network surface in this change.
