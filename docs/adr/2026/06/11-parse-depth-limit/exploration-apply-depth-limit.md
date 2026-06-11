# Adversarial Validation: `apply-depth-limit` / `parser-depth-limit` TODOs

Concise. Precise. No fluff. Audience: implementer or reviewer deciding whether to act.

---

## 1. Is the recursion path real and unbounded?

**Real: yes. Unbounded: yes.**

Concrete path in the generated parser (`tests/rust_parser_fixture/src/parser.rs`):

```
apply__parse_expr (line 449)
  → apply() [fltk-parser-core/src/memo.rs:102] — Step 3 miss: calls rule(parser, pos)
    → parse_expr (line 506) — rule body
      → parse_expr__alt0 (line 465)
        → parse_expr__alt0__item0 (line 453)
          → apply__parse_expr (line 454)  ← back to top
```

Each grammar nesting level adds approximately 5 Rust stack frames:
`apply__parse_X` → `apply` → `parse_X` → `parse_X__altN` → `parse_X__altN__itemM` → `apply__parse_X`.

The recursion terminates only when the packrat memoizer detects left-recursion (poison hit at the same position) or when the input runs out. For right-recursive or deeply nested grammars, every additional nesting level adds those frames with no check or limit. No counter, no guard, no early-exit exists in `PackratState` (`memo.rs:68-74`).

`invocation_stack` (`memo.rs:71`, `PackratState.invocation_stack: Vec<u32>`) is **not** a depth proxy — it is pushed only on a cache miss (Step 3, `memo.rs:200`) and is empty on cache hits. For a deeply nested but non-recursive input where every call is a miss, `invocation_stack.len()` equals the number of active memoized rules on the call stack at that moment, which coincides with actual depth. But the stack does not bound or limit recursion; it is a bookkeeping aid for `setup_recursion`.

---

## 2. Does stack overflow abort the process?

**Yes — and the comment in the code already says so accurately.**

`memo.rs:86-88`:
> Rust overflows the stack (abort/SIGSEGV) — a hard DoS, not a recoverable error, in contrast to the Python backend.

`gsm2parser_rs.py:260` emits into every generated file header:
> `//! Stack exhaustion aborts the process (cannot be caught with `catch_unwind`).`

This is correct for the cdylib case. The generated parsers compile as cdylib (`tests/rust_parser_fixture/Cargo.toml`: `crate-type = ["rlib", "cdylib"]`; `tests/rust_cst_fegen/Cargo.toml`: `crate-type = ["cdylib", "rlib"]`). `fltk-parser-core` itself is `crate-type = ["rlib"]` (`crates/fltk-parser-core/Cargo.toml`). The `apply` function in the rlib is inlined into the cdylib.

When a cdylib is loaded as a CPython extension (the Phase 3 use case via `PyParser`), a stack overflow produces `SIGSEGV`. CPython's signal handler cannot catch `SIGSEGV` from native stack exhaustion; the process aborts. `catch_unwind` does not help because stack overflow is not a Rust panic — it is delivered as an OS signal before any Rust unwinding begins.

Python's reference implementation raises `RecursionError` (a Python exception) which is catchable. The Rust backend is strictly worse: same input, unrecoverable abort vs. catchable exception.

The Python `PyParser` boundary (`parser.rs:1090-1095`, generated doc comment on `PyParser`) now carries the warning. Python callers cannot intercept the abort from Python code.

---

## 3. Is the proposed `PackratState` depth counter feasible?

**Structurally feasible. Two complications.**

### 3a. Counter placement

`PackratState` (`memo.rs:68-74`) is the correct struct — it is `&mut`-accessed by every `apply` call via the `state` projector. Adding a `call_depth: u32` field and incrementing/decrementing at the `rule(parser, start_pos)` call site in Step 3 (`memo.rs:201`) and the `rule(parser, start_pos)` call inside `grow_seed` (`memo.rs:332`) would cover all paths where the Rust stack actually grows due to `apply` recursion.

The `state(parser).invocation_stack.len()` is a lower bound on actual depth (it equals depth when every call is a miss). A dedicated `call_depth` counter incremented unconditionally in `apply` (not just on misses) would be exact.

### 3b. Limit configuration — no existing mechanism

There is no configuration infrastructure anywhere in `PackratState`, `Parser`, or the generated structs for a configurable limit. Three options exist:

1. Hard-coded constant in `memo.rs` (simplest; breaking change to change value).
2. `max_depth: u32` field added to `PackratState` (set during `Parser` construction; requires `PackratState::default()` to pick a default or be replaced by a constructor).
3. `max_depth: u32` field on the generated `Parser` struct (requires `_gen_parser_struct` in `gsm2parser_rs.py` to emit it and `_emit_apply_wrapper` to thread it through).

Option 2 is compatible with `PackratState::default()` if a `const DEFAULT_MAX_DEPTH` is defined and used in the `Default` impl. `PackratState::default()` is the only external construction path (`memo.rs:68` doc comment: "Default is the only external construction path").

### 3c. Failure surfacing — no error channel today

`apply` returns `Option<ApplyResult<T>>`: `None` means parse failure, `Some(_)` means success. There is no error channel distinguishing "depth exceeded" from "grammar didn't match". The TODO acknowledges this: "convert exceeding a configurable limit into a parse failure (or a dedicated error channel in Phase 3)."

Returning `None` on depth exceeded is immediately implementable but loses the reason. A dedicated error channel would require adding a `Result`-like wrapper or a side-channel field to `PackratState` (analogous to `ErrorTracker`). Neither exists yet.

---

## 4. Two-TODO interaction: do both counters cover all paths?

The TODO system has two linked entries:

- `apply-depth-limit` (`TODO.md:45-52`): counter in `PackratState` / `apply` in `memo.rs`.
- `parser-depth-limit` (`TODO.md:76-78`): counter in generated `Parser` struct / `apply__*` wrappers in `gsm2parser_rs.py`.

The two TODOs describe **two different counter locations** for what may be the same underlying depth.

**What `apply` in `memo.rs` sees:** all recursion that passes through the memoizer — i.e., all calls to memoized rules (every `apply__parse_X`). Non-memoized helper functions (`parse_X__altN`, `parse_X__altN__itemM`) do not call `apply`; they are plain non-recursive leaf functions or wrappers that eventually delegate to `apply__parse_Y` for a different rule. The recursion depth as seen by `apply` counts memoized-rule re-entries, not raw Rust stack frames.

**What `_gen_apply_wrapper` generates:** `apply__parse_X` calls `apply(...)` — a one-line delegation (`parser.rs:449-451`). Incrementing a counter here (before calling `apply`) would give the same count as incrementing inside `apply`'s Step 3 path.

**Conclusion on coverage:** A single counter in `PackratState`, incremented in `apply` at the `rule(parser, start_pos)` invocation (Step 3, `memo.rs:201`), would count every memoized-rule call that actually recurses into the grammar. The non-memoized helper functions between `apply__parse_X` calls add constant stack depth per level (approximately 3–4 frames: `parse_X`, `parse_X__altN`, `parse_X__altN__itemM`) that is bounded by grammar structure, not input depth.

The `parser-depth-limit` TODO's proposed location (`_gen_apply_wrapper`) would duplicate a counter that `apply` already could maintain, not extend coverage. Both TODOs therefore describe two access points to the same semantic counter. One implementation in `memo.rs` suffices to bound depth; the generated-parser TODO is about where to expose or configure the limit, not about covering an uncovered path.

The `parser-depth-limit` TODO specifically says the two "should be wired together" (`TODO.md:78`), confirming they are not independent. A single `call_depth` in `PackratState` (incremented/decremented in `apply`) with a `max_call_depth` field (set via `Parser::new`) satisfies both TODOs.

---

## 5. Any deeper problem?

The underlying problem is structural: the generated parsers are recursive-descent with depth proportional to input nesting. This is inherent to the packrat approach as implemented — not a local oversight. The `invocation_stack` already exists and accurately reflects the memoized call chain; the missing piece is a bound check on its growth (or on a parallel `call_depth` counter).

The `gsm2parser_rs.py:260-263` generated header comment and `memo.rs:83-90` doc comment both accurately describe the risk. The TODO text in `TODO.md:45-52` and `76-78` accurately describes the fix. No facts are misstated.

One nuance the TODO text does not call out: `invocation_stack.len()` at any point inside `apply`'s Step 3 already equals the current memoized recursion depth minus 1 (it was just pushed at `memo.rs:200` before calling `rule`). So a depth limit could be implemented by checking `invocation_stack.len()` against a threshold before the `rule(parser, start_pos)` call, without adding a new field — though a dedicated `call_depth` is cleaner.

---

## 6. Key source locations

| Fact | File:line |
|---|---|
| `PackratState` struct (no depth field) | `crates/fltk-parser-core/src/memo.rs:68-74` |
| `apply` Step 3 miss — where recursion descends | `memo.rs:196-203` |
| `apply` TODO comment | `memo.rs:83-90` |
| `invocation_stack` push/pop | `memo.rs:200-202`, `247-250` |
| `grow_seed` recursive `rule(parser, start_pos)` call | `memo.rs:332` |
| Generated `apply__parse_X` wrapper (one-line) | `tests/rust_parser_fixture/src/parser.rs:449-451` |
| `parse_expr__alt0__item0` calls `apply__parse_expr` (direct recursion) | `parser.rs:453-455` |
| Generated file header stack-overflow warning | `gsm2parser_rs.py:258-263`; emitted at `parser.rs:2-7` |
| `_emit_apply_wrapper` (generator) | `fltk/fegen/gsm2parser_rs.py:443-458` |
| `parser-depth-limit` TODO | `TODO.md:76-78` |
| `apply-depth-limit` TODO | `TODO.md:45-52` |
| `fltk-parser-core` crate type (`rlib`) | `crates/fltk-parser-core/Cargo.toml` |
| Generated fixture crate type (`cdylib + rlib`) | `tests/rust_parser_fixture/Cargo.toml` |
