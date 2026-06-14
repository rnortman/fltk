# Recommended Actions — Plain-English Explanation

This document explains each recommended action from the Rust backend production-readiness assessment in plain, accessible language. Each item is keyed by the same slug used in the companion `recommended-actions.md` so you can cross-reference easily.

For background: FLTK is a toolkit for building parsers (programs that read structured text and turn it into a data structure called a Concrete Syntax Tree, or CST). FLTK has historically been written entirely in Python. Over the past three months, a Rust backend was added to make parsing faster. The assessment reviewed whether that Rust backend is ready for real use and produced this list of things to do. The overall verdict is "refine-then-ship" — the Rust backend is fundamentally sound and worth keeping, but it needs specific fixes before it can be shipped to real users.

The actions are organized into four phases:

- **Phase A** covers things that absolutely must happen before anyone uses the Rust backend in production. These are safety fixes and basic integrity checks.
- **Phase B** covers validation work — proving that the Rust backend actually does what it claims (produces correct results and is actually faster).
- **Phase C** covers cleanup — removing dead code, writing down what the Rust backend does and does not cover, and documenting known differences between the two backends.
- **Phase D** covers the actual rollout to a real user and a long-term strategic decision that is deliberately deferred until later.

---

## `fix-forged-abi-segfault`

**Phase A (step 1) -- Blocker -- No prerequisites**

### What this is

There is a specific method on the `Span` class (a class that tracks where a piece of parsed text came from in the original input) called `_with_source_unchecked`. This method is publicly accessible, meaning any code — including code written by someone using FLTK as a library — can call it.

The problem: if someone passes this method a fake Python object that pretends to be a real native Rust object (by copying certain identifying attributes off a genuine one), the Rust code trusts those attributes, tries to interpret the fake object's memory as if it were a real Rust data structure, and crashes the entire Python interpreter with a segmentation fault — an unrecoverable, instant crash. This was verified to happen 100% of the time in testing (4 out of 4 attempts).

### Why it matters

This is the single hardest blocker in the entire assessment. In the Python-only version of FLTK, the equivalent code is memory-safe — passing it bad input might raise an error, but it will never crash the interpreter. The Rust backend is supposed to be a near-drop-in replacement, so having a public method that crashes where the Python version does not is unacceptable. Beyond crashing, the underlying mechanism (interpreting arbitrary memory as a known type) is also a potential security concern.

### What the fix is

Add a check before the dangerous memory operation that verifies the incoming object is a genuine native Rust object, not a plain Python object with copied attributes. This check needs to be strict enough to reject fakes but not so strict that it rejects legitimate Rust objects created by a different compiled copy of the library (which is a real use case in this system). The crash scenario should also be added as a permanent regression test, run in a separate process so that if the crash somehow recurs, it does not take down the entire test suite.

---

## `gencode-drift-gate`

**Phase A (step 2) -- Major -- No prerequisites**

### What this is

FLTK has code generators: Python scripts that read a grammar description and produce Rust source code (about 75,670 lines of it). That generated Rust code is checked into the repository — it is the actual product that ships. The problem is that nothing in the build system or CI (continuous integration — the automated checks that run when code is submitted) ever re-runs the generators and checks that the committed Rust code matches what the generators would produce today.

### Why it matters

Without this check, the generated code can silently "drift" from its generators in two dangerous ways. First, someone could update a generator but forget to regenerate the output, so the committed code is stale. Second, someone could hand-edit the generated code directly (perhaps to fix a quick issue), and that edit would be silently lost the next time someone regenerates. This class of drift has already happened once in the project's history. Four separate findings in the assessment independently identified this gap, making it the most frequently surfaced issue.

This check is also described as the "cheapest high-leverage fix in the assessment" because it is a small amount of build-system work (adding one step to the existing `Makefile`) that closes four findings at once. Beyond that, it is a prerequisite for safely doing any future refactoring of the generators — without it, you cannot be sure that a change to a generator actually produces the same output.

### What the fix is

Add a step to the shared part of the build check (a `Makefile` target called `check-common`) that re-runs the code generators and then asks `git` whether any files changed. If any file differs, the check fails. Because both the local check and the CI check inherit from `check-common`, this automatically lands in both places.

---

## `cst-generated-header`

**Phase A (step 3) -- Major -- No prerequisites**

### What this is

One of the two types of generated Rust files (the CST file, which defines the data structure classes for parse trees) is missing a standard header comment that says "this file was generated by a machine — do not edit it by hand." The other generated file (the parser) already has this header.

### Why it matters

Without the header, a 15,515-line machine-generated file looks like it was written by hand. This actively invites the failure mode described in `gencode-drift-gate`: someone sees something they want to fix, edits the file directly, and their fix is silently lost on the next regeneration. The project already knows the right pattern (the parser file has the header), and the CST generator just never adopted it.

### What the fix is

Add the standard "generated — do not edit" header to the CST generator's output, matching the pattern already used by the parser generator.

---

## `cargo-deny-in-ci`

**Phase A (step 4) -- Major -- No prerequisites**

### What this is

`cargo-deny` is a tool that checks Rust dependencies for known security vulnerabilities (via the RustSec advisory database), yanked (recalled) packages, and license compliance. FLTK has `cargo-deny` configured, but it only runs as part of a local pre-commit hook — a check that runs on the developer's own machine before they commit code. It never runs in CI.

### Why it matters

The local-only hook has several gaps. A fresh clone of the repository (as a new contributor would have) does not have the hook installed. CI-only contributors (who submit changes through the web interface or automated tools) bypass it entirely. And any developer can skip it with a `--no-verify` flag on their commit. The result is that a newly disclosed security vulnerability in any of FLTK's Rust dependencies could go completely undetected by all automated systems. Additionally, GitHub's Dependabot (which can automatically suggest dependency updates) is currently only configured for GitHub Actions workflows, not for the Rust or Python package ecosystems.

### What the fix is

Add a CI job that runs `cargo-deny`, ideally both on every pull request and on a weekly schedule (to catch newly disclosed vulnerabilities between PRs). Also add the Rust (`cargo`) and Python (`pip`/`uv`) ecosystems to the Dependabot configuration so that dependency update suggestions cover the full stack.

---

## `differential-property-harness`

**Phase B (step 5) -- Major -- Depends on: `gencode-drift-gate`**

### What this is

Right now, the test that the Rust backend produces the same parse results as the Python backend relies on a hand-picked set of 63 test inputs across 2 grammars. A "differential/property harness" would instead generate random inputs (both valid and invalid) and automatically check that both backends produce identical results, dramatically expanding coverage.

### Why it matters

A hand-picked corpus tests only the cases someone thought to write down. A real divergence (involving "trivia" — whitespace and comments attached to parse tree nodes) already slipped through the hand-picked tests during development. For FLTK's promise to hold — that the Rust backend is a drop-in replacement for any downstream grammar, not just the two grammars tested — the parity testing needs to go beyond human foresight. Property testing and fuzzing are the standard tools for this: generate many random inputs, feed them to both backends, and assert the outputs match.

### What the fix is

Wire random input generation (either via `cargo-fuzz` on the Rust side or a Python-side generator) into the existing parity test infrastructure, which already has the comparison logic (`assert_cst_equal` / `assert_error_equiv`). Ideally include grammars from real downstream consumers (such as Clockwork, a project that uses FLTK) in the corpus. Gate it so it runs as part of the standard checks.

This item depends on `gencode-drift-gate` because the drift gate ensures the generated code under test actually matches its generators — without that guarantee, a differential test failure could be caused by stale generated code rather than a real behavioral difference.

---

## `regex-portability-lint`

**Phase B (step 6) -- Major -- No prerequisites**

### What this is

Grammars in FLTK can include regular expressions (patterns for matching text). The Python backend uses Python's built-in `re` regex engine; the Rust backend uses a different engine called `regex-automata`. These two engines handle certain advanced regex features differently — not just "one crashes and the other doesn't," but they silently produce different parse trees for the same input. The affected features include POSIX character classes (like `[[:alpha:]]`), Unicode property classes (like `\p{Letter}`), nested character sets, and lookaround assertions.

### Why it matters

Today, nothing warns the grammar author that their regex uses a construct that will behave differently between backends. The existing "do all regexes compile?" check passes these constructs because both engines can compile them — the problem is that they interpret them differently at runtime. A grammar author could write a perfectly reasonable regex, have it work fine with the Python backend, switch to the Rust backend, and get silently wrong parse results with no error.

### What the fix is

Add a check at code-generation time (when the Rust parser code is being generated from a grammar) that detects non-portable regex constructs and rejects them with a clear error message, rather than letting them through to produce silent mismatches. Also update the documentation to describe the regex engine difference as a hard semantic boundary (not merely a compile-time restriction), and add tricky-but-portable regex cases to the parity test corpus.

---

## `perf-harness`

**Phase B (step 7) -- Major -- No prerequisites**

### What this is

The entire reason the Rust backend exists is to be faster than the Python backend. After three months of development, there is no measurement of whether it actually is faster, and no infrastructure to produce such a measurement.

### Why it matters

The only existing benchmark is a pure-Rust micro-benchmark that tests tree traversal without ever crossing the Python/Rust boundary. But in real use, FLTK's Rust backend is called from Python — every time Python code accesses a child node of the parse tree, it crosses the Python-to-Rust boundary (via pyo3, the library that connects the two). The earlier exploration phase of the project explicitly warned that the cost of repeatedly crossing this boundary could negate the speed gains from using Rust. That cost is present in the current code and has never been measured.

Additionally, there are several performance-improvement TODOs in the codebase that are waiting on profiling data before they can be acted on. Without a performance harness, those TODOs are stuck in a deadlock: they need profiling evidence to justify the work, but the profiling infrastructure does not exist.

### What the fix is

Build an end-to-end benchmark that parses a representative grammar and input using both backends, measuring wall-clock time and peak memory usage. Crucially, the benchmark must include Python-side CST traversal (repeatedly accessing children, doing a deep walk of the tree) — the exact workload where the per-child boundary-crossing cost matters. Establish a baseline and wire a loose performance smoke check into a non-CI lane (meaning it is available for developers to run but does not block every PR).

---

## `remove-dead-duplicate-crate`

**Phase C (step 8) -- Cleanup -- No prerequisites**

### What this is

There is a directory (`tests/rust_cst_fegen/`) that contains a complete, byte-identical copy of a Rust "crate" (package) that already exists at `crates/fegen-rust/`. This duplicate is about 17,000 lines of code, is fully checked into version control, and is not built, tested, or checked by any part of the build system. It also has a package name that collides with the real crate's name, creating a potential for one to shadow the other.

### Why it matters

This duplicate fell off every build and test lane during an earlier refactor, and nothing noticed — which is itself a concrete demonstration that the current system for tracking multiple Rust packages (the "per-crate fan-out") is a drift surface. The duplicate also left behind stale references in documentation (the CHANGELOG claims it is regenerated; the extension guide references its path), which mislead anyone reading those documents.

### What the fix is

Delete the duplicate directory and fix the stale references in `CHANGELOG.md` and `docs/rust-cst-extension-guide.md`.

---

## `demote-cst-spike`

**Phase C (step 8) -- Cleanup -- Depends on: `perf-harness`**

### What this is

There is a Rust crate called `fltk-cst-spike` that was an early prototype ("spike") for the CST implementation. It keeps its own copy of a generated file (`cst.rs`) in sync with a test directory via a literal `cp` (copy) command in the Makefile. It also has a development dependency on the `criterion` benchmarking library, which leaks into the downstream-facing Bazel build configuration.

### Why it matters

The `cp`-based synchronization is fragile — it is another instance of the drift problem. The leaked `criterion` dependency unnecessarily complicates the build for downstream consumers. However, the spike is not entirely dead: it currently owns the only Rust traversal benchmark and exercises a build configuration where Python bindings are turned off.

### What the fix is

Fold the spike into the existing test directory (`tests/rust_poc_cst`), eliminating the duplicated file and the workspace member. This depends on `perf-harness` because the performance work needs to first relocate any benchmark from the spike that is worth keeping, before the spike can be removed.

---

## `document-scope-boundary`

**Phase C (step 9) -- Cleanup -- No prerequisites**

### What this is

Several things the Rust backend does not support are currently undocumented "implicit cuts" — they are simply absent, with no explicit statement that they are intentionally out of scope. This action calls for making those boundaries explicit.

### What the boundaries are

Three specific scope items need documentation:

1. **No unparser.** The Rust backend handles parsing (text to tree) and CST (the tree data structure). It does not handle unparsing (tree back to text). The Python unparser is a headline feature of the upcoming 0.2.0 release, and the Rust equivalent does not exist — there is not even a TODO for it. This should be stated as an explicit, deliberate decision, not left as a silent absence.

2. **Regex subset is a permanent boundary.** The difference in regex engine behavior (described in `regex-portability-lint`) is not a temporary limitation to be fixed later — it is an inherent difference between the two engines. This should be documented as a permanent characteristic of the Rust backend.

3. **INLINE disposition and Invocation terms are unsupported on both backends.** Early assessment framing suggested these were Rust-only gaps, but in fact the Python parser generator also refuses them. This should be documented correctly as a system-wide limitation, not a Rust-specific one.

Additionally, there is a three-way version number disagreement (the wheel says 0.1.1, the `fltk-native` crate says 0.1.0, the runtime crates say 0.2.0), and the consumer guide's example of how to depend on FLTK uses a version specifier that does not resolve. These should be reconciled, and the documented path for downstream consumers should use a git or Bazel pin rather than a non-working version number.

---

## `accept-publicapi-divergences`

**Phase C (step 10) -- Cleanup -- No prerequisites**

### What this is

The assessment found several places where the Rust backend's public API behaves slightly differently from the Python backend's. All of these were reviewed adversarially and downgraded to "minor" — meaning they affect only non-idiomatic usage patterns, and the normal, documented way of using the API works identically on both backends. This action says: accept these as known differences, document them in a migration guide, and add tests that pin the current behavior so it becomes an explicit contract rather than an accident.

### The specific divergences

- **Children snapshot in-place no-op:** In the Python backend, calling `children` returns a mutable list; modifying it in place changes the node. In the Rust backend, `children` returns a snapshot; modifying it in place silently does nothing. The sanctioned way to mutate children (using `insert_at`, `remove_at`, `replace_at`, `clear`) works the same on both.
- **`children_<label>` iterator vs list:** The Python backend returns a list; the Rust backend returns an iterator. Both work identically in a `for` loop, which is the normal usage.
- **Span hand-in asymmetry:** A subtle difference in how source-position information is provided when constructing nodes.
- **Positional `match` break:** Using Python's structural pattern matching (`match`/`case`) with positional arguments works differently. Using `.kind` (the documented approach) works the same.
- **Span-union cast:** A minor type-casting difference in how span ranges are combined.

### What the fix is

Document these in a migration guide. Optionally, change the type annotation for `children` to indicate a read-only sequence type (a deliberate, called-out change) to steer users toward the mutation methods that work the same on both backends. Add two categories of tests: a deep-tree stress test (50,000-100,000 nodes) that exercises the iterative stack-safety machinery for `Drop`/equality/`Debug` (this machinery exists precisely to prevent stack overflow on deep trees, but no test currently exercises it at depth, so a regression to naive recursion would pass CI silently), and pinned tests for each of the known divergences above.

---

## `clockwork-committed-pin-proof`

**Phase D (step 11) -- Major -- Depends on: `fix-forged-abi-segfault`, `gencode-drift-gate`**

### What this is

Clockwork is a downstream project that uses FLTK — it is the closest thing to a real consumer of the Rust backend. Currently, Clockwork depends on FLTK via a `local_path_override`, which means it points directly at a live checkout of the FLTK source code on the developer's machine. This is a temporary development convenience (there is even a TODO in the code flagging it for replacement). The actual mechanism that real consumers would use — fetching a specific committed version of FLTK from its git repository — has never been tested for the Rust/Bazel path.

### Why it matters

If the dependency mechanism that real users would actually use has never been exercised, it could be broken in ways no one knows about. Additionally, the Bazel-built version of the Rust library has never been verified to have a critical build property (`extension-module`) that prevents it from linking against `libpython` — a requirement for the library to work correctly when loaded as a Python extension. And Bazel currently has zero CI coverage.

### What the fix is

Switch Clockwork's FLTK dependency from the temporary local-path override to a committed git pin (pointing at a specific commit hash) and run Clockwork's existing roundtrip test to verify everything works end-to-end. Add a minimal Bazel CI job that builds the native library and verifies it does not link `libpython`.

---

## `ship-opt-in-first-consumer`

**Phase D (step 12) -- Strategic -- Depends on: all Phase A and Phase B items, plus `clockwork-committed-pin-proof`**

### What this is

This is the actual ship decision: make the Rust backend available to a deliberate first consumer on an opt-in basis, with the Python backend remaining fully supported and co-equal.

### Why it matters

This is the realization of the assessment's overall "refine-then-ship" verdict. It is not a "flip the switch for everyone" moment — it is a controlled rollout to one willing consumer, with the Python backend still available as a fallback. The Rust backend is scoped to parsing and CST only; the unparser is explicitly out of scope.

### What must be true first

All Phase A items (the segfault fix, the drift gate, the generated-file header, and the CI supply-chain check) must be done because they are mandatory integrity and safety controls. All Phase B items (the differential testing harness, the regex portability lint, and the performance harness) must be done because they validate the two foundations behind the "drop-in replacement" claim. The Clockwork committed-pin proof must be done because it is the actual end-to-end demonstration that a real consumer can use the Rust backend through the normal dependency mechanism. Phase C cleanup items are release-engineering quality improvements — they should accompany the rollout but are not hard gates.

---

## `emission-ir-decision`

**Phase D (deferred strategic decision) -- Strategic -- Depends on: `gencode-drift-gate`**

### What this is

This is not something to do now. It is a decision to make later, at a specific future moment, about whether to restructure how FLTK generates Rust code.

### The background

Currently, FLTK generates Rust code using "direct string emission" — the Python generators build up Rust source code as strings, line by line, and write them to files. There are two such generators (one for the CST data structures, one for the parser), and they share no intermediate representation (IR). An IR would be a structured, language-neutral description of what to generate, which could then be rendered into either Rust or Python syntax by separate, simpler renderers.

The lack of a shared IR means the generators duplicate work. The per-label accessor methods (a family of five related methods for accessing labeled children of a node) are hand-emitted three times in the Rust generator versus once in the Python generator. The Rust CST generator is 2,351 lines versus 1,026 for the Python one despite producing semantically equivalent output. The direct-emission approach also forced the creation of a roughly 250-line subsystem just to handle Rust identifier collisions, and requires pervasive conditional emission of lint-suppression attributes — complexity that a structured IR would have absorbed naturally.

### Why it was deferred, not dismissed

The assessment concluded this is real debt but verified it to be *minor* for now, for two specific reasons. First, the public type-annotation surface (the part downstream consumers rely on most) is not held together by convention — it is mechanically checked by a type checker, so annotation drift between the two generators is caught automatically. Second, grammar interpretation (deciding which classes to generate, what their fields are, etc.) is single-sourced in a shared Python layer; only the final step of rendering to syntax is duplicated.

The idea of building an IR was proposed and rejected twice (in May and June 2026) on cost grounds. The assessment agrees with both rejections — for now. The key insight is that the forcing function for revisiting this decision is clear: the day work begins on a Rust unparser. The Python unparser is a large subsystem (about 73KB of code) and a headline upcoming feature. Building a Rust version of it would mean adding a third hand-maintained string-emitting generator, which would triple the duplication. That is the moment when the cost-benefit calculus for an IR changes, and the moment to make the decision.

### Why it depends on `gencode-drift-gate`

The drift gate is what makes any future refactoring of the generators safe. Without it, changing a generator and not being sure the output matches is dangerous — you could silently break the generated code that downstream consumers depend on. The deferral of this decision is explicitly premised on the drift gate being in place: once it is, the duplication can be paid down incrementally and safely whenever the time is right.
