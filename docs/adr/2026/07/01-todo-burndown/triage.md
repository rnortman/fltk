# TODO Burndown Triage — 2026-07-01

All 24 real TODO.md entries triaged (every entry except the placeholder). Each was
adversarially validated against source by a dedicated explorer; exploration docs live in
this directory as `exploration-<slug>.md`. Recommendations are **Do** / **Delete** /
**Blocked**. "I accept all recommendations" means: do the 11 Do items as reframed below,
remove the 12 Delete items (entry + paired code comment, downgrading comments to plain
notes where noted), and leave the 1 Blocked item in place.

Tally: **11 Do, 12 Delete, 1 Blocked**, plus one incidental real bug (folded into item 4).

---

## Delete — already done or verified moot

### 1. `bazel-rules-rust` — DELETE (it's done)

- **Problem:** TODO says the Rust extension isn't buildable via Bazel.
- **Ground truth:** `rules_rust` is in `MODULE.bazel:6`; live `bazel build //:native` and
  `bazel build //...` (26 targets) both green this session. The work landed in commit
  `7200d9c`, an ancestor of HEAD. Only TODO.md's "implementation in progress" text is stale.
- **Recommendation: Delete the entry.** No code comment exists to remove.
- **Aside for the user:** the closing ADR named three follow-up slugs that were never
  promoted into TODO.md: `fltk-pin-finalize` (revert Clockwork's temporary
  `local_path_override` to a git pin), `rust-pyany-qualify`, `rust-recursion-limit-macro`.
  Say the word if any should become real TODO entries.

### 2. `verify-pyo3-ext-module` — DELETE (verification performed, passed)

- **Problem:** A one-time verification task: confirm pyo3's `extension-module` feature is
  active under Bazel (symptom if not: the `.so` links libpython) and that dev-deps don't
  leak into the crate hub.
- **Ground truth:** The TODO's own pass condition was executed: `ldd` on the Bazel-built
  `.so` shows **no libpython**. There are zero `[dev-dependencies]` in any workspace
  manifest, so the leak half has nothing to leak. The conditional fallback
  (`crate.annotation`) was never needed.
- **The case for keeping:** the check wasn't on a pristine clean checkout, and the feature
  was proven on the artifact, not introspected on the hub target. Both are pedantic given
  the artifact is the thing that ships.
- **Recommendation: Delete** the entry and the `MODULE.bazel` comment block (lines ~38-44).

### 3. `native-submodule-error-context` — DELETE (described problem doesn't exist)

- **Problem claimed:** submodule registration errors propagate with no context naming the
  failing submodule.
- **Ground truth:** **False since before the TODO was written.** The `register_classes`
  path has carried `.map_err` context naming the qualified submodule since 2026-06-11; the
  TODO was authored 2026-06-14 as a comment-only addition describing a state the code had
  already left. The only bare `?`s left are `sub.setattr("__name__", ...)`,
  `py.import("sys")`, `.getattr("modules")` — failures at "interpreter is broken" level.
- **Recommendation: Delete** the entry and the comment at
  `crates/fltk-cst-core/src/py_module.rs:86-89`. Wrapping the three residual sites is not
  worth an entry; if an implementer is ever in that file, it's a 3-line courtesy.

### 5. `submodule-register-fn-convention` — DELETE

- **Problem:** `Submodule.register_fn` isn't validated against the `register_classes`
  convention; a wrong name surfaces as a Rust compile error instead of a Python error.
- **Ground truth:** the field defaults to `"register_classes"`, every constructor call
  in-tree leaves the default, no CLI flag can override it, and all three Rust generators
  hardcode the matching function name. The escape hatch exists only for hypothetical
  hand-written crates with nonstandard entry points — exactly the users enforcement would
  break. The limitation is already documented in `validate()`'s docstring.
- **Recommendation: Delete** the entry; trim the TODO lines out of the docstring (the
  surrounding documentation of the limitation stays — the "document" half of
  "document-or-enforce" is done).

### 6. `bazel-lib-rs-no-cst` — DELETE (guard unreachable via any supported path)

- **Problem:** the Bazel crate-assembly step hard-requires `cst.rs`/`parser.rs`, which
  would confuse a hypothetical future span-only crate.
- **Ground truth:** through the public `generate_rust_parser` macro there is **no way** to
  produce sources without `cst.rs` — the hypothetical caller cannot reach the guard at all
  without calling a private helper directly. The guard's error messages are explicit, not
  misleading. A prior review already judged this "defer until a concrete caller exists."
  TODO.md's text also still names a macro (`fltk_pyo3_cdylib`) that was renamed away.
- **Recommendation: Delete** the entry; downgrade the `rust.bzl` comment to a plain
  (slug-less) note, which is genuinely useful to a future editor. If a span-only consumer
  ever materializes, the loud guard failure will re-raise the question at the right time.

### 9. `regex-unicode-class-divergence` — DELETE (tracking note for a closed item)

- **Problem:** a tracking entry to ensure the "document-scope-boundary" work covered the
  non-ASCII semantic residual ledger of `\d`/`\w`/`\s`/`\b`/`(?i)`.
- **Ground truth:** the ledger **is documented** — fully in `regex_portability.py`'s module
  docstring and per-production in `regex.fltkg` comments. The `document-scope-boundary`
  item it defers to was completed (and its regex prose deliberately declined as obsolete)
  *before* this TODO was even created; the same commit that created this TODO added the
  documentation it asks for. There is no remaining action.
- **Recommendation: Delete** the entry and the one TODO line inside the
  `regex_portability.py` docstring (the ledger text above it stays).

### 10. `regex-portability-target-list-drift` — DELETE

- **Problem:** a 3-item grammar list is duplicated between the Makefile's `gencode` recipe
  and a completeness test; adding a grammar in one place but not the other silently
  shrinks test coverage.
- **Ground truth:** the two lists match today (no live drift). The cited Makefile line
  numbers were wrong from the moment of authorship. The `gencode-drift-gate` family this
  was meant to join was **explicitly rejected/deferred by you** in a prior burndown.
  Single-sourcing needs new manifest machinery read by both Make and pytest (and Bazel is
  a silent third copy) — heavy plumbing to protect a 3-item list that changes rarely and
  by people staring at both files.
- **Recommendation: Delete** entry + test-file comment. If you'd rather keep a guard,
  the honest version is re-opening the (rejected) regenerate-and-diff gate, not this.

### 11. `regex-portability-roundtrip-test` — DELETE

- **Problem:** nothing pins that the committed regex-subset parser was actually generated
  from the committed grammar.
- **Ground truth:** the TODO's own "lighter oracle" alternative **already exists** — all 93
  admitted/excluded unit patterns run against the committed parser on every test run, so
  any drift that changes classification of any known pattern is caught. The residual gap
  is drift that reclassifies *none* of 93 patterns. The explorer proved the byte-compare
  gate feasible (regen + `ruff check --fix` + `ruff format` converges to a 0-line diff),
  so "Do" is available — but it means invoking the generator and ruff inside a test, and
  it's the same regenerate-and-compare family you previously rejected as a gate.
- **Recommendation: Delete** entry + test-file comment. (If you disagree, the Do version
  is well-scoped and its feasibility is now proven — see the exploration.)

### 13. `linecol-cache-consolidate` — DELETE (stated fix doesn't compile; harm is nil)

- **Problem:** two independent lazy line-ends caches over the same immutable text (one on
  `TerminalSource`, one on `SourceInner`) duplicate state.
- **Ground truth:** duplication is real but *benign* — both derive deterministically from
  the same immutable text; worst case is computing a small Vec twice on a cold error path.
  The TODO's one-line fix is **not compilable**: the shared field is `pub(crate)` in a
  different crate, so the fix actually requires widening `fltk-cst-core`'s cross-crate API
  with a new accessor — API surface added to remove a harmless private field.
- **Recommendation: Delete** entry + both code comments (optionally downgrading the
  `span.rs` doc-comment sentence to a plain note).

### 14. `py-span-linecol-cache` — DELETE (optimizing a path nobody calls)

- **Problem:** Python `Span.line_col()` rescans the whole source on every call (Rust
  caches).
- **Ground truth:** the sole production caller is `error_formatter.format_source_line`,
  which itself has **zero production callers in-tree** (test-only + offered to downstream).
  The fix is genuinely non-trivial: `Span` deliberately stores a raw `str`, never a
  `SourceText` handle, so "thread a cache through `with_source`" means changing what Span
  retains — with 1126 generated call sites downstream of that decision.
- **The case for keeping:** same shape as `extend-children-owned`, which you chose to keep
  as blocked-on-profiling. Keeping both blocked would be consistent.
- **Recommendation: Delete** entry + comment; re-add if a downstream consumer ever
  reports `line_col` heat. (Say "keep blocked" if you want the extend-children treatment.)

### 21. `unparser-join-sep-resolve` — DELETE (verified true, verified tiny)

- **Problem:** a join's separator is re-resolved once per gap (M-1 times) with
  byte-identical results — pure redundant work.
- **Ground truth:** every claim checks out, including the mitigating one: separators are
  restricted (enforced, no bypass) to flat 1-3 node docs, so the waste is a small constant
  per gap — the same asymptotic order as the unavoidable per-gap work. No profiling
  evidence exists or is plausible. The fix perturbs the "preserved_trivia holds unresolved
  trivia" invariant for an unmeasurable gain.
- **Recommendation: Delete** entry + `resolve.rs` comment (downgrade to a plain note if
  you like — it's accurate documentation of a deliberate choice).

### 23. `unparser-pyi-doc-stub-shared` — DELETE (6 duplicated lines; wrong precedent)

- **Problem:** a grammar-independent 3-line `Doc` stub is duplicated into every generated
  `unparser.pyi` (currently 2 copies).
- **Ground truth:** the TODO's precedent ("how the CST side shares `CstModule`") is
  **wrong** — `CstModule` is grammar-dependent and regenerated per grammar, never
  import-shared. The real precedent is `SpanProtocol` (shared via an `fltk`-package
  import), which *would* work — but adopting it restructures every downstream consumer's
  generated stub surface, a deliberate public-API decision per CLAUDE.md, to save two
  copies of three lines.
- **Recommendation: Delete** entry + generator comment. Revisit only if `Doc`'s stub
  surface actually grows.

---

## Blocked — keep as-is

### 12. `extend-children-owned` — BLOCKED (keep; already thrice-adjudicated)

This slug has now been explored four times and user-decided three times, always landing on
"keep, blocked on profiling evidence." This pass re-verified every factual claim (still
accurate; the new `impl Drop` doesn't block the fix; still no profiling harness or
evidence in-tree). Nothing has changed. **Recommendation: leave the entry exactly as-is;
stop re-triaging it** (consider adding "(triaged 4x — do not re-triage without profiling
data)" to the entry text).

---

## Do — real, actionable, worth it

### 4. `native-span-init-error-context` — DO, reframed (rider on a real drift bug)

- **The real problem found:** committed `src/lib.rs` **has drifted from its generator**.
  Someone added `LineColPos` registration to `src/lib.rs` without teaching
  `gsm2lib_rs.py` about it — so the next `make gencode` run will silently **drop
  `LineColPos` from `fltk._native`**, breaking the native module. This is a live
  regression trap, found incidentally during validation.
- **The TODO itself:** wrap one generated `Py::new(...)?` with an error message naming the
  UnknownSpan sentinel. Failure is OOM-only — marginal on its own (prior judge:
  "marginal-yes"), but it's a 3-line generator change with an established sibling pattern.
- **What the work looks like:** teach the generator to emit `LineColPos` registration
  (fixing the drift), add the `map_err` wrap, regenerate `src/lib.rs`, pin both with
  generator tests.
- **The case for skipping:** none for the drift fix; the wrap alone would be skippable.
- **Recommendation: Do** — drift fix is the substance, error-context wrap rides along.

### 7. `gsm-for-each-item-public` — DO (the rename, not the helper)

- **Problem:** `regex_corpus.py` calls `gsm._for_each_item` — a private-by-convention name
  across module boundaries that no type checker will guard.
- **What the work looks like:** rename to public `for_each_item` (docstring already
  present); update the one cross-module call site + two in-module call sites. Skip the
  TODO's alternative `iter_regexes(grammar)` helper — it moves regex-specific filtering
  into `gsm.py`, which has none today, for no additional caller.
- **The case for skipping:** it's cosmetic-adjacent; the call works fine.
- **Recommendation: Do** — trivial, gives the walk a stable public contract.

### 8. `forged-abi-extract-span-uniformity` — DO, reframed (the "no rejection power" claim is wrong)

- **Problem as written:** a "revisit only if a future change makes `extract_span` reachable
  by forged objects" note.
- **Ground truth:** the exploration traced a **pre-existing** forge path, no future change
  needed: `get_span_type` resolves `fltk._native.Span` **by name from a mutable module
  namespace** and validates it only via forgeable class attributes. Reassign
  `fltk._native.Span` to a classattr-matching plain-Python class before the first lookup
  (the existing ABI-gate tests already perform exactly this pre-init reassignment pattern)
  and `extract_span`'s `cast_unchecked` reinterprets a plain Python object's memory as a
  Rust `Span` — the same undefined-behavior class the `fix-forged-abi-segfault` work
  closed for `extract_source_text`. `check_instance_layout` (already built, generic)
  would reject it via the immutable `type.__basicsize__` descriptor.
- **What the work looks like:** TDD — subprocess test forging a classattr-matching
  `FakeSpan` through `extract_span`'s slow path first, then apply `check_instance_layout`
  on that path. Small, pattern-established.
- **The case for skipping:** an attacker who can reassign module attributes already runs
  arbitrary Python; this hardens against UB/segfault, not privilege escalation. But the
  project already decided that class of hardening is worth it for `extract_source_text`.
- **Recommendation: Do.**

### 15. `spanprotocol-native-linecol` — DO

- **Problem:** native `fltk._native.Span` is not *statically* assignable to
  `SpanProtocol` (pyright-reproduced) because the two backends return two nominally
  distinct `LineColPos` classes. Downstream code annotating with `SpanProtocol` — the
  documented cross-backend pattern — type-fails when handed native spans.
- **What the work looks like:** the shape consistent with every verified constraint is a
  structural `LineColPosProtocol` in `span_protocol.py` (mirroring how `SpanProtocol`
  itself already bridges the two nominal `Span` types), with `line_span` retyped to
  `SpanProtocol`. Touches exactly three hand-written files (`span_protocol.py`,
  `terminalsrc.py`, native `.pyi`); generated artifacts don't name `LineColPos` at all.
  **Load-bearing constraint (verified real and untested):** `span_protocol.py` itself must
  keep naming zero `fltk._native` symbols, and the fix must add a stub-stability guard
  since no existing test covers that transitive property.
- **The case for skipping:** the gap is contained today (one deliberate
  assignability-pin site in pyright scope) and conformance holds at runtime.
- **Recommendation: Do** — this is the "near-drop-in Rust backend" promise made static.

### 16. `span-selector-broken-native-diagnostic` — DO (narrow the catch)

- **Problem:** the backend selector's `except Exception` silently falls back to
  pure-Python for *any* failure — a present-but-broken native extension (ABI mismatch,
  corrupted `.so`) is indistinguishable from a clean pure-Python install.
- **Ground truth:** both cited sites confirmed; in-tree consumers are tests-only, so this
  is downstream-facing robustness for the standalone selector utility.
- **What the work looks like:** the TODO's option (a): narrow to `except ImportError` at
  both `span.py` and the `AnySpan` block in lockstep (absent-native still raises
  `ImportError`, so the legitimate fallback keeps working; a genuinely broken extension
  now propagates loudly), plus a test for the non-ImportError path.
- **The case for skipping:** zero in-tree impact; some ABI breaks surface as ImportError
  anyway and would still fall back silently.
- **Recommendation: Do** — small, "robust as fuck"-aligned, decision already framed.

### 17. `unparser-source-helper` — DO

- **Problem:** a test file re-implements `plumbing.generate_unparser`'s 7-step assembly
  pipeline line-for-line because plumbing offers no way to get the generated source
  before it's `exec`'d. Any pipeline change must be mirrored in both places.
- **Ground truth:** duplication confirmed; no behavioral drift *yet* (two harmless
  differences already exist — redundant double-run of idempotent trivia steps, and an
  inlined default). The proposed fix is purely additive to `fltk.plumbing`
  (`generate_unparser_source(...)`; existing `generate_unparser` exec's its output),
  which is the safe category per CLAUDE.md.
- **The case for skipping:** the pipeline changes rarely.
- **Recommendation: Do** — classic drift foot-gun with a clean additive fix.

### 18. `unparser-none-path-diagnostics` — DO, reframed (backends already diverge)

- **Problem:** two silent `None` paths in the generated Rust unparser: (1) a confirmed
  comment can be silently dropped from formatted output; (2) a bad span silently nulls the
  whole `unparse_*` result with no record of which span failed.
- **Ground truth that changes the framing:** the TODO says a policy must be applied to both
  backends "so behavior stays in parity" — but for site 2 **parity does not exist today**:
  the Python unparser already raises a `ValueError` naming the span for the source-bearing
  bad-offset case, while Rust silently propagates `None`. So this is reconciling an
  existing divergence, and the direction is nearly forced: bring Rust up to Python's
  established raise-with-context behavior. Site 1 is genuinely symmetric (both drop
  silently) and needs one small policy call applied to both.
- **What the work looks like:** small design note (site-1 policy + exact Rust error
  shape), then generator changes in both backends' emitters + regen + tests.
- **The case for skipping:** both are invariant-violation paths unreachable in the
  shipping `fltkfmt` pipeline (every span carries source).
- **Recommendation: Do** — silent data loss in a formatter is the worst failure mode to
  leave undiagnosed, and half the "policy decision" turns out to be already made.

### 19. `fmt-cli-per-consumer-about` — DO (its blocker landed)

- **Problem:** every out-of-tree formatter binary built on `fltk-fmt-cli` gets the same
  generic `--help` text; there's no hook to say which language the binary formats.
- **Ground truth:** the TODO was explicitly deferred until `run_main`/`fltk_formatter_main!`
  exist. They landed (commit `1e9e402`) — precondition satisfied, work outstanding,
  exactly as prescribed: thread `about: &'static str` through `run_main` and the macro,
  build via `FmtArgs::command().about(..)`.
- **The case for skipping:** cosmetic (`--help` wording); one consumer exists today.
- **Recommendation: Do** — public-API polish the review chain already committed to.

### 20. `fltkfmt-integration-tests` — DO (user-accepted deferral, now due)

- **Problem:** the `fltkfmt` binary crate has **zero tests**. Four design-specified
  integration tests (idempotency, golden, trailing-newline, parse-error path) were
  user-accepted as a deferral during review and never picked up. They're also the only
  way to exercise the `fltk_formatter_main!` macro's two error branches.
- **Ground truth:** all four confirmed absent; the parity pytest covers single-pass
  byte-parity only. The TODO's framing is stale in one way that *helps*: check-gating
  already happened, so landing the tests auto-gates them — no Makefile work needed.
- **The case for skipping:** the parity test already catches gross formatting breakage.
- **Recommendation: Do** — write the four tests in `crates/fltkfmt/tests/`.

### 22. `protocol-module-truthiness-gate` — DO

- **Problem:** a code generator decides whether to emit precise `kind: Literal[...]`
  discriminants based on the *truthiness of an unrelated field*, silently degrading to
  `kind: object` for empty-module-backed generators; the Rust backend works around it by
  constructing a throwaway generator with a fake module name.
- **Ground truth:** fully verified, and better than claimed: `py_module` has **no other
  live use** anywhere in the protocol-emission path, so an explicit
  `emit_kind_literal` parameter doesn't just rename the trap — it lets the Rust backend
  reuse its existing generator and **delete the throwaway construction** (including its
  redundant context + full rule-model re-derivation). Two production callers; a defaulted
  keyword keeps both source-compatible. (TODO.md misnames the containing method; the
  gate is in `_protocol_class_for_model` — exploration has exact lines.)
- **The case for skipping:** the trap is documented at the gate; both callers work today.
- **Recommendation: Do** — removes a rediscovered-per-caller trap and net-deletes code.

### 24. `bazel-neg-test-harness` — DO

- **Problem:** the public Bazel macro's misconfiguration guards (7 conditions protecting
  downstream users from confusing failures) have no automated test — verified once by
  hand; a future edit disabling a guard goes unnoticed.
- **Ground truth:** guards confirmed live post-unification (now 1 shared helper + 1
  templated loop, which makes testing *cheaper* than when the TODO was written);
  `bazel_skylib` confirmed absent from `MODULE.bazel`; `analysistest` is the standard,
  purpose-built mechanism for asserting analysis-time failures without breaking
  `bazel build //...`.
- **What the work looks like:** add `bazel_skylib` dep; one `analysistest` negative target
  per guard condition asserting failure with the expected message.
- **The case for skipping:** guards are simple and rarely edited; this adds a dep and
  Bazel boilerplate for a low-probability regression.
- **Recommendation: Do** — now that the Bazel Rust surface is confirmed working and public,
  its misconfiguration UX is API; cheap insurance.

---

## Incidental findings (not TODO entries)

1. **`src/lib.rs` generator drift (real bug)** — folded into item 4 above.
2. **Clockwork breakage** — the `fltk_pyo3_cdylib` → private rename means the Clockwork
   checkout's Bazel build won't load `rust.bzl` until it migrates. Known/accepted per the
   unification ADR; noted here only for awareness (relates to the orphaned
   `fltk-pin-finalize` slug in item 1's aside).
3. **Stale line/name citations in TODO.md** — several entries cite line numbers or symbol
   names that were wrong at authorship or have drifted. Moot for deleted entries; the
   exploration docs carry corrected citations for the Do items.
4. **Stray worktree** — `.claude/worktrees/agent-ab295be24eef6e7ce/` is a leftover
   untracked checkout that pollutes naive greps; multiple explorers had to exclude it.
   Consider removing it.

## Suggested implementation order for the Do items (if all accepted)

Small/independent first: 7, 16, 5-adjacent cleanups land inside deletes → then 4 (drift
fix), 8, 22, 17, 19 → then 20, 24 (test-writing) → then 15, 18 (need a small design note
each). Implementation is serialized per burndown policy; explore/requirements/design can
run in parallel.
