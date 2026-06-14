# A1 — Architecture Soundness & Long-Term Coherence (Rust backend)

Dimension judge for the production-readiness retrospective. Scope: the big structural
bets — (a) dual generators, (b) direct string emission vs IIR, (c) the crate split,
(d) the cross-cdylib ABI sentinel + handle/registry/Shared<T> machinery. All citations
against HEAD `c0182064`. `.claude/worktrees/**` ignored throughout.

Verdict up front: **adequate-leaning-sound foundation, with one structural liability
(dual string-emitting generators) that should be addressed before this is called
production-grade — but NOT a restart.** The runtime crates and the crate split are
coherent and well-factored. The generator architecture is the weak bet: it works, it is
honestly documented, it is backstopped by real tests that actually run — but it locks in
a permanent dual-maintenance drift surface that has already drifted, and it manufactured
two whole Rust-only subsystems (collision detection + lint-suppression conditional
emission) that a structured IR would have folded into the framework. That is a
fix-before-scale liability, not a tear-down.

---

## (a) DUAL GENERATORS — the central architecture bet

### What it actually is

There are two emission paths kept behaviorally identical by convention + pinned tests,
**with no shared emission abstraction**:

- Python: `gsm2tree.py` (1026 LoC) builds a real `ast.Module`; `gsm2parser.py` (845 LoC)
  builds an `iir.ClassType`. Both go through unparse/compile.
- Rust: `gsm2tree_rs.py` (2351 LoC) and `gsm2parser_rs.py` (1036 LoC) assemble
  `list[str]` of `.rs` source lines and `"\n".join` them. No IIR, no AST.

The **model/front-end layer IS genuinely single-sourced**: `RustCstGenerator.__init__`
instantiates a real Python `CstGenerator` (`gsm2tree_rs.py:165-170`) and delegates every
grammar-semantic decision to it — `rule_models`, `class_name_for_rule_node`
(→ `naming.snake_to_upper_camel`), `node_kind_member_name` (explicitly "single source of
truth" `gsm2tree_rs.py:527-533`), `protocol_annotation_for_model_types`. A change to
*which children/labels a rule produces* is implemented once. This is the right seam and
it is real.

But the **emission layer is fully duplicated, and the Rust parser generator does not even
import the Python parser generator** (verified: the only reference in `gsm2parser_rs.py`
to `gsm2parser` is a *comment* — "Mirrors the identical Python guard in gsm2parser.py"
at `gsm2parser_rs.py:697`). The two parser generators share zero code. Parity is held by
(i) comments ("Mirrors the Python reference", 7 such comments in `gsm2tree_rs.py`, 4 in
`gsm2parser_rs.py`) and (ii) the cross-backend parity test corpus.

### Is it sustainable, or will it drift?

It has **already drifted**, in a way that proves the convention is not mechanically
enforced:

- Memo-cache field naming: Python emits `_cache__parse_X` (`gsm2parser.py:387`,
  `cache_name=f"_cache__{base_name}"`) while Rust emits `cache__parse_X`
  (`gsm2parser_rs.py:155`, `cache_field = "cache__" + name`). These are supposed to be
  "side-by-side auditable" with "same path-tuple bookkeeping" (design §2.7), yet the
  field names diverge. It's internal so it's harmless *today* — but it is direct
  evidence that "kept identical by hand" does not hold even for the names the design
  explicitly claims are matched for auditability.
- A Python/Rust **trivia-capture behavioral divergence** already required a root-cause
  investigation (`docs/adr/2026/06/05-cst-type-annotations-regression/trivia-divergence-rootcause-v2.md`,
  per U1) — i.e. a *behavioral* drift, not just a cosmetic one, reached the tree.

The drift surface is **large and N-sited**. A single grammar-semantics change to the
generated public API surface forces edits across:
- Python: `_emit_label_quintet` (once, shared concrete+protocol, `gsm2tree.py:820-867`).
- Rust: the per-label quintet is re-emitted **three times** — pymethods
  (`_per_label_methods` `gsm2tree_rs.py:2039-2136`), native (`_native_per_label_methods`
  `:1738-2012`), and the `.pyi` stub (`generate_pyi` `:377-386`) — plus the protocol in
  `gsm2tree.py`. So one accessor-surface change = 1 Python edit + 3 Rust edits + 1
  protocol edit, held together only by tests.

The same N-site fan-out applies to mutators (native + pymethod + pyi + Python),
dispositions, separators, and parser fn-naming (U3 §3 table). This is the dual-maintenance
burden the **original exploration explicitly flagged up front** ("~2,550 lines of
generator logic duplicated", "dual maintenance burden", U1 §1.1) — the project chose the
path it had already named as carrying the largest duplication cost, with eyes open
(design §2.7 "Two generators that can drift").

### Would a shared IR / single-source generator have been better?

The team's **rejection of the IIR-adaptation path is well-argued and I largely agree with
it** (design `06/10-rust-parser-codegen/design.md §2`, four load-bearing reasons):
1. The IIR encodes the *Python* CST API (`RefType`, `NodeRef`, `Optional[NodeRef]`); the
   Rust CST is type-directed (push_child variant selection from runtime type,
   `Shared<T>` wrapping) — info absent at the IIR call site (§2.1).
2. The literal memoizer body is three simultaneous `&mut self` borrows; cannot compile
   in Rust without restructuring the IIR cannot express (§2.2).
3. "RefType becomes meaningful for free" is *false*: `consume_literal` is declared
   `mutable_self=False` yet mutates `self.error_tracker` — an IIR path would force
   auditing/fixing annotations across the *working* Python generators (§2.3). This
   directly refutes the exploration's own central selling point.
4. Rust needs module-level `static`/`OnceLock` regex tables, `#[cfg(feature="python")]`
   gating, `#[pymethods]` — none representable in the IIR (§2.4).

So **reusing the *existing* IIR as-is was correctly rejected.** That is not the same
question as "should there be *any* shared emission abstraction." The exploration's Path 3
(a shared *codegen plan* — a small backend-neutral description of the per-label quintet /
mutator / disposition shape, with thin Python-AST and Rust-string renderers) was rejected
"now" only because "it refactors working code for no immediate benefit … Revisit only if
a third backend appears" (design §2.7 final para). That rationale is reasonable for a
prototype but is exactly the kind of debt that compounds: there are now effectively
**three** render targets for the same per-label concept (Python AST, Rust pymethods +
native + pyi). The "third backend" trigger has, in spirit, already arrived — the `.pyi`
stub is a third renderer of the same surface.

### Is a shared-renderer retrofit still feasible?

**Partially, and it is the highest-leverage architectural improvement available** — but
it is not free and it is not a small refactor. The honest read:
- The *front-end* (grammar walk, rule models, naming) is already shared, so a retrofit
  does not have to touch grammar interpretation. Good.
- A retrofit would target the *most duplicated, most parity-critical* surfaces: the
  per-label quintet, the mutators (insert/remove_at/replace_at/clear incl. byte-equal
  error text), and the cross-backend eq/hash. These are pure "given (class_name, label,
  type-info) → method body" templating. A neutral spec + two thin renderers (one emitting
  Python AST nodes, one emitting Rust strings) would collapse the 3-Rust-sites +
  1-Python-site fan-out into 1 spec + 2 renderers, and the byte-equal error messages would
  become single-sourced rather than pinned by golden tests.
- It would NOT eliminate the collision subsystem or the lint-suppression conditional
  emission (those are inherent to targeting Rust's flat namespace + `-D warnings`), but a
  symbol-table in the neutral layer would let the collision check be structural rather
  than the ~250-line hand-maintained table (see below).

Net: dual generators are **sustainable in the short term** (tests catch a lot) but are a
**standing drift liability that grows with the public surface**, and a partial
shared-renderer retrofit of the highest-churn surfaces is feasible and would materially
de-risk it. This is a "fix before you scale the grammar/feature surface," not a restart.

---

## (b) DIRECT STRING EMISSION vs IIR — what it costs

The IIR-rejection is justified (above). But direct string emission has **concrete,
measurable costs** that the retrospective should not wave through:

1. **No machine-verification that emitted `.rs` is even syntactically valid.** The
   generator cannot check validity; correctness is established only downstream by
   `rustc`/`clippy` at build time (U3 §1). Bugs surface at `cargo build`, not at
   generation. For a tool whose output is the public product, "the generator can't tell if
   it emitted valid code" is a real altitude drop vs the Python path (which builds a typed
   `ast`/`iir` model).

2. **A ~250-line Rust-only identifier-collision subsystem** (`gsm2tree_rs.py:17-249`)
   that exists *only because* string emission targets a flat namespace shared with pyo3
   imports: `_IDENTIFIER_RE` build-time injection defense (`:22`, `:172-193`),
   `_RESERVED_LABELS` (`:28`), `_RESERVED_CLASS_NAMES` + `_RESERVED_CLASS_NAMES_SEEDED`
   (`:43-106`), a module-load `if/raise` invariant that survives `python -O` (`:108-142`),
   and a cross-rule claims-dict collision check (`:203-249`). It is careful and
   well-documented, but it is a **manually-maintained invariant**: the comments
   themselves say future reserved names "must also be seeded into claims" (`:42`,
   `:112-117`). A new reserved pyo3/runtime name added without updating the seeded tables
   could let a rule name silently shadow it. An IIR symbol table would surface most of
   these structurally.

3. **Pervasive lint-suppression conditional emission** drives much of the 2351-line bulk.
   `_child_enum_block` (`gsm2tree_rs.py:768-938`) — one method — branches on `has_span`,
   `child_classes`, `num_variants > 1`, `needs_drop_item`, `py_param` vs `_py`,
   `worklist_param` vs `_worklist`, `extract_span_type_param` — all to emit-or-omit match
   arms / Drop impls / `_` wildcards / `_`-prefixed params so the output passes
   `clippy -D warnings`. This is essential complexity *introduced by the choice to hand-emit
   strings into a `-D warnings` target*; a structured emitter that knew which symbols were
   used could suppress dead-code lints structurally.

4. **Feature gaps the string approach left standing as hard errors** (U3 §3, U7 §2):
   `NotImplementedError` for INLINE disposition (`gsm2parser_rs.py:824-826, 1010-1012`)
   and Invocation terms (`:768-770`). A grammar that compiles on Python can fail outright
   on Rust. These are real holes in the "near-drop-in" claim.

The cost is real but the *output quality* is good (clippy-clean, reviewable). The honest
framing: string emission bought a faster path to working Rust at the price of (i) no
generation-time validity guarantee, (ii) two Rust-only subsystems, and (iii) a permanent
dual-maintenance contract. The decision was defensible for a prototype; whether it should
be the *production* architecture is exactly the question this retrospective exists to ask,
and the answer leans "keep, but retrofit the highest-churn renderers."

---

## (c) THE CRATE SPLIT — coherent, not accidental

This is the **strongest part of the architecture.** The runtime split is along the right
seam and is enforced structurally, not by convention:

- `fltk-cst-core` (CST runtime): pyo3 optional behind a default-on `python` feature
  (`Cargo.toml`). CST crosses the language boundary, so it needs pyo3.
- `fltk-parser-core` (parser runtime): **no `python` feature exists at all** — pyo3-freedom
  is structural absence, the strongest possible guarantee (you cannot turn on what doesn't
  exist), verified empirically by `cargo tree` / `check-no-pyo3` (U2 §0). Parsers don't
  cross the boundary, so this is correct.
- `fltk-native` cdylib (root `src/lib.rs`, 22 lines): post-`c018206` it is **runtime-only**
  — registers only `Span`/`SourceText`/`UnknownSpan` as canonical type objects, carries no
  grammar. Clean. This mirrors the Python backend's `pyrt` (hand-written runtime) vs codegen
  split exactly. Verified: `src/lib.rs` is a 22-line `#[pymodule]` with no grammar code.

The seam is *coherent and load-bearing*: it is what makes the no-pyo3 path real for
pure-Rust consumers, and it keeps `fltk-cst-core` free of a `regex` dependency for CST-only
consumers. I would not change it.

**However, the crate *inventory* is not coherent — it is accreted:**

- `tests/rust_cst_fegen/` is a **byte-identical, git-tracked, dead duplicate** of
  `crates/fegen-rust/` — verified via `diff -q` (both `cst.rs` and `parser.rs` report
  IDENTICAL; ~17,171 LoC of generated Rust). It is referenced by **no** Makefile target,
  no test, no cargo-deny manifest (verified: `grep rust_cst_fegen Makefile .github/ deny.toml`
  → NONE). The crate was "promoted" to `crates/` without deleting the original. CHANGELOG.md
  still points at the stale path. This is pure drift bait and the single largest cleanup win.
- `crates/fltk-cst-spike/` is a live workspace member (`Cargo.toml:2`) whose `cst.rs` is a
  **literal `cp`** of `tests/rust_poc_cst/src/cst.rs` (`Makefile:288`,
  `cp tests/rust_poc_cst/src/cst.rs crates/fltk-cst-spike/src/cst.rs`). It is not dead (it
  owns the *only* perf bench, `benches/traverse.rs`, and exercises the python-off lane), but
  it is redundant scaffolding carried as a first-class workspace member — and
  `TODO(bazel-cst-spike-hub)` (`MODULE.bazel:31`) already flags that its membership leaks it
  into the Bazel crate hub.

So: the **runtime crate split is sound and should be kept**; the **fixture/spike crate
inventory is accreted prototype residue** that should be pruned (delete `rust_cst_fegen`,
demote/merge `fltk-cst-spike`) before production. These are mechanical, low-risk cleanups,
not architectural reworks — but their existence (a dead duplicate that fell off every lane)
is itself evidence that the hand-maintained per-crate Makefile fan-out is a drift surface.

---

## (d) cross-cdylib ABI sentinel + handle/registry/Shared<T> — essential or over-engineered?

**Essential complexity for FLTK's stated primary use case, not over-engineering — but it
concentrates the entire `unsafe` surface and its soundness rests on non-mechanical
invariants.**

The machinery exists because FLTK's whole point is **out-of-tree consumers, each its own
cdylib** linking its own copy of `fltk-cst-core` and registering its own `Span`/`SourceText`
pyclasses. Across that cdylib boundary, pyo3 type-object identity differs, so the normal
safe `extract::<Span>()` / `downcast` *fails*, and there is no safe pyo3 path to recover the
native type from the foreign Python object (U2 §4). Given the architecture (per-grammar
separate cdylibs), some cross-cdylib type-recovery mechanism is genuinely required.

Assessment of the pieces:
- `Shared<T> = Arc<RwLock<T>>` (`shared.rs`): zero unsafe, justified for reference-semantics
  CST sharing matching the Python backend. Safe.
- `registry.rs`: a Python-identity cache (WeakValueDictionary keyed by Arc address), not a
  GC; zero unsafe; ensures stable `is`-identity. Sound under the single-threaded-Python
  assumption it documents. Justified.
- `cross_cdylib.rs`: holds **all 3 `unsafe` blocks** in the entire runtime (verified per U2
  §9: `cast_unchecked` at `:86`, `:112`, `:331`). Crucially, the **fast path is safe** — for
  the single-cdylib `fltk._native` deployment, `obj.cast::<SourceText>()`
  (`cross_cdylib.rs:65`) is a *safe* pyo3 downcast that succeeds and the unsafe is never
  reached. The unsafe only fires on the multi-cdylib path, gated by a forgeable
  `_fltk_cst_core_abi` version string + `_fltk_cst_core_abi_layout` size_of probe.

Residual risks the code *itself admits* (`cross_cdylib.rs:98-115`, the SAFETY comments are
unusually candid):
1. **Size-preserving layout skew is not caught** — size equality is necessary but not
   sufficient; the probe "narrows — not closes — the layout-skew window." This is an
   *accepted, explicit* risk, defended by a plausibility argument (frozen pyo3 types collapse
   to `{ffi::PyObject, T}`), not a proof.
2. **Pure-Python forgery → UB** through the underscore-private `_with_source_unchecked`,
   defended only by naming convention ("out of contract," `:46-53`).

So: this is **essential complexity given the chosen architecture**, executed with
exceptional honesty. But note the *architecture forced it*: the decision to ship a separate
cdylib per grammar (rather than, say, one runtime cdylib that all generated CST links and
shares type objects through) is what creates the cross-cdylib boundary that requires the
sentinel and its unsafe. An alternative architecture where the canonical `Span`/`SourceText`
type objects are *always* the `fltk._native` ones (which the `c018206` runtime-only refactor
moved toward) could in principle let consumers depend on `fltk._native` for the canonical
types and never register their own — shrinking or eliminating the cross-cdylib cast. The
current design retains `get_source_text_type` "for backward compat with already-generated
consumer cst.rs" explicitly **not** ABI-validated (U2 §4) — a loaded gun left in the public
API for compat. For a production judgment: the machinery is sound *enough* for the
single-cdylib fast path (which is the near-drop-in `fltk._native` story), but the
multi-cdylib path — **which is FLTK's stated primary use case** — rests its soundness on a
build-discipline invariant (same rlib, same pyo3) that nothing mechanically enforces and a
size-only probe. That is the riskiest residual in the whole architecture and it lives
exactly where the primary use case lives.

---

## Cross-cutting structural finding: no automated generator-drift gate

~75,670 lines of committed generated Rust (U7 §5) are regenerated only by a manual
`make gencode`. `make check` / `check-ci` / `check-common` (`Makefile:39-76`, verified) run
lint/format/typecheck/test/clippy/deny but **never** run `gencode` followed by
`git diff --exit-code`. The gencode target's own comment admits the gate is human-driven
("`git diff --stat` reveals any drift … cheat-detection: committed hand-patches show as
diffs", `Makefile` gencode header). Consequence: a generator regression can pass CI against
stale committed code, or a hand-patched committed `.rs` can pass CI while being
unreproducible from the generator. For a project whose generated output is the public
product, and whose architecture *deliberately* duplicates emission across two generators
held together by "the committed code matches what the generator emits," the absence of an
automated regen-and-assert-no-diff gate is the missing control that ties the whole
dual-generator bet together. This is the single highest-leverage process fix and it is
cheap.

---

## Bottom line for the retrospective

**Did we build it right (architecturally)?** Mostly. The runtime crate split is genuinely
good and should be kept verbatim. The IIR rejection is well-reasoned. The cross-cdylib
machinery is essential, not gold-plating, and is documented with rare honesty.

**Is it a sound foundation to build on, or should it be reworked before production?**
It is a **sound-enough foundation that needs targeted hardening, not a restart.** The three
things that must be addressed before this is "production architecture":
1. The **dual string-emitting generators** are a permanent drift liability that has already
   drifted; retrofit a shared neutral renderer for the highest-churn surfaces (per-label
   quintet, mutators, eq/hash) and/or, at minimum, add the automated gencode-drift gate so
   drift becomes a CI failure rather than a latent divergence.
2. The **multi-cdylib unsafe path** (FLTK's primary use case) needs either a mechanically
   enforced same-rlib/same-pyo3 invariant or an architecture that routes all consumers
   through the canonical `fltk._native` type objects — the size-only forgeable sentinel is
   the riskiest residual.
3. **Prune the accreted crate inventory** (delete the dead `rust_cst_fegen` duplicate,
   demote `fltk-cst-spike`) — mechanical, but the dead duplicate's existence is itself
   evidence the hand-maintained fan-out drifts.

None of these is a tear-down. The bones (crate seam, runtime, model-layer sharing) are
good. The structure that should be reworked-before-scale is the *emission layer* and the
*drift controls around it*, not the architecture as a whole.
