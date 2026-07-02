# Design: close the forged-Span path through `extract_span` (`forged-abi-extract-span-uniformity`)

Requirements: `request.md` (this directory). Exploration: `exploration.md` (this directory).
Base commit: `c03a801`. (Exploration was written at `8fd5ecf`; its `TODO.md:37-44` cite
corresponds to `TODO.md:15-22` here after the intervening TODO cleanup commit.)

## 1. Root cause / context

The TODO (`TODO.md:15-22`, code marker at `crates/fltk-cst-core/src/cross_cdylib.rs:417-421`)
claims `check_instance_layout` on `extract_span` "would add no rejection power" because the
slow path is gated by `is_instance` against the non-subclassable canonical `Span` plus
`check_abi_pair::<Span>` in `get_span_type`. Exploration §4 shows that claim is wrong: it
silently assumes the value `get_span_type` returns is the genuine canonical `Span` type, but
`get_span_type` (`cross_cdylib.rs:461-478`) resolves `fltk._native.Span` **by name from a
mutable module namespace** and validates it only via `check_abi_pair`, which reads two
forgeable class attributes (`cross_cdylib.rs:185-260`).

Concrete pre-existing forge path (exploration §4, steps 1-4): reassign `fltk._native.Span`
to a plain-Python `FakeSpan` carrying copied `_fltk_cst_core_abi` /
`_fltk_cst_core_abi_layout` values *before* the first `get_span_type` call (the same
pre-init reassignment pattern the existing `TestSpanPathAbiGate` subprocess tests at
`tests/test_rust_span.py:528-599` already exercise, just with *wrong* attribute values).
Then:

1. `check_abi_pair::<Span>` passes — it only reads the two copied classattrs.
2. `get_span_type`'s `PyOnceLock` caches `FakeSpan` as the reference type.
3. In `extract_span` (`cross_cdylib.rs:433`), `obj.is_instance(&native_span_type)` is
   trivially satisfied by any `FakeSpan` instance.
4. `cast_unchecked::<Span>()` (`cross_cdylib.rs:443`) reinterprets a plain Python object's
   memory as `PyStaticClassObject<Span>` — the same undefined-behavior class the
   `fix-forged-abi-segfault` work closed for `extract_source_text`.

No test currently covers the correct-attrs forge combination (exploration §4, last bullet
of the test survey). The already-built, generic `check_instance_layout`
(`cross_cdylib.rs:292-339`) rejects exactly this forge via the immutable
`type.__basicsize__` descriptor; its own doc comment anticipates reuse for `Span`.

`extract_span` is the **only** `cast_unchecked` on the Span path: generated consumer code
(`crates/fegen-rust/src/cst.rs`, and its generator `fltk/fegen/gsm2tree_rs.py`) contains no
direct `cast_unchecked` — every span extraction funnels through `extract_span`, and every
`is_instance` check funnels through `get_span_type`.

## 2. Proposed approach

### 2.1 Gate placement: inside `get_span_type`, not per-call in `extract_span`

Add one line to `get_span_type`'s `PyOnceLock` init closure
(`crates/fltk-cst-core/src/cross_cdylib.rs:461-478`), after the existing `check_abi_pair`:

```rust
check_abi_pair::<Span>(&span_type, "Span", || "fltk._native.Span".to_string())?;
check_instance_layout::<Span>(&span_type, "Span")?;   // new
```

`check_instance_layout` needs no changes — it is already generic over `T: PyClassImpl` and
already parameterized by `type_label`.

Why the reference type in `get_span_type` rather than `obj.get_type()` in `extract_span`
(exploration §4 notes the two coincide in the forge scenario):

- **Establishes the same invariant as `extract_source_text`**: the cache cell
  (`FLTK_NATIVE_SPAN_TYPE`) can only ever hold a type that passed both gates — mirroring
  the documented `FLTK_FOREIGN_SOURCE_TEXT_TYPE` invariant (`cross_cdylib.rs:56-65`). One
  validation per process, at `PyOnceLock` init.
- **Covers every consumer uniformly**: `extract_span`, `span_to_pyobject`, and the dozens
  of generated `get_span_type` call sites in consumer `cst.rs` files all receive an
  already-validated reference type. A per-call check inside `extract_span` would leave
  the other consumers holding an unvalidated forged type (no UB there today, but confusing
  downstream failures instead of one clear `TypeError` at first boundary crossing).
- **No per-call cost on the hot path**: `extract_span`'s slow path is the *normal* path
  for cross-cdylib span setters (same reason `extract_source_text` grew a cache cell). A
  per-call `check_instance_layout` would add two `getattr`s per setter call;
  `get_span_type`'s `PyOnceLock` already is the cache.
- Soundness of validating the reference type instead of the object's own type: if the
  reference type is genuine, `Span` is non-subclassable (`span.rs:287`, no `subclass`
  flag), so an `is_instance` pass means the object's type *is* the validated reference
  type. If the reference type is a `__slots__`-padded forge that passes the basicsize
  gate, we are already inside the documented accepted residual (§3, last bullet) — an
  attacker who can build the padded forge reaches UB under either placement, so the
  placement difference adds no attacker power.

Ordering is load-bearing, same as on the SourceText path (`cross_cdylib.rs:56-62`):
`check_abi_pair` runs first so its pinned diagnostic messages keep firing for the existing
wrong-string / wrong-layout / missing-attr subprocess tests
(`tests/test_rust_span.py:528-758`); the basicsize gate narrows further only after those
pass.

### 2.2 Comment and bookkeeping changes

All in service of keeping the safety story readable at the point of the `unsafe`:

- `cross_cdylib.rs` `extract_span` (lines 411-450): delete the
  `TODO(forged-abi-extract-span-uniformity)` comment block; rewrite the doc comment and
  the SAFETY comment at the `cast_unchecked` to state the two-gate invariant ("the type
  `get_span_type` returned passed `check_abi_pair` AND `check_instance_layout`; `Span` is
  non-subclassable, so `is_instance` pass ⇒ the object's type is that validated type"),
  plus the padded-forge residual (identical in kind to the accepted `extract_source_text`
  residual).
- `cross_cdylib.rs` `get_span_type` doc comment (lines 452-460): document the second gate,
  the gate ordering rationale, and the "`FLTK_NATIVE_SPAN_TYPE` only ever holds a
  dual-gated type" invariant.
- `crates/fltk-cst-core/src/span.rs:573-584` (classattr doc comments referencing the
  `get_span_type` gate): mention the basicsize gate alongside the ABI pair.
- `TODO.md`: remove the `forged-abi-extract-span-uniformity` entry (lines 15-22).
- The superseded "no rejection power" claim also appears in the immutable prior burndown
  artifact
  (`docs/adr/2026/06/14-rust-backend-assessment/burndown/fix-forged-abi-segfault/design.md:217-219`). Per the ADR-immutability rule, that file is **not** edited; this
  ADR directory (request + exploration + this design) is the superseding record.

No generator changes, no generated-code changes, no public-symbol or type-annotation
changes. Out-of-tree consumers see no behavioral change on any legitimate path; the only
new behavior is a diagnostic `TypeError` on a path that previously invoked undefined
behavior. Previously-built consumer cdylibs embed the old rlib and keep old behavior until
rebuilt — acceptable, same as every prior `fltk-cst-core` hardening.

## 3. Edge cases / failure modes

- **False rejection of genuine types**: the canonical `Span` (same-cdylib or foreign, same
  rlib) always has `tp_basicsize == size_of::<PyStaticClassObject<Span>>` and metaclass
  `type` — same argument already relied on for `SourceText`
  (`cross_cdylib.rs:266-278`). Pinned by a new precondition test (§4, test d).
- **Pinned error messages**: existing wrong-attrs subprocess tests must still get
  `check_abi_pair` messages. Guaranteed by gate ordering (§2.1); those tests are the
  regression net.
- **`PyOnceLock` error semantics**: errors are not cached (noted at
  `tests/test_rust_span.py:494-496`), so a rejected forge re-runs lookup+gates and fails
  again on every subsequent call — same behavior `check_abi_pair` failures have today.
- **Wider blast radius than `extract_span`**: with the gate in `get_span_type`, a
  correct-attrs forge process now fails at the *first* span boundary crossing of any kind
  (including `span_to_pyobject` reads), not only at `extract_span`. This is intended
  uniform hardening; previously those sibling paths failed with incidental
  Python-level errors (e.g. missing `_with_source_unchecked` on the fake) rather than UB,
  and now they fail with the deliberate gate diagnostic.
- **Race on first call**: `get_or_try_init` — two threads may both run the gates against
  the same type; harmless, identical to today.
- **Accepted residual (documented, not closed)**: a `__slots__`-padded plain-Python forge
  whose `tp_basicsize` matches `size_of::<PyStaticClassObject<Span>>` and whose metaclass
  is `type` passes both gates; `cast_unchecked` on its instances is still UB. Identical
  in kind to the residual accepted for `extract_source_text`
  (`cross_cdylib.rs:67-73, 287-291`). One nuance specific to reference-type validation:
  instances of an *un-padded subclass* of such a padded forge would also pass
  `is_instance`; since mounting that attack requires building the padded forge anyway,
  attacker capability is unchanged versus per-object validation. Recorded in the SAFETY
  comment; no new residual-pinning test required (the boundary is already pinned for the
  shared helper by `test_padded_forge_passes_basicsize_gate_boundary`).
- **Threat model**: an attacker who can reassign `fltk._native.Span` already runs
  arbitrary Python. As with `fix-forged-abi-segfault`, the goal is UB/segfault
  elimination and clear diagnostics for accidental forgery/skew, not privilege
  separation (request.md, "case for skipping" — overruled by the same project precedent).

## 4. Test plan

TDD per `request.md`: write (a) first, observe the failure (SIGSEGV or garbage extraction
in the subprocess) at base, then apply §2 and watch it pass. All forge tests are
subprocess-isolated (`_run_script` helper, `tests/test_rust_span.py:17-25`) so a
regression segfaults the child, not the suite.

New class `TestForgedSpanRejected` in `tests/test_rust_span.py`, mirroring
`TestForgedSourceTextRejected`:

- **(a) `test_forged_span_via_reassignment_raises_type_error`** — the exploration §4
  scenario end-to-end. Subprocess: import `fltk._native`; define plain-class `FakeSpan`
  copying the real `Span._fltk_cst_core_abi` and `_fltk_cst_core_abi_layout`; set
  `native.Span = FakeSpan` before any span boundary crossing; import `fegen_rust_cst` and
  construct `Grammar(span=FakeSpan())` (drives `extract_span`'s slow path via the
  generated constructor, `cst.rs:572` — fast-path `extract::<Span>()` fails because the
  forge is not a local `Span`). Expect `TypeError` whose message names the basicsize gate
  (`"__basicsize__"` or `"not a genuine Span"` — the specific `check_instance_layout`
  message, not a weaker `"layout"` substring that `check_abi_pair` also matches); assert
  `returncode != -11` (explicit SIGSEGV-recurrence message) and `returncode == 0`.
  Uses `fegen_rust_cst` (already a module-level import-or-skip of this file) rather than
  `phase4_roundtrip_cst` so the core regression test does not depend on the optional
  fixture.
- **(b) `test_forged_span_metaclass_property_raises_type_error`** — same subprocess shape,
  but `FakeSpan` uses a metaclass whose `__basicsize__` property returns the expected
  size; expect the metaclass-guard `TypeError` (message names "metaclass"). Pins step-1
  wiring on the Span path, mirroring `test_metaclass_property_forge_raises_type_error`.
- **(c) `test_genuine_native_span_accepted_cross_cdylib`** — no-false-rejection: pass a
  genuine `fltk._native.Span` into a `fegen_rust_cst` node
  (`Grammar(span=fltk._native.Span(0, 5))`), i.e. `extract_span`'s slow path with the
  genuine canonical type; succeeds after the gate. **Subprocess** (`_run_script`, no
  forge — subprocess isolation is not for UB safety here but to guarantee a fresh
  interpreter, so `get_span_type`'s `PyOnceLock` init — and therefore the new
  `check_instance_layout` accept branch — provably executes inside this test. In-process,
  earlier phase4/fegen tests would already have populated the cache
  (e.g. `TestSpanToPyobjectCaching.test_repeated_span_reads_from_consumer_cdylib`,
  `tests/test_rust_span.py:772-780`), silently degrading (c) to a cache-hit test).
- **(d) `test_span_basicsize_matches_layout_attr`** — accept-branch precondition pin,
  analogous to `test_foreign_source_text_basicsize_matches_native_layout`:
  `Span.__basicsize__ == Span._fltk_cst_core_abi_layout`, and (phase4 branch,
  `importorskip`) `phase4.Span.__basicsize__ == Span._fltk_cst_core_abi_layout`. If this
  ever breaks, the gate would reject genuine spans.

Existing coverage that must stay green, unmodified: all of `TestSpanPathAbiGate`
(check_abi_pair-first ordering and its pinned messages), `TestSpanToPyobjectCaching`,
`test_control_no_patch_passes`, and the whole `TestForgedSourceTextRejected` class.

Gates: `uv run --group dev maturin develop` then `uv run pytest tests/test_rust_span.py`;
full `uv run pytest`; `uv run ruff check . && uv run pyright`; and `make check` — the
precommit gate's Rust lanes (`cargo-clippy`, `cargo-test`, `cargo-test-python-features`,
`cargo-test-no-python`, `cargo-clippy-no-python`, `check-no-pyo3`; `Makefile:40`) cover
the edited `cross_cdylib.rs`/`span.rs`, including the `--no-default-features` compile.

## 5. Open questions

None. The one genuine judgment call — gate placement — is resolved in §2.1 with rationale;
the request's directive ("apply `check_instance_layout` on that path") is satisfied by
either placement and the chosen one strictly dominates on cost and coverage.
