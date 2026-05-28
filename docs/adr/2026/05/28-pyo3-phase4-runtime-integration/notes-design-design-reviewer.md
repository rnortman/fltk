# Design Review: Phase 4 Runtime Integration

Concise. Precise. Source-backed. Audience: smart LLM/human.

Reviewed: `design.md` against `requirements.md`, `exploration.md`, and source at base
commit f8a2fe1. Verified plumbing.py, lib.rs, gsm2tree_rs.py, gsm2tree.py,
genparser.py, fltk2gsm.py, fltk_parser.py, src/cst_fegen.rs, src/cst_generated.rs,
Makefile.

---

## design-1 — AC5 has no wiring mechanism: `fltk2gsm.py` cannot use Rust-backed nodes without a re-export (out of scope) or a source edit (forbidden)

**Section.** "register-classes-module-type" (lines 104-127); Test Plan
`test_fltk2gsm_against_rust_fegen_cst` (lines 450-456) — "run the real `fltk2gsm.py`
against a Rust-backed CST module for the FLTK grammar ... with zero changes to
`fltk2gsm.py`."

**What's wrong.** `fltk2gsm.py:4` is a static binding: `from fltk.fegen import fltk_cst
as cst`. Every consumer reference is `cst.Grammar`, `cst.Items.Label.NO_WS`,
`isinstance(item, cst.Item)`, etc. (verified `fltk2gsm.py:12-68`). `cst` is the
**Python dataclass** module `fltk.fegen.fltk_cst`. There is no runtime injection seam,
no module parameter, no monkeypatch hook (single import, confirmed). The design's
backend selector flows through `plumbing.generate_parser` → a per-call
`types.ModuleType` that the *generated parser/unparser* import. `fltk2gsm.py` is not on
that path; it never imports the runtime `cst_module`.

For AC5 to exercise Rust-backed nodes, `cst.Item` / `cst.Items.Label.NO_WS` must resolve
to the PyO3 classes in `fltk._native.fegen_cst`. They cannot today:
- `isinstance(rust_item, fltk_cst.Item)` is **False** — the PyO3 class in
  `fltk._native.fegen_cst` (src/cst_fegen.rs) and the dataclass `fltk_cst.Item` are
  distinct type objects.
- `rust_item.children[0][0] == cst.Items.Label.NO_WS` is **False** — LHS is the PyO3
  `Items_Label` enum (gsm2tree_rs.py:151 `#[pyclass(eq, hash, frozen)]`), RHS is the
  Python `enum.Enum` member (gsm2tree.py:112-115). Different types; `__eq__` returns
  `NotImplemented`/False.

The only ways to make `cst.*` resolve to Rust classes are (a) re-export
`fltk_cst.py` from `fltk._native.fegen_cst` — **explicitly out of scope** (requirements
line 27, "Replacing `fltk/fegen/fltk_cst.py` with a Rust re-export ... folded in as
dual-mode coexistence; both backends remain; neither is removed"), or (b) edit
`fltk2gsm.py` — **forbidden** (requirements line 116 "Static-consumer immutability";
design line 144 reaffirms zero changes to `fltk2gsm.py`). The design picks neither and
provides no third mechanism.

**Why.** Exploration line 410 hedged exactly this with "*If* `fltk_cst.py` re-exports
from `fltk._native.fegen_cst`, then `cst.Item` is the PyO3 class." The design dropped
the conditional and asserts AC5 is satisfiable while keeping the re-export out of scope.
Requirements line 99/131 designate AC5 the *binding* verification of the API Contract
for the Rust backend — so this is not a peripheral test.

**Consequence.** AC5 (Tier-2, the single binding contract verification for the Rust
backend per requirements lines 99, 131) is unachievable as designed. The design's
`test_fltk2gsm_against_rust_fegen_cst` cannot be written without violating either the
out-of-scope boundary or the static-consumer-immutability constraint. The contract
items most at risk (stride slices, label `==`/`in`, `isinstance`) go unverified for the
Rust backend, leaving the central Rust-backend risk the requirements call out
undischarged. Either: (i) AC5 must be reframed to construct Rust nodes directly and
assert the list/label/`isinstance` operations against `fltk._native.fegen_cst` classes
*without* going through the imported `cst` alias in `fltk2gsm.py` (i.e. a hand-written
test mirroring fltk2gsm's operations, not "the real fltk2gsm.py"), or (ii) a re-export
seam must be brought into scope. The design must state which; as written it claims a
verification path that does not exist.

**Suggested fix.** Reframe AC5's test to exercise the API-Contract operations
(`children[::2]`, `children[1::2]`, `children[-1]`, tuple unpack, label `==`/`in`,
`isinstance`) directly against node instances built from `fltk._native.fegen_cst`,
parallel to fltk2gsm's logic, rather than invoking `fltk2gsm.Cst2Gsm`. Or add an
explicit, scoped re-export/aliasing mechanism and update the scope boundary. Note this
also implicates AC7's "same consumer code against each backend."

---

## design-2 — AC3 (non-FLTK roundtrip) requires building/committing a brand-new Rust submodule the design treats as a mere test fixture; this is real Phase-4 build work, not pre-existing

**Section.** Test Plan Tier 2 (lines 436-449); `test_rust_roundtrip_non_fltk_grammar`
(AC3); "A test grammar's Rust CST is wired into `src/lib.rs` (manual step, committed for
the test fixture) and built by CI" (lines 438-439).

**What's wrong.** Only two Rust CST modules exist in the tree: `cst_generated`
(Identifier/Items/Trivia PoC) registered **directly on `m`** at lib.rs:31 (NOT an
importable submodule), and `cst_fegen` registered as the submodule
`fltk._native.fegen_cst` (lib.rs:35-49). AC2/AC3 require a **non-FLTK** grammar's Rust
CST exposed as an importable `fltk._native.<submodule>`. That artifact does not exist;
producing it means: generate `.rs` via `gen-rust-cst`, hand-edit `lib.rs` to add a
`mod` + `register_classes` + `add_submodule` + `sys.modules` block, commit the generated
`.rs`, and rebuild. The design labels this a "test fixture" (line 438) but it is the
core Tier-2 build deliverable (AC6) and is non-trivial committed source + a manual
lib.rs edit per the design's own "manual, reviewed step" (lines 333-339).

**Consequence.** AC2, AC3, AC6, and the Rust half of AC7 all depend on this committed
artifact + lib.rs edit existing. The design under-scopes it as fixture setup. If the
implementer treats it as "just a fixture," the committed `.rs` (potentially thousands of
lines, cf. cst_fegen.rs 4588 lines) and the lib.rs edit may be omitted or
under-reviewed, and every Tier-2 AC silently degrades to skip-when-absent (design lines
341-349) — i.e. never actually verified. The design should name the concrete test
grammar, the submodule name, and that its `.rs` is committed, so the Tier-2 ACs are
genuinely exercised rather than perpetually skipped.

**Suggested fix.** Specify the AC3 test grammar (small, non-FLTK), its submodule name,
that its generated `.rs` and the lib.rs edit are committed deliverables of Phase 4, and
that CI's lane has them wired so skips do not mask unverified ACs.

---

## design-3 — `cst_generated` is not an importable submodule; if reused for a Tier-2 test it will fail `importlib.import_module`

**Section.** artifact-build-mechanism decision (lines 43-51) — "following the exact
pattern `lib.rs:30-49` already uses"; `_load_rust_cst_classes` import note (lines
239-241).

**What's wrong.** The design states the pattern at lib.rs:30-49 registers submodules in
`sys.modules`. Only `fegen_cst` does (lib.rs:35-49). `cst_generated::register_classes(m)`
at lib.rs:31 adds classes **directly to the top-level `_native` module**, with no
submodule and no `sys.modules` entry. `importlib.import_module("fltk._native.<x>")` only
works for `fegen_cst` today. The design's prose ("the exact pattern lib.rs:30-49 already
uses for `cst_fegen` → `fltk._native.fegen_cst`") is accurate for `fegen_cst` but the
broader "lib.rs:30-49" range conflates it with the top-level `cst_generated`
registration, which is the wrong template.

**Consequence.** Minor if the implementer copies the `fegen_cst` block specifically;
becomes a bug if anyone reuses `cst_generated` as the AC2/AC3 fixture (its classes are
not importable as a submodule, so `_load_rust_cst_classes("fltk._native.cst_generated")`
raises `RustBackendUnavailableError`). Tighten the citation to lib.rs:35-49 and note
that `cst_generated`'s top-level registration is NOT a usable template.

---

## design-4 — Python-backend `parser_globals` injection set narrows from "all cst_globals" to "public only"; argued safe, but the design omits that the *node-class label enums* are nested and unaffected — verify the claim is the binding guard

**Section.** Rust-backend path pseudocode (lines 193-208); Edge Cases "Python backend
behavior is unchanged" (lines 395-407).

**What's wrong (partial — mostly a verification note).** Current code does
`parser_globals.update(cst_globals)` (plumbing.py:127), injecting **every** key incl.
`__builtins__`. The redesign injects only `public` (`not k.startswith("_")`). The design
argues (lines 404-407) the only dropped key is `__builtins__`, which `exec` re-supplies.
Verified: `gen_py_module` emits `import dataclasses, enum, typing,
fltk.fegen.pyrt.terminalsrc` + ClassDefs (gsm2tree.py:96-107); a dotted import binds
top-level name `fltk` (pygen.import_ uses `import {imp}`, pygen.py:27-30). So
`cst_globals` public keys = {`dataclasses`,`enum`,`typing`,`fltk`, node-class names};
sole underscore key is `__builtins__`. The argument holds.

However, the runtime-generated parser does **not** depend on `dataclasses`/`enum`/
`typing`/`fltk` coming from `cst_globals` at all — `parser_globals` already supplies
`fltk`, `terminalsrc`, `typing`, `Span`, `Optional` (plumbing.py:118-126), and the
generated parser references `fltk.fegen.pyrt.terminalsrc.Span(...)` and
`fltk.fegen.pyrt.memo.*` (verified fltk_parser.py:78-117 pattern). So for the **Rust**
path, `_load_rust_cst_classes` filtering to `isinstance(obj, type)` (dropping module
objects entirely) is also safe — the parser needs only the CST *class* names from the
CST module. This is correct but the design does not explicitly state why dropping the
module objects on the Rust path is safe (it only justifies it for the Python path's
`__builtins__`).

**Consequence.** Low. The change is sound but rests on AC1 (existing tests) as the only
guard (design line 407). If a future grammar's generated CST module gained a top-level
non-class public name the parser relied on, the Rust path (type-only filter) and Python
path (now public-only) would diverge silently. Recommend an explicit assertion/comment
that the parser namespace's CST contribution is class-names-only, so the two backends'
`public` dicts are contractually class-only. Otherwise acceptable.

---

## design-5 — `_load_rust_cst_classes` broad `except Exception` can mask a real bug as "backend unavailable"

**Section.** `_load_rust_cst_classes` (lines 220-235); Edge Cases (lines 375-381) —
"The broad `except Exception` is deliberate."

**What's wrong.** `importlib.import_module(module_name)` runs arbitrary module-init code.
Wrapping it in `except Exception` and re-raising as `RustBackendUnavailableError`
converts *any* exception during import (e.g. a genuine bug in a future Python-side shim,
a `KeyError`, an `AttributeError` from unrelated init) into "backend unavailable." The
design defends this as "any load failure must become the hard error." For a pure
submodule lookup (Option A/E) the import is a cached `sys.modules` hit and effectively
cannot fail except `ModuleNotFoundError` — so the broad catch is over-broad relative to
the actual failure surface.

**Consequence.** Low-to-moderate. A real defect during import would be reported as a
missing/unloadable artifact, sending the developer to investigate the build/artifact
rather than the actual bug. AC4 only requires that import failure hard-errors with no
fallback; catching `ImportError` (covers `ModuleNotFoundError` and ABI/version mismatch,
which surface as `ImportError`) satisfies AC4 precisely without swallowing unrelated
exceptions. Narrow the catch to `ImportError` (and chain via `from exc`), or document
why broader is needed.

**Suggested fix.** `except ImportError as exc:`.

---

## design-6 — Makefile `build-native` / `rust-cst` cannot actually build a user grammar without the manual lib.rs edit; `rust-cst` as written produces an artifact that does NOT expose the new grammar

**Section.** Makefile targets (lines 316-339); `test_makefile_builds_rust_cst` (AC6,
lines 457-460) — "the `make rust-cst` target (with the test grammar pre-wired) produces
an importable `fltk._native.<submodule>`."

**What's wrong.** `rust-cst: gen-rust-cst build-native` (line 330) emits `.rs` then runs
`maturin develop`. But `maturin develop` compiles only what `src/lib.rs` `mod`-includes.
The emitted `.rs` is NOT wired into `lib.rs` (the design explicitly makes lib.rs wiring a
**manual, non-automated** step, lines 333-339). So `make rust-cst` on a fresh grammar
produces a `fltk._native` that does **not** contain the new submodule — the emitted
`.rs` is dead until a human edits `lib.rs`. The Makefile target name and the AC6 test
("`make rust-cst` ... produces an importable `fltk._native.<submodule>`") imply an
end-to-end build that the targets do not deliver without an interposed manual edit.

**Consequence.** Moderate. AC6 as tested ("make rust-cst produces an importable
submodule") passes ONLY when the lib.rs edit was already committed — i.e. the test
verifies `maturin develop` recompiles an already-wired tree, not that `make rust-cst`
turns a grammar into a loadable submodule. The requirement (line 75-76: "Compile it to a
loadable artifact exposing `register_classes`. Place the artifact at a location the
runtime selector can reference") is only met with a manual step the Makefile cannot
encode. This is defensible given Option A/E, but the design should not name a target
`rust-cst` that suggests one-shot grammar→artifact, and AC6's phrasing should state the
prerequisite lib.rs edit explicitly. Otherwise an implementer wires AC6 to expect
`make rust-cst GRAMMAR=new.fltkg` to yield an importable module and it will not.

**Suggested fix.** Rename/redocument so the targets read as "emit .rs" + "rebuild
already-wired native"; state in AC6 that the submodule is pre-wired+committed before
`make rust-cst` is meaningful.

---

## design-7 — Empty `public` dict from a valid-but-classless module: filter could also drop a single zero-label rule's lone node class? No — but flag the `isinstance(obj, type)` interaction with PyO3 enums

**Section.** `_load_rust_cst_classes` filter (lines 225-235, 242-248); Edge Cases
"Empty-label-enum rules" (lines 389-393).

**What's wrong (verification note, likely fine).** The filter keeps
`not name.startswith("_") and isinstance(obj, type)`. PyO3 `#[pyclass]` node structs and
`#[pyclass]` label enums are both `type` instances at the Python level, so both pass
(confirmed: gsm2tree_rs.py:191 `#[pyclass]` struct, :151 `#[pyclass(...)]` enum). Good.
The "empty module ⇒ raise" guard (lines 230-234) is reasonable. One unverified assumption:
the design asserts the top-level `*_Label` enums "do not collide with node-class names
(suffix `_Label`)" and "nothing references them" (lines 358-364). Verified the suffix
claim against gsm2tree_rs.py:142/466 (`{class_name}_Label`). The "nothing references
them" claim is correct for the generated parser/unparser (they use `ClassName.Label.*`
via the `#[classattr] Label`, gsm2tree_rs.py:245-254), but injecting the extra top-level
`*_Label` names into `parser_globals` is a behavioral asymmetry vs the Python backend
(which has no top-level `*_Label`). Harmless as argued, but it means the two backends'
`parser_globals` are NOT identical in keys.

**Consequence.** Low. No known breakage; the asymmetry is benign because the names are
distinct and unreferenced. Worth a one-line note that backend parity is "node-class
names identical; Rust adds extra `*_Label` aliases that are inert," so a future reader
does not assume key-for-key parity (relevant if anything ever iterates
`parser_globals` by predicate).

---

## design-8 — TODO(rust-cst-standalone-so) lacks the required TODO.md entry per CLAUDE.md two-piece convention

**Section.** Open Questions, `TODO(rust-cst-standalone-so)` (lines 493-503) — "Add the
matching `TODO(rust-cst-standalone-so)` comment ... and a `TODO.md` entry."

**What's wrong.** The design correctly commits to both pieces. This is a forward
reminder, not a defect in the design doc itself — flagged so implementation does not drop
the `TODO.md` half. CLAUDE.md "TODO System": both the `TODO(slug)` comment AND the
`TODO.md` entry are mandatory and join on the slug. The design also defers Option B with
"see TODO below" (line 58) — ensure that deferral maps to the same slug, not a second
unlogged TODO.

**Consequence.** Low (process). If only the code comment lands, the TODO is "silent" and
violates the project convention. Non-blocking; noted for implementation.

---

## Coverage summary

- AC1 (Python unchanged): covered (design lines 167, 395-407, 417-419). Sound.
- AC2 (Rust module registered): covered but depends on design-2/design-3 (artifact must
  exist as importable submodule).
- AC3 (non-FLTK roundtrip): under-scoped — design-2.
- AC4 (hard error, no fallback): covered well (lines 250-270, 420-427); raise precedes
  `sys.modules` set and parser exec — verified achievable. See design-5 (catch breadth).
- AC5 (fltk2gsm vs Rust): **not achievable as designed** — design-1 (the binding AC).
- AC6 (Makefile builds artifact): partial / mis-scoped — design-6.
- AC7 (both backends satisfy contract): Python half covered; Rust half inherits design-1.

Resolved [DESIGN] open questions (artifact-build-mechanism→A/E, module-name-stability,
register-classes-module-type, selector-shape) are internally consistent and correctly
follow the requirements' coupling note (line 141). The selector reframe from path-based
(b) to module-name-string is well-justified by Option A/E and the source facts
(crate::UNKNOWN_SPAN pub(crate), Cargo.toml cdylib-only — verified lib.rs:10,
Cargo claim via exploration). No scope creep; no over-engineering. The single new
exception class is justified.
