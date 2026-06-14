# ELI5: Fixing the Defects That a Real Build Uncovered

## What this is about

FLTK is a toolkit that generates parsers -- programs that read structured text and break it into a tree of meaningful pieces. It works by reading a grammar file (a description of a language's syntax) and producing code that can parse that language. FLTK can generate parsers in both Python and Rust, and the Rust parsers use a library called PyO3 to expose themselves to Python code.

A separate project called Clockwork uses FLTK as a dependency. Clockwork has its own grammar describing a domain-specific language, and it uses FLTK to generate a parser for that language. Both projects use a build system called Bazel, which manages how code is compiled and tested in a reproducible way.

A prior design (the "original design") laid out a plan for how Clockwork would consume FLTK's Rust-generated parser through Bazel. That plan was reviewed and approved entirely by reading code -- nobody actually ran the Bazel build to see if it worked. When someone finally did run `bazel test`, seven genuine bugs surfaced: things the code review missed because they are properties of real toolchains (the Rust compiler, the Bazel build system, the PyO3 library) that are invisible on paper.

An implementer fixed all seven bugs ad hoc to get the build to pass. This document is a retroactive design review of those fixes. For each bug, it asks: what is the real underlying problem, is the fix the right design, and does anything need to change? Each fix gets a verdict of either RATIFY (the fix is correct, keep it) or REVISE (the fix needs adjustment).

## The seven problems and their fixes

The problems are organized into three tiers based on how many people they affect:

- Tier 1 affects the generated public API -- code that downstream users outside of both FLTK and Clockwork write against. Changes here are the most consequential.
- Tier 2 affects FLTK's public Bazel surface -- the build rules and configuration that any consumer of FLTK uses.
- Tier 3 affects only Clockwork's local build scaffolding, though each encodes a real fact that future consumers will also encounter.

### Problem 1 (Tier 1): Name collisions between generated code and PyO3 library types

This is the most important problem and gets the most thorough treatment.

**Background you need to follow this.** When FLTK generates Rust code from a grammar, it creates two things for each grammar rule: a data struct (named after the rule, like `List` for a rule called `list`) and a PyO3 "handle" struct (prefixed with `Py`, like `PyList`). The generated code also imports various types from the PyO3 library -- and some of those imported types happen to have names like `PyList`, `PyTuple`, `PyType`, and `PyModule`. If a grammar has a rule called `list`, the generated code tries to define a struct called `PyList` while also importing PyO3's own `PyList`. The Rust compiler rejects this as two definitions of the same name.

FLTK already had a defense mechanism for name collisions: a reserved-names list (`_RESERVED_CLASS_NAMES`). If a grammar rule's name would collide with a known identifier, the generator rejects the grammar with a clear error message at generation time. So there were always two possible responses to a collision: (a) reserve the name and reject the grammar, or (b) qualify the reference (write `pyo3::types::PyList` instead of just `PyList`) so there is no collision and the name stays available for grammars to use.

**What went wrong.** Clockwork's grammar has rules called `list` and `module`, which collided with PyO3's `PyList` and `PyModule`. The build failed with Rust compiler errors. This was invisible to reviewers because nobody compiled the code.

**What the implementer did.** They chose a mixed strategy. For the four common names (`list`, `tuple`, `type`, `module`), they qualified the PyO3 references -- writing out full paths like `pyo3::types::PyList` instead of importing the short name. This lets grammars freely use those rule names. For three exception types (`IndexError`, `TypeError`, `ValueError`) and for `Any`, they took the other approach: added them to the reserved list so grammars cannot use those names. The reasoning for `Any` was pragmatic -- it appears at roughly 30 sites in the generated code, so qualifying all of them was considered too tedious for now.

**The design's verdict: RATIFY the overall approach, but REVISE for robustness.**

The mixed strategy is the right design. Qualifying common names like `list` and `module` is the right call because those are extremely common grammar rule names -- reserving them would permanently prevent every consumer from using natural names in their grammars, which is worse than a one-time edit to the generator. FLTK's guiding principle is that generated output is public API; keeping the consumer's namespace as large as possible serves that principle.

However, the design identifies a deeper robustness problem that the fix does not fully address. The generated code uses a Rust "glob import" -- `use pyo3::prelude::*` -- which pulls an unknown and potentially changing set of names into scope. The generator cannot know exactly which names that glob brings in, which means it cannot reliably check for collisions against all of them. The design found specific gaps: rule names like `bound`, `py`, `python`, or `borrowed` would produce data structs that collide with non-`Py`-prefixed names that the glob imports (like `Bound`, `Py`, `Python`, `Borrowed`), and none of these are in the reserved list. A grammar with a rule called `bound` would hit a confusing compiler error with no indication of what went wrong.

The mandated fix is to "de-glob" the import: replace `use pyo3::prelude::*` with an explicit list of only the specific names the generated code actually uses. Once the generator knows exactly which names it imports, it can mechanically check every grammar rule name against that list and either qualify the collision or reject the grammar with a helpful message. This closes both halves of the collision surface -- the `Py`-prefixed handle structs and the bare data structs.

There is also a separate observation that the parser generator (`gsm2parser_rs.py`) is not vulnerable to this problem in the same way, because it only emits fixed class names (like `PyParser`), never rule-derived names. This asymmetry matters: if someone later changes the parser generator to emit rule-derived names, they would need to redo this analysis. The design calls for documenting this fact so the assumption is not silently load-bearing.

**Open question (O1).** Whether to also qualify the remaining `Py`-prefixed emission sites now (recovering the ability to use `any` as a rule name) or to defer that work. Both options satisfy the robustness requirement once the glob is removed; the difference is effort now versus completeness now. The design recommends doing both at once.

### Problem 2 (Tier 2): Bazel does not forward crate features the way Cargo does

**Background.** Rust's Cargo build tool has a concept called "features" -- optional compilation flags that enable or disable chunks of code. When you enable a feature on one crate in Cargo, it can automatically "forward" that feature to the crate's dependencies. The original design assumed Bazel's Rust rules (`rules_rust`) would work the same way. They do not. In Bazel, features are per-target and do not propagate to dependencies.

**What went wrong.** The FLTK Rust code has sections guarded by `#[cfg(feature = "python")]` -- they only compile when the `python` feature is turned on. The original design set `extension-module` on the consumer's build target and assumed Bazel would forward `python` to the FLTK core library automatically. It did not. The `python`-guarded symbols compiled away, and the build failed with "unresolved symbols" errors.

**The fix and verdict: RATIFY.** The fix simply adds `"python"` to the explicit feature list on the FLTK build target. The design also calls for documenting this Bazel-vs-Cargo difference prominently, because any future consumer who writes their own build target (instead of using FLTK's provided macro) will hit the same problem. The macro already handles this correctly; the documentation ensures people who bypass the macro know the rule.

### Problem 3 (Tier 2): Starlark does not allow implicit string concatenation

**Background.** In Python, you can write two string literals next to each other and they automatically concatenate: `"hello" " world"` becomes `"hello world"`. Starlark, the language Bazel uses for its build files, looks like Python but forbids this.

**What went wrong.** A docstring in FLTK's new Bazel rule file used adjacent string literals across lines (the Python habit). When Bazel tried to load the file, it failed immediately with "Implicit string concatenation is forbidden." Every consumer would have hit this on first use.

**The fix and verdict: RATIFY.** The fix adds an explicit `+` between the string fragments. This is a pure syntax correction with no design significance. The broader lesson is that a `.bzl` file in the public surface must actually be loaded by Bazel at least once before it can be considered reviewed -- the overarching theme of this entire document.

### Problem 4 (Tier 3): Rust compiler recursion limit exceeded for large grammars

**Background.** Rust's compiler has a recursion limit (default: 128) for how deeply it will evaluate certain type-checking operations. When a grammar has deeply recursive rules (rule A references B, which references C, which eventually references A again), the generated PyO3 structs create a chain of nested types that the compiler must validate. Clockwork's grammar is deeply recursive -- it has chains like `DflArg` to `DflExpr` to `DflCallSuffix` to `DflArgList` back to `DflArg`. The default limit was not enough.

**What went wrong.** The Rust compiler hit its recursion limit and failed with an "overflow evaluating" error. This never appeared in FLTK's own test grammars because none are as deeply recursive as Clockwork's.

**The fix and verdict: RATIFY the value, REVISE the placement.** Setting the recursion limit to 512 is the correct fix -- there is no alternative for deeply recursive types. But the implementer put the `#![recursion_limit = "512"]` line in Clockwork's hand-authored `lib.rs` file, meaning every consumer with a large grammar must independently discover and apply this obscure compiler directive.

The design recommends that FLTK's build macro should automatically inject this line. The macro already assembles the crate's source directory; extending it to prepend the recursion-limit attribute is a small change that moves the knowledge from "every consumer must remember" to "the FLTK macro guarantees it." There is a technical subtlety -- the attribute must be the very first line of the file due to Rust's inner-attribute ordering rules -- but the design accounts for this.

**Open question (O2).** Whether the recursion limit should be a fixed value (512) or a configurable macro parameter with 512 as the default. Fixed is simpler; configurable accommodates consumers with even deeper grammars. The design recommends making it configurable.

### Problem 5 (Tier 3): Test target naming convention in Clockwork

Clockwork's internal build macros hardcode the name `:__test__` for the pytest main target. The original design used the name `__rust_test__`, which did not match. The fix was simply to rename it to `__test__`. This is purely a Clockwork-internal naming convention with no design significance beyond "conform to your host repo's conventions."

**Verdict: RATIFY.** Keep as-is.

### Problem 6 (Tier 3): PyO3 does not report the expected module name

**Background.** The roundtrip test needs to verify that the Rust extension is actually loaded, not the pure-Python fallback. The original test checked whether `Span.__module__` equals `"fltk._native"`. But PyO3 (version 0.29), when a class does not have an explicit `module` attribute set, reports `__module__` as `"builtins"` -- not the importing module's name. So the assertion would have failed even when the Rust extension was working correctly.

**The fix and verdict: RATIFY.** The fix inverts the test logic: instead of asserting the module name *is* the Rust path, it asserts the module name *is not* the pure-Python fallback path (`"fltk.fegen.pyrt.terminalsrc"`), and also checks that the module name is one of the expected values (`"builtins"` or `"fltk._native"`). This correctly distinguishes "Rust extension loaded" from "fell back to Python" without depending on PyO3's exact module-name reporting behavior.

**Open question (O3).** If FLTK ever wants `Span.__module__` to report a meaningful module name (useful for pickling, repr, or stricter downstream checks), it would need to add `#[pyclass(module = "fltk._native")]` to the Span class definition in FLTK's core Rust code. That is out of scope for this work but is noted so the `"builtins"` behavior is not a mystery later.

### Problem 7 (cross-cutting): Finalizing the temporary local override

**Background.** Bazel has two ways to point at a dependency's source code: a `git_override` (fetch a specific commit from a remote repository) and a `local_path_override` (point at a directory on the local filesystem). During verification, the implementer used a `local_path_override` to point Clockwork at the local FLTK checkout. This was intentional scaffolding to prove the build works, but it cannot stay -- the real build must fetch FLTK from the remote repository.

**Verdict: RATIFY as scaffolding, but finalization is required.** The override is correct for verification but must not be merged as-is. The finalization steps are: push the FLTK commits to the remote repository, switch Clockwork back to `git_override` pointing at the pushed commit, re-run the tests to confirm they pass against the remote fetch path, and remove the temporary TODO comment.

## What is still undecided

Three open questions remain for the user to resolve:

**O1: How far to push the name-collision robustness upgrade now.** The mandatory step is removing the glob import (`use pyo3::prelude::*`) so the generator can see exactly what names are in scope. That is required regardless. The question is whether to also qualify all the remaining `Py`-prefixed emission sites in the same pass (more work now, but recovers `any` as a legal rule name and eliminates the entire `Py`-prefixed reservation category) or to defer that part and reserve the remaining names for now. The design recommends doing both at once.

**O2: Should the recursion limit be configurable?** The macro will inject a recursion limit into every consumer's crate. Should it always be 512, or should there be a macro parameter (defaulting to 512) so consumers with exceptionally deep grammars can raise it? The design recommends making it configurable.

**O3: Should `Span` declare its PyO3 module name?** Currently `Span.__module__` reports `"builtins"` because the Rust class definition does not specify a module. This is harmless for now and the test tolerates it. But if FLTK ever wants the module name to be authoritative (for pickling, repr, or stricter checks), it would need a one-line change to the Span class in FLTK's core Rust code. The design recommends leaving it as-is for the POC and filing a TODO only if the user wants the module name to be meaningful.

## The overarching lesson

All seven defects share the same root cause: the original design was validated by reading code, not by running the build. Every bug is a fact about a real toolchain -- Bazel's feature model, Starlark's parser, the Rust compiler's recursion limits, PyO3's module-name reporting -- that is invisible to a reviewer who never compiles. None is a logic error in the design's intent. Each is a place where a stated mechanism met a real-toolchain rule it had not accounted for. The design itself captures this lesson: a Bazel `.bzl` file in the public surface must be loaded by Bazel at least once before it can be called "reviewed."
