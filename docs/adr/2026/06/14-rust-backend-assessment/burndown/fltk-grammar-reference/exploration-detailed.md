# FLTK Grammar Language — Detailed Semantics, Constraints & Limitations

Code-level depth pass for the persistent FLTK grammar reference. Input: `exploration-syntax.md`
(the surface layer). This pass digs into the implementation and pins **detailed semantics,
constraints, and limitations** a grammar author must know. Every claim is grounded in code
(`file:line`).

Primary sources read in full:
- `fltk/fegen/gsm.py` — Grammar Semantic Model + validators.
- `fltk/fegen/gsm2parser.py` — Python parser generator.
- `fltk/fegen/gsm2tree.py` — Python CST node-class generator.
- `fltk/fegen/fltk_parser.py` — generated parser (worked example of emitted code).
- `fltk/fegen/pyrt/memo.py` — packrat memoizer + left-recursion engine.
- `fltk/fegen/pyrt/terminalsrc.py` — terminal matching (`re`), spans, line/col.
- `fltk/fegen/pyrt/errors.py` — error tracking / "Expected" reporting.
- `fltk/fegen/fltk2gsm.py` — CST→GSM mapper (defaulting rules).
- `crates/fltk-parser-core/src/{memo.rs,terminalsrc.rs}` — Rust runtime parity + divergences.
- `crates/fegen-rust/src/parser.rs`, `fltk/fegen/gsm2parser_rs.py` — Rust parser generator.

---

## 1. LEFT RECURSION — FLTK supports it (the truth, from code)

**FLTK DOES support left recursion**, both direct and indirect/mutual. A prior design that
claimed otherwise was wrong. The mechanism is a **packrat memoizer with seed-growing**, a
simplified variant of the Warth et al. algorithm. It is implemented once in the runtime, not
in generated code, so it applies to **every rule of every grammar automatically** — there is
no opt-in.

### 1.1 Where it lives
- Python: `fltk/fegen/pyrt/memo.py`, class `Packrat` (`memo.py:77-257`). Generated rule
  methods call `self.packrat.apply(...)` via their `apply__parse_<rule>` wrapper
  (`gsm2parser.py:441-463`; worked example `fltk_parser.py:103-108, 149-150`).
- Rust: `crates/fltk-parser-core/src/memo.rs`, free function `apply`/`apply_inner`
  (`memo.rs:182-353`), `setup_recursion` (`memo.rs:363-381`), `grow_seed` (further down).
  The Rust file documents it as a deliberate port: "Port of `Packrat._setup_recursion`
  (memo.py:206-226)" etc.

### 1.2 The mechanism (Python, authoritative)
`Packrat.apply` (`memo.py:82-156`):
1. **Recall** the memo for `(rule, pos)` (`_recall`, `memo.py:158-204`).
2. On a **cache miss**, write a **poison** entry `Poison(recursion_info=None)` into the cache
   at this position, push `rule_id` on `invocation_stack`, and run the rule
   (`memo.py:111-118`). The poison is the left-recursion sentinel: an in-progress marker.
3. If, while running, the rule **re-enters itself at the same position**, the recall finds the
   poison (`memo.py:96-106`) and calls `_setup_recursion` (`memo.py:206-226`), which records
   the cycle **head** (`rule_id`) and the **involved** rules (everything on the stack between
   the re-entry and the head). It then **returns `None`** at the recursion point so a *different*
   alternative can produce a non-recursive **seed parse** (`memo.py:104-106`).
4. After the initial call returns, if recursion was detected (`poison.recursion_info is not
   None`, `memo.py:132,143-144`) and the seed parse succeeded, `_grow_seed` runs
   (`memo.py:151-156`).
5. **`_grow_seed`** (`memo.py:228-257`): repeatedly re-runs the head rule at `start_pos` with a
   **cache bypass** for involved rules (`_recall`'s `eval_set` logic, `memo.py:193-204`),
   keeping each longer result, **until the parse stops advancing** (`new_pos <= memo.final_pos`,
   `memo.py:248`). The longest result wins.

`RecursionInfo` (`memo.py:27-41`) = head `rule_id`, `involved` set, and `eval_set` (rules still
due for a cache bypass this growth cycle). `_recursions` is keyed by **position**
(`memo.py:80`), so independent recursions at different offsets don't interfere.

### 1.3 Scope and what's actually exercised
- **Direct left recursion**: `expr := lhs:expr . "+" . rhs:atom | atom:atom`
  (`rust_parser_fixture.fltkg:30-32`).
- **Indirect / mutual left recursion**: `lval := inner:rval . "!" | base:name ;`
  `rval := inner:lval . "?" | base:num ;` (`rust_parser_fixture.fltkg:34-37`).
- **Left recursion through a sub-expression** (the inline-to-parent path):
  `rec_via_sub := (inner:rec_via_sub . "+" | inner:atom) . suffix:name ;`
  (`rust_parser_fixture.fltkg:63-66`).
- **Growth that descends into nesting**: `nest_sum := lhs:nest_sum . "+" . rhs:nest |
  first:nest ;` (`rust_parser_fixture.fltkg:68-73`) — pins the case where a growth iteration
  is depth-rejected and `grow_seed` returns the seed.
- The toolchain self-hosts on a left-recursive grammar — `fegen.fltkg`'s
  `alternatives`/`items` and several CST rules go through the same memoizer; the bootstrap and
  fltk parsers all use `Packrat.apply`.

### 1.4 Caveats and precise behavior (must-know for authors)
- **Associativity / shape**: direct left recursion produces **left-associative** nesting.
  `expr := expr "+" | "x"` on input `x+` yields `expr(left=expr("x"), "+")`, NOT a flattened
  node — pinned by `test_regression_recursive_inlining.py:35-178`. Each growth iteration wraps
  the previous result as the left child.
- **A non-recursive alternative is mandatory for any left-recursive rule.** Seed growing needs
  a base case: if the recursion point returns `None` (`memo.py:104-106`) and *no* alternative
  yields a seed, the result is `None` (`memo.py:147-149` "Did not find a seed parse"). A rule
  that is left-recursive in *every* alternative simply fails to parse.
- **Alternative ordering still matters under recursion**: the seed comes from the first
  alternative that succeeds without recursing; growth then re-tries from the top each cycle.
- **One untested corner case is deliberately a hard error**, not silent behavior: `_recall`
  raises `NotImplementedError("Untested corner case...")` for a path the author could not
  construct a test for (`memo.py:181-187`). The Rust port `panic!`s in the same spot
  (`memo.rs:225-228`). Grammars that somehow reach it abort rather than misparse.
- **Memo cache is per-parse-instance** and never invalidated mid-parse except by the growth
  bypass; a `Rule`/`Items` object's `_can_be_nil` memo is **per-object and grammar-dependent**
  — reusing GSM objects across grammars returns stale values (`gsm.py:30-43, 86-89`). Normal
  pipeline use is safe because `classify_trivia_rules` rebuilds rules via
  `dataclasses.replace` (`gsm.py:35-36, 366`).

### 1.5 Recursion-depth limits — backend divergence (LIMITATION)
- **Rust backend has a configurable depth guard**; **Python backend does not.**
  - Rust: `DEFAULT_MAX_DEPTH = 1000` (`memo.rs:74`); `apply` checks `depth >= max_depth`,
    sets a **sticky** `depth_exceeded` flag, and returns `None` (`memo.rs:190-201`). Callers
    **must** check `depth_exceeded()` after parsing and discard the result if set
    (`memo.rs:104-106, 158-161`; generated header `parser.rs:1-11`). Python bindings raise
    `RecursionError`. The default is sized for ~8 MiB stack / ~5-7 frames per rule; smaller
    thread stacks require lowering it (`parser.rs:4-11`).
  - Python: `Packrat` has **no `max_depth` / no `depth_exceeded`** (`memo.py:77-80`). Deep or
    right-recursive input is bounded only by CPython's own recursion limit / native stack,
    raising `RecursionError` (or crashing) rather than returning a clean failure. This is a
    real cross-backend behavioral difference for pathological inputs.

---

## 2. ALTERNATION ORDERING, PRECEDENCE, ASSOCIATIVITY, MATCH RESOLUTION

### 2.1 First-match (ordered choice), NOT longest-match
Alternation is **PEG-style ordered choice**: `gen_alternatives_parser` tries each alternative
in source order and **returns the first that succeeds** (`gsm2parser.py:718-732`): a chain of
`if self.<alt_i>(pos): return Success(...)`, falling through to `Failure`. Worked example:
`parse_grammar` returns `alt0` or `None` (`fltk_parser.py:98-101`).

Consequences for authors:
- **Order your alternatives most-specific-first.** A shorter/earlier alternative that succeeds
  shadows a longer later one even if the later would consume more — there is **no longest-match
  arbitration** among top-level alternatives.
- There is **no backtracking *across* a committed alternative** once it returns success at the
  rule boundary (the memo caches it). Within an alternative, a later item's failure causes the
  whole alternative to fail (early `return Failure`, `gsm2parser.py:816-818`) and the next
  alternative is tried — so backtracking is *between* alternatives, not a global search.

### 2.2 No precedence/associativity operators
FLTK has **no precedence or associativity declarations** in the grammar language. The four
term kinds (`fegen.fltkg:13`) and the disposition/quantifier/separator glyphs are the entire
operator set; there is no `%left`/`%right`/precedence-level construct anywhere in the GSM
(`gsm.py`) or generators. Precedence must be encoded structurally — via stratified rules
(`expr`/`term`/`factor` layering) and/or left recursion (§1.4) for associativity. Direct left
recursion gives left-associativity; right-associativity is expressed by right-recursion (which
does **not** use the seed-grower — it's ordinary recursive descent and is the case bounded by
the depth guard in §1.5).

### 2.3 Quantifier matching is greedy with a progress guard
`+`/`*` loops consume **greedily** with no backtracking of the count: `gen_item_parser_multiple`
emits `while (one_result := consume(...)): ...` (`gsm2parser.py:505-618`). There is no attempt
to give back matched repetitions to satisfy a following item. Two guards:
- **Per-iteration progress guard**: breaks the loop if a match did not advance position
  (`one_result.pos > pos` is false → `break`, `gsm2parser.py:570-577`; worked example
  `fltk_parser.py:135-136`). Uses `<=` so a position regression also breaks.
- **`+` minimum guard**: after the loop, `+` fails if position never advanced
  (`gsm2parser.py:595-599`; worked example `fltk_parser.py:139-140`).

---

## 3. PACKRAT / MEMOIZATION / BACKTRACKING / CUT

### 3.1 Memoization
Every rule gets a per-rule cache `_cache__parse_<rule>: dict[pos, MemoEntry]`
(`gsm2parser.py:464-472`; worked example `fltk_parser.py:35-76`) and a memoized entry method
`apply__parse_<rule>` that delegates to `Packrat.apply` (`gsm2parser.py:441-463`). Sub-rules
created for alternatives/items/sub-expressions are **not** independently memoized — only
top-level rules and the `_trivia` rule get a `rule_id` and cache (`memoize=True` only at
`gsm2parser.py:237-242` for rules and `676-680` for trivia). Alternatives/items are plain
helper methods (`memoize` defaults False, `gsm2parser.py:380-405`), so packrat guarantees hold
at **rule granularity**.

`MemoEntry.result` is a tri-state union `Poison | ResultType | None` (`memo.py:59-62`): poison =
in-progress (left-recursion sentinel), a value = success, `None` = cached failure
(`memo.py:107-109`). Cached failures are reused, so a rule failing at a position is not retried.

### 3.2 Backtracking
Backtracking is **local and position-based**: positions are plain ints passed by value; a
failed alternative/optional item simply doesn't advance `pos`, and the next alternative starts
from the original `pos`. There is no global backtracking stack. Optional/`?` and `*` items
that fail are non-fatal: the `if cond: ... else: ...` only returns `Failure` when the item is
**required** (`gsm2parser.py:795-818`; the `orelse=item.quantifier.is_required()` flag and the
guarded `item_if.orelse.return_(Failure)`).

### 3.3 Cut / commit
**There is no cut / commit operator and no PEG `&`/`!` lookahead predicates.** Searching the
GSM and generators shows only the four term kinds; no syntactic predicate or cut term exists.
The only "commitment" is implicit: once a rule's `apply__parse_<rule>` returns a success, it's
memoized and won't be re-derived at that position. Authors cannot prune the search explicitly.

---

## 4. TRIVIA (WHITESPACE / COMMENTS) AND SEPARATOR-DRIVEN CONSUMPTION

### 4.1 Separators drive trivia, exhaustively
Trivia is consumed **only at separator positions**, generated by `_gen_separator_handling`
(`gsm2parser.py:620-697`):

| Glyph | `Separator` | Emitted behavior |
|-------|-------------|------------------|
| `.` | `NO_WS` | **no code emitted** — early `return` (`gsm2parser.py:642-643`). Items must be adjacent. |
| `,` | `WS_ALLOWED` | trivia parsed; absence is OK (`orelse=False`). Worked example: the unconditional `if ws := apply__parse__trivia(pos): pos = ws.pos` blocks throughout `fltk_parser.py`. |
| `:` | `WS_REQUIRED` | trivia parsed; **absence is a parse failure** — `orelse=(separator == WS_REQUIRED)` then `sep_if.orelse.return_(Failure)` (`gsm2parser.py:684, 696-697`). |

Separators appear at three slots per `Items`: `initial_sep` (before first item,
`gsm2parser.py:767-776`), `sep_after[i]` (after each item, `gsm2parser.py:820-829`). A missing
trailing separator defaults to `NO_WS` (`fltk2gsm.py:93-102`).

### 4.2 The `_trivia` rule and recursion avoidance
- **Reserved name** `_trivia` (`gsm.py:18`). At non-trivia separator positions the generated
  code calls the memoized `apply__parse__trivia` (`gsm2parser.py:674-685`).
- **Inside a trivia rule** the generator does NOT recurse into `_trivia`; it falls back to a raw
  `re` pattern `\s+` (`gsm2parser.py:655-665`), since a trivia rule consuming trivia would loop.
- **Auto-injection**: a grammar with no `_trivia` gets a built-in `Item(label="content",
  Regex(r"[\s]+"), REQUIRED)` (`gsm.py:477-504`).

### 4.3 Invariants enforced on trivia (HARD CONSTRAINTS)
- **Non-nil**: `_trivia` must not match empty (`validate_trivia_rule_not_nil`,
  `gsm.py:406-415`). This is what makes `WS_REQUIRED` (`:`) meaningful — a nilable trivia rule
  would make `:` vacuously satisfiable. `Separator.WS_REQUIRED.can_be_nil()` returns `False`
  precisely because trivia can't be nil (`gsm.py:77-78`).
- **Separation**: a **non-trivia rule may not reference a trivia rule by name**
  (`validate_trivia_separation`, `gsm.py:456-474`). Trivia is reachable only via separators,
  never as a term. Trivia-ness is computed by reachability from `_trivia`
  (`classify_trivia_rules` / `_mark_trivia_reachable`, `gsm.py:348-403`), so e.g.
  `line_comment` and `block_comment` become trivia rules transitively and likewise cannot be
  named by ordinary rules.

### 4.4 Trivia capture (optional, off by default)
When `context.capture_trivia` is set, consumed trivia is appended as an **unlabeled `Span`
child** of the enclosing node (`gsm2parser.py:666-673, 688-694`); otherwise it is discarded.
A rule that has any whitespace separator gains a `_trivia` (or `Span`, in trivia rules) member
in its CST model (`gsm2tree.py:1019-1023`) — but children only materialize when capture is on.

---

## 5. DISPOSITIONS (`%` / `$` / `!`) — DEPTH, AND WHAT IS NOT SUPPORTED

### 5.1 The three dispositions and CST effect
`Disposition.{SUPPRESS, INCLUDE, INLINE}` (`gsm.py:194-197`). Defaulting in `visit_item`
(`fltk2gsm.py:117-122`): labeled item OR sub-expression term → `INCLUDE`; else → `SUPPRESS`.

CST-model effect (`gsm2tree.py:625-643`, `model_for_items`):
- **`%` SUPPRESS** (`gsm2tree.py:628-630`): term parsed, **no child** contributed. Asserts the
  term is **not** a sub-expression (`assert not isinstance(item.term, Sequence)`). Parser:
  `if item.disposition != SUPPRESS:` gates the append (`gsm2parser.py:802`), so a `%` item
  advances `pos` but appends nothing → **span gap**.
- **`$` INCLUDE**: contributes a child — the rule's node for identifiers, or a `Span` for
  literal/regex (`gsm2tree.py:618-619`). An unlabeled `$`-literal is an **unlabeled `Span`
  child** (`rust_parser_fixture.fltkg:48`, `tagged := $"tag" . value:/[a-z]+/`).
- **`!` INLINE** (`gsm2tree.py:631-636`): asserts term is a bare `Identifier`; the referenced
  rule's model is **spliced** (`incorporate`) into the parent rather than nested. Cycle
  detection via `inline_stack` (`gsm2tree.py:1008-1012`, `model_for_rule`).

### 5.2 LIMITATION — INLINE disposition (`!`) is NOT implemented in either parser generator
This is a **major constraint** the surface doc understates. While the **CST/tree generator**
(`gsm2tree.py`) models INLINE, **both parser generators reject it**:
- Python: `gen_alternative_parser` raises `NotImplementedError("Inline items not yet
  supported")` for any `item.disposition == INLINE` (`gsm2parser.py:782-784`).
- Rust: `NotImplementedError("INLINE disposition is not supported in Rust parser generation")`
  (`gsm2parser_rs.py:824-826` and `1010-1012`).

So **`!rule` cannot appear in any grammar that is actually compiled to a parser.** The only
uses of `!` are in `fltk.fltkg` (`:11`, `:34`), which the file itself declares "actually broken
and was never completed" (`fltk.fltkg:2`) — it is not in the live pipeline. The live
`fegen.fltkg`/`bootstrap.fltkg` define `inline:"!"` in the `disposition` rule (so the *syntax*
parses) but never *use* `!` on any item. **Bottom line: `!` is syntactically accepted but
semantically unsupported by the parser backends.**

### 5.3 Do not confuse INLINE disposition with "inline_to_parent" (sub-expressions)
There is a separate, fully-working "splice into parent" mechanism: **sub-expression terms**
(`(...)`) set `inline_to_parent=True` (`gsm2parser.py:355-372`) and their children are merged
via `extend_children` (`gsm2parser.py:803-806`, `582-587`). This is automatic for parenthesized
groups and is unrelated to the `!` disposition. The `+`/`*` multiple path also uses
`extend_children` when the repeated term is a sub-expression (`gsm2parser.py:582-587`).

### 5.4 LIMITATION — Invocation / Expression / Var terms are dead
`gsm.Invocation`, `Expression`, `Add`, `Var` (`gsm.py:267-288`) exist in the GSM `Term` union
(`gsm.py:175-181`) but:
- The **live grammar `fegen.fltkg` never produces them** (`fltk2gsm.visit_term` only yields
  identifier/literal/regex/sub-expression, `fltk2gsm.py:130-140`).
- The **Python parser generator** has no branch for them — `_gen_consume_term_expr` raises
  `NotImplementedError` on any unrecognized term (`gsm2parser.py:374-375`).
- The **Rust parser generator explicitly rejects Invocation**: `NotImplementedError("Invocation
  terms are not supported in Rust parser generation")` (`gsm2parser_rs.py:768-770`).

These are vestigial from the aspirational `fltk.fltkg` and are unreachable from any working
pipeline.

### 5.5 Other hard constraints around dispositions/labels/names
- **Underscore-only rule names and labels are rejected** (`validate_no_underscore_only_names`,
  `gsm.py:323-345`; label variant `gsm.py:305-320`) because `snake_to_upper_camel` would derive
  `""`. `_foo`-style names are fine (that's why `_trivia` is legal).
- **No repeated nilable item**: a `+`/`*` item whose term can match empty is rejected
  (`validate_no_repeated_nil_items`, `gsm.py:418-453`), recursively into sub-expressions, to
  prevent infinite loops. The regex-emptiness test is an **under-approximation** for
  context-sensitive patterns (`\ba*`, `(?=x)` test False vs `""` but can match zero-width on
  real input, `gsm.py:438-444`), so both backends keep the **runtime progress guard** (§2.3) as
  defense-in-depth.
- **Unknown rule reference** (an identifier term naming a non-existent rule) is a hard error at
  CST-model build time (`gsm2tree.py:614-616`) and at parser build time (`_gen_consume_term_expr`
  indexes `self.parsers[(term.value,)]`, `gsm2parser.py:310-311`, KeyError if absent).
- **A node model must have ≥1 included member**: a rule whose every item is suppressed (and has
  no sub-expression/label) yields an empty model and is rejected with
  `"Model class ... would have no members"` (`gsm2tree.py:251-256`).

---

## 6. REGEX TERM HANDLING — `re` (Python) vs `regex-automata` (Rust)

### 6.1 Storage and emptiness analysis
A `/.../` term stores its inner text **verbatim** as `gsm.Regex.value` (`fltk2gsm.py:168-170`).
Nilability uses Python `re`: `re.compile(value).match("") is not None` (`gsm.py:165-169`); an
invalid regex conservatively returns `False` (`gsm.py:170-172`).

### 6.2 Python backend matching
`TerminalSource.consume_regex` compiles **on every call** with Python `re` and **anchors at
`pos`** via `re.compile(regex).match(self.terminals, pos=pos)` (`terminalsrc.py:177-181`).
`re.match` with `pos=` anchors the start but **still sees the full string** before `pos`, so
`\b`/`\B`/lookbehind resolve against preceding context. (`gsm2parser.py:340-341` has a
`TODO pre-compile regexes` — currently not precompiled in the Python runtime.)

### 6.3 Rust backend matching and the ENGINE BOUNDARY (key limitation)
- Rust uses **`regex_automata::meta::Regex`** (`terminalsrc.rs:8`,
  `crates/fltk-parser-core/Cargo.toml:17-27`), re-exported from `fltk-parser-core` so generated
  code and runtime share one version (`crates/fltk-parser-core/src/lib.rs:20-23`).
- Patterns are **compiled once** into `OnceLock` cells, lazily (`parser.rs:25-33`).
- `consume_regex` does an **anchored search over the full haystack** with the search span
  starting at the byte offset for `pos` (`terminalsrc.rs:141-166`), specifically to preserve
  `\b`/`\B` context-before-pos parity with Python's `re.match(..., pos=)`
  (`terminalsrc.rs:131-140`; pinned by `consume_regex_context_before_pos`,
  `consume_regex_word_boundary_reject_mid_word_via_context`, `terminalsrc.rs:368-389`).
- **REGEX SUBSET RESTRICTION (hard limitation):** grammar regexes must use the **common subset
  of Python `re` and `regex-syntax`**. **Lookahead, lookbehind, and backreferences are NOT
  supported** — `regex_automata::meta::Regex` rejects them at compile time
  (`gsm2parser_rs.py:6-15`). This is a permanent default per ADR
  `docs/adr/2026/06/10-rust-parser-codegen/README.md` §Regex subset.
- **Enforcement**: every generated Rust parser emits `#[test] fn all_regex_patterns_compile`
  (the panic message at `gsm2parser_rs.py:990` / `parser.rs:1346-1347`:
  `"grammar regex {pat:?} is not supported by regex_automata::meta::Regex: {e}"`). An
  unsupported pattern fails `cargo test`, naming the offender. There is an open
  `regex-portability-lint` task (TODO/tracking item) to lint this earlier than test time.
- **Author consequence**: a grammar regex using `(?=...)`, `(?<=...)`, or `\1` will compile and
  run on the **Python** backend but **fail to build on the Rust** backend. For cross-backend
  drop-in compatibility, restrict regexes to the common subset.

### 6.4 Codepoint indexing (both backends)
Span offsets are **codepoint-indexed, not byte-indexed**. Python operates on `str` directly
(`terminalsrc.py`). Rust builds a `cp_to_byte` table at construction and converts match-end byte
offsets back to codepoint indices via binary search (`terminalsrc.rs:43-44, 60-68, 156-165`).
Multibyte literals/regexes are pinned by `rust_parser_fixture.fltkg:39-45` (`arrow := %"→"`,
`latin_word := /[À-ÿ]+/`).

### 6.5 Negative / out-of-range position divergence
Python `consume_literal`/`consume_regex` rely on Python slice/`re` semantics. Rust **explicitly
rejects `pos < 0`** (returns `None`, deliberate divergence — negative positions are unreachable
from generated code, `terminalsrc.rs:33-37, 110-113, 141-144`). Both accept `pos == len` (empty
match at end-of-input, `terminalsrc.rs:139, 359-366`).

---

## 7. CST CONSTRUCTION — SPANS, GAPS, LABELED ACCESSORS, NODE IDENTITY

### 7.1 Node shape
Each rule → one `@dataclass` (`gsm2tree.py:237`) with three fields (`gsm2tree.py:262-277`):
- `kind: Literal[NodeKind.X] = NodeKind.X` — discriminant, default = own member.
- `span: terminalsrc.Span | fltk._native.Span = UnknownSpan` — codepoint-indexed source range.
- `children: list[tuple[Optional[Label], child]] = field(default_factory=list)` — ordered,
  each tagged with its label or `None`.

### 7.2 Span construction and merging
- Spans are built with `Span.with_source(start, end, source)` (`gsm2parser.py:254-276`,
  `terminalsrc.py:130-149`).
- An alternative/item parser initializes its result node with a **sentinel end of `-1`** and
  overwrites `span` at the end with `(_span_start, final_pos)` (`gsm2parser.py:745-763,
  832-838`; worked example `fltk_parser.py:113-124`). `_span_start` is captured **before** any
  mutation, deliberately so the span start isn't read back off the result (the Rust backend
  can't read `result.span.start`, `gsm2parser.py:535-536, 743-744`).
- `Span.merge` = smallest covering span; `Span.intersect` = overlap or `UnknownSpan` if disjoint
  (`terminalsrc.py:109-128`). `UnknownSpan = Span(-1, -1)` (`terminalsrc.py:152`).
- `Span` equality **ignores `_source` and `kind`** (`compare=False`, `terminalsrc.py:54-55`),
  so cross-backend and sourceless/source-bearing spans compare by `(start, end)` only.

### 7.3 Gaps from suppression
`%`-suppressed terms **advance position but append no child** (§5.1). The parent node's span
still covers the suppressed text (span = `[start, end)` over the whole match), but **no child
entry exists for the suppressed span** — so the union of child spans can be a strict subset of
the parent span, i.e. **suppression creates gaps in child coverage**. Whitespace consumed at
separators is likewise gap-producing unless `capture_trivia` is on (§4.4).

### 7.4 Labeled accessors (the quintet) and cardinality
For each label, `_emit_label_quintet` (`gsm2tree.py:820-867`) emits:
`append_<l>`, `extend_<l>`, `children_<l>() -> Iterator`, `child_<l>() -> T` (raises unless
exactly one, `gsm2tree.py:345-357`), `maybe_<l>() -> Optional[T]` (raises if >1,
`gsm2tree.py:358-370`). Plus generic `append`/`extend`/`extend_children`/`child` and strict
mutators `insert`/`remove_at`/`replace_at`/`clear` (`gsm2tree.py:283-326, 386-610`).

- **Label defaulting**: a bare rule-reference term auto-labels with the rule's own name
  (`fltk2gsm.py:113-116`). So `atom := num:num | name:name` and `expr := term, ...` get labels
  without writing them.
- **Union labels**: one label mapping to multiple types widens the accessor return annotation to
  `typing.Union[...]` (`gsm2tree.py:91-93, 640-642`; pinned by
  `rust_parser_fixture.fltkg:53`, `val := item:num | item:name | item:/[!@#$]+/`). The
  `children_<l>` body inserts a `typing.cast` when multi-type (`gsm2tree.py:338`).
- **Quantifier ↔ accessor**: `+`/`*` naturally yield multiple same-label children; authors pick
  `children_<l>()` (iterator), `child_<l>()` (exactly one), or `maybe_<l>()` (0-or-1) to assert
  the expected cardinality. The generator does **not** restrict which accessor you may call —
  cardinality is enforced at call time, not generation time.

### 7.5 Mutator strictness and cross-backend parity (constraints)
- `insert`/`replace_at` validate **child type then label type then index**, matching the Rust
  order (`gsm2tree.py:531-603`). `_check_child_type_for_mutators` rejects unknown child classes
  with `TypeError` (`gsm2tree.py:447-493`); native `Span` is admitted **lazily** so the module
  stays pure-Python-importable (`gsm2tree.py:436-469`).
- `_check_label_type_for_mutators`: label-free nodes reject any non-`None` label
  (`gsm2tree.py:515-529`); labeled nodes require `None` or the node's own `Label` enum.
- `insert` **clamps** out-of-range indices (matching `list.insert` and Rust);
  `remove_at`/`replace_at` raise `IndexError` out of range (`gsm2tree.py:558-603`).
- `append`/`extend` are **grandfathered un-strict** (no type check) for backward compat
  (`gsm2tree.py:283-297`); only the newer named mutators are strict (`gsm2tree.py:395-396`).

### 7.6 Node identity / cross-backend equality (drop-in contract)
- `NodeKind` and per-node `Label` enums carry a cross-backend `__eq__`/`__hash__` keyed on a
  plain string `_fltk_canonical_name` (e.g. `"NodeKind.LINECOMMENT"`, `"Items.Label.NO_WS"`)
  set post-class (`gsm2tree.py:99-156, 158-169`). Same-type comparisons use member name;
  cross-type comparisons compare canonical names; foreign operands return `NotImplemented`
  (`gsm2tree.py:117-126`). So Python-backend and Rust-backend members **compare equal across
  backends** — the load-bearing piece of the "drop-in replacement" promise. `SpanKind.SPAN`
  has the same bridge (`terminalsrc.py:24-45`).
- The parallel `*_cst_protocol.py` module (`gsm2tree.py:721-1006`) mirrors the concrete surface
  with `typing.Protocol` classes and a runtime `NodeKind` + `_ProtocolLabelMember` sentinels,
  for structural typing across backends without importing a concrete backend at load
  (`gsm2tree.py:692-755`).
- **Public-API naming**: node class = `snake_to_upper_camel(rule_name)` (no `Node` suffix);
  accessor names derive from labels. Per `CLAUDE.md`, these are public API for out-of-tree
  consumers — renames are breaking.

---

## 8. ERROR REPORTING (author/runtime behavior)

`ErrorTracker` (`errors.py:24-49`) records the **furthest position reached** and the set of
expected literals/regexes there. On failure at a literal/regex, `consume_literal`/`consume_regex`
call `fail_literal`/`fail_regex` with the **current rule id** (top of `invocation_stack`,
`gsm2parser.py:171-180, 220-229`; worked example `fltk_parser.py:85, 95`). `format_error_message`
(`errors.py:126-152`) renders `Syntax error at line L col C`, the offending line with a caret,
and the expected tokens grouped by rule. Control/bidi/zero-width chars in the echoed line are
escaped (`escape_control_chars`, `errors.py:96-123`) — byte-identical to the Rust port
(`crates/fltk-cst-core/src/escape.rs`).

---

## 9. CONSTRAINTS & LIMITATIONS — QUICK REFERENCE

| Topic | Status / Constraint | Code |
|-------|---------------------|------|
| Left recursion (direct/indirect) | **Supported** via packrat seed-growing, automatic, all rules | `memo.py:82-257`; `rust_parser_fixture.fltkg:30-37` |
| Left-recursive rule needs base case | **Required** — no seed ⇒ fail | `memo.py:104-106, 147-149` |
| Associativity of direct LR | **Left-associative** nesting | `test_regression_recursive_inlining.py:35-178` |
| Precedence/associativity operators | **None** — encode structurally | (absent from `gsm.py`/generators) |
| Alternation | **Ordered first-match (PEG)**, no longest-match | `gsm2parser.py:718-732` |
| Quantifier matching | **Greedy**, no give-back; progress guard | `gsm2parser.py:555-599` |
| Cut / commit / lookahead predicates | **None** | (absent) |
| Memoization granularity | **Per top-level rule + `_trivia`** | `gsm2parser.py:237-242, 676-680` |
| Recursion-depth limit | **Rust: `max_depth=1000`, sticky flag; Python: none** | `memo.rs:74,190-201`; `memo.py:77-80` |
| `.` `,` `:` trivia | none / optional / **required (fail if absent)** | `gsm2parser.py:642-697` |
| `_trivia` non-nil | **Enforced** | `gsm.py:406-415` |
| Non-trivia → trivia reference | **Forbidden** | `gsm.py:456-474` |
| `%` on sub-expression | **Forbidden** (assert) | `gsm2tree.py:629` |
| `!` INLINE disposition | **NOT implemented in either parser backend** (syntax-only) | `gsm2parser.py:782-784`; `gsm2parser_rs.py:824-826,1010-1012` |
| Invocation/Expression/Var terms | **Dead / unsupported** | `gsm2parser.py:374-375`; `gsm2parser_rs.py:768-770` |
| Repeated nilable item (`+`/`*`) | **Rejected** (under-approx + runtime guard) | `gsm.py:418-453` |
| Underscore-only name/label | **Rejected** | `gsm.py:305-345` |
| All-suppressed node (empty model) | **Rejected** | `gsm2tree.py:251-256` |
| Unknown rule reference | **Hard error** | `gsm2tree.py:614-616`; `gsm2parser.py:310-311` |
| Regex lookahead/lookbehind/backref | **Python OK; Rust REJECTS at compile/test** | `gsm2parser_rs.py:6-15, 990`; `terminalsrc.py:177-181`; `terminalsrc.rs:141-166` |
| Span offsets | **Codepoint-indexed**, both backends | `terminalsrc.rs:43-44,156-165` |
| Suppression / uncaptured trivia | **Creates gaps** in child coverage | §7.3 |
| Cross-backend enum equality | **Canonical-name-keyed eq/hash** | `gsm2tree.py:99-156` |

---

## 10. OPEN FACTUAL QUESTIONS

- `_recall`'s "untested corner case" (`memo.py:181-187`, `memo.rs:225-228`): both backends abort
  rather than execute it; the exact grammar that would reach it is unknown by design.
- Rust `grow_seed` body (below `memo.rs:381`) was confirmed present and stack-pushed at
  `memo.rs:347-352`; a line-by-line parity diff vs `memo.py:228-257` was not transcribed here
  (the apply/recall/setup paths were verified as deliberate ports).
- Whether any downstream out-of-tree grammar relies on Python-only regex features (lookahead
  etc.) that would block its Rust migration — not observable in this repo.
