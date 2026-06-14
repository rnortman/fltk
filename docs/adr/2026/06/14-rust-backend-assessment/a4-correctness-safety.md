# A4 — Correctness & Memory Safety (Rust backend)

Scope: every `unsafe` block, the `Shared<T>`/registry ownership + GC/eviction model, the
iterative `Drop`/`eq` machinery, the packrat `memo.rs`, the parse-depth limit, the
regex-anchoring DoS guard, panics crossing the pyo3 boundary, integer/Span arithmetic,
and reference-cycle leaks. All citations against HEAD `c0182064`. Findings are
reasoned from source and, where possible, **empirically confirmed by running the built
extension** (notes below the relevant finding).

Bottom line: the *core memory-safety engineering is genuinely careful and, where I could
test it, correct* — the iterative Drop/eq actually survives 80k-deep trees, the
no-pyo3 split is real, the parser DoS guards are wired through every generated entry
point. **But there is one reproducible, pure-Python-reachable SIGSEGV** (forged ABI
markers → `cast_unchecked` UB), the unsafe surface has **zero sanitizer/Miri coverage**,
the stack-safety machinery has **zero deep-tree regression test** (so it can silently
regress), and there are **two safe-Python-reachable leaks/footguns** (Arc cycles leak
where Python collects; source-blind node equality). Verdict for this dimension:
**adequate, gated by must-fix items before production** — the unsafe path is sound on
the fast (`fltk._native`) path and the residual UB is documented, but a segfault
reachable from pure Python and an untested stack-safety invariant are not acceptable for
a public API consumed out-of-tree.

---

## 1. `unsafe` inventory (exhaustive): 3 blocks, all in `cross_cdylib.rs`

`crates/fltk-cst-core/src/cross_cdylib.rs:86`, `:112`, `:331` — three `cast_unchecked`
reinterpreting a foreign Python object's memory as the local pyclass across a cdylib
boundary. Everything else (`shared.rs`, `registry.rs`, `span.rs`, `escape.rs`,
`error.rs`, `py_module.rs`, `memo.rs`, `terminalsrc.rs`, `errors.rs`, `src/lib.rs`) is
zero-unsafe. Confirmed: no `build.rs`, no `panic = "abort"` in any Cargo.toml (panics
unwind → `PanicException`, not process abort — good).

The gate before each cast is `check_abi_pair::<T>` (`:158-233`), validating two
**Python-readable, Python-forgeable** classattrs: `_fltk_cst_core_abi` (version string,
`span.rs:104`) and `_fltk_cst_core_abi_layout` (`size_of::<PyClassImpl::Layout>()`,
`span.rs:128`). On the canonical single-cdylib `fltk._native` fast path the unsafe is
never reached (`IS_CANONICAL_CDYLIB` short-circuits, `cross_cdylib.rs:258-266`). The
SAFETY comments are unusually honest and name their own residual unsoundness.

### Residuals the code itself admits
- **Size-preserving layout skew is undetected** (`:101-108`, `:325-330`,
  `span.rs:117-126`): size equality is necessary, not sufficient, for layout identity.
  The argument that a size-preserving reorder is "not constructible" is a plausibility
  claim, not a proof. Narrows, does not close, the window.
- **Forgery → UB** (`:46-53`, `span.rs:439-443`): both markers are plain Python values.
  A pure-Python class with matching markers passed to the underscore-private
  `_with_source_unchecked` reaches `cast_unchecked` with a non-pyclass layout. Defended
  only by the leading-underscore naming convention.

→ See **F1** (this is reproducible, not theoretical) and **F2** (no Miri/sanitizer).

---

## 2. Empirically reproduced: pure-Python forgery → SIGSEGV (F1)

I built the extension (`maturin develop`, success) and ran:

```python
from fltk._native import Span, SourceText
class Forged:
    _fltk_cst_core_abi = SourceText._fltk_cst_core_abi          # correct version string
    _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout  # correct layout int
Span._with_source_unchecked(0, 5, Forged())
```

**Process exit code 139 (SIGSEGV).** Both markers are readable from any `SourceText`
class object and copyable onto a plain Python class; the gate (`check_abi_pair`) passes
because it only checks the two integer/string values, then `extract_source_text`
(`cross_cdylib.rs:112`) does `cast_unchecked::<SourceText>()` and dereferences
`st.get().inner` on a pure-Python object → segfault.

`_with_source_unchecked` is a `#[classmethod]` (`span.rs:444-453`), so it is a fully
public, callable attribute of `fltk._native.Span`. "Private by convention" means nothing
to (a) a buggy downstream library, (b) untrusted code sharing the interpreter, or (c) a
fuzzer. For a library whose generated output is consumed out-of-tree, a public method
that segfaults the interpreter on a pure-Python argument is a correctness/robustness
defect, even if the documented "contract" excuses it. (Also note: this is a *type
confusion* primitive, not merely a crash — with a crafted object it can read arbitrary
offsets as an `Arc<SourceInner>`.)

The forgery and ABI-mismatch *rejection* paths are well tested
(`tests/test_rust_span.py:347-842`), but — necessarily — **the actual UB path is
untestable and untested**; the only defense is the naming convention.

---

## 3. No Miri / sanitizer / cross-version coverage of the unsafe (F2)

`grep` over `Makefile`, `.github/`, `deny.toml`: **no `miri`, no ASan, no
`MIRIFLAGS`**. The entire `unsafe` surface — three `cast_unchecked` blocks whose
soundness rests on a same-rlib/same-pyo3-layout invariant — is verified only by
functional tests that all run within a *single* build where the invariant trivially
holds (`tests/test_rust_span.py`, `test_phase4_rust_fixture.py`). The cross-cdylib test
(`test_rust_span.py:399`) uses `phase4_roundtrip_cst`, which links the *same*
`fltk-cst-core` — so it never exercises an actual layout/version *mismatch* under
`cast_unchecked` (the thing the gate exists to catch); it only exercises the happy
matching case. There is no test that builds two extensions at genuinely different
`fltk-cst-core` / pyo3 versions and proves the gate produces `TypeError` rather than UB.
For the project's *primary* multi-cdylib use case, the unsafe is effectively unverified
under the conditions it was written to handle.

---

## 4. `Shared<T>` / registry / iterative Drop / eq — sound today, untested for the property it exists for

### What's right
- `Shared<T> = Arc<RwLock<T>>` (`shared.rs:51`), zero unsafe, poison-ignored
  (`:61,:66`), `ptr_eq` short-circuit in `PartialEq` (`:108-114`) to avoid same-thread
  double-read-lock deadlock. Documented DAG-deadlock residual (`:27-36`) is precise and
  only bites under a concurrent writer — impossible under the GIL single-writer model.
- `registry.rs` is a `WeakValueDictionary` identity cache keyed by Arc address, not a
  Rust GC. The ABA argument (`:19-22`) holds: the canonical handle holds the `Arc`
  strongly, so an address can't recycle while a live entry exists. Zero unsafe.
- Iterative `Drop` (generated `cst.rs:322-341` + `DropWorklistItem::drain_into`
  `:15156-15267`) and iterative `eq` (`:346-366` + `EqWorklistItem::compare`
  `:15296-15472`) replace recursion with an explicit worklist to avoid
  attacker-controlled-depth stack abort. The `strong_count()==1` steal logic
  (`:15163`) is correct: I traced the diamond-DAG case (two entries → two worklist
  items → first sees count 2, no steal; second sees count 1, steals) and it does the
  right thing.

### Empirically confirmed the machinery works
- Built an **80,000-node-deep** owned chain (`Items→Item→Term→Alternatives→Items…`) via
  the public `append()` API and dropped it: **no stack overflow, exit 0.**
- Compared two independent 80k-deep trees with `==`: returns `True`, **no overflow.**

So the iterative machinery is genuinely correct on deep owned chains today.

### The gap (F3): zero deep-tree regression test
The entire justification for the worklist machinery is the threat model spelled out in
the generated comments: "tree depth is attacker-controlled for parsers over untrusted
input, so `{:?}`/drop on a deep tree would abort the process (stack exhaustion,
uncatchable)" (`cst.rs:305-309`, `:319-321`, `:343-345`). Yet **no test anywhere
constructs a deep tree to verify Drop/eq/Debug don't overflow**:
- `test_phase4_rust_fixture.py:463` "deep_tree" parses `"a = 1; b = 2; c = 3;"` — that is
  3 levels, not deep.
- spike `spike_tests.rs` (43 tests) has eq/deadlock tests but no deep-tree case.
- No Rust `#[test]` named `*deep*`/`*overflow*`/`*drain*` exists in any crate.

Because generated `cst.rs` carries no `@generated` header and `make check` runs no
gencode-drift gate (per U5/U7), a regression of the generator back to a derived
`Drop`/`PartialEq` — or a hand-edit — would compile clean, pass every existing test, and
silently reintroduce an *uncatchable process abort* DoS on deep untrusted input. The
safety property is real, currently satisfied, and completely unguarded against
regression.

---

## 5. Reference cycles leak from safe Python — and this *diverges* from the Python backend (F4)

`shared.rs:42-47` says cycles leak (Arc can't break them) and calls this "the same
contract as the Python backend." I tested both backends:

- **Rust**: built a cycle through the public API
  (`items→item→term→alt→items`), dropped all handles, `gc.collect()` — no crash, and the
  Rust `Arc` cycle is unreclaimable (Python's cyclic GC cannot traverse into the
  `Shared<T>` graph). Leak is silent and permanent.
- **Python backend**: built the analogous cycle, took `weakref`s, `del` + `gc.collect()`
  → **both nodes collected** (`a alive? False, b alive? False`). Python's cyclic GC
  reclaims node cycles because the nodes are ordinary GC-visible Python objects.

So the "same contract" claim is **false**: a downstream consumer who creates a CST cycle
(easy: `node.append(ancestor)`) gets transparent reclamation on Python and a permanent
memory leak on Rust. For a long-running process (a language server, a build daemon —
exactly the kind of out-of-tree consumer FLTK targets) this is an unbounded leak
reachable from entirely safe code, and it is a genuine cross-backend behavioral
divergence relative to the drop-in promise. Severity major: it's a real divergence and a
real leak, though it requires the consumer to build a cycle (not the parser's normal
output, which is a tree).

---

## 6. Source-blind node equality: footgun, but parity-preserving (F5)

`Span::eq` ignores `source` (`span.rs:176-180`), and the iterative node `eq` compares
spans with it (`cst.rs:15305` etc.). I confirmed two `Items` nodes with identical offsets
`(0,5)` but different source text (`"hello"` vs `"world"`) compare **equal**. This means
CST nodes parsed from *different files* at the same offsets are `==`. It is the
documented contract and it is **identical on the Python backend** (so not a divergence),
but the public Protocol types `span` as a real `Span` and nothing signals that equality
is source-blind — a consumer diffing two parse trees can get false "equal". Minor/nit
(documented + parity-preserving), but worth a louder note in the public docs.

---

## 7. Parser runtime: memo, depth limit, regex anchoring — correct, with a panic caveat

### Depth limit (correct, fully wired)
`apply` (`memo.rs:182-201`) increments `depth`, checks `depth_exceeded || depth >=
max_depth` (`:192`) → sets sticky `depth_exceeded` and returns `None`. The sharp caller
obligation ("check `depth_exceeded()` and discard the result if set", `:158-164`) **is
honored by the generated binding**: every `PyParser::apply__parse_*` method checks
`self.inner.depth_exceeded()` after the call and raises `PyRecursionError`
(`parser.rs:1427-1430` and the 13 siblings). So the footgun is closed in generated code;
a hand-written pure-Rust consumer calling `apply` directly must still obey it (documented
only in doc-comments). Boundary arithmetic (`>=`, increment-before-check) is correct:
max 1000 concurrent applies, matching the 8 MiB-stack sizing rationale (`:64-73`).

### Regex anchoring DoS guard (correct)
`consume_regex` (`terminalsrc.rs:141-166`) uses `regex-automata` with
`Anchored::Yes` over the full haystack + `span(byte_pos..len)` — a non-match fails
immediately without scanning forward, and `\b`/`\B` resolve against the char before
`byte_pos` (tested `:368-389`). Linear-time engine (no catastrophic backtracking). The
byte→codepoint conversion uses `partition_point` with a `debug_assert` char-boundary
check (`:160-164`). Sound. (Note: the boundary `debug_assert` is compiled out in release
— if a non-char-boundary ever occurred the subsequent slice would panic, not corrupt, so
acceptable.)

### Panics crossing pyo3 (F6, minor)
`memo.rs` ports all Python `assert`s as always-on `assert!` plus two `panic!`s: the
"Untested corner case" (`:227`, faithful port of `memo.py:181-187`'s `NotImplementedError`)
and a memo-invariant violation (`:233`). Under pyo3 these become `PanicException`.
Two concerns:
1. The Python original raises a *catchable, expected* `NotImplementedError`; the Rust
   port raises a `PanicException` and — per the doc at `:84-91` — on a panic the `depth`
   counter is **not decremented**, so the parser instance is silently corrupted ("spent")
   even though Python can catch the exception and might reuse it. The mitigation is a
   doc-comment only ("treat any PanicException as instance spent"), not enforced by the
   API. A reused parser after a caught `PanicException` would observe a stale `depth` and
   could spuriously trip `depth_exceeded`.
2. Reachability of the corner-case panic is believed-unreachable (same as Python), so the
   liveness risk is low — but "panic in a parser over untrusted input" is a heavier event
   in Rust than `NotImplementedError` is in Python. Faithful port, so minor.

The `assert!`s (`:276,:304,:332,…`) and `setup_recursion` bounds (`:373,:379`) are
algorithm invariants; if any fired it would be a memo bug, not attacker-reachable.

---

## 8. Integer / Span arithmetic — no overflow found

Checked: `Span::merge`/`intersect` use `i64 min/max` (no overflow for realistic spans);
`len()` guards negatives and `.max(0)` (`span.rs:337-342`); `text()` casts `i64 as usize`
only after `< 0` guards (`:288-294`); `consume_literal`/`consume_regex` index
`cp_to_byte[pos as usize]` only after `pos < 0 || pos > len()` guards
(`terminalsrc.rs:111,142`); the `insert` clamp `n as i64 + i` (`cst.rs:772`) operates on
`Vec::len()`-bounded values. `pos_to_line_col` domain is `[-1, len]` with an `assert!`
bisect invariant (`terminalsrc.rs:210`). No realistic overflow path. `errors.rs` farthest-
failure tracking and `py_repr_str`/`format_error_message` are allocation-tight and
byte-pinned to Python with golden tests. Clean.

---

## 9. Legacy loaded gun (minor): `get_source_text_type` is not ABI-validated

`cross_cdylib.rs:384` retains `get_source_text_type` for "previously-generated consumer
cst.rs" and explicitly returns a **non-ABI-validated** type, with a doc warning "callers
MUST NOT use it for `cast_unchecked`" (`:380-383`). I confirmed **no committed generated
`cst.rs`** (fegen-rust, rust_cst_fixture, rust_poc_cst, rust_parser_fixture) calls it or
`source_full_text_str` — current generation uses the validated `span_to_pyobject` path.
So it's dead-but-public: a second unvalidated entry point kept alive in the public API
for backward compat, currently untriggered. Minor (latent), but it widens the
forgery/skew attack surface and should be retired once no shipped consumer needs it.

---

## Severity-ranked findings

| id | title | sev | conf |
|----|-------|-----|------|
| F1 | Pure-Python forged ABI markers → reproducible SIGSEGV via public `_with_source_unchecked` | blocker | high |
| F3 | Stack-safety (iterative Drop/eq) invariant has zero deep-tree regression test; silently regressable | major | high |
| F4 | Reference cycles leak on Rust but are GC-collected on Python — false "same contract", safe-code leak | major | high |
| F2 | Unsafe cross-cdylib path has no Miri/sanitizer and no real version/layout-mismatch test | major | high |
| F6 | memo `panic!`/`PanicException` corrupts parser depth state; only doc-enforced "instance spent" | minor | high |
| F5 | Source-blind node equality (parity-preserving footgun, not a divergence) | minor | high |
| F7 | Non-ABI-validated `get_source_text_type` retained as public, currently-unused loaded gun | minor | medium |

The fast-path (`fltk._native` single cdylib) is sound and the parser DoS guards are
correctly wired. The blocker is F1 (a public method that segfaults from pure Python);
F2/F3/F4 are the must-address-before-production gaps in *verification and cross-backend
fidelity* of otherwise-careful code.
