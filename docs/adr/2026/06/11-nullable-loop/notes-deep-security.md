# Security review — nullable-loop (61f9384..6ac52d5)

Concise. Precise. Complete. Unambiguous. No padding.

Scope: `git diff 61f9384..6ac52d5`. Change is itself a DoS fix (unbounded CPU loop on
zero-width repetition matches, both backends) plus a validator tightening. Reviewed for
introduced vulnerabilities and residual DoS gaps. Verified: guard emitted in the single
repetition-loop site per backend (`gsm2parser_rs.py:_gen_item_multiple`,
`gsm2parser.py:gen_item_parser_multiple`); all regenerated artifacts carry it; the
runtime left-recursion grow loop (`fltk/fegen/pyrt/memo.py:242-250`) already has a
`new_pos <= memo.final_pos` progress break and is untouched. Test subprocess/cargo
usage is sane (no shell, list argv, timeouts, tmp_path crate, absolute path deps).
No secrets, no injection, no new trust-boundary crossings introduced.

## security-1

- **File:line**: `fltk/fegen/gsm2parser_rs.py:715` (emitted `if one_result.pos == pos { break; }`); `fltk/fegen/gsm2parser.py:564-575` (emitted `if one_result.pos == pos: break`).
- **Issue**: The progress guard breaks only on *exact* equality. It does not terminate the loop if a consume helper ever returns `one_result.pos < pos` (position regression), in which case the infinite loop — the DoS this change exists to fix — resurfaces.
- **Trust boundary / data flow**: Untrusted parse input drives the consume helpers whose returned `pos` feeds the loop variable. The guard is explicitly defense-in-depth for grammars that bypass validation (design §3.3), i.e. for exactly the situations where invariants elsewhere have already failed.
- **Consequence**: 100% CPU unbounded loop (DoS) on attacker-supplied input, conditioned on any current-or-future consume path returning a position less than its input position. Today no generated path does (regex/literal ends ≥ start; memoized results computed at the same pos; sub-expr pos monotone by induction — design §2.3's `<`-impossible claim checks out). But the guard's entire reason to exist is "the other layer was wrong"; relying on a monotonicity invariant inside the layer that defends against broken invariants is the same structural bet the validator just lost. Cost of robustness is zero.
- **Suggested fix**: Emit `if one_result.pos <= pos { break; }` (Rust) / `one_result.pos <= pos` (Python, via `iir.LessThanOrEquals`-equivalent or `Not(GreaterThan(...))`). Behavior identical for all reachable cases today; strictly safer.

## security-2

- **File:line**: `fltk/fegen/gsm.py:339-355` (`validate_no_repeated_nil_items`); `fltk/fegen/gsm.py:146-154` (`Regex._test_regex_empty`).
- **Issue**: The tightened validator (the design's "root fix") still under-approximates in two ways, so pathological grammars continue to pass validation and the runtime guard is the *sole* protection for them:
  1. **No recursion into sub-expressions.** The walk iterates only top-level `alternative.items`. A nested repeated-nullable item, e.g. `rule := ((r"a*")* "x")` — outer item REQUIRED over a sub-expression whose inner item is ZERO_OR_MORE with `Regex(r"a*")` — is never visited (outer quantifier not `is_multiple()`, inner item never enumerated). Codegen emits the inner loop; pre-guard this was an undetected hang identical to the trigger grammar.
  2. **Context-dependent zero-width regexes.** `_test_regex_empty` checks `compiled.match("") is not None`. Patterns whose emptiness depends on surrounding input — `\ba*`, `(?=x)`, `$`-anchored — return False against `""` but match zero-width on real input (e.g. `r"\ba*"` matches empty at pos 0 of `"bcd"`). `rule := (r"\ba*")+` passes the tightened validator. (Invalid-regex → False is the same under-approximation, already noted in design §4.)
- **Trust boundary / data flow**: Grammar authors are semi-trusted (downstream developers), but parse input is untrusted; for these grammars the hang is triggered by attacker-chosen input against a grammar its author believes the validator vetted.
- **Consequence**: Today, none exploitable — the loop guard terminates these cases (empty match discarded), which is why this is a gap report, not a vuln report. The risk is structural: the design designates the validator as the root fix and the guard as defense-in-depth, but for nested repetitions and context-dependent regexes the layering is inverted — the guard is the *only* layer. Any future change that weakens or removes the guard "because the validator rejects nullable repetitions" reintroduces an input-triggered 100% CPU DoS in both backends. Secondary effect: grammar authors get silent acceptance plus surprising empty-match-discard semantics instead of the clear validation error the trigger grammar now gets.
- **Suggested fix**: (a) Recurse into `Sequence[Items]` terms in `validate_no_repeated_nil_items` so nested `+`/`*` items are checked. (b) Document (comment at the guard and/or in the validator docstring) that regex emptiness is an under-approximation and the guard MUST remain even with the validator in place. (b) is the cheap, load-bearing half.

## No further findings

Guard placement (before `pos` update and before append) verified correct in both
generators and all regenerated artifacts — no vacuous-true or CST-divergence variant.
`Item.can_be_nil` tightening is monotone (False→True only); cannot newly *accept* a
grammar. Test-only validator monkeypatching is confined to subprocess/try-finally
scopes. No injection surface in the test harness (`subprocess.run` list argv, no
shell; Cargo.toml path interpolation uses repo-derived paths, not external input).

Reviewed commit: 6ac52d5 against base 61f9384.
