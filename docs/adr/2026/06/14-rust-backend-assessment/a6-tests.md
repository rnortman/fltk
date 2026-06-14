# Dimension A6 — Test Coverage & Quality (Rust backend)

Verdict: **adequate**, trending toward strong on the runtime/parity layers but with two
material blind spots: (1) the generator's correctness is validated almost entirely by
brittle substring assertions against emitted source text, and (2) the single most
dangerous safety property — the iterative Drop/eq/Debug worklist that exists to stop an
attacker-controlled deep tree from aborting the process — is implemented but never tested
at a depth that would trip a recursive implementation. There is no property/fuzz/differential-random
testing anywhere, and no Rust line-coverage tooling, so branch coverage of the unsafe ABI
boundary and the packrat memoizer is unmeasured.

Ground truth on this machine: the cross-backend/parity/registry subset runs (not skips):
`157 passed, 0 skipped` for the parity+bindings+registry files; the full `make check` is
green per the build-health map. So the tests that exist *do run* in the gate (Makefile
`test:` depends on `build-test-fixtures`). The problem is not flakiness or silent skipping
on a correctly-invoked gate — it is *what is and isn't asserted*.

---

## What is genuinely good (do not discount)

- **Packrat memoizer (`memo.rs`) is well-tested via a hand-written toy parser.**
  `crates/fltk-parser-core/tests/memo_toy.rs` (13 tests) ports the full Python `test_memo.py`
  suite: direct + indirect + multi-path left recursion (test_direct/test_indirect/test_multi_b/c),
  failure-seed poisoning (test_fail:396), failure caching no-recompute (test_failure_caching:431),
  and the entire depth-limit contract T1–T5 including the subtle "flag outranks Some" truncated-parse
  case (test_depth_limit_t4_some_with_flag:540) and the sticky-flag-not-cache distinction
  (test_depth_limit_t3_sticky:507, which clears caches to prove stickiness). These are real
  behavioral assertions, not smoke tests. Note `memo.rs` has 0 inline `#[test]` — all coverage is
  in the external `tests/memo_toy.rs` integration file, which is correct (it exercises the public API
  the way generated code does).

- **Depth-limit DoS guard is tested through real Python bindings**, not just the Rust toy.
  `tests/test_rust_parser_fixture_bindings.py` (T5/T6/T7): `_make_nest(50)` with `max_depth=10`
  raises `RecursionError` (:35-39); `max_depth=200` succeeds (:42-47); the "spent instance"
  stickiness is verified across a *cold-cache different rule* (:77-92), proving the sticky flag,
  not a cached Failure, drives the second raise. T6 (:99-105) pins that the default 1000 limit
  fires on `DEFAULT_MAX_DEPTH+100` nesting *before* a native stack overflow — i.e. the guard
  actually protects the process. This is the must-check-caller obligation flagged in the runtime
  map, and it is covered at the binding layer.

- **Registry/GC eviction tests are disciplined and meaningful.**
  `tests/test_registry_gc_eviction.py` documents and enforces real test-authoring hazards
  (delta-not-absolute assertions because the registry is process-wide; snapshot dicts hold strong
  refs and must be del'd; id()-reuse must not be asserted against). It covers the core ABA scenario
  (`test_arc_alive_handle_dead_fresh_handle_no_resurrection`:136 — handle GC'd while Arc still alive
  in parent, fresh handle minted at same address, canonical identity stable), a 200-iteration
  create/drop stress (:166), and direct registry semantics (register_if_absent True/False,
  force_register overwrite, weak eviction, re-register after eviction). It is honest about the one
  arm it *can't* force from single-threaded CPython (the concurrent-install race, :197-211).

- **Parity comparators have negative self-tests** — the verifier is itself verified.
  `tests/test_rust_parser_parity_fegen.py:104-339` proves `assert_cst_equal` and
  `assert_error_equiv` actually FAIL on kind mismatch, span mismatch, child-count mismatch (with
  hand-built same-span nodes so length is the only discriminator, :164-185), label mismatch, deep
  nested mismatch (:221), and both species directions (node-vs-span / span-vs-node). Likewise the
  error-message comparator (`_assert_messages_equiv`) is negatively tested for header/group-order/
  token-set divergence. This is a high-quality discipline that most projects skip.

- **The nullable-loop guard test is the gold-standard pattern.**
  `tests/test_nullable_loop_guard.py::test_rust_backend_guard` (:357-413) *generates Rust from a
  synthesized trigger grammar, monkeypatches the validator to let the dangerous grammar through,
  cargo-builds the result, runs it under a 10s timeout, and fails if it hangs* (infinite loop on
  nullable repetition). This is end-to-end generator→compile→run→behavior. It is the only test that
  does this, for exactly one property.

- **escape.rs / errors.rs cross-language byte-pins are well-covered.**
  `escape.rs` (9 tests): table-driven control chars, bidi embedding/override/isolates/implicit-marks,
  line/paragraph separators, zero-width chars, mixed `\xHH`/`\uXXXX`. The parser-parity fixture corpus
  also drives control/bidi/invisible chars through the real error-formatting path
  (`test_rust_parser_parity_fixture.py:113-127`: ESC `\x1b`, RLO U+202E, LRI U+2066, ZWSP U+200B,
  LS U+2028). `errors.rs` has 25 inline tests.

- **The committed fixture `cst.rs`/`parser.rs` are compiled + clippy'd by `make`** (build-test-fixtures
  → fegen-rust, rust_parser_fixture, poc_cst, phase4; cargo-clippy -D warnings). So the brittle
  string assertions in `test_gsm2tree_rs.py` are *backstopped* for the specific committed grammars by
  a real "it compiles and is lint-clean" signal. The gap (below) is that this only covers the handful
  of committed grammars, not arbitrary downstream grammars.

---

## Findings

### a6-tests:deep-tree-drop-eq-untested — BLOCKER (high confidence)
The iterative worklist Drop/PartialEq/Debug machinery in `crates/fegen-rust/src/cst.rs:305-364`
(and the byte-identical `crates/fltk-cst-spike/src/cst.rs:1087+`) exists *specifically* to prevent a
deep tree from overflowing the stack and aborting the process. The code comments are explicit:
"so `{:?}` on a deep tree would abort the process (stack exhaustion, uncatchable abort). Drains the
subtree via a worklist instead" (cst.rs:308,321,345). **No test builds a deep tree (tens of thousands
of nodes) and verifies Drop, `==`, or `{:?}` complete without overflowing the stack.** The
misleadingly-named `test_phase4_rust_fixture.py:463 test_node_eq_distinct_allocation_deep_tree`
parses `"a = 1; b = 2; c = 3;"` — a ~3-deep tree — and only exercises the *delegation chain*, not
depth. `shared.rs:33-44` documents that even the worklist itself can loop indefinitely / grow
unboundedly under a queued-writer DAG, also untested. A regression that reintroduced naive recursion
into any of Drop/eq/Debug would pass `make check` and CI 100% green, then abort a downstream
consumer's process on adversarial nested input — exactly the DoS this machinery was built to stop.
Remediation: add a Rust integration test (and ideally a Python binding test) that constructs an
N≈100_000-deep owned chain and asserts Drop, `==` (distinct allocations), and Debug-format all return
without crashing.

### a6-tests:no-property-or-fuzz-testing — MAJOR (high confidence)
Zero property-based, fuzz, or randomized differential testing exists anywhere in the backend
(`grep -rniE "proptest|quickcheck|fuzz|arbitrary"` over all `.rs`/`.py`/`.toml` returns only two
unrelated prose hits). Cross-backend parity — the entire near-drop-in claim — rests on two *fixed,
hand-written* corpora: ~19 entries in `test_rust_parser_parity_fegen.py` and ~44 in
`test_rust_parser_parity_fixture.py` (each × 2 trivia modes). The corpora are thoughtfully chosen
(left/indirect recursion, quantifiers, separators, multibyte, control-char escaping, depth nesting),
but they are a closed set. A grammar/input combination on an uncovered path can silently diverge
between Python and Rust with no type error and no test failure — and the runtime map already records
that a real trivia divergence occurred during development. The single highest-value addition would be
a differential fuzzer that generates random valid+invalid inputs for the fixture grammar and asserts
`assert_cst_equal` / `assert_error_equiv` across backends. Remediation: add `cargo-fuzz` or a
Python-side randomized input generator wired through the existing `run_parity_corpus_entry` harness.

### a6-tests:generator-tested-by-substring-not-behavior — MAJOR (high confidence)
`tests/test_gsm2tree_rs.py` (195 test fns, 366 asserts) is the primary generator test, and its own
docstring states it "validate[s] the source text produced by the generator, not the compiled Rust
output" (:1-6). **316 of 366 assertions (86%) are substring matches** of the form
`assert "...some rust snippet..." in source` / `not in source` (e.g. :176,188,195,220,225). These are
brittle and partly tautological: they re-encode the exact strings the generator emits, so a
behavior-preserving refactor of the emitter forces test churn, while a *behavior-changing* emit can
pass as long as the asserted substring survives. The IIR-bypassing string-emission design (the Rust
generators emit `.rs` text directly, no AST/typecheck) means the generator itself cannot verify its
output is even syntactically valid — that only surfaces at `cargo build`. The compile signal exists
only for the handful of *committed* fixture grammars (build-test-fixtures), not for the generator's
behavior on arbitrary grammars. The nullable-loop-guard test (generate→compile→run) proves the
better pattern is achievable but it is applied to exactly one property. Remediation: add a small
matrix of synthesized grammars that are generated, cargo-built, and behaviorally asserted (the
nullable-guard pattern), so generator correctness is validated by compilation+behavior rather than
string identity.

### a6-tests:unsafe-abi-layout-skew-untested — MAJOR (medium confidence)
The only 3 `unsafe` blocks in the runtime (`cross_cdylib.rs:86,112,331`, `cast_unchecked`) are gated
by a *forgeable* ABI sentinel (version string + `size_of` layout int). The tests in
`tests/test_rust_span.py:244-439` and `test_phase4_rust_fixture.py:538-575` do exercise the *guard*
thoroughly — foreign-cdylib SourceText acceptance (via the separately-built phase4 fixture, a genuine
second cdylib), missing/non-str/bogus marker rejection, escaped type names, and a wrong layout int
(`999999`, :574) producing the right TypeError. **But the residual-UB path the runtime map flags —
a *size-preserving field reorder* that passes the `size_of` probe yet has skewed layout, and the
pure-Python forgery of `_with_source_unchecked` — is by construction unreachable from safe test code,
so it is untested and arguably untestable.** The sentinel is a *narrowing* defense, not a closing one,
and there is no test (or even a `#[should_panic]`/Miri lane) that pins the boundary's behavior under
deliberate layout skew. `cross_cdylib.rs` and `registry.rs` and `span.rs` have 0 inline `#[test]`;
their coverage is entirely Python-binding-level. Consequence: a future fltk-cst-core change that
reorders Span/SourceText fields without changing size would pass every test and silently introduce UB
across the cdylib boundary for downstream consumers who build their CST extension against a different
fltk-cst-core rlib. Remediation: at minimum add a Miri lane over the cross_cdylib unit path, and a
build-invariant doc-test asserting same-rlib/same-pyo3; document the layout-skew gap as a known
residual risk in the deny/CI surface.

### a6-tests:no-rust-line-coverage — MAJOR (high confidence)
There is no Rust coverage tooling anywhere (no tarpaulin/llvm-cov/grcov in Makefile, pyproject,
deny.toml, or `.github/`). Python has `coverage[toml]` configured but **no `fail_under` gate**
(`grep fail_under` → none). Consequence: branch coverage of the security-critical runtime — packrat
memoizer error/poison arms (`memo.rs` has always-on `assert!`/`panic!` including a "faithfully-ported
Untested-corner-case" that becomes a `PanicException` under pyo3, per the runtime map), the registry
race arm, the cross_cdylib slow-path arms — is entirely unmeasured. Nobody can answer "which lines of
the unsafe boundary or the memoizer are never executed by any test." For a project whose generated
output is the public product, the absence of a coverage signal means dead/untested error paths are
invisible. Remediation: add `cargo llvm-cov` (works across the workspace + standalone crates) to the
local check family and surface a coverage report; consider a `fail_under` floor for the runtime crates.

### a6-tests:no-gencode-drift-gate — MAJOR (high confidence)
`make check`/`check-ci`/`check-common` never run `make gencode` followed by `git diff --exit-code`.
The `gencode` target's own comment admits drift detection is manual: "`git diff --stat` reveals any
drift between committed generated files and the [generators]" (Makefile:245-247). ~75k lines of
committed generated Rust (the public-API CST surface across fegen-rust + 4 fixtures) are regenerated
only by a human running gencode. Consequence: a generator regression that produces *different* output
than what's committed passes CI (CI compiles the stale-but-valid committed code), and conversely a
hand-patched committed `cst.rs` passes CI while being unreproducible from the generator. The tests
validate the *committed artifact*, not that *the generator still produces it*. This is squarely in the
test-quality dimension because it determines whether the generator unit tests (which assert against
freshly-generated strings) and the fixture compile/behavior tests (which run against committed code)
are testing the *same* thing — today they can drift apart undetected. Remediation: add a CI step that
runs gencode and `git diff --exit-code` over the generated paths.

### a6-tests:parity-corpus-shallow-and-closed — MINOR (high confidence)
Beyond the no-fuzz point: the parity corpora never exercise the *known feature gaps* as parity
entries — INLINE disposition and Invocation terms raise `NotImplementedError` in the Rust parser
generator, and there is no parity test that a grammar using them is *rejected consistently* or
flagged; they are simply absent from every corpus. The fegen self-host parity runs on the reduced
`fegen.fltkg`, not the richer `fltk.fltkg` (which the Rust backend cannot handle), so the
"it self-hosts" parity evidence understates the real Python-parity distance. The corpus also has no
entry larger than a few hundred bytes, so memoizer cache behavior and span computation at scale are
unexercised. Remediation: add explicit "this grammar is unsupported and rejected with a clear error"
tests for INLINE/Invocation/lookahead-regex, and a large-input parity entry.

### a6-tests:children-snapshot-trap-untested-as-divergence — MINOR (medium confidence)
The runtime/parity maps flag the highest-severity "works on Python, wrong on Rust" trap: the Rust
`children` getter returns a per-call snapshot list so in-place mutation is a silent no-op, while
Python returns the live list, and the Protocol types `children` as a mutable `list[...]`. The mutator
parity suite (`test_cst_mutators_parity.py`, 63 fns) exhaustively tests the *sanctioned*
insert/remove_at/replace_at/clear path and asserts byte-equal error messages, which is good. But there
is no test that *pins the divergence itself* — i.e. asserts that `node.children.append(x)` mutates the
tree on Python and is a no-op on Rust — so a future change that accidentally made the Rust getter
return a live list (or made Python return a snapshot) would not be caught as a parity regression; it
would just silently change behavior. Pinning a known divergence with an explicit asserting test is the
standard way to make it a *contract* rather than an accident. Remediation: add a test that documents
and pins the snapshot-vs-live behavior on each backend.

---

## Note on prompt premise
The prompt named generator unit-test files `test_gsm2parser_rs.py` (43K), `test_genparser.py`,
`test_gsm2lib_rs.py`, `test_name_validation.py`, `test_nil_validation.py`. **None of these files
exist** (`ls tests/` confirms). The Rust *parser* generator (`gsm2parser_rs.py`) and the *lib*
generator (`gsm2lib_rs.py`) and the `genparser.py` CLI have **no dedicated unit-test file**: parser-
generator behavior is exercised only indirectly (the generated fixture parsers are compiled and run
through parity), `RustParserGenerator` is touched directly only inside `test_gsm2tree_rs.py` and
`test_nullable_loop_guard.py` for construction-time validation, and `gsm2lib_rs.py` /
`genparser.py` have essentially no behavioral unit coverage. Name-validation / collision logic is
covered as classes inside `test_gsm2tree_rs.py` (TestReservedLabelRejection,
TestReservedClassNameRejection, TestCrossRuleIdentifierCollisions). This is itself a coverage finding:
the parser generator — the newer, scope-crept half of the backend — is the least directly unit-tested
generator, validated mostly by the closed parity corpus.
