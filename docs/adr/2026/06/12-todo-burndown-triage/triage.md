# TODO Burndown Triage — 2026-06-12

Style: concise, precise, no padding. Audience: reader who has not read the code and doesn't want to. Each item validated against source by an independent exploration agent (see `exploration-<slug>.md` in this dir); claims below are grounded in those.

Scope: all TODO.md entries except `bazel-rules-rust` (user-excluded) and `example-placeholder` (not real).

## Summary

| Slug | Recommendation |
|---|---|
| `rust-cst-eq-depth` | **Do** |
| `rust-generated-ident-collisions` | **Do** |
| `regex-automata-features` | **Do** |
| `error-msg-bidi-escape` | **Do (reframed)** |
| `error-msg-escape-zero-copy` | **Delete** |
| `mutator-remove-at-oob-atomicity` | **Delete** |
| `mutator-rs-fast-path-int-index` | **Delete** |
| `extend-children-owned` | **Blocked** (on profiling evidence) |

---

## `rust-cst-eq-depth` — Do

**What the problem is.** When you compare two parse trees with `==` on the Rust backend, the code walks down the tree by calling itself for each level (recursion). A parse tree's depth is controlled by whatever text was parsed — so an attacker (or just a deeply-nested input file) can make the tree thousands of levels deep. Walking that deep blows the call stack, and in Rust that's not an error you can catch: the whole process dies instantly. We already fixed the exact same bug in two sibling code paths (printing a tree, and freeing a tree); equality comparison is the last one left.

**Why it matters.** Any downstream application that calls `assert_eq!` or `==` on a tree built from untrusted input can be killed dead by a crafted input. Uncatchable process abort — the worst failure class. This is the same vulnerability we already considered serious enough to fix twice.

**What the work actually looks like.** Make the generator emit equality code that uses an explicit to-do list (a "worklist") instead of recursion, mirroring the existing fix for tree-freeing. One real complication validation surfaced: freeing walks *one* tree, but equality walks *two trees in lockstep*, so the worklist must hold *pairs* of nodes — the existing worklist type can't be reused as-is. Tests mirror the existing 100,000-deep-tree tests (deep-equal trees compare without crashing). Note: the Python backend has a milder analogue (catchable `RecursionError`, not an abort) — out of scope here.

**The case for skipping.** Only bites consumers who compare deep trees from untrusted input.

**Recommendation: Do.** Real correctness/security bug, clear fix shape, established pattern to follow.

USER DECISION: Do

---

## `rust-generated-ident-collisions` — Do

**What the problem is.** For each grammar rule, the generator invents several Rust names from the rule's name: rule `foo` produces not just `Foo` but also helper types `FooChild`, `FooLabel`, and `PyFoo`. Nothing checks whether *another rule's* name collides with these. If your grammar has both a rule `foo` and a rule `foo_child`, the generator happily emits two different things both named `FooChild`, and the result doesn't compile — you get a cryptic Rust compiler error with no hint that the cause is your grammar's rule names. Validation confirmed all three collision families, plus a fourth the TODO missed: a rule named `drop_worklist_item` collides with an internal generated type.

**Why it matters.** A user with a perfectly legal grammar gets uncompilable generated code and a `cargo` error naming internal Rust identifiers — they have no way to know they should rename a grammar rule. The generator already rejects a fixed list of reserved names with a clear message; this is the same foot-gun, just between rules.

**What the work actually looks like.** At generation time, compute every name the generator will emit for every rule (the formulas are simple and all known), put them in one set, and raise a clear `ValueError` naming the two colliding rules if there's a duplicate. Also add `DropWorklistItem` to the reserved-names list. Pure Python change in the generator + tests with deliberately colliding grammars. No generated-API change, no downstream impact (collisions today don't compile anyway).

**The case for skipping.** Only fires on unluckily-named grammars; no known real grammar hits it.

**Recommendation: Do.** Cheap, contained, turns an opaque compile failure into an actionable error.

USER DECISION: Do

---

## `regex-automata-features` — Do

**What the problem is.** The Rust parser core depends on a regex library, and currently pulls it in with *all* optional features enabled. Two of those features (a heavyweight "compile the regex all the way down to a lookup table" engine) were *not* enabled by the previous dependency setup, are large to compile, and bloat the binary of every downstream project that uses an FLTK-generated parser. Validation confirmed: our code only uses the library's high-level interface, the exact minimal feature list in the TODO is correct, and turning the extra features off changes no behavior — the library transparently falls back to a lazy variant of the same engine with the same match results.

**Why it matters.** Compile time and binary size for every downstream consumer crate, forever, for an engine we never explicitly asked for. The only thing the extra features buy is slightly faster matching for very small patterns, and the lazy fallback warms up to comparable speed on the repeated-use access pattern a parser has.

**What the work actually looks like.** Change one line in `Cargo.toml` to `default-features = false` plus the validated explicit feature list; build and run the test suite. Optionally record before/after binary size in the commit message.

**The case for skipping.** The defaults were kept deliberately at the time, and there's no measurement showing either the cost (size/compile time) or the perf delta matters. If you'd rather not touch it without numbers, keep the TODO.

**Recommendation: Do.** One verified-correct line, behavior-identical, removes dead weight from every consumer build.

USER DECISION: Do

---

## `error-msg-bidi-escape` — Do (reframed)

**What the problem is.** When parsing fails, the error message quotes the offending line of input. We already escape invisible control characters in that quote so a malicious input can't, e.g., inject terminal commands into your logs. But the escaping stops partway through the Unicode range: right-to-left override characters (which visually *reorder* text on screen), invisible line separators (which can split one log line into two), and zero-width characters all pass through untouched. An attacker who controls the parsed text can make the quoted error line *display* as something other than what it is, or forge log entries.

Validation also found something worse than the TODO knew: there are **three** separate copies of this escaping function (Rust parser core, Python runtime, and a third private copy in the Rust CST bridge), and the third one already disagrees with the other two — it escapes TAB when the others don't, mangles certain characters into double escapes, and carries a comment that describes behavior the code doesn't have.

**Why it matters.** Log forging and visual spoofing of error output is the same asset class as the ESC-injection hole we already closed — lower severity (no code execution), but the same "attacker text reaches your terminal/logs unsanitized" story. Separately, three drifting copies of a security-relevant function is exactly how the next escaping bug ships in one backend but not the others.

**What the work actually looks like.** Reframed, two parts: **(a)** Fix the third, divergent copy in the CST bridge to match the canonical behavior (or have it share the canonical code) and fix its wrong comment. **(b)** Extend the escape set to bidi controls, U+2028/U+2029, and zero-width characters — which forces a new escape spelling, since the current `\xHH` format only fits two hex digits (something like `\u{XXXX}`), applied identically in both backends, with the cross-backend byte-identical-output tests re-pinned. Part (b) touches both backends and many test literals; mechanical but not tiny.

**The case for skipping.** The original TODO explicitly accepted this risk "until consumers surface bidi-aware display paths." Severity is genuinely low (visual trickery, not execution). Part (b) could be deferred again — but part (a), the drift fix, is hard to argue against.

**Recommendation: Do**, the reframed version: drift fix (a) plus escape-set extension (b) as one project. If you want to economize, (a) alone is acceptable and (b) returns to the TODO list.

USER DECISION: Do

---

## `error-msg-escape-zero-copy` — Delete

**What the problem is.** The error-message escaping function returns a fresh copy of the text even when there was nothing to escape. A fancier return type (`Cow`) could hand back the original text with zero copying. The TODO defers that as "a future cleanup."

**Why it matters (it doesn't).** Validation showed: the function is called exactly twice, both times when *formatting a parse-error message* — a cold path that runs only on failure — and both results are immediately pasted into a bigger string anyway, which allocates regardless. The entire prize is avoiding two short-lived allocations per error message. Meanwhile the cost is real: the function is public API re-exported at the crate root and used by downstream generated parsers, so changing its signature is exactly the kind of downstream-visible API churn CLAUDE.md says to avoid without strong cause.

**What the work actually looks like.** A public signature change rippling to downstream consumers, to save two allocations on a path that runs only when parsing fails.

**The case for doing it anyway.** None found. The fast path already eliminated the measurable regression that motivated the original discussion.

**Recommendation: Delete.** Negative expected value: API churn for an unmeasurable win on a cold path.

USER DECISION: Delete

---

## `mutator-remove-at-oob-atomicity` — Delete

**What the problem is.** `remove_at` (remove the Nth child from a tree node, return it to Python) first removes the child, then wraps it into a Python object. If that wrapping fails — essentially only possible when the process is out of memory — the child is already gone: you get an exception *and* the tree was modified. The TODO calls this a violation of an "atomic: all-or-nothing" contract and proposes a fix.

**Why it doesn't hold up.** Validation found: (1) the "atomic" contract is not documented anywhere — no docstring, no design doc, no stub; it exists only in the TODO text itself, so nothing promised is being broken. (2) The TODO's preferred fix (wrap the child *before* removing it) has a race condition: between peeking at the child and removing it, another thread can shuffle the children, and you'd remove the wrong one. The proposed cure is buggier than the disease. (3) The only realistic trigger is out-of-memory, at which point the Python process is dying anyway and no library guarantees survive. (4) The other mutators don't have this issue; there's no pattern to fix.

**What the work would actually look like.** A remove-then-re-insert-on-failure dance with a second lock acquisition, plus tests for an effectively untriggerable condition.

**The case for doing it.** Purity. If you want *something*, a one-line docstring noting "on MemoryError the child may be lost" is the honest fix — but that hardly needs a TODO.

**Recommendation: Delete.** Unpromised contract, unreachable trigger, and the proposed fix introduces a real concurrency bug to fix a theoretical one.

USER DECISION: Delete

---

## `mutator-rs-fast-path-int-index` — Delete

**What the problem is.** The Rust-backend tree-editing methods (`insert`, `remove_at`, `replace_at`) convert their index argument by calling Python's `operator.index` helper, which costs three small Python-level operations per call. The TODO proposes skipping that for plain integers via a direct Rust-side extraction.

**Why it doesn't hold up.** Validation found: (1) these methods are user-facing tree-*editing* calls, not used during parsing — there's no hot path and no profiling showing they matter. (2) The TODO's technical claims are sloppy: wrong C-API function named, savings count off by one (a string capture for error messages still costs a Python call either way). (3) The fast path would change the `TypeError` message text for non-integer inputs, in a way that varies by CPython version — and the Python backend would keep producing the old message, quietly eroding the cross-backend "identical behavior" property this project treats as a core promise. No test pins that message today, so the divergence would land silently.

**What the work would actually look like.** Careful ordering surgery in three generated-code templates, new parity tests for error-message text, to shave a few hundred nanoseconds off operations nobody calls in a loop.

**The case for doing it.** Only if profiling ever shows mutator-call overhead matters to a real consumer.

**Recommendation: Delete.** Micro-optimization of a cold path that risks silent cross-backend behavioral drift.

USER DECISION: Delete

---

## `extend-children-owned` — Blocked

**What the problem is.** During parsing, the Rust backend frequently merges a temporary node's children into its parent. The merge *copies* each child reference (an atomic reference-count bump per child) even though the temporary node is thrown away immediately afterward — the children could just be *moved* over for free. Validation confirmed every claim: the donor really is always discarded immediately, a consuming "move" variant would drop in cleanly at both call sites, and there are no hidden blockers (it even composes with the planned `Drop` work).

**Why it matters.** It's on the parse hot path — per-child atomic operations during every parse. But: nobody has measured it. There is no in-tree profiling of parse throughput or of this overhead, and the TODO itself says "re-open only with profiling evidence."

**What the work actually looks like.** Add a new method to the generated node API (`extend_children_owned`) and switch the two parser-generator call sites to use it. Mechanical — *if* it's worth doing. The catch: it permanently grows the generated public API surface (which out-of-tree consumers see) for a win of unknown size.

**The case for skipping.** Unmeasured perf win; public-API growth on speculation contradicts this repo's API-conservatism rules.

**Recommendation: Blocked** — keep the TODO as-is; blocked on profiling evidence (a parse-throughput benchmark showing `extend_children` clone cost is material). Do not implement on speculation.

USER DECISION: Keep blocked.
