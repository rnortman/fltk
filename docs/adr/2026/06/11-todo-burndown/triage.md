# TODO Burndown Triage — 2026-06-11

Style: concise, precise, no padding. Audience: someone who has not read the code and doesn't want to. Each item validated against source by an adversarial explorer agent (see `exploration-<slug>.md` in this dir); claims below reflect code ground truth, not the TODO text.

Scope: all of TODO.md except `bazel-rules-rust` (user-excluded) and `example-placeholder` (not a real TODO).

## Summary

| # | Slug | Recommendation |
|---|------|----------------|
| 1 | consume-regex-anchor | **Do** |
| 2 | apply-depth-limit + parser-depth-limit | **Do (merged: one work item)** |
| 3 | nullable-loop | **Do (expanded: guard + validation fix)** |
| 4 | error-msg-escape | **Do** |
| 5 | parser-bindings-name-collision | **Do (add NodeKind to reserved list)** |
| 6 | rust-naming-shared | **Do** |
| 7 | rust-cst-accessor-clone-efficiency | **Do (corrected fix shape)** |
| 8 | rust-cst-debug-depth | **Do** |
| 9 | crosscdylib-abi-check-helper | **Do** |
| 10 | registry-unit-tests | **Do (reframed: Python-side GC/eviction tests)** |
| 11 | rust-str-lit-shared | **Delete** |
| 12 | rust-cst-children-list-view | **Delete** |
| 13 | extend-children-owned | **Delete** |
| 14 | abi-gate-test-consolidation | **Delete** |
| 15 | crosscdylib-abi-size-probe | **Delete** |

"I accept all recommendations" = implement items 1–10 as described in their **Recommendation** lines (merged/reframed versions, not original TODO text), and delete entries 11–15 from TODO.md (plus their code comments).

---

## 1. consume-regex-anchor — **Do**

**ELI5.** When the parser tries to match a regex at position X in your input and it doesn't match there, the Rust regex library doesn't just say "no" — it keeps scanning the *entire rest of the file* looking for a match somewhere later, then we throw that answer away. Python's regex engine stops immediately. So a malicious (or just unlucky) input can make the Rust parser do enormous amounts of pointless work: worst case roughly (number of regex rules) × (input length)². That's a CPU-exhaustion denial-of-service against anyone parsing untrusted input.

**Why it matters.** Untrusted-input parsing is the library's primary use case. This is a real, quadratic complexity DoS, and the Rust backend is supposed to be the *fast* one.

**What the work looks like.** Validated feasible: switch `consume_regex` to `regex_automata::meta::Regex` with an anchored search (`Anchored::Yes`, span starting at the position). The full input string stays visible, so `\b`/`\B` word boundaries still work (the TODO's "look-behind" wording is a misnomer — the `regex` crate has no look-behind; word boundaries are the real concern). There is no fix within the plain `regex` crate (prepending `\A` doesn't work — it anchors to byte 0, not the search start). Cost: add `regex-automata` as a direct dependency (it's already in the tree transitively), change the regex type in the runtime API and in the generated parser's regex table — contained to `fltk-parser-core` + `gsm2parser_rs.py` + regenerated fixtures.

**Case for skipping.** Only exploitable when inputs cause many regex failures; trusted-input users never notice. But that's exactly the wrong bet for a parser library.

**Recommendation: Do.** Use the `regex_automata` anchored approach.

USER DECISION: Do

## 2. apply-depth-limit + parser-depth-limit — **Do, merged into ONE work item**

**ELI5.** The generated parsers are recursive: deeply nested input (e.g. ten thousand nested parentheses) means ten-thousand-deep function calls. Python eventually says "too deep!" and raises a catchable `RecursionError`. Rust doesn't — it blows the stack and **the whole process dies instantly with a segfault**, uncatchably. If your web service parses attacker-supplied input with the Rust backend, the attacker can kill your process with one nested input. Strictly worse than the Python backend.

**Why it matters.** Hard, unrecoverable process-kill DoS on the primary use case. The most severe item in this batch.

**What the work looks like.** The two TODOs *look* like two pieces of work but validation showed they're one: every cross-rule recursive call funnels through a single function (`apply` in `memo.rs`), and the bookkeeping stack there already effectively counts depth. One counter + limit check in the runtime covers everything; the generated-parser side only needs a way to *configure* the limit (a constructor parameter / default constant) and a distinguishable failure when it trips. Helper functions between rule calls add only constant extra frames, so a rule-depth limit (Python-equivalent ~1000) maps safely onto the 8 MiB stack. Caveat surfaced by validation: the existing bookkeeping stack briefly double-counts during left-recursion seed-growing, so a dedicated counter is cleaner than reusing it. Failure surfacing needs a small design decision (plain parse failure vs. a flagged "depth exceeded" error) — the error tracker is the natural place for the flag.

**Case for skipping.** None worth taking. Both backends already document the hazard in generated file headers; documenting a process-kill isn't a fix.

**Recommendation: Do.** One implementation: depth counter + configurable limit in the parser-core runtime, limit exposed via the generated parser's constructor, depth-exceeded surfaced distinguishably. Replaces *both* TODO entries.

USER DECISION: Do

## 3. nullable-loop — **Do (guard + close the validation gap)**

**ELI5.** Grammar rules can say "match this thing repeatedly" (`+`/`*`). The generated loop assumes each match consumes at least one character. If the repeated thing can match *zero* characters, the loop matches nothing, advances nowhere, and spins forever at 100% CPU. There IS a validator that's supposed to reject such grammars — but validation found a hole in it: it checks "can this be empty?" by looking only at the `?` markers on items, ignoring what the items actually *are*. A concrete grammar like `rule := (r"a*" .)+` (a repeated group containing a regex that can match empty) sails through validation and then hangs the parser forever. Both backends (Python and Rust) have the identical bug.

**Why it matters.** A grammar author can write an innocent-looking grammar that passes validation, works in testing, and hangs in production on certain inputs. Infinite loop = unkillable-without-SIGKILL CPU burn.

**What the work looks like.** Two small fixes, both backends in lockstep:
1. Loop guard: break when an iteration makes no progress. Validation pinned the exact placement — the check must come *before* the position update, or it breaks on every iteration (the TODO didn't specify this and the naive reading is wrong). Python's IIR may lack a `break` construct, in which case its guard takes a slightly different form (early exit).
2. Root fix: make the nullability check term-aware (`Item.can_be_nil` currently ignores the item's term entirely), so the validator actually rejects the grammars that trigger this.

**Case for skipping.** No known shipped grammar triggers it. But it's cheap, it's a hang, and the validator hole means "no known grammar" is luck, not safety.

**Recommendation: Do.** Both the lockstep loop guard and the validator gap fix.

USER DECISION: Do: start TDD (failing test first) and do both Python and Rust backends. If we cannot construct a grammar that tricks the current parsers then we should revisit whether this is real or not.

## 4. error-msg-escape — **Do**

**ELI5.** When parsing fails, the error message includes the offending line of input, verbatim. If that input contains terminal control characters (like ANSI escape sequences), and an application prints the parse error to a terminal or log, the attacker's bytes get interpreted by the terminal — they can rewrite what you see on screen, forge log lines, etc. Classic "escape injection."

**Why it matters.** Any downstream app that shows parse errors for untrusted input (very normal behavior) is exposed. Both backends are identical here — by design, since a comparator test asserts Python and Rust error messages match exactly. That's why neither side can be fixed alone.

**What the work looks like.** Validated straightforward: escape C0 control characters (except `\n`/`\t`) in the quoted line, identically in Python and Rust. Surprise from validation: the parity comparator *doesn't need changing* — if both sides escape identically, the byte-equality check still passes. No existing test uses control characters, so nothing else breaks; add new tests with hostile input. There is no in-tree display layer that could own escaping instead — the formatter is the only sensible place.

**Case for skipping.** A purist could argue display-time escaping is the consumer's job. But no consumer is warned, the default is unsafe, and the fix is a few lines in two functions.

**Recommendation: Do.**

USER DECISION: Do

## 5. parser-bindings-name-collision — **Do**

**ELI5.** The Rust backend packs everything into one Python module: your grammar's node classes *plus* fixed classes named `Parser`, `ApplyResult`, `Span`, `SourceText`. If your grammar has a rule named `parser`, its generated node class is also called `Parser` — and the last one registered silently wins. Your node class just vanishes from the module, no error, no warning. You find out at runtime, confusingly.

**Why it matters.** Silent shadowing footgun for every downstream grammar author. (The Python backend is immune — it puts node classes and the parser in separate files.) Nothing fails at generation time or compile time; validation confirmed the Rust code compiles fine because the duplicate names live in different Rust modules.

**What the work looks like.** Tiny: a generation-time check that raises a clear error when a rule's class name collides with a reserved name. Validation found the TODO's reserved list is **incomplete** — `NodeKind` must be on it too (a rule named `node_kind` silently clobbers the NodeKind enum). There's already a precedent mechanism (`_RESERVED_LABELS` in the CST generator's constructor) to extend.

**Case for skipping.** No shipped grammar collides. But this is ten lines of validation that turns a silent runtime mystery into an immediate, clear error.

**Recommendation: Do**, with the reserved set {`Parser`, `ApplyResult`, `Span`, `SourceText`, `NodeKind`}.

USER DECISION: Reframe: The core problem here is that we shoved everything in one module. That is a design mistake. We should mimic the Python backend: separate parser and cst modules. Redesign/refactor and this problem goes away.

## 6. rust-naming-shared — **Do**

**ELI5.** Two code generators (one emits the parser, one emits the node classes) must agree on generated Rust type names like `GrammarChild`. Today that naming rule is written out independently in **four places** (validation found one more than the TODO claimed: three inline copies in the tree generator plus one method in the parser generator). If someone changes one copy, the generated parser references types that don't exist — and you only find out when the generated Rust fails to compile, far from the actual mistake.

**Why it matters.** Drift footgun between generators. The failure is confusing and far removed from the cause.

**What the work looks like.** Easier than the TODO implies: the parser generator *already* holds a reference to the CST generator and already delegates other naming through it — zero new coupling. Add one `child_enum_name()` method on `RustCstGenerator`, point all four sites at it.

**Case for skipping.** It's pure refactoring with no user-visible change. But it's small, reduces code, and removes a real drift trap.

**Recommendation: Do.**

USER DECISION: Do (after or as part of parser-bindings-name-collision refactoring)

## 7. rust-cst-accessor-clone-efficiency — **Do (with corrected fix shape)**

**ELI5.** When Python code asks a node "give me your children labeled `name`," the Rust side currently copies the *entire* children list (bumping a reference count per child) and then filters out the few it wanted. Wasted work proportional to total children on every accessor call.

**Why it matters.** Pure waste on a hot read path. Not a correctness issue — an efficiency cleanup that makes accessors O(matching) instead of O(all).

**What the work looks like.** The TODO calls the fix "mechanical: filter inside the read guard." Validation found that's **wrong as stated** for most of the accessors: converting children to Python objects inside the lock would violate a deliberate, documented invariant (never do Python work while holding a node lock — risk of deadlock/poisoning). The correct shape: filter and clone *only the matching entries* under the lock, release the lock, then convert to Python objects outside. For the single-child `child()` accessor the simple version is fine. It's a contained template edit in one generator file + regeneration.

**Case for skipping.** Nobody has profiled this as a bottleneck. But it's a small, safe, strictly-better change with no API impact.

**Recommendation: Do**, using the corrected (filter-under-guard, convert-outside) shape.

USER DECISION: Do (but see the native children list item below also for possible interactions)

## 8. rust-cst-debug-depth — **Do**

**ELI5.** Generated Rust node types get an auto-derived debug-printer (`{:?}`). It prints a node by recursively printing all its children, all the way down, with no depth limit. If a downstream Rust app debug-logs a tree parsed from attacker-controlled input, a deeply nested input makes the *printer* blow the stack — process dies instantly, uncatchable. Same severity class as item 2, but triggered by logging instead of parsing.

**Why it matters.** `{:?}` is the most natural thing for any Rust developer to do (it's in every `assert_eq!` failure message, every `dbg!`). Once item 2 lands, parse-time depth is bounded — but the limit is configurable, and the Debug recursion uses fresh stack at print time, so it's not automatically safe.

**What the work looks like.** Replace `derive(Debug)` with a generated manual implementation that prints span + child count instead of recursing (the existing Python-facing `__repr__` already does exactly this and is the model). Only in-tree users of `{:?}` on nodes are three smoke tests in the spike crate; update those. Note for out-of-tree consumers: Debug output format changes, but Rust convention treats Debug output as unstable, so this is not an API break.

**Case for skipping.** The alternative in the TODO — "just document the hazard" — is cheaper. And if item 2's default limit is conservative, real exposure shrinks. But a non-recursive Debug is small, removes the hazard class entirely, and arguably prints *more useful* output for big trees.

**Recommendation: Do** (manual depth-capped/non-recursive Debug).

USER DECISION: Do

## 9. crosscdylib-abi-check-helper — **Do**

**ELI5.** Two functions in the cross-library safety layer (the code that lets two separately compiled Rust extensions safely hand each other objects) perform the same two-step safety check — "is your ABI marker string right? is your memory layout number right?" — as two hand-written copies. Validation confirmed the copies have drifted: five of the error messages differ in wording between them, and one copy quietly skips a case the other reports specifically (a missing marker falls through to a generic, less helpful error).

**Why it matters.** This is *the* safety-critical gate before an `unsafe` memory reinterpretation. Two divergent copies of a safety check is exactly where a future edit fixes one and forgets the other. Consolidation here is security-primitive hygiene, not cosmetics.

**What the work looks like.** Extract one generic helper (verified feasible — the only things that vary are the type and a label string), call it from both sites. ~40 duplicated lines become one helper + two one-line calls. One deliberate decision included: the missing-marker case in one path changes from a generic "expected SourceText, got X" error to a specific "no ABI marker" error — a strictly more informative message, but it is a user-visible error-text change and should be called out, not slipped in. Note: the two call sites keep their different caching strategies (one checks once per process, the other per unknown type); the helper unifies the check logic only.

**Case for skipping.** Pure internal refactor, no behavior bug today. If you're touchy about error-message text changes, skip.

**Recommendation: Do**, with the missing-marker message change made deliberately.

USER DECISION: Do

## 10. registry-unit-tests — **Do, reframed**

**ELI5.** There's a Rust-side registry that guarantees "one Python object per underlying node" (so `node is node` works). It has no direct Rust tests; the TODO says Rust tests are blocked by a build/linking problem and lists three elaborate workarounds. Validation found: (a) the "blocker" is mostly just a missing dev symlink on this machine, not architectural; (b) but Rust unit tests are the wrong goal anyway, because every function in the registry requires a live Python interpreter — Python-side tests ARE the natural harness; (c) the *actual* coverage hole is specific and scary: nobody tests what happens when Python's garbage collector evicts a registry entry and a new node reappears at the same memory address (the "ABA" scenario the registry's own comments claim to handle). A `snapshot()` test helper was built for exactly this and is never called.

**Why it matters.** If eviction/ABA handling is subtly wrong, you'd get two Python objects for one node — breaking identity semantics — and current tests can't catch it because the GC never runs at the right moment in them.

**What the work looks like.** Drop the original framing (Rust unit tests + build contortions). Write Python tests that force the scenario: create node handles, drop all references, force `gc.collect()`, verify the registry entry is evicted (via the existing unused `snapshot()` helper), create new nodes, verify no stale-handle resurrection. Plus a test pinning `force_register` overwrite semantics.

**Case for skipping.** Existing identity tests pass and no bug is known. But the one scenario tests can't currently see is the one the registry's safety argument depends on.

**Recommendation: Do the reframed version** — Python-side GC/eviction/ABA tests using `snapshot()`. Rewrite the TODO's framing accordingly (delete the three build-workaround options).

USER DECISION: Do (reframed)

## 11. rust-str-lit-shared — **Delete**

**ELI5.** One generator has a helper that safely escapes strings before embedding them in generated Rust code; the other generator embeds strings raw. The TODO worries a rule name with a quote or backslash in it would produce broken Rust. Validation checked what rule names *can be*: the grammar only allows `[_a-z][_a-z0-9]*` — lowercase letters, digits, underscore — and a constructor validator enforces the same thing even if you bypass the grammar parser. None of the dangerous characters can ever appear. The bug is unreachable.

**Why it matters (it doesn't, much).** The only string that genuinely needs escaping (a free-form source-file path) is already escaped in the one place it's used.

**Case for doing anyway.** If item 6 (rust-naming-shared) is done, sharing the escaping helper into the same module is nearly free, and guards against someone widening the identifier charset someday. But that's insurance against a hypothetical, defended by two existing validation layers.

**Recommendation: Delete.** Unreachable bug; the identifier validators are the real protection. Re-open only if the identifier charset is ever widened.

USER DECISION: Delete

## 12. rust-cst-children-list-view — **Delete**

**ELI5.** On the Python backend, `node.children` hands you the node's *actual* internal list — append to it and you've edited the tree. On the Rust backend you get a *copy* — append to it and nothing happens, silently. The TODO wants to make the Rust one a "live view" so they match. Validation found: the Python behavior was never designed — it's an accident of using plain dataclasses; the codebase has already moved *away* from relying on it (the parser generator was changed to use the proper `extend_children` method, and a test now actively forbids the mutation-through-`children` pattern in generated code); and faking a live list in Rust would require generating a whole extra proxy class per node type, roughly **doubling** the generated Python-class count, with new lock-discipline and equality questions.

**Why it matters.** Drop-in compatibility for out-of-tree consumers is a stated project goal, and an out-of-tree consumer who mutates `node.children` in place would silently break on migration. That's the one real argument for keeping this.

**Case for doing.** Only that compat argument. Against it: the documented mutation API (`append`, `extend_children`, etc.) works identically on both backends; the live-list behavior was an accident, is now test-guarded against internally, and the implementation cost is enormous relative to the exposure.

**Recommendation: Delete**, and add one line to the Rust-backend migration docs: "`node.children` returns a snapshot; mutate via `append`/`extend_children`." (The doc line can ride along with any other docs change; it doesn't justify keeping a tracked work item for the proxy.)

USER DECISION: This seems likely related to rust-cst-accessor-clone-efficiency? We have to either do this or support all operations that an application might need through specific mutators (clear, insert, replace). At that point do we have just as much code as if we'd made the proper proxy container?

## 13. extend-children-owned — **Delete**

**ELI5.** During parsing, child lists get merged from temporary nodes into parent nodes by *copying* (cheap reference-count bumps), even though the temporary is thrown away immediately — it could just *hand over* its list. The TODO proposes adding a "consuming" variant to avoid the copies. Validation confirmed everything: the facts are right, the fix is possible, no hidden blockers. But it also priced it: a couple of atomic operations per child, a few nanoseconds each, estimated well under 5% of parse time — and nobody has profiled to show it matters at all.

**Why it matters (it doesn't, yet).** It's a speculative micro-optimization requiring a new generated API method plus changes in both generators, justified by no measurement.

**Case for doing.** If parse-throughput profiling ever fingers `extend_children`, this is a known, validated remedy — the exploration doc in this dir preserves the full analysis.

**Recommendation: Delete.** Re-open only with profiling evidence.

USER DECISION: Don't do this but don't delete it yet. Leave it in TODO.md.

## 14. abi-gate-test-consolidation — **Delete**

**ELI5.** Five tests (the TODO says three — it's stale) each launch a separate Python subprocess to check that the cross-library ABI safety gate rejects mismatches. The TODO suggests merging them into one subprocess to save startup time. Validation found the merge would only work because of a subtle, undocumented property of a pyo3 internal ("failed initializations aren't cached") that this project doesn't control — if pyo3 ever changed that, the merged test would silently stop testing what it thinks it tests. It would also need careful monkey-patch save/restore and import-order gymnastics. All to save a few subprocess startups in a test suite.

**Why it matters (it doesn't).** Modest test-time savings, paid for with fragility in exactly the tests guarding the most dangerous `unsafe` code in the project.

**Case for doing.** Test suite speed, if it ever becomes a problem. It isn't.

**Recommendation: Delete.** The five isolated subprocesses are the *robust* design, not the wasteful one.

USER DECISION: Delete

## 15. crosscdylib-abi-size-probe — **Delete**

**ELI5.** The cross-library safety gate includes a probe that compares the *size* of a memory layout between two compiled extensions. Same size doesn't strictly prove same layout, so the TODO wants to also bake the exact pyo3 library version into the compatibility string, via a build script. Validation dismantled this: (a) for the actual types involved, a "same size, different layout" situation is essentially impossible to construct — all the layout-relevant pieces are pinned or zero-sized, and the realistic dangerous variations (free-threaded Python, debug tracing builds) *do* change the size and are already caught; (b) one of the two proposed mechanisms (`DEP_*` env vars) flatly doesn't exist — pyo3 doesn't emit the needed metadata, so it would require an upstream pyo3 change; (c) the other (parsing Cargo.lock from a build script) breaks for library consumers who don't ship a lock file and gets ambiguous with multiple pyo3 versions in one workspace.

**Why it matters (it doesn't).** It's hardening against a scenario that can't currently occur, using mechanisms that are respectively nonexistent and fragile.

**Case for doing.** If `SourceText`/`Span` ever gain layout-variable fields (e.g. become non-frozen, add `dict`/`weakref` slots), the residual becomes real. That's a future-conditional, not a work item.

**Recommendation: Delete.** Optionally leave a one-line SAFETY comment noting the analysis (the exploration doc in this dir has the full version).

USER DECISION: Delete

---

## Suggested implementation order (if accepted)

Severity-first, dependency-aware:

1. **apply/parser-depth-limit** (merged) — process-kill DoS, most severe.
2. **consume-regex-anchor** — CPU DoS.
3. **nullable-loop** — hang + validator hole.
4. **error-msg-escape** — escape injection, small.
5. **parser-bindings-name-collision** — small, isolated.
6. **rust-naming-shared** — small refactor.
7. **rust-cst-accessor-clone-efficiency** — generator template edit.
8. **rust-cst-debug-depth** — generator template edit (benefits from #1's limit being settled).
9. **crosscdylib-abi-check-helper** — contained Rust refactor.
10. **registry-unit-tests (reframed)** — test-only.

Deletions (11–15) are a single TODO.md + code-comment cleanup commit.
