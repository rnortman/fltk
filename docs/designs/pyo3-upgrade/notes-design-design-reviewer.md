# Design review findings — pyo3-upgrade

Style note (applies to this doc): concise, precise, complete, unambiguous; audience is a smart
LLM/human implementer.

Verification performed against base commit 2919733 and vendored pyo3 0.29.0 /
pyo3-macros-backend 0.29.0 sources. The load-bearing claims check out:

- All cited tier-1 sites verified exact: `crates/fltk-cst-core/src/span.rs:6,10,40,130,149,404`;
  `cross_cdylib.rs:4,19,35,65,86,111,133,199,239,244,303,312,330,354,372,388`;
  `registry.rs:28,34,145`; `src/lib.rs:3,17`.
- pyo3 0.29 claims verified in vendored source: `PyClassImpl::Layout` at
  `pyo3-0.29.0/src/impl_/pyclass.rs:183`; macro assigns
  `type Layout = <Self::BaseNativeType as PyClassBaseType>::Layout<Self>` at
  `pyo3-macros-backend-0.29.0/src/pyclass.rs:3023`; `PyAny`'s `PyClassBaseType` assigns
  `PyStaticClassObject<T>` (`pyo3-0.29.0/src/types/any.rs:81`), `#[repr(C)] { ob_base, contents }`
  at `src/pycell/impl_.rs:389-393` — so the §2.A probe replacement and the
  `>= size_of::<ffi::PyObject>() + size_of::<T>()` guard-test inequality are sound.
  `PyOnceLock` has `new/get/get_or_init/get_or_try_init` **and `set`** (used by
  `src/lib.rs:27`; `once_lock.rs:93`) — F is drop-in as claimed. `from_py_object` is a parsed
  `PyClassPyO3Option` (`pyo3-macros-backend-0.29.0/src/pyclass.rs:97,125,178`).
  `cast/cast_into/CastError` confirmed (`instance.rs:161,210`).
- Generator claims verified: `gsm2tree_rs.py` PyObject emission anchors, `downcast` at 1071
  (`to_py_canonical`), `extract::<{type_name}>()` at 427, `extract::<{rust_enum_name}>()` at 1251,
  GILOnceCell docstring at 423-424; NodeKind + label enums are `Clone` pyclasses, node handles
  (`Py{CN}`) are not `Clone` and use `PyRef` extraction; `gsm2parser_rs.py:853,861` confirmed.
- Build scaffolding verified: spike regen via `cp` at Makefile:202 (resolves the exploration §4
  open question correctly); all named make targets exist; four lockfiles (root + 3 tests/*);
  six pyo3-bearing manifests; all step-7 parity test files exist. `tests/test_rust_span.py`
  asserts only the `"fltk-cst-core/"` ABI prefix, not the version, so the 0.2.0 bump does not
  break pinned tests.
- Requirements coverage complete: bump (§3.1), advisories + deny.toml ignores (§3.1), all tests
  pass (§3.6-8), cross-backend equivalence (§3.7), public-surface guard (§1, §3.5, §5), TODO
  bookkeeping (§3.8). The two called-out decisions (single jump; 0.2.0 bump) are grounded and
  flagged per CLAUDE.md's deliberate-decision rule.

## design-1

Section: §2.G, "This accounts for the 19 warnings in `fltk-native` (NodeKind + 18 label enums
for fegen.fltkg)".

What's wrong: the accounting is incorrect. `fltk-native` compiles TWO generated grammars:
`src/cst_fegen.rs` (1 NodeKind + 14 label enums = 15 `Clone` pyclasses) and
`src/cst_generated.rs` (PoC grammar: 1 NodeKind + 3 label enums = 4). 19 = 15 + 4, i.e.
2 NodeKinds + 17 label enums across two grammars — not "NodeKind + 18 label enums for
fegen.fltkg". Verified by grep on the committed files (14 and 3 `name = "*_Label"` pyclass
attrs; 1 NodeKind each; `derive(Clone)`-adjacent pyclass counts 15 and 4).

Why: groundedness — the per-grammar breakdown is stated as fact and is wrong; fegen.fltkg has
14 labeled rules, not 18.

Consequence: low for the fix itself (the generator change in `_node_kind_block` /
`_label_enum_block` covers both files via regeneration), but an implementer using this
breakdown as the step-5 verification target ("18 fegen label-enum warnings cleared") will see
numbers that don't match and may hunt for phantom residuals, or fail to notice if PoC-grammar
warnings survive (e.g. a regen step skipped) since the design implies all 19 live in fegen.

Suggested fix: restate as "2 NodeKinds + 17 label enums across `cst_fegen.rs` (1+14) and
`cst_generated.rs` (1+3)".

## design-2

Section: §3 step 8 "Bookkeeping" / §1 "Bump `crates/fltk-cst-core` version 0.1.0 → 0.2.0"
(omission — no section covers consumer documentation).

What's wrong: the plan never updates `docs/rust-cst-extension-guide.md`, the out-of-tree
consumer build guide. Its Cargo.toml template pins both versions the upgrade changes:
`fltk-cst-core = { version = "0.1", ... }` (line 59) and
`pyo3 = { version = "0.23", features = ["abi3-py310"] }` (line 63).

Why: CLAUDE.md — generated artifacts and the surfaces downstream consumers build against are
public API; the guide is the published recipe for exactly the consumer-cdylib scenario the
0.2.0 ABI bump targets. After the upgrade, a consumer following the guide verbatim builds a
pyo3-0.23 / fltk-cst-core-0.1-pattern extension — precisely the mixed-version skew the design's
own §1 decision exists to reject. (With the in-tree path dep they'd get 0.2.0 + a pyo3 version
conflict at build time; with the `version = "0.1"` form, a non-resolving or stale dep.) The
design's §1 rationale ("consumers must rebuild their extension crates against the new
fltk-cst-core + pyo3 0.29") makes the guide the natural place that instruction must land, yet
no step touches it.

Consequence: downstream consumers following the published guide after this lands get builds
that fail or extensions that the new `fltk._native` deterministically rejects with the §1
`TypeError`, with no documented path forward — an avoidable downstream break in exactly the
surface CLAUDE.md says to protect.

Suggested fix: add to step 8: update `docs/rust-cst-extension-guide.md` template to
`pyo3 = "0.29"` and `fltk-cst-core = "0.2"`, and note the rebuild requirement for existing
consumer crates.
