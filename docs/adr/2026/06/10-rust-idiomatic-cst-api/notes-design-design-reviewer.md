# Design review findings: rust-idiomatic-cst-api (revision: identity + ABI sentinel in scope)

Reviewer: design-reviewer. Base: 63e6b76. Charter respected: feasibility verdict + phased path (ADR seed),
now covering `TODO(rust-cst-child-node-identity)` and `TODO(crosscdylib-abi-sentinel)`. Prior-round findings
(spike provenance, `children` label collision, typed-accessor precedence, getter/setter attribute forms) are
all correctly addressed in this revision — verified against code, not just the dispositions.

Verified and correct (not findings): `_native` origin and the four plain-impl methods (gsm2tree_rs.py:571–595);
clone-on-boundary `Py::new(py, (**n).clone())` (:488); label validation (:18, :52–63) with no reserved-name
check, so the §4.2 latent `extend_children` collision claim is real (per-label `fn extend_{label}` :829 vs
generic `fn extend_children` :778, same `#[pymethods]` block → duplicate definition → uncompilable; `children`
matches the regex); the "no other prefix/fixed-name pair collides" claim (checked against the full fixed-name
set incl. Phase-2 native additions `push_child`/`set_span`/`kind`/`child`); `__hash__` TypeError (:925–931);
bare `#[getter]`/`#[setter]` forms (:647–653); per-label quintet matches labels only, never variant types
(:846–907), and `child_<lbl>` message text (:875) matches the design's `ChildCount` mirror; the five `==`-relaxed
tests at tests/test_phase4_rust_fixture.py:242,276,291,350,371 (each with the TODO comment) and no other test
pins clone/snapshot mutation semantics; tests/test_rust_cst_poc.py:47 list-snapshot pin is compatible with
element-identity restoration and with the Q4 recommended default; cross_cdylib.rs TODO sites (:14, :114, :166),
`extract_span` isinstance-only slow path (:147–176), SourceText per-object classattr gate, version-only
`FLTK_CST_CORE_ABI`; cst-core never bumped past 0.1.0 (Cargo.toml:3); spike `forbid(unsafe_code)` (lib.rs:1),
Debug-gap note (spike_tests.rs:6–8), spike cst.rs regenerated via gencode `cp` (Makefile:131–132); python-off
lanes at Makefile:51–58 + check-no-pyo3; `frozen, weakref` together genuinely unused in-tree (grep clean) and
correctly flagged verify-first; Python backend reference semantics incl. `extend_children` sharing
(gsm2tree.py:273,281,289) — the "converges toward the Python backend" framing is accurate; self-extend claims
(Python list.extend-self duplicates; current Rust PyRefMut+PyRef borrow error) check out. The registry no-ABA
argument is sound *for registry-routed paths* (but see design-2). Requirements coverage: R1→Phases 1–2,
R2→gates (§5/§6), R3→Phases 1+3, R4→Phase 4 shape, identity TODO→Phase 1, sentinel TODO→Phase 0 as scoped by
A2 — all mapped. Breaking-change posture satisfies CLAUDE.md's "deliberate, called-out decision" bar; the
Python name/signature/`.pyi` surface is genuinely untouched and the near-drop-in constraint holds. No scope
creep found (Debug/CstError/label-enum rename fall under the "idiomatic" charter and preserve Python names).

---

## design-1: "`make gencode` covers all five outputs" is false — `tests/rust_cst_fegen/src/cst.rs` is not regenerated

- Section: §4 opening — "Regen path: `make gencode` covers all five outputs (Makefile:121–132)"; the same
  paragraph lists `tests/rust_cst_fegen/src/cst.rs` among the five committed generated outputs to be changed.
- What's wrong: The `gencode` target (Makefile:103–141) regenerates four Rust outputs: `src/cst_generated.rs`
  (:121–123), `src/cst_fegen.rs` (:124–128), `tests/rust_cst_fixture/src/cst.rs` (:129–130), and the spike
  copy (:131–132). `tests/rust_cst_fegen/src/cst.rs` appears nowhere in `gencode`. The only Makefile mention
  of that crate is `build-fegen-rust-cst` (:90), which builds but does not regenerate, and the crate is
  deliberately excluded from the root workspace (its Cargo.toml: "standalone crate intentionally excluded"),
  so root `cargo check`/`clippy` will not flag staleness either.
- Why: Makefile read in full; `tests/rust_cst_fegen/Cargo.toml` header.
- Consequence: An implementer following the design's stated regen → `make fix` → commit path leaves one of
  the five outputs stale. Best case: the next `build-fegen-rust-cst` fails to compile against the
  restructured cst-core, mid-implementation surprise. Worse case: a previously built `fegen_rust_cst` .so
  keeps serving old clone-semantics nodes to the AC8/`parse_grammar(rust_fegen_cst_module=...)` pytest path,
  so the §6 item 3 cross-backend-equivalence gates appear green against stale code — undermining exactly the
  R2/R3 verification story the design leans on.
- Suggested fix: Correct the claim, and have Phase 1 extend `gencode` with a
  `gen-rust-cst GRAMMAR=fltk/fegen/fegen.fltkg RS_OUT=tests/rust_cst_fegen/src/cst.rs` step (or equivalent)
  so all five outputs regenerate from one target.

## design-2: `from_shared` bypasses the canonical-wrapper registry — the single-canonical-handle invariant argument omits a handle-producing path

- Section: §4.0 — "Soundness of the invariant 'at most one live canonical handle per `Shared`': ... every
  path that could later produce a second handle for the same `Shared` goes through wrap-out (which reuses)
  or hand-in (which registers the first handle seen)"; §4.0 defines
  `pub fn from_shared(s: Shared<Identifier>) -> Self` as the mixed-app bridge; §4.4 and §4.5 direct mixed
  apps and the future parser to use it.
- What's wrong: `from_shared` is a third handle-producing path, and as specified it *cannot* participate in
  the registry: it returns bare `Self`, but registration needs the Python heap object that exists only after
  the caller's subsequent `Py::new`/`into_pyobject` — at which point nothing registers it. Mixed-app Rust
  code that wraps the same `Shared` twice, or wraps a child `Shared` that Python also reaches via wrap-out
  through the parent, mints two distinct Python objects for one node. Hand-in's "register if absent" then
  crowns whichever object crosses the boundary first; the other permanently aliases.
- Why: registration requires the canonical handle *object* (weak-value map value); `from_shared(s) -> Self`
  has no `py` token and no object. The §4.0 invariant enumeration simply doesn't mention this path.
- Consequence: `is`-stability — the R3 definition itself ("a child read from Python is the same object on
  every read", §1) — breaks precisely in the mixed Rust/Python scenario R3 exists to serve. §6 item 4 tests
  only registry-routed paths and would stay green while the documented §4.4 pattern violates the invariant.
- Suggested fix: Replace the bridge with a GIL-bound, registry-routed constructor (e.g.
  `fn to_py_canonical(py, s: &Shared<T>) -> PyResult<Py<PyT>>` doing lookup-or-create-and-register), keep
  `.shared()` for the handle→native direction, and add a both-directions test (native-wrap of an
  already-Python-read child → `is` the existing object). Alternatively document `from_shared` as
  identity-unsafe and exclude it from the §4.4 supported pattern — but then §4.5's parser hand-off must use
  the registry-routed form too.

## design-3: `Shared` deep `PartialEq` can self-deadlock; "deadlocks excluded by construction" does not cover `__eq__`

- Section: §4.0 — "`PartialEq` = deep (read-locks both, compares values)"; §4.0 lock discipline — "This
  excludes GIL↔lock ordering deadlocks by construction"; §5 "Lock recursion / re-entrancy" — "Excluded in
  generated code by the snapshot-then-drop-guard rule".
- What's wrong: Handle `__eq__` and native `==` route through `Shared`'s deep `PartialEq`, which by nature
  holds read guards across the recursive compare — it cannot follow snapshot-then-drop. Two cases read-lock
  the *same* `RwLock` twice on one thread: (a) `x == x` from Python — CPython calls `__eq__` even for
  identical operands, and the registry makes two reads of one child the *same* object, so self-compare is
  routine (`node.child_x() == node.child_x()`); (b) DAG compares where the same `Shared` appears at the same
  position on both sides — §5 itself blesses shared acyclic subtrees as well-defined. std `RwLock` documents
  that a second same-thread `read()` may deadlock when a writer is queued — i.e. exactly in the
  multithreaded mixed apps R3 targets. §5 attributes residual lock hazards to misbehaving *user* code; this
  one is built into the generated/`Shared` code path.
- Why: §4.0's own `Shared` spec plus std `RwLock` documented semantics; no `ptr_eq` short-circuit is
  specified for `eq` (it is specified only for self-extend).
- Consequence: A plain `==` can hang a mixed app under concurrent mutation, and the ADR's "excluded by
  construction" claim is recorded false. Single-threaded behavior is platform-dependent rather than
  guaranteed.
- Suggested fix: Specify `ptr_eq` short-circuit as step one of `Shared::eq` (eliminates both same-lock cases
  except true cycles, which are already documented out of contract; also makes DAG compares cheaper). Add
  `x == x` to §6 item 3/4.

## design-4: §6 item 6's Span ABI-mismatch test is not executable as described against the init-time gate

- Section: §6 item 6 — "a fake span-like type with absent/mismatched `_fltk_cst_core_abi` fails
  `get_span_type`-gated extraction with a `TypeError` naming both ABI strings"; vs §4.1 item 1 — the gate is
  verified "once in `get_span_type`'s `GILOnceCell` init" against the canonical `fltk._native.Span`.
- What's wrong: Under the §4.1 mechanism, a fake span-like *object* never reaches the ABI gate: it fails the
  ordinary `isinstance` in `extract_span` (cross_cdylib.rs:156) and yields the existing generic
  "expected fltk._native.Span" TypeError. The ABI comparison runs once, against the canonical *type object*,
  at first init. Triggering the mismatch path requires `fltk._native.Span` itself to present an
  absent/mismatched marker *before the first span boundary crossing in the process* — impossible in the
  shared pytest process, where earlier tests have already initialized the `GILOnceCell` (not resettable from
  Python). The per-object fake-marker test shape is valid for the *SourceText* path (per-object gate,
  cross_cdylib.rs:59–77) but the test plan applies it to the Span path, conflating the two mechanisms.
- Why: §4.1 item 1's own wording; cross_cdylib.rs:143–193 (`FLTK_NATIVE_SPAN_TYPE` GILOnceCell).
- Consequence: The TDD-first test either exercises the wrong path (pre-existing isinstance failure — it
  would pass before the feature is implemented, violating TDD) or can never reach the new code; Phase 0's
  headline fail-loud behavior ships unverified.
- Suggested fix: Specify the isolation mechanism in §6 item 6: a subprocess test (fresh interpreter,
  `fltk._native.Span._fltk_cst_core_abi` patched/absent via an import shim before the first span operation —
  the repo already runs subprocess-based test batching, cf. commit 3217a14), or exercise the gate through a
  consumer-cdylib fixture (`rust_cst_fixture`) whose first span crossing happens in the controlled process.

## design-5: Minor inconsistencies

- **Phase-1 snippets use the Phase-2 name.** §4.0 ("`children: Vec<(Option<IdentifierLabel>, IdentifierChild)>`")
  and §4.2's plain-impl block ("`&[(Option<IdentifierLabel>, IdentifierChild)]`") are presented as Phase 1
  output, but the `Identifier_Label` → `IdentifierLabel` rename is scheduled in Phase 2 (§4.3 item 5). At
  Phase 1 the type is still `Identifier_Label`. Consequence: an implementer working phase-by-phase either
  pulls the rename forward (defeating §4.3's "signatures designed once ... the reason this phase follows
  Phase 1" sequencing and bloating the Phase-1 diff the two-commit reviewability plan assumes is mechanical)
  or must silently correct the doc. Fix: write Phase-1 snippets with `Identifier_Label` or footnote the
  anachronism.
- **`__repr__` listed as a cycle-recursion hazard.** §5 "Reference cycles" says `__eq__`/`__repr__`/`Debug`/
  `PartialEq` recurse infinitely. The generated Rust `__repr__` prints only span + child *count*
  (gsm2tree_rs.py:933–943) and does not recurse; the design moves it unchanged. Only `__eq__`/`PartialEq`/
  the new `Debug` recurse on the Rust side (the *Python backend's* dataclass repr does recurse). Consequence:
  minor — an overstated hazard recorded in what becomes the immutable ADR. Fix: drop `__repr__` from the
  Rust-side list or attribute it to the Python backend only.
