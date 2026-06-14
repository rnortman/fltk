# Design: Build-Surfaced Defect Fixes for the FLTK+Rust Bazel POC

Status: Draft (retroactive / reverse-engineered). Decision date 2026-06-13.

This is a **follow-on** design to [`design.md`](./design.md). The original design
was approved and implemented on code review alone (fltk HEAD `fac3da5`, Clockwork
HEAD `932320e`), with **no actual Bazel build**. A real `bazel test` run against a
local fltk checkout then surfaced seven genuine defects that review missed. An
implementer fixed them ad hoc to reach GREEN (delta: fltk `fac3da5..11d8460`,
Clockwork `932320e..42fedc8`).

This document reverse-engineers the **underlying problem** behind each fix and
states how it *should* be solved, independent of what the implementer did. For
each problem it states a **verdict**: **RATIFY** (existing commit is the right
design — keep, possibly edit comments) or **REVISE** (existing commit diverges —
change it). The downstream actor either reverts or edits the commits to conform.

Grounding: [`requirements.md`](./requirements.md), the original
[`design.md`](./design.md), the two verify reports
([`verify-bazel-run.md`](./verify-bazel-run.md),
[`verify-fltk-gate.md`](./verify-fltk-gate.md)), and the
[`implementation-log.md`](./implementation-log.md) Increment 5. This document does
not restate them; it cites them.

---

## 1. Root cause / context

The common root cause of all seven defects is the same methodological gap the
verify reports name explicitly: the original design and its implementation were
validated by **reading code, not running Bazel** (`verify-bazel-run.md`: "entirely
on CODE REVIEW, with no actual build"). Every defect below is a fact about the
*real* toolchain — Bazel's feature model, Starlark's parser, rustc's name
resolution, rustc's trait solver, PyO3 0.29's runtime behavior, or Clockwork's own
macro conventions — that is invisible to a reviewer who never compiles. None is a
logic error in the design's *intent*; each is a place where the design's stated
mechanism met a real-toolchain rule it had not accounted for.

The seven problems fall into three tiers of design significance:

- **Tier 1 — generated PUBLIC API surface (highest scrutiny).** The pyo3
  name-collision fix in `gsm2tree_rs.py` / `gsm2parser_rs.py`. This emits Rust
  that out-of-tree consumers compile; per CLAUDE.md it must be robust and general,
  not a two-name patch.
- **Tier 2 — FLTK public Bazel surface.** The `@fltk//:native` `python`
  crate-feature and the `rust.bzl` docstring fix. These are in the new public
  Bazel surface the original design shipped.
- **Tier 3 — consumer-local POC scaffolding.** The `#![recursion_limit]`, the
  `__test__` rename, and the `Span.__module__` test assertion. These live in
  Clockwork and do not constrain FLTK's public surface, but each encodes a real
  fact future consumers will hit.

---

## 2. Problem 1 (Tier 1): pyo3 name collisions in generated Rust — `PyList`, `PyTuple`, `PyType`, `PyModule`

### 2.1 The underlying problem

`gsm2tree_rs.py` emits, for a grammar rule named `X`, a `pub struct PyX` (the
PyO3 handle class). The generated `cst.rs` preamble historically imported several
PyO3 types **unqualified**:

```
use pyo3::types::{PyList, PyTuple, PyType};   // removed by the fix
use pyo3::prelude::*;                          // brings PyModule, PyAny, ... into scope
```

When a downstream grammar has a rule named `list`, `tuple`, `type`, or `module`,
`snake_to_upper_camel` yields `List`/`Tuple`/`Type`/`Module`, and the handle
struct is `PyList`/`PyTuple`/`PyType`/`PyModule` — colliding with the imported
pyo3 name. rustc fails with `E0255` (name defined twice) / `E0117`. Clockwork's
`clockwork.fltkg` has both a `list` rule and a `module` rule (its top rule), so
this is not hypothetical — it blocked the build (`implementation-log.md` Inc 5).

This is a **generated-public-API correctness bug**: the set of grammar rule names
a downstream consumer may legally use was silently narrower than documented, and
the narrowing was invisible until a real consumer grammar hit it under a real
compile.

The pre-existing `_RESERVED_CLASS_NAMES` mechanism (`gsm2tree_rs.py:43`) is the
design's chosen tool for "rule name X collides with a fixed generated identifier":
it rejects the grammar at generation time with a clear diagnostic. So the design
already had two possible responses to a collision: **(a) reserve the name**
(reject the grammar) or **(b) qualify the generated reference** (so no collision
exists and the name stays legal).

### 2.2 What the implementer did

Chose **(b) qualify** for `PyList`/`PyTuple`/`PyType`/`PyModule`: dropped the
unqualified `use pyo3::types::{...}`, rewrote every emission site to
`pyo3::types::PyList::...` etc., and changed both `register_classes` signatures
(`gsm2tree_rs.py`, `gsm2parser_rs.py`) to `&Bound<'_, pyo3::types::PyModule>`.
Chose **(a) reserve** for `IndexError`/`TypeError`/`ValueError` (still imported
unqualified from `pyo3::exceptions`) and for `Any` (`PyAny`, used at ~30 sites
via `pyo3::prelude::*` — qualifying all 30 deferred). Added a machine-checked
invariant and tests for both the now-accepted names (`list`/`tuple`/`type`/
`module`) and the still-reserved ones.

### 2.3 Verdict: RATIFY the chosen mix, with one mandated follow-up (TODO)

The **(b)-where-cheap / (a)-where-expensive** split is the correct design, and the
two responses are the *only* two correct responses available. Rationale:

1. **Preferring qualify (b) over reserve (a) for common names is right.** `list`,
   `module`, `type`, `tuple` are extremely common grammar rule names (Clockwork
   hit two of four immediately). Reserving them would permanently amputate natural
   rule names from the public grammar surface for every consumer forever — a
   worse outcome than a one-time generator edit. CLAUDE.md's "generated output is
   public API" principle cuts *toward* qualifying: keep the consumer's namespace
   maximal. So qualifying the cheap cases is not just acceptable, it is the
   compatibility-preserving choice.
2. **Reserving `Any` for now is a defensible cost trade**, but it leaves `any` —
   another plausible rule name — rejected. This is acceptable *only as a tracked
   deferral*, not as a permanent design choice. The fix must carry a
   `TODO(rust-pyany-qualify)` so the asymmetry ("we qualified four names but
   reserved a fifth purely because it was tedious") is visible and burned down,
   not silently load-bearing. See §2.5.

### 2.4 Is the fix robust and general, or does it merely patch the names Clockwork hit?

This is the question the task flags hardest. Assessment:

**The defense-in-depth structure is general; the qualify-list is not yet
exhaustive.** The design is robust *because* the `_RESERVED_CLASS_NAMES` backstop
plus the module-load invariant (`gsm2tree_rs.py:77`) guarantees that **any**
rule-name/identifier collision is either fixed-by-qualification or
rejected-with-a-diagnostic — never a silent miscompile. A consumer can never get
a confusing rustc error from a name the generator failed to anticipate *as long as
the reserved set is complete*. That backstop is the real robustness property, and
it predates this fix.

However, the **completeness of the reserved set is audited by hand**, and the fix
only audited the names Clockwork's grammar exercised plus the obvious
`pyo3::prelude` / `pyo3::exceptions` imports. The generated `cst.rs` and
`parser.rs` preambles bring in more than the four names that were qualified:

- `pyo3::prelude::*` re-exports a broad set of types into the **type namespace**.
  Confirmed against pyo3 0.29's `prelude.rs` (lines 11–18), the re-exported types
  are: `FromPyObject`, `FromPyObjectOwned`, `IntoPyObject` (`:11`); `PyErr`,
  `PyResult` (`:12`); `Borrowed`, `Bound`, `Py` (`:13`); `Python` (`:14`); `PyRef`,
  `PyRefMut` (`:15`); `PyClassInitializer` (`:16`); `PyAny`, `PyModule` (`:17`);
  `PyClassGuard`, `PyClassGuardMut` (`:18`) — plus the method traits. Note that
  `PyObject` is **not** in the prelude (nor re-exported at the crate root: `lib.rs`
  re-exports only `FromPyObject`, `IntoPyObject`, `IntoPyObjectExt` from
  `conversion`), so a rule named `object` → `PyObject` does **not** collide — it is
  not an example of a gap. The real un-reserved `Py`-prefixed gaps are `err` →
  `PyErr` and `result` → `PyResult` (both `prelude.rs:12`): each derives a
  `pub struct PyErr`/`PyResult` that collides with the prelude import (`E0255`, two
  definitions in the type namespace) and is **not** in the reserved set. Only
  `PyModule` and `PyAny` were reasoned about. The design must not rest on this set
  being re-audited by hand against each pyo3 release's prelude.
- **The collision surface is wider than the `Py`-prefixed handles.** The generator
  emits, per rule, a **bare data struct named `{CN}`** (`gsm2tree_rs.py:_node_block`,
  `pub struct {class_name}` — *not* `Py`-prefixed) alongside the `Py{CN}` handle.
  The prelude glob brings several **non-`Py`-prefixed** names into the type namespace:
  `Bound`, `Py`, `Python`, `Borrowed`, `PyRef`, `PyRefMut`, `PyClassInitializer`,
  `PyClassGuard`, `PyClassGuardMut`. A rule named `bound` → `Bound`, `py` → `Py`,
  `python` → `Python`, or `borrowed` → `Borrowed` derives a bare `pub struct
  Bound`/`Py`/`Python`/`Borrowed` that collides with the prelude re-export (`E0255`).
  None of these are in `_RESERVED_CLASS_NAMES`, and the cross-rule claims check
  (`gsm2tree_rs.py:144`) compares generated identifiers only against each other, not
  against the pyo3 glob — so these reach rustc as the exact silent-miscompile failure
  mode the backstop is supposed to prevent.
- The `parser.rs` preamble (`gsm2parser_rs.py:845`) imports `PyRecursionError`,
  `PyValueError` unqualified and uses `PyAny`. But — importantly — the **parser
  generator emits only fixed class names** (`PyParser`, `PyApplyResult`), never
  rule-derived `PyX` structs. So rule-name collisions cannot reach the parser
  preamble; only the `register_classes(module: ...)` parameter mattered there, and
  that was fixed. This asymmetry (cst.rs is rule-name-driven, parser.rs is not) is
  load-bearing and must be documented so a future change that *does* emit
  rule-derived names in parser.rs re-opens the analysis.

**Mandated robustness upgrade (REVISE the fix to add this):** the reserved-set
completeness must be converted from "audited by hand against the names we
happened to think of" into a **mechanically-derived or mechanically-checked**
property — over the **full set of unqualified names the preamble brings into the
type namespace**, `Py`-prefixed or not. The collision surface has two halves and the
upgrade must cover both:

1. The rule-derived `Py{CN}` handle vs. `Py`-prefixed pyo3 imports (`PyErr`,
   `PyResult`, `PyAny`, `PyModule`, the qualified-already `PyList`/`PyTuple`/`PyType`,
   the exception imports).
2. The bare `{CN}` data struct vs. **non-`Py`-prefixed** prelude re-exports
   (`Bound`, `Py`, `Python`, `Borrowed`, `PyRef`, `PyRefMut`, `PyClassInitializer`,
   `PyClassGuard`, `PyClassGuardMut`).

Qualifying every `Py`-prefixed emission site addresses only half 1; it does *nothing*
for half 2, where the collision is between the bare `{CN}` struct and a glob
re-export, not a `Py{CN}` handle. The completeness property "structurally cannot ship
an unhandled pyo3 collision" is therefore **not** achievable by qualifying
`Py`-prefixed types alone — it requires making the preamble's full import set
enumerable.

**The load-bearing step is de-globbing.** A `use pyo3::prelude::*;` glob is, by
construction, *unenumerable* by the generator: it cannot know which names rustc pulls
into scope from a given pyo3 version, so it can neither reserve nor qualify against
them. Replace the glob with an explicit `use pyo3::prelude::{Bound, Py, Python, PyAny,
PyModule, ...};` listing only what the generated code uses. The import set then
becomes **data the generator owns**, and a generator-load check can compare every
imported unqualified name (`Py`-prefixed or not) against the rule-derived/`{CN}`
identifier space and either reserve it or require it qualified — covering both halves.
This de-glob is mandatory in either upgrade path below; without it, half 2 stays open.

Given a de-globbed, enumerable import set, one genuine choice remains for the
`Py`-prefixed half:

- **(Preferred) Qualify the `Py`-prefixed emission sites too.** Beyond reserving, also
  rewrite the `Py`-prefixed uses (`PyAny`'s ~30 sites being the bulk) to fully-qualified
  paths so the `Py{CN}` handles can never collide. This empties the `Py*` half of
  `_RESERVED_CLASS_NAMES`, recovers `any` as a legal rule name, and subsumes
  `TODO(rust-pyany-qualify)`.
- **(Acceptable) Reserve the residual `Py`-prefixed names; defer qualification.** The
  generator-load check rejects a grammar whose rule derives a still-imported
  `Py`-prefixed name, with a clear diagnostic. Cheaper now; keeps `any` and the other
  residual names reserved until the qualification is done.

**Non-pyo3 generated identifiers.** The task also asks about rule names colliding
with *other* generated identifiers (not pyo3). That class is already handled by
the pre-existing machinery: fixed generated names (`NodeKind`, `Span`, `Shared`,
`CstError`, `DropWorklistItem`, `EqWorklistItem`) are in `_RESERVED_CLASS_NAMES`,
and cross-rule collisions (`Py{CN}`, `{CN}Child`, `{CN}Label`) are detected in
`RustCstGenerator.__init__`'s claims check (`gsm2tree_rs.py:144`). The pyo3 fix
correctly slots into this existing framework rather than inventing a parallel one.
No change needed there; it is already general.

### 2.5 Net disposition for Problem 1

- **RATIFY** the qualify-vs-reserve split and the qualified emission of
  `PyList`/`PyTuple`/`PyType`/`PyModule`. The committed generated artifacts are in
  sync and the full gate is GREEN (`verify-fltk-gate.md`): keep them.
- **REVISE** to add the robustness upgrade in §2.4: drop the `pyo3::prelude::*`
  glob in `cst.rs` in favor of an explicit prelude import list, then mechanize the
  reserved-or-qualified check over the **full** import set (`Py`-prefixed handles
  *and* non-`Py`-prefixed re-exports such as `Bound`/`Py`/`Python`/`Borrowed` that
  collide with the bare `{CN}` data struct). Qualifying the `Py`-prefixed sites
  additionally recovers `any`. This is an *edit* to the existing commits, not a
  revert.
- **TODO(rust-pyany-qualify)** if the preferred upgrade is not done in this pass:
  the `Any`/`PyAny` reservation is a tedium-driven deferral, not a design
  position, and must be tracked in `TODO.md` + a `TODO(slug)` comment at the
  reservation site per CLAUDE.md's TODO convention.

---

## 3. Problem 2 (Tier 2): `@fltk//:native` needs explicit `python` crate-feature

### 3.1 The underlying problem

The original design (§3.1) asserted that the consumer cdylib's `["extension-module"]`
feature would forward to `fltk-cst-core/python` "the way Cargo does." That is false
under Bazel. `rules_rust` `crate_features` are **per-target and non-transitive**:
Bazel does not run Cargo's feature unification, so a feature enabled on a dependent
crate does not turn on a feature of a dependency crate. The `register_classes`
symbols (and other PyO3 glue) in `cst_generated.rs` / `cst_fegen.rs` are gated on
`#[cfg(feature = "python")]`; without `python` explicitly enabled on the
`@fltk//:native` target itself, those symbols compile out and the cdylib fails to
link (`E0425`, unresolved symbols) — `implementation-log.md` Inc 5.

This is a defect in the original design's Cargo-vs-Bazel feature-model assumption,
exactly the kind of thing only a real build surfaces.

### 3.2 Verdict: RATIFY

The fix — add `"python"` alongside `"extension-module"` in the `@fltk//:native`
`crate_features` (`BUILD.bazel`) — is correct and minimal. The accompanying comment
correctly records *why* (Bazel non-forwarding). Keep it.

**Generalization the design must state (no code change, doc only):** this is not
specific to `@fltk//:native`. **Every** PyO3 cdylib built under these rules — most
importantly the consumer cdylib produced by `fltk_pyo3_cdylib` — needs
`fltk-cst-core/python` enabled on the link, because the same `#[cfg(feature =
"python")]` gating applies to the generated consumer `cst.rs`. The original design
§3.1 said the macro sets `["extension-module"]` and expected forwarding; that is
the same false assumption. The macro must therefore **also** set `python` (or
equivalently, the `fltk-cst-core` rust_library target that all cdylibs link must be
built with `python` on, and the cdylib's own `cst.rs` gating must be satisfied).
The fact that Clockwork's cdylib built GREEN means this is *already* handled on the
macro path (the macro links `//crates/fltk-cst-core` with `crate_features =
["python"]` per `implementation-log.md` Inc 1, and sets the cdylib's features); the
required action is to **document** the invariant "every pyo3 cdylib target on this
surface must carry both `extension-module` and `python`, because Bazel does not
forward features" in the ADR and in the `fltk_pyo3_cdylib` macro docstring, so a
future consumer who writes a raw `rust_shared_library` instead of using the macro
knows the rule. Without that note, the next hand-rolled cdylib re-hits this exact
defect.

---

## 4. Problem 3 (Tier 2): Starlark implicit string concatenation in `rust.bzl`

### 4.1 The underlying problem

The `cst_mod_path` attr docstring in `generate_rust_parser` used adjacent string
literals across lines (Python-style implicit concatenation). Starlark **forbids**
implicit string concatenation; loading `rust.bzl` fails with "Implicit string
concatenation is forbidden" (`implementation-log.md` Inc 5). Because this is in the
*new public Bazel surface*, any consumer who `load`s `rust.bzl` — i.e. every
consumer — hits it immediately. Review missed it because the file was never loaded
by a Bazel process.

### 4.2 Verdict: RATIFY

The fix (explicit `+` between the string fragments) is the correct and only
idiomatic resolution. Keep it. This is a pure syntax correction with no design
content; the only lesson is that a Bazel `.bzl` file in the public surface must be
**loaded by Bazel at least once** before it can be called "reviewed" — which is the
overarching finding of this whole follow-on (see §8).

---

## 5. Problem 4 (Tier 3): `#![recursion_limit = "512"]` in the consumer `lib.rs`

### 5.1 The underlying problem

Clockwork's grammar contains deeply recursive type references (`DflArg → DflExpr →
... → DflCallSuffix → DflArgList → DflArg`). The generated `PyX` structs hold
nested `Shared<...>` children, and PyO3's `#[pyclass]` macro requires the trait
solver to evaluate `Send + Sync` bounds across the full recursive chain. The
default rustc recursion limit (128) is exceeded, producing `E0275` "overflow
evaluating `Shared<DflArg>: Send`" (`implementation-log.md` Inc 5). The fix raises
the crate-root limit to 512.

This is a real property of large recursive grammars, and it is **consumer-grammar-
dependent** — it did not appear for any fltk in-tree fixture grammar because none
is as deeply recursive as Clockwork's DSL.

### 5.2 Verdict: RATIFY the immediate fix; REVISE its placement/ownership

Raising `recursion_limit` is the correct mechanical resolution — there is no way to
make rustc's trait solver evaluate a deeply recursive bound without it, and 512 is
a reasonable headroom. So the *value* and *mechanism* are ratified.

But the **placement** in the hand-authored consumer `lib.rs` makes correct cdylib
generation depend on the consumer knowing to add an obscure inner attribute. That
is a sharp edge on the public surface: a downstream consumer with a large grammar
will hit `E0275`, an error that gives no hint that "add `#![recursion_limit]` to
your crate root" is the fix. Two better designs, in preference order:

1. **The generated `cst.rs` carries the recursion-limit need to the consumer.**
   `cst.rs` is generated and is a `mod` of the consumer crate; `#![recursion_limit]`
   is a *crate-level* attribute and cannot be set from a submodule, so it cannot
   live in `cst.rs` directly. Therefore: have `fltk_pyo3_cdylib` **inject the
   crate-root attribute** at crate assembly. Implementation note — the macro today
   owns the crate *directory layout*, not the *contents* of `lib.rs`: the
   `_assemble_crate` genrule copies the consumer-authored `lib.rs` **verbatim**
   (`rust.bzl`: `cp $(location {lib_rs}) $$OUTDIR/lib.rs`) and points `crate_root`
   at the copy. So this is not a hook into an existing synthesis step — it is a
   genuine (small) behavioral change to that genrule: modify the copy step to
   **prepend** `#![recursion_limit = "512"]` ahead of the copied content (e.g. write
   the attribute line, then `cat` the consumer `lib.rs` after it). Ordering
   constraint: `#![recursion_limit]` is an **inner attribute** and must precede all
   items *and* all other inner attributes in the file; a naive prepend produces
   `error: an inner attribute is not permitted following an outer attribute` if the
   consumer's `lib.rs` leads with its own attributes, so the macro must emit the
   recursion-limit line as the very first line of the assembled `lib.rs`. This moves
   the knowledge from "every consumer must remember" to "the FLTK macro guarantees
   it," matching the turnkey-macro philosophy of the original design.
2. **(Weaker) Document it as a required line in the consumer `lib.rs` template** in
   the ADR, with the exact `E0275` symptom, so a consumer who hits it can find the
   fix. Acceptable only if (1) is judged too invasive for the POC.

Recommendation: **(1)** — the macro is the right owner, since it already assembles
the crate-root directory; extending it from "copy `lib.rs` verbatim" to "prepend the
recursion-limit inner attribute, then copy" is a small, contained change to the
existing `_assemble_crate` genrule (subject to the inner-attribute-ordering
constraint above), not a new public surface. If (1) is deferred, file
**TODO(rust-recursion-limit-macro)** and ship (2)'s documentation in the interim.
The consumer `lib.rs` line in the current commit should then be removed once the
macro owns it (otherwise it is redundant/misleading).

---

## 6. Problem 5 (Tier 3): `py_pytest_main` target rename `__rust_test__` → `__test__`

### 6.1 The underlying problem

Clockwork's local `py_test` macro (from `//tools/rules:python.bzl`) **hardcodes the
pytest-main label as `:__test__`**; a `py_pytest_main` named `__rust_test__` is
rejected. This is a Clockwork-internal convention the original design did not know,
and it is purely a consumer-side build wiring fact (`implementation-log.md` Inc 5).

### 6.2 Verdict: RATIFY

The rename is correct and entirely local to Clockwork's BUILD file; it touches no
FLTK surface and has no design content beyond "conform to the host repo's macro
convention." Keep it. No generalization needed — this is Clockwork's rule, and any
future Clockwork test target must use `__test__` regardless of this work.

---

## 7. Problem 6 (Tier 3): `Span.__module__` assertion in the roundtrip test

### 7.1 The underlying problem

The roundtrip test (AC #3) must distinguish "Rust `fltk._native.Span` is live" from
"silent pure-Python fallback." The original test asserted `Span.__module__ ==
"fltk._native"`. But **PyO3 0.29 `#[pyclass]` without an explicit `module = "..."`
attribute reports `__module__ == "builtins"`**, not the importing module name
(`implementation-log.md` Inc 5; corroborated by the test-file diff in the Clockwork
delta). So the original assertion would have *failed on a correctly-working Rust
extension* — a false-negative gate. The fix inverts the test: assert
`__module__ != "fltk.fegen.pyrt.terminalsrc"` (the fallback's module), and sanity-
check it is one of `("builtins", "fltk._native")`.

This is a genuine PyO3-runtime-behavior fact invisible without running the import.

### 7.2 Verdict: RATIFY the inversion; note a latent question about `Span`'s `module=`

The corrected assertion is the right shape: the **discriminating fact** is "is this
the pure-Python fallback class, whose `__module__` is
`fltk.fegen.pyrt.terminalsrc`," and the test should key on *that*, not on a
positive `"fltk._native"` that PyO3 does not actually produce. The negative
assertion plus the `("builtins", "fltk._native")` allow-list is correct and is the
most robust available signal for AC #3. Keep it.

**Latent design question to record (does not block; not a defect in this fix):**
the reason `fltk._native.Span` reports `"builtins"` is that the `#[pyclass]` for
`Span` in `fltk-cst-core` does not set `module = "fltk._native"`. If FLTK ever
wants `Span.__module__` to be meaningful (for pickling, repr, or stricter
downstream checks), it would add `#[pyclass(module = "fltk._native")]` to the
`Span` definition — a FLTK-core change outside this POC's scope. Recording it so the
"`builtins` is expected" comment in the test does not later read as a mystery.
**TODO(span-pyclass-module)** is optional and should be filed only if the user
wants the module name to be authoritative; otherwise the current behavior is fine
and the test correctly tolerates it.

---

## 8. Problem 7 (cross-cutting): the override + pin finalization

`implementation-log.md` Inc 5 and `verify-bazel-run.md` establish that the GREEN
run used a `local_path_override` in Clockwork's `MODULE.bazel`
(`932320e..42fedc8`), pointing at the local fltk checkout, marked
`TODO(fltk-pin-finalize)`. Per the task framing this is **deliberate temporary
verification scaffolding, not a defect**. The design's only obligation here is to
specify the **finalization step**:

1. Push the fltk Rust-Bazel commits (through `11d8460`, plus any edits this design
   mandates in §2.4 / §5.2) to the remote `rnortman/fltk.git` that Clockwork's
   `git_override` fetches from. (The verify report notes the prior pin `f32b2c9`
   was both unpushed and stale.)
2. Revert Clockwork's `MODULE.bazel` from `LOCAL_PATH_OVERRIDE` back to the
   `git_override` tuple, bumping the pin to the **pushed** reviewed fltk HEAD.
3. Re-run `bazel test //clockwork/dsl:clockwork_rust_roundtrip_test` against the
   git pin (not the local override) to confirm GREEN survives the real fetch path.
4. Remove the `TODO(fltk-pin-finalize)` comment and its `TODO.md` entry once done.

This step is **REVISE-by-completion**: the override commit is correct *as
scaffolding* but must not merge as-is; finalization is required before the work
lands. It is not a code-design change, but it is a gating action this design owns.

---

## 9. Summary of dispositions

| # | Problem | Tier | Verdict | Action on existing commits |
|---|---------|------|---------|----------------------------|
| 1 | pyo3 name collisions (`PyList/Tuple/Type/Module`) | 1 (gen API) | RATIFY split + REVISE for robustness | Edit: drop `pyo3::prelude::*` for an explicit import list, then mechanize the reserved-or-qualified check over the full import set — both `Py`-prefixed handles and non-`Py`-prefixed re-exports (`Bound`/`Py`/`Python`/`Borrowed`/…) that collide with the bare `{CN}` struct. Qualifying `Py`-prefixed sites also recovers `any`. Keep the four-name qualification + tests. |
| 2 | `python` crate-feature on `@fltk//:native` | 2 (Bazel) | RATIFY | Keep. Add ADR + macro-docstring note that every pyo3 cdylib needs both `extension-module` + `python` (Bazel non-forwarding). |
| 3 | Starlark implicit string concat in `rust.bzl` | 2 (Bazel) | RATIFY | Keep as-is. |
| 4 | `#![recursion_limit = "512"]` | 3 (consumer) | RATIFY value, REVISE placement | Move ownership into `fltk_pyo3_cdylib` (inject at crate-root assembly), default 512; remove the hand-authored consumer line once macro owns it. Interim: document. |
| 5 | `__rust_test__` → `__test__` rename | 3 (consumer) | RATIFY | Keep as-is. |
| 6 | `Span.__module__` test assertion | 3 (consumer) | RATIFY | Keep the inverted assertion. |
| 7 | `local_path_override` + pin finalize | cross-cutting | RATIFY as scaffolding, complete finalization | Push fltk; revert override to git pin at pushed HEAD; re-verify; drop TODO. |

Net: **five of seven fixes are ratified as the right design and kept** (2, 3, 5, 6,
plus the core of 1 and 4). **Two require edits to the existing commits** — Problem 1
(robustness generalization of the pyo3 qualification) and Problem 4 (move the
recursion limit into the macro). Problem 7 is a required finalization action rather
than a code change. No fix is rejected/reverted outright.

---

## 10. Test plan

The original [`design.md`](./design.md) §5 test plan stands. This follow-on adds:

1. **pyo3-collision generality tests (Problem 1).** Beyond the existing
   `list/tuple/type/module` accepted-rule tests and `index_error/type_error/
   value_error/any` reserved-rule tests in `tests/test_gsm2tree_rs.py`, add tests
   covering the further collisions the robustness upgrade must close. For the
   `Py`-prefixed half: a rule named `err` → `PyErr` or `result` → `PyResult` is
   **accepted** if qualified, or **rejected with a clear diagnostic** if reserved.
   (Do **not** include `object`/`PyObject`: `PyObject` is not in pyo3 0.29's prelude
   and is not re-exported at the crate root, so `object` does not collide and is not
   a valid test of the reservation.) For the non-`Py`-prefixed half (the bare `{CN}`
   data struct vs. the prelude glob): a rule named `bound`/`py`/`python`/`borrowed`
   is **accepted** if the de-globbed import set no longer brings the colliding name
   into scope, or **rejected with a clear diagnostic** if reserved. Add a
   generator-load test that an unqualified preamble import (`Py`-prefixed *or* not)
   lacking a corresponding reservation-or-qualification raises at generator load.
   When the `Py`-prefixed sites are qualified, add a test that a rule named `any` is
   now **accepted** and its `PyAny` handle emitted, and that the reserved set no
   longer contains any `Py*`-derived entry.
2. **Macro recursion-limit test (Problem 4, if macro ownership is implemented).**
   A FLTK-side build test that `fltk_pyo3_cdylib` injects `#![recursion_limit]`
   into the assembled crate root (assert on the assembled `lib.rs` content, or a
   build of a deeply-recursive fixture grammar that would otherwise `E0275`).
3. **Real-pin verification (Problem 7).** The roundtrip test must pass under the
   git `bazel_dep`/`git_override` pin (not just `local_path_override`) — the
   finalization re-run is the gate.

All existing gates remain: full pytest (1662), pyright (gate scope), ruff
check/format, zero gencode drift (`verify-fltk-gate.md`), and the two GREEN Bazel
targets (`clockwork_rust_roundtrip_test` 2/2, `bootstrap_rust_srcs`).

---

## 11. Open questions (user judgment)

- **O1 — How far to push the pyo3-collision robustness upgrade now (Problem 1,
  §2.4).** Both acceptable mechanisms require dropping the `pyo3::prelude::*` glob so
  the preamble's import set is enumerable (the glob is the reason the bare `{CN}`
  collisions — `bound`/`py`/`python`/`borrowed` — are invisible to the generator).
  Given that, the choice is whether to *also* qualify the `Py`-prefixed emission
  sites now (more generator churn, but recovers `any` and empties the `Py*` half of
  the reserved set) versus reserving the residual `Py`-prefixed names and deferring
  the qualification. Both satisfy the robustness bar once de-globbed; the choice is
  effort-vs-completeness and is the user's call. Recommendation: de-glob now (it is
  load-bearing for completeness either way) and qualify the `Py`-prefixed sites,
  subsuming `TODO(rust-pyany-qualify)`.

- **O2 — Macro-owned recursion limit value and configurability (Problem 4, §5.2).**
  Inject a fixed `#![recursion_limit = "512"]`, or expose a `recursion_limit` macro
  attr (default 512) for consumers with even deeper grammars? Fixed is simpler;
  configurable is future-proof. Recommendation: configurable attr with default 512.

- **O3 — Whether `Span` should carry `#[pyclass(module = "fltk._native")]`
  (Problem 6, §7.2).** Out of this POC's scope, but it determines whether the
  roundtrip test's `"builtins"` tolerance is permanent or a stopgap. Only the user
  can decide if `Span.__module__` should be authoritative (affects pickling/repr).
  Recommendation: leave as-is for the POC; file `TODO(span-pyclass-module)` only if
  the user wants it.
