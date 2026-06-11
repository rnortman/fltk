# Exploration: parser-depth-limit TODO adversarial validation

Concise. Precise. Token-dense — no fluff, full information.

## Claims under test

TODO.md:76-78 (`parser-depth-limit`) + TODO.md:45-52 (`apply-depth-limit`):

> Generated parsers are recursive-descent with no depth limit. Deeply nested input exhausts the
> thread stack and aborts the process (cannot be caught with `catch_unwind`). Python raises a
> catchable `RecursionError`; the Rust backend is strictly worse for untrusted input. Fix: emit a
> depth counter in the generated `Parser` struct, increment/decrement in `apply__*` wrappers, and
> return a parse failure (with a distinguishable error) when a configurable limit is exceeded.
> Closely related to `apply-depth-limit` (Phase 1 runtime TODO) — the generated parser and the
> runtime counter should be wired together. Location: `fltk/fegen/gsm2parser_rs.py`
> (`_gen_apply_wrapper`, `_gen_parser_struct`).

## Call graph: does all recursion flow through `apply`?

**YES — all cross-rule recursive calls pass through `apply` in `memo.rs`.**

The generated call structure (verified against `tests/rust_parser_fixture/src/parser.rs`):

```
apply__parse_X  (line 123, 151, 179, etc.)
  -> apply()  [memo.rs:102]
  -> parse_X  (private fn, called only as rule fn pointer to apply)
    -> parse_X__altN  (private intra-rule fn)
      -> parse_X__altN__itemN  (private intra-rule fn)
        -> apply__parse_Y  (cross-rule call, always via apply__)
          -> apply()  [memo.rs:102]
          -> ...
```

Every reference to another rule in `_gen_consume_term` emits `self.{fn_info.apply_name}(pos)` where `apply_name = "apply__" + name` for all memoized rules (`gsm2parser_rs.py:724`). The intra-rule helpers (`parse_X__altN`, `parse_X__altN__itemN`, `parse_X__altN__item0__alts`, etc.) call each other directly but never recurse — they are bounded-depth static structure per parse position.

Sub-expression recursion (`rec_via_sub` case, `parser.rs:941-942`): even recursion through a sub-expression (`(rec_via_sub | atom)`) goes through `apply__parse_rec_via_sub` → `apply()`, not a direct recursive call. `_gen_consume_term` always resolves `gsm.Identifier` terms to their `apply_name` (`gsm2parser_rs.py:722-724`).

**A single counter in `apply` (memo.rs) would see every cross-rule recursive hop.** The intra-rule helper functions add O(grammar-width at that rule) fixed additional frames above each `apply` frame, but these are not depth-proportional to input nesting — they are constant per rule invocation.

The `invocation_stack: Vec<u32>` already exists in `PackratState` (`memo.rs:71`) and is pushed/popped at every `apply` call (`memo.rs:200-203`, `memo.rs:247-250`). Its `.len()` is a live depth counter with no additional cost.

## Does the TODO description mismatch the actual code locations?

**Minor mismatch:** The TODO says `_gen_apply_wrapper` and `_gen_parser_struct`. The actual method names in `gsm2parser_rs.py` are:

- `_emit_apply_wrapper` — `gsm2parser_rs.py:443` (not `_gen_apply_wrapper`)
- `_gen_parser_struct` — `gsm2parser_rs.py:329` (this one is correct)

The `TODO(parser-depth-limit)` comment itself lives in `_gen_header` at line 263, not in `_emit_apply_wrapper` or `_gen_parser_struct`. The header comment (`//! TODO(parser-depth-limit)`) is present in both generated fixture files (`tests/rust_parser_fixture/src/parser.rs:7`, `tests/rust_cst_fegen/src/parser.rs:7`).

## Are both TODOs genuinely needed, or does one suffice?

Two separate issues with an interaction:

**`apply-depth-limit` (memo.rs `PackratState`)**: counter inside the runtime `apply` fn. Would catch all cross-rule recursive hops. `invocation_stack.len()` is already an exact depth measurement. The fix is entirely within `crates/fltk-parser-core/src/memo.rs`.

**`parser-depth-limit` (gsm2parser_rs.py)**: a counter in the *generated* `Parser` struct, configurable per-parser. This is a separate concern: where is the limit configured and how is it surfaced?

**Interaction**: if `PackratState` holds the counter and limit, the generated `Parser` struct needs no new field — it already contains `packrat: PackratState`. The generated `apply__*` wrappers already delegate entirely to `apply()` in memo.rs. A counter in `PackratState` alone, checked inside `apply()`, would enforce the limit without any generator changes — the depth count already flows through `apply` as `invocation_stack.len()`.

The `parser-depth-limit` TODO proposes an alternative: counter in the generated `Parser` struct, incremented in generated `apply__*` wrappers. This would not require `PackratState` changes but duplicates state already available as `invocation_stack.len()` and adds generated boilerplate to every parser.

**Both are not strictly needed simultaneously.** Either:
- Runtime only: depth check in `apply()` against a limit stored in `PackratState`. Generated parsers would need to expose a setter/constructor param to configure the limit — but the `Parser` struct already wraps `PackratState::default()` with no configurable fields (`parser.rs:62-89`). API surface change is on `PackratState` or a new `Parser::new_with_limit(...)` constructor.
- Generator only: counter in generated `Parser`, incremented in `apply__*` wrappers before the `apply()` call.

The "wired together" language in the TODO reflects that neither approach is complete without the other: a runtime counter needs a way to be configured per-parser (generator concern), and a generator counter needs to actually enforce the limit (which happens at the `apply()` callsite).

## Python RecursionError: is the claim correct?

**Verified correct.** No `sys.setrecursionlimit` call exists anywhere in the codebase (`grep` returned nothing). Python hits CPython's default recursion limit (~1000 frames) and raises `RecursionError`, which IS a catchable exception (subclass of `Exception`). No evidence of any explicit recursion limit being set or relied upon.

The Python `Packrat.apply` (`pyrt/memo.py:82-156`) calls `rule_callable(start_pos)` (`line 118`) which recurse through the same chain: `parse_X` → `self.apply__parse_X__<path>` → `packrat.apply` → `rule_callable`. Every cross-rule call goes through `self.packrat.apply`, same structural constraint as Rust. Default CPython recursion limit is 1000; each grammar rule depth adds ~4-6 Python stack frames (apply wrapper + packrat.apply + parse_X + parse_X__altN).

The claim that "Python raises a catchable `RecursionError`" is correct by CPython semantics, not by any explicit code in this repo.

## `catch_unwind` claim: verified?

**Asserted in code comments, not proven by a test.** The claim appears verbatim in:
- `crates/fltk-parser-core/src/memo.rs:87-88` (doc comment on `apply`)
- `fltk/fegen/gsm2parser_rs.py:260` (generated file header template)
- `tests/rust_parser_fixture/src/parser.rs:4` (generated fixture)

The claim is correct by Rust semantics: stack overflow on x86/x86_64 is a SIGSEGV (or stack guard page hit), which causes the process to abort via signal handler. Rust's `catch_unwind` only catches Rust panics unwound via the panic machinery; it does not catch signals. No `stacker`, `RUST_MIN_STACK`, or `catch_unwind` usage exists anywhere in the codebase.

## Where would limit be configured, how would failure surface?

**Current state: zero infrastructure.** No depth counter or limit field exists anywhere:
- `PackratState` (`memo.rs:68-74`): only `invocation_stack: Vec<u32>` and `recursions: HashMap<i64, RecursionInfo>`.
- `ErrorTracker` (`errors.rs:39-43`): only `longest_parse_len: i64` and `expected_context: Vec<ParseContext>`.
- Generated `Parser` struct (`gsm2parser_rs.py:336-349`): fields are `terminals`, `packrat`, `error_tracker`, `capture_trivia`, and one `Cache<Shared<cst::X>>` per rule.
- No `limit` param in `Parser::new` or `Parser::from_source_text` (`gsm2parser_rs.py:353-370`).

**Failure surface options (not yet designed):**
- `apply()` returning `None` with a depth-exceeded sentinel in `ErrorTracker` would surface as a normal parse failure — indistinguishable from "input doesn't match grammar" unless a new field is added to `ErrorTracker`.
- A dedicated error type / error channel (referenced in TODO.md:51 as "Phase 3") does not exist yet.

## Open factual questions

- What default limit value is appropriate? Python's default of ~1000 effective rule-depth calls (not raw frames) would be a natural baseline but is not specified anywhere.
- Does `invocation_stack.len()` accurately represent grammar nesting depth, or does seed-grow double-count (push at line 200, push again at line 247)? The second push at line 247 is inside `grow_seed` scope for the same rule_id being grown — it inflates the stack length briefly. A dedicated `depth: usize` counter separate from `invocation_stack` would be cleaner.
- The `parser-depth-limit` TODO names `_gen_apply_wrapper` but the actual method is `_emit_apply_wrapper` (`gsm2parser_rs.py:443`). The TODO text should reference the correct name.

## Verdict on TODO validity

The TODO is substantially correct:

| Claim | Status |
|---|---|
| No depth limit exists | **Correct** — zero depth counter code anywhere |
| Rust aborts (not catchable) | **Correct** — Rust stack overflow → SIGSEGV/abort, not unwindable panic |
| Python raises catchable RecursionError | **Correct** — CPython default behavior, no code contradicts it |
| All recursive paths go through `apply` | **Correct** — verified in generated code; `invocation_stack.len()` is already live depth |
| Both TODOs needed and "wired together" | **Partially correct** — a single counter in `apply`/`PackratState` would suffice structurally; the "wired together" claim is accurate in that configuration and limit exposure are cross-cutting |
| Location `_gen_apply_wrapper` | **Wrong name** — actual method is `_emit_apply_wrapper` at `gsm2parser_rs.py:443` |
| Location `_gen_parser_struct` | **Correct** — `gsm2parser_rs.py:329` |
| TODO(parser-depth-limit) comment location | The comment in `_gen_header` (`gsm2parser_rs.py:263`), not `_emit_apply_wrapper` |
