# Design Review: Phase 3 Rust CST Generator (`gsm2tree_rs.py`)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Reviewed: design.md against requirements.md, exploration.md, phase-plan.md, and source
(`gsm2tree.py`, `cst_poc.rs`, `lib.rs`, `gsm.py`, `context.py`, `plumbing.py`, `genparser.py`,
`fegen.fltkg`, `test_rust_cst_poc.py`, `test_gsm2tree.py`, `test_regression_empty_nary.py`).
Most load-bearing claims verified accurate. Findings below are the exceptions.

---

## design-1: Submodule classes not importable via `from fltk._native.fegen_cst import ...` (AC-7/AC-8 test design likely broken)

**Section**: "`lib.rs` Changes" (lines 292-296); Test Plan "`tests/test_fegen_rust_cst.py`",
`test_all_classes_importable` ("importable from `fltk._native.fegen_cst`", line 381).

**What's wrong**: The design registers fegen classes into a child module created with
`PyModule::new(m.py(), "fegen_cst")` + `m.add_submodule(&fegen_sub)`. In PyO3 0.23
(`Cargo.toml:15`), `add_submodule` attaches the submodule as an *attribute* of the parent but
does NOT insert it into `sys.modules`. Consequently `from fltk._native.fegen_cst import Grammar`
and `import fltk._native.fegen_cst` raise `ModuleNotFoundError`. Only attribute access
(`fltk._native.fegen_cst.Grammar`) works. This is a well-known PyO3 submodule gotcha; no existing
code in this repo uses `add_submodule` (`grep` of `src/` finds none), so the pattern is unproven
here.

**Why**: PyO3 0.23 docs ("Python submodules") state submodules added via `add_submodule` are not
registered in `sys.modules` and `import`/`from ... import` on them fails unless the package
manually inserts them. The design's test phrasing "importable from `fltk._native.fegen_cst`"
(line 381) and AC-7's framing strongly imply an `import` statement.

**Consequence**: If `test_fegen_rust_cst.py` uses `from fltk._native.fegen_cst import ...` or
`importlib.import_module("fltk._native.fegen_cst")`, AC-7/AC-8 tests fail at import with
`ModuleNotFoundError` despite correct compilation (AC-7 compile may still pass, but the smoke test
AC-8 cannot run). Implementer wastes a debug cycle, or silently rewrites the test to attribute
access without noticing the design said "import".

**Suggested fix**: Either (a) state explicitly that the smoke test accesses classes via attribute
(`import fltk._native; fltk._native.fegen_cst.Grammar`), not via `import`/`from import`; or
(b) add a `sys.modules` registration in `lib.rs` after `add_submodule`
(`m.py().import("sys")?.getattr("modules")?.set_item("fltk._native.fegen_cst", &fegen_sub)?;`) and
note it. Pick one and make the test plan match.

---

## design-2: `capture_trivia` value inconsistent between design body and cited exploration; design body is correct but the contradiction is unresolved

**Section**: "Model Reuse Strategy" (line 65: `create_default_context()` — no arg) vs the design's
own line 78 ("`capture_trivia` on the context is irrelevant") vs exploration §13 (line 472:
`create_default_context(capture_trivia=True)`), which the design otherwise endorses.

**What's wrong**: The design's `__init__` snippet omits `capture_trivia` (defaults to `False`),
and line 78 argues it is irrelevant to model building. That argument is **correct**:
`add_trivia_rule_to_grammar` and `classify_trivia_rules` both ignore `context`
(`gsm.py:380 # noqa: ARG001`, and `classify_trivia_rules` takes only `grammar`), and
`CstGenerator.__init__` (`gsm2tree.py:34-44`) never reads `context.capture_trivia`. But the
exploration the design builds on shows `capture_trivia=True`. The two artifacts disagree and the
design does not flag the divergence.

**Why**: Source-verified — `context.py:50` signature, `gsm.py:380/273`, `gsm2tree.py:34-44`.
`plumbing.py:97-101` (the canonical reuse site) passes whatever `capture_trivia` the caller gave;
it does not force `True` for CST model building.

**Consequence**: Low. The chosen value (`False`) is harmless and correct. Risk is only that an
implementer copying the exploration snippet introduces `capture_trivia=True` and a later reader
assumes it matters. No functional breakage.

**Suggested fix**: One sentence noting the exploration's `capture_trivia=True` is superseded;
`False`/omitted is fine because no trivia-relevant path reads it.

---

## design-3: Minimal-grammar reference path imprecise (file is under `fltk/fegen/`, not `tests/`)

**Section**: Test Plan `test_minimal_grammar_single_rule` (line 367), citing
"`numbers := digit+` from `test_regression_empty_nary.py`"; also "New Files" places
`tests/test_gsm2tree_rs.py` in `tests/`.

**What's wrong**: The `numbers := digit+` fixture exists at
`fltk/fegen/test_regression_empty_nary.py:55` (verified), not at a top-level `tests/` path. The
design (and exploration §6) cite the bare filename, implying `tests/`. All existing generator and
grammar tests live under `fltk/fegen/` (`test_gsm2tree.py`, `test_gsm2parser.py`,
`test_regression_*.py`); only the Rust-extension tests live in `tests/` (`test_rust_cst_poc.py`,
`test_rust_span.py`). The design puts the new generator unit tests in `tests/`.

**Why**: `ls tests/` returns 5 files, all Rust/span; `find . -name 'test_*.py'` shows the grammar
test suite under `fltk/fegen/`.

**Consequence**: Low. The `numbers := digit+` pattern is real and copyable; the design's intent
(construct a `gsm.*` single-rule grammar, assert no crash) is sound regardless of location. Risk
is only minor: an implementer searching `tests/` for the fixture finds nothing, and the
test-file placement splits generator tests across two directories (existing convention puts them
in `fltk/fegen/`). Worth a deliberate decision rather than accident.

**Suggested fix**: Correct the citation to `fltk/fegen/test_regression_empty_nary.py`. Decide
test placement explicitly: `tests/` is defensible (it is where Rust-backed tests live and these
tests exercise compiled Rust), but state the rationale since it diverges from the `fltk/fegen/`
generator-test convention.

---

## design-4: `register_classes` for fegen submodule — `Identifier.Label.NAME` resolution across submodule unverified

**Section**: Edge Cases "Name collisions in `_native` module" (lines 341-343); "`fegen.fltkg`
Grammar" (line 268).

**What's wrong**: The design asserts the `#[classattr] Label` pattern (returning
`T::type_object(py)`) works identically whether the node class is registered at top level or in a
submodule, but does not verify it. Phase 2 validated `#[classattr]` only for top-level
registration (`cst_poc.rs` + `lib.rs:31-34`, all top-level). `type_object(py)` returns the
interpreter's registered type object (populated at class init), so this is *likely* fine
regardless of which module the class is `add_class`'d into — but the submodule path is new and the
design treats it as proven when it is only inferred.

**Why**: `cst_poc.rs:89-93,275-279` and Phase 2 design "Module Registration" (lines 343-366)
establish `#[classattr]` correctness for top-level classes only. No source exercises a `#[classattr]`
enum type object on a class registered into a child `PyModule`.

**Consequence**: Low-to-medium. If `type_object` resolution interacts with module membership
(it should not, but is unverified), AC-8 (`ClassName.Label.VARIANT` access on fegen classes)
fails. Bounded by the smoke test, so caught early — but the design's "the same submodule pattern
applies" reads as more certain than the evidence supports.

**Suggested fix**: Mark this as an assumption to validate in the AC-8 smoke test, not a settled
fact. The test already covers it; just downgrade the prose from assertion to expectation.

---

## design-5: "Open Questions: None" overstates resolution given design-1

**Section**: "Open Questions" (lines 393-395); requirements OQ-fegen-compilation-test (req line 148).

**What's wrong**: Requirements explicitly leave OQ-fegen-compilation-test open (compile vs
source-only). The design resolves it (compile, via submodule) but the chosen mechanism carries the
unaddressed `sys.modules`/import gap (design-1). Declaring "None" open hides a real, unresolved
integration detail that determines whether the AC-7/AC-8 tests can use `import`.

**Why**: req line 148 poses the question and recommends "compile it … import classes from
`fltk._native` (or a test submodule)" — the parenthetical "test submodule" is exactly the path
that needs `sys.modules` handling, which the design does not address.

**Consequence**: Low (subsumes design-1's consequence). Reader trusts "None" and skips the import
mechanics, then hits design-1 at implementation.

**Suggested fix**: Replace "None" with the single resolved-with-caveat item from design-1.

---

## Verified accurate (no action)

- Preamble (design 84-91) matches `cst_poc.rs:1-6` exactly. (AC-10)
- Reuse pipeline `create_default_context()` → `add_trivia_rule_to_grammar` →
  `classify_trivia_rules` → `CstGenerator(..., py_module=pyreg.Builtins, context=...)` matches
  `plumbing.py:97-101` and `test_gsm2tree.py:12-13`. `pyreg.Builtins` exists (`reg.py:16`).
- `class_name_for_rule_node` reuse and `sorted(model.labels.keys())` (design 114, 128) match
  `gsm2tree.py:47, 113`.
- `child_{label}` early-break + dynamic count, and `maybe_{label}` fixed
  `"...have at least 2"` string (design 234-235) match `cst_poc.rs:179-189, 211-216` and
  `test_rust_cst_poc.py:104, 124`. (AC-11)
- Downcast `.map_err` context strings (design 239-241) match `cst_poc.rs:153-156`.
- `__eq__` uses `is_instance_of` + `PyRef<T>` returning `NotImplemented` (design 224) matches
  `cst_poc.rs:219-230`. `__hash__` raises `PyTypeError` (design 226). `__repr__` format (design 228).
- PoC `items` trivia reasoning (design 257-262): auto-added `_trivia` is unreferenced, so
  `classify_trivia_rules` marks only `_trivia`; `items` is non-trivia and gains `"_trivia"` type.
  No `validate_trivia_separation` violation (`items` references only `identifier`). Verified against
  `gsm.py:273-407, 359-377` and `gsm2tree.py:296-300`.
- Empty-label-enum decision (omit enum + `#[classattr]`, design 244-249) is the sound Rust choice;
  Python emits empty enum (`gsm2tree.py:112-116`). Reasonable divergence, justified.
- Model-no-types RuntimeError inheritance (design 329-331) matches `gsm2tree.py:117-122`.
- `fegen.fltkg` has 14 rules incl. `_trivia` at line 19 (verified `fegen.fltkg`), so
  `add_trivia_rule_to_grammar` is a no-op there (design 268). Correct.
- Scope matches requirements In/Out-of-scope; no bonus features; no premature abstraction.
  Generator reuses existing analysis rather than reimplementing — correct call.
