# FLTK Rust Backend Assessment -- Plain-Language Explanation

This document explains the production-readiness assessment of FLTK's Rust backend. It assumes you know general software engineering but nothing about FLTK, this codebase, or the history of this project. Every term and concept is introduced before it is used.

---

## What FLTK is and why any of this matters

FLTK (Formal Language ToolKit) is a Python library for building parsers and compilers. You feed it a grammar -- a formal description of a language's syntax -- and it generates two things: a parser (which reads source code and recognizes its structure) and a set of Concrete Syntax Tree (CST) node classes (data structures that represent the parsed source code as a tree). FLTK can also generate an unparser (which takes a CST and turns it back into formatted source text), though that is relevant here mainly as something the Rust backend does not yet do.

The critical thing to understand about FLTK is that its primary purpose is to be used by other, external applications. Those applications use FLTK to generate their own parsers and CST classes, and then they write code against those generated artifacts. The generated class names, method signatures, type annotations, and equality behaviors are all public API consumed by real downstream code that lives outside the FLTK repository. Any change to that surface -- renaming a class, changing a type annotation -- is a breaking change for people the FLTK team cannot even see. This constraint dominates the entire assessment.

## What the Rust backend is

Until recently, FLTK's code generation produced only Python code: Python CST classes (as dataclasses) and a Python parser. The Rust backend is a parallel code-generation path that produces Rust implementations of the same CST classes and parser. These Rust implementations are compiled into Python extension modules (native libraries loadable from Python via PyO3, a Rust-to-Python bridge), so from a Python consumer's perspective, the Rust-backed CST classes and parser look and behave like the Python ones -- same class names, same methods, same type annotations -- but the underlying work happens in compiled Rust.

The Rust backend was built over approximately three months, motivated by the expectation that Rust would be faster than Python for parsing and CST operations. The backend is designed to be opt-in: a consumer chooses at generation time whether to use the Python or Rust backend, and the Python backend remains first-class and fully supported.

## What the assessment found: the verdict

The verdict is **refine-then-ship**, with medium-high confidence. In plain terms: the Rust backend is a genuinely healthy, well-tested system built on a sound architectural foundation. It is not a throwaway prototype, but it is also not yet a finished product. There is one safety defect that must be fixed before any production use, a small set of missing process controls that need to be installed, and some leftover prototype debris that should be cleaned up. The expensive, hard-to-reverse work -- the core Rust runtime, the structural separation between Python-dependent and Python-free code, the cross-backend compatibility contract, and a comprehensive test gate -- is done and verified clean. What remains is the kind of work normally finished during a controlled rollout.

The assessment explicitly considered and rejected two more drastic alternatives: restarting from scratch (unjustified -- the costly substrate is sound) and doing a large architectural refactor before shipping (premature -- the duplication is verified minor, and the safety preconditions for such a refactor do not yet exist).

The confidence is "medium-high" rather than "high" for two honest reasons: the performance benefit that motivates the whole backend has never been measured end-to-end, and the cross-backend correctness guarantee rests on a limited test corpus with no fuzz or property testing. Neither blocks an opt-in ship, but both must be addressed before the backend can claim to be a reliable drop-in replacement for arbitrary grammars.

---

## The parts of the system you need to understand

### The runtime layer (the crown jewel)

The Rust runtime is a set of hand-written Rust crates that provide the infrastructure generated parsers and CST nodes link against. Think of it as the plumbing: memory management for tree nodes, span tracking (which part of the source text a node corresponds to), the packrat memoization engine (which makes parsing efficient), and the machinery for making Rust objects look like Python objects.

The runtime is split along a deliberate architectural seam. There are two main runtime crates:

- **fltk-cst-core**: The CST runtime. It handles node ownership, the span data type, and the mechanism for safely sharing typed objects across separately-compiled Python extension modules. It optionally depends on PyO3 (the Rust-to-Python bridge), controlled by a feature flag. With the flag off, it compiles as pure Rust with no Python dependency.

- **fltk-parser-core**: The parser runtime. It provides packrat memoization, input source management, regex matching, and error tracking. It has no PyO3 dependency at all -- not even an optional one. This is enforced by the structural absence of a feature flag, which is the strongest possible guarantee: you cannot accidentally turn on what does not exist. A pure-Rust consumer can use the parser runtime with zero Python.

This split matters because FLTK's stated goal is that out-of-tree consumers should be able to use the generated Rust parser from pure Rust (no Python at all) or from Python (via PyO3). The split makes that real, not aspirational.

The entire unsafe surface (Rust code that bypasses the compiler's safety guarantees) in the runtime is exactly three blocks, all in a single file (`cross_cdylib.rs`), all performing the same operation: reinterpreting the memory layout of a Python object that came from a separately-compiled extension module. This is necessary because when two different compiled extensions each register their own version of the Span type with Python, Python sees them as different types even though they have identical memory layouts. The runtime uses a sentinel-based check (verifying version strings and layout sizes) to confirm compatibility before doing the unsafe reinterpretation. The safety comments in the code are unusually honest about the residual risks, which is itself a strength.

### The code generators

FLTK's code generation works in two layers, and understanding this distinction is essential to understanding the assessment's central architectural discussion.

The **semantic layer** -- which decides what classes to generate, what labels and child types each grammar rule produces, what the node-kind enum members are called -- is shared. The Rust CST generator wraps a real instance of the Python CST generator and delegates every model decision to it. A grammar-semantics change is implemented once and both backends pick it up.

The **emission layer** -- which turns those model decisions into actual source code -- is not shared. The Python backend builds a Python AST (abstract syntax tree) and unparses it, or builds an IIR (Intermediate IR, a typed code model) and compiles it. The Rust backend assembles lists of Rust source-code strings and joins them. There is no Rust-side AST, no Rust-side IR, and no shared abstraction between the two emission paths. The Rust generator is 2,351 lines of code versus the Python generator's 1,026 for the same semantic output, and the difference is almost entirely string-building volume.

This means that while the two generators agree on *what* to generate (because the model is shared), they independently re-implement *how* to generate it. A change to the per-label accessor surface -- say, adding a new method -- requires editing one place in Python but three or more places in the Rust generator (native implementation, PyO3 bindings, and the type-stub file), plus keeping the protocol module in sync.

### The cross-backend compatibility contract

The whole point of having a Rust backend is that a consumer can switch to it without rewriting their code. This is enforced through a generated Protocol module -- a single Python file that defines, for each grammar rule, a typing.Protocol class describing the interface both backends must satisfy. The Protocol is the contract: class names, label namespaces, accessor method names, and type annotations are all defined there, and both backends are checked against it using pyright (a Python type checker).

Cross-backend equality is particularly subtle. Python's enum-based NodeKind and Label types and Rust's PyO3 enum types are different Python types at runtime, so naive equality comparison would always return False. Both generators therefore emit a canonical-name-based equality scheme: each enum member carries a canonical string, and two values are equal if and only if their canonical strings match, regardless of which backend produced them. This means you can compare a label from a Python-parsed tree against a label from a Rust-parsed tree and get the correct answer.

### The test gate

The project has a comprehensive test gate (`make check`) that runs approximately 1,700 Python tests and 220 Rust tests, with zero skipped, zero ignored, and zero clippy warnings under strict settings, across the full Python-on/Python-off feature matrix. The gate builds all necessary test fixtures before running pytest, so the cross-backend parity tests genuinely execute -- they are not silently skipped.

The parity test suite includes a 63-entry corpus run through both backends, with assertions on tree structure, span positions, child counts, label equality, and error messages. There is also an end-to-end self-hosting equivalence test: parsing the same grammar through both backends and asserting the resulting Grammar Semantic Model is identical.

---

## What we are going to do and why

### Fix the one true blocker: the segfault

There is a public classmethod on the Rust-backed Span class (`_with_source_unchecked`) that can be called from pure Python with a hand-crafted object whose attributes mimic a legitimate native object. When this happens, the runtime's sentinel check passes (because it only verifies two attribute values), the code performs an unsafe memory reinterpretation on an object with the wrong memory layout, and the Python interpreter crashes with a segfault.

This is the only blocker. It matters because the Python backend it replaces is memory-safe in this same situation, and because a public method that crashes the interpreter from pure-Python input is not acceptable for a library consumed by external applications -- a buggy downstream caller or a fuzzer could hit it without any malicious intent.

The fix is bounded and well-understood: add a check that verifies the object is a genuine native PyO3 instance (not just a plain Python object with forged attributes) before performing the unsafe cast. This is hours to days of work, not an architecture problem.

### Install the regenerate-and-diff gate (the highest-leverage process fix)

The Rust backend's generated output -- approximately 75,670 lines of committed Rust source code -- is the actual public product. These files are generated by Python code generators, committed to the repository, and then compiled and tested. But nothing in the test gate or CI ever re-runs the generators and checks that the committed files match what the generators would produce. This means two failure modes are invisible: a generator regression that changes the output (CI tests the stale committed files and sees green), and a hand-edit to a committed generated file that CI cannot distinguish from legitimate generator output.

The fix is one step appended to the shared Makefile target: run the generators, then `git diff --exit-code`, failing if anything changed. This single step closes four independent major findings from the assessment and makes every subsequent change to the generators automatically verified. It is the cheapest high-leverage fix in the entire assessment.

### Add a @generated header to the CST output

The Rust parser generator already marks its output as machine-generated. The CST generator does not, which means the 15,515-line generated `cst.rs` files look like hand-written code to tools and reviewers. The fix is one line in the generator's preamble function.

### Put cargo-deny in CI

cargo-deny is a supply-chain security tool that checks for known security advisories, license violations, and yanked crate versions in Rust dependencies. It currently runs only via a local pre-commit hook that is itself uncommitted -- meaning a developer on a fresh clone, or one who bypasses the hook, gets no supply-chain enforcement. CI never runs it. A new security advisory in a transitive dependency is invisible to all automation. The fix is adding cargo-deny to the CI workflow.

### Build a differential testing harness (before claiming "drop-in for arbitrary grammars")

Cross-backend equivalence currently rests on 63 hand-picked test entries covering two grammars, with no property testing, no fuzz testing, and no differential testing (automatically generating inputs and comparing both backends' behavior). A real trivia-handling divergence already slipped through this corpus during development and was caught only by manual investigation. For the "drop-in for arbitrary grammars" claim to be credible, the parity surface needs random/generated input coverage over multiple grammars, wired into the gate.

### Add a regex-portability lint

The Python and Rust backends use different regex engines (Python's `re` and Rust's `regex-automata`), and these engines silently disagree on certain constructs: POSIX character classes, Unicode property classes, and some behaviors of `\d`, `\w`, and `\b`. A grammar that uses these constructs will parse differently on the two backends with no error at generation time and no test coverage. The fix is a generation-time lint that rejects non-portable regex constructs with a clear error, turning a silent wrong parse into a loud "this grammar is not portable to the Rust backend."

### Build a real performance harness

The Rust backend exists for speed, and after three months there is no end-to-end measurement comparing it against the Python backend, and no infrastructure to produce one. The one benchmark in the repository measures pure-Rust lock overhead on a hand-built proof-of-concept tree -- it never crosses the PyO3 boundary, runs against a stale copy of the CST, and is wired into no test target. Meanwhile, the code confirms that every Python-side child access pays a per-child cost (registry lookup, Arc clone, Python object materialization) that the project's own exploration warned could erase the performance advantage. A real harness measuring wall time and memory for both backends on representative workloads, including Python-side CST traversal, is needed to validate the premise.

### Delete the dead duplicate crate

During a refactoring, the canonical generated-code crate was moved from `tests/rust_cst_fegen/` to `crates/fegen-rust/`, but the original was never deleted. It is a byte-identical, 17,000-line dead duplicate that is built by nothing, tested by nothing, checked by nothing, and regenerated by nothing. It has a package-name collision with the canonical crate and a stale CHANGELOG pointer. It is concrete proof that the hand-maintained per-crate build configuration is itself a drift surface. The fix is `git rm -r`.

### Document the real scope boundary

The Rust backend is parse + CST only. There is no Rust unparser (the Python unparser is a large multi-file subsystem and a headline feature). The parser rejects certain grammar constructs (INLINE disposition, Invocation terms) at generation time, and the regex engine supports only a subset of what Python's engine supports. These are all legitimate scope decisions, but they are currently implicit -- a consumer reading the documentation cannot tell. The fix is documentation: a published compatibility matrix and explicit scope statements.

### Ship to a deliberate first consumer

The only real downstream consumer (Clockwork) currently consumes FLTK via a temporary local-path override, never a committed git reference. The Rust-Bazel integration path has never been validated through the actual code path a real consumer would use (fetching from a git repository). Flipping Clockwork to a committed pin and running its roundtrip test end-to-end is the proof that the drop-in story works in practice.

---

## The big strategic question: should we unify the code generators first?

This is the central disagreement the assessment had to adjudicate, and it deserves thorough treatment.

### The problem

The two code generators (Python and Rust) share their semantic layer (what to generate) but independently implement their emission layer (how to generate it). The Rust generator assembles raw strings; the Python generator builds an AST or typed IR. This means:

- The per-label accessor (a set of five methods per grammar label) is hand-emitted three times inside the Rust generator alone (native Rust implementation, PyO3 bindings, type-stub file), versus once in the Python generator. A change to this surface is a multi-site hand edit.
- The Rust generator had to build a 250-line identifier-collision detection subsystem that has no Python equivalent, because it emits into a flat namespace with no symbol table. An IR with a symbol table would have made collisions structurally impossible.
- The generator cannot verify its own output -- malformed Rust surfaces as a rustc error pointing into a 15,515-line file with no way to map back to the grammar rule that caused it.
- The Rust unparser (the next major planned feature) would be a third string-emitting generator, tripling the duplication.

### Why it was rejected (for now)

The assessment decided against refactoring the emission layer before shipping, for three reasons.

First, the duplication is verified to be minor in severity, not major. The most consumer-critical surface -- type annotations -- is not held together by convention and tests alone. It is mechanically conformance-gated: the Rust type stub is regenerated from the live generator and checked against the single-sourced protocol module using pyright, asserting zero errors. Annotation drift produces a type error, not silence. The behavioral surface is covered by enumerated parity tests. This is a maintenance tax with a partial safety net, not a correctness hole.

Second, the approach the duplication would be replaced with -- a shared backend-neutral IR -- was formally rejected twice in prior design decisions (in May and June 2026), with detailed reasons. The second rejection specifically refuted the key premise of the IR approach (that certain type annotations would be available "for free"), showing that the existing Python code had annotation bugs that would have to be fixed first. Re-litigating a twice-decided architecture bet carries its own costs and risks.

Third, and most importantly, the safety precondition for doing such a refactor -- the regenerate-and-diff gate described above -- does not yet exist. Refactoring the emission layer means changing what the generators produce, which means the committed generated code changes. Without a gate that catches generator-vs-committed divergence, the refactor would be the riskiest possible change against the most stable, most consumed surface in the system. The correct sequence is to install the gate first (which is itself a convergence-forcing mechanism), ship, and revisit the emission architecture when there is a natural forcing function.

### When to revisit

The assessment pins the decision to a specific trigger: the day the Rust unparser is started. That is when a third string-emitting generator would otherwise triple the duplication, and it is the moment when the cost of the IR (building a backend-neutral spec plus thin per-language renderers) is most clearly justified against the alternative (yet another independent string emitter). With the drift gate already in place by then, the duplication can be paid down incrementally and safely, or the IR can be built from scratch -- whichever the cost analysis favors at that point.

---

## What could go wrong and how it is handled

### The segfault (the one blocker)

A pure-Python object with forged attributes can trick the Rust runtime's sentinel check and cause a memory-safety violation. This is fixed by adding a genuine native-instance check before the unsafe cast. The check must be carefully designed: it cannot simply use isinstance, because a legitimate extension module compiled separately would have a distinct type object for the same Rust struct. The check needs to distinguish "a real PyO3 native instance from any cdylib" from "a plain Python object with copied attributes."

### Silent cross-backend divergence

The two generators could silently produce different behavior for the same grammar. This is mitigated by the shared semantic model (both generators agree on what to generate), the type-level conformance gate (annotation drift is a type error), and the parity test corpus (behavioral divergence on tested inputs is caught). The residual risk is behavioral divergence on untested inputs, which is why the differential testing harness is needed. A real divergence already slipped through once during development (a trivia-handling difference).

### Regex engine disagreement

The Python and Rust regex engines disagree on certain constructs. A grammar author who uses POSIX classes or Unicode property escapes will get different parse trees from the two backends with no warning. The generation-time lint addresses this by rejecting non-portable constructs loudly at generation time rather than producing silent wrong results at parse time.

### Performance might not materialize

The Rust backend exists for speed, but speed has never been measured. The per-child boundary-crossing cost (every Python-side access to a child node involves a hash-map lookup, Arc reference-count bump, and Python object materialization) is exactly the cost the project's own exploration warned could erase the advantage. Because the backend is opt-in and co-equal with the Python backend, this does not block shipping -- no consumer is forced onto it. But it means the "Rust is faster" claim is aspirational until measured, and a consumer migrating for speed has no evidence it pays off.

### Unbounded memo memory

The parser's packrat memoization retains the full memo table for the entire parse with no eviction or cap. On large or adversarial inputs, memory grows with input length times the number of grammar rules. This is a known packrat tradeoff, but it is undocumented, unmeasured, and unbounded. A downstream consumer parsing large files has no guidance on expected memory usage.

### Dead code and drift

The repository contains a byte-identical dead duplicate of the canonical generated-code crate, a proof-of-concept crate with a copied CST, and historical references pointing at moved paths. These are cleanup items, not safety issues, but they are concrete proof that the hand-maintained per-crate build configuration drifts when crates are moved or promoted. Deleting the dead duplicate and fixing stale references reduces the maintenance surface.

---

## What is still open

### Is the Rust backend actually faster?

The assessment does not know. After three months, there is no end-to-end measurement and no infrastructure to produce one. The per-child PyO3 boundary crossing is real and unmeasured. The assessment treats this as post-ship work rather than a gate, on the grounds that the backend is opt-in and a consumer can measure it themselves. But it is the most important unanswered question for anyone considering adoption for performance reasons.

### When and how should the emission layer be unified?

The assessment defers this to the day the Rust unparser is started, but the question is genuinely live. The restart advocate's case is that the duplication tax compounds with every new method, disposition, or accessor, and that refactoring becomes harder (and riskier to downstream consumers) as the generated surface grows. The counterargument is that the duplication is verified minor today, the IR was rejected twice on cost, the drift gate that would make a refactor safe does not yet exist, and the forcing function (the unparser) has not arrived. The assessment sides with deferral but explicitly preserves the trigger.

### Should the protocol's `children` type be tightened?

The Rust backend returns a fresh snapshot list from the `children` getter, while the Python backend returns the node's live internal list. This means in-place mutation of `node.children` (like `node.children.append(x)`) works on the Python backend but silently does nothing on the Rust backend. The Protocol types `children` as `list[...]`, which actively invites mutation. Tightening it to a read-only sequence type would steer consumers toward the sanctioned mutation methods (which work identically on both backends), but it would be a deliberate annotation change that downstream consumers would see. The assessment mentions this as an option but does not resolve it.

### How should the cross-cdylib ABI check be hardened?

The current sentinel check verifies a version string and a layout size. The code itself documents that size equality is necessary but not sufficient for layout identity -- a hypothetical pyo3 build that reordered internal fields while preserving total size would pass the check and produce undefined behavior. The code argues this is not constructible for the specific types involved (frozen, ABI3-stable), and the assessment accepted this as a minor residual risk. But the forgery path (a pure-Python object with copied sentinel values) is the source of the one blocker, and hardening it beyond attribute-value matching is an open design question.

### What about free-threaded Python?

The registry and shared-ownership machinery were designed under the assumption of Python's Global Interpreter Lock (GIL), which serializes access to Python objects. The code contains race-condition handling that is annotated "single-threaded Python: this never races." With the ecosystem moving toward free-threaded (no-GIL) Python, this assumption may weaken. The code degrades to an error rather than undefined behavior in the race case, so it is not a safety issue, but it is a noted design limitation.

---

## The recommended path, in sequence

The assessment recommends four phases, sequenced so that safety and integrity come first, validation second, cleanup third, and the strategic architecture decision is deferred to its natural trigger.

**Phase A** (must precede any production use): Fix the segfault. Add the regenerate-and-diff gate. Add the @generated header. Put cargo-deny in CI.

**Phase B** (before claiming "drop-in for arbitrary grammars"): Build the differential/property testing harness. Add the regex-portability lint. Build the performance harness.

**Phase C** (release engineering): Delete the dead duplicate crate. Document the real scope boundary. Accept the downgraded public-API divergences as migration-guide items.

**Phase D** (controlled rollout): Flip the downstream consumer to a committed git pin. Ship opt-in to a deliberate first consumer. Defer the emission-IR refactor decision to the day the Rust unparser is scheduled.
