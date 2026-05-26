# Design Review: Phase 0 Rust/PyO3 Infrastructure

Reviewer notes. Concise. Precise. No padding. Audience: smart human/LLM.

Verified against source at base commit f1e2a98. Round-trip test logic in design Part B was
executed and passes; pyproject/MODULE.bazel/.gitignore/plumbing.py claims checked against files.

---

## design-1: `#[pymodule]` function name does not match `module-name` last component — `import fltk._native` will fail

**Section:** Part A, `src/lib.rs` (design.md:69-73) + `pyproject.toml changes` (design.md:88-95).

**Quote:**
```rust
#[pymodule]
fn fltk_native(m: &Bound<'_, PyModule>) -> PyResult<()> { ... }
```
combined with `module-name = "fltk._native"` and `[lib] name = "fltk_native"`.

**What's wrong:** With maturin's mixed layout and `module-name = "fltk._native"`, the importable
module is `_native`. PyO3 derives the extension init symbol (`PyInit_<fn>`) from the `#[pymodule]`
function name. `fn fltk_native` produces `PyInit_fltk_native`, but Python importing `fltk._native`
looks for `PyInit__native`. The function must be `fn _native(...)` (or use
`#[pyo3(name = "_native")]`). The maturin docs show exactly this: for
`module-name = "my_project._my_project"` the function is `fn _my_project(...)`. The `[lib] name`
(cdylib filename) is independent and may stay `fltk_native`.

**Why:** maturin project-layout guide (verified): dotted `module-name` requires the pymodule
function name to equal the final path component. Design's exploration.md:232 also says lib.rs should
export `fltk._native`, but the code in design.md names the function `fltk_native`.

**Consequence:** The Phase 0 "Done when" acceptance criterion (`from fltk._native import Ping;
assert Ping().pong() == "pong"`, phase-plan.md:36) fails — `import fltk._native` raises
`ImportError: dynamic module does not define module export function (PyInit__native)`. The single
deliverable of Part A/C is not met. Hard failure, discovered only at runtime after a full Rust build.

**Fix:** Rename the function to `fn _native(...)`, or add `#[pyo3(name = "_native")]`.

---

## design-2: Maturin build-backend switch likely breaks the entire CI run, not just the native test

**Section:** Test Plan (design.md:249), Edge Cases "Maturin + uv interaction" (design.md:214-217),
Open Questions (design.md:257).

**What's wrong:** The design treats the only CI/build risk as "`test_native.py` would skip" and
frames the Rust toolchain in CI as an optional enhancement. But switching `build-backend` from
`setuptools.build_meta` to `maturin` changes how the *root project itself* is installed. `fltk` is an
editable install (`uv.lock`: `source = { editable = "." }`, verified). `make check` runs `uv run ...`
(Makefile verified) which syncs/builds the editable project via the configured backend. With maturin
as backend, that build invokes maturin + cargo + rustc. CI (`.github/workflows/ci.yml`, verified)
installs only uv + Python 3.10 — no Rust, no maturin. The editable rebuild that `uv run` performs
would attempt to compile the extension and fail, breaking `lint`, `typecheck`, and `test` — i.e. all
of CI, not just the smoke test.

**Why:** ci.yml:11-21 (checkout → setup-uv → `make check`); Makefile (`check: lint typecheck test`,
all `uv run`); uv.lock editable source; pyproject build-system change is the whole of Part A.

**Consequence:** "All existing tests pass unchanged … validated by running the full test suite as the
final CI step" (design.md:249) is false post-migration. CI goes red on the Phase 0 commit even though
the grammar/native tests are individually fine. This is the blocking risk R3 from the plan
(phase-plan.md:229-233) and the design does not mitigate it — it requires either adding Rust+maturin
install steps to ci.yml, or configuring uv to not rebuild the backend in CI. Not addressed.

**Fix:** Add to Part A scope: update `.github/workflows/ci.yml` to install Rust toolchain + run
`uv run --group dev maturin develop` (or `maturin build`) before `make check`; regenerate `uv.lock`
after the build-system change. Decide and document, rather than deferring in an Open Question.

---

## design-3: pyright (`typecheck`) will fail on `from fltk._native import ...` — no stub, module absent at lint time

**Section:** Part C (design.md:178-192); File Summary lists no `.pyi`.

**What's wrong:** `make check` runs `pyright` over `include = ["fltk", "*.py"]`
(pyproject.toml:47, verified). `test_native.py` uses `pytest.importorskip("fltk._native")` at module
scope, so the symbol is dynamic and pyright will not see a `fltk._native` module (it is a compiled
artifact with no source and no stub). The broader plan (phase-plan.md:291 Open Question 1) explicitly
flags that Rust classes have no source for type checkers. For Phase 0 the smoke test only does
`native.Ping().pong()` on a `pytest.importorskip` result (typed `Any`), so this specific file is
probably tolerated — but the design never checks pyright behavior and never states it was considered.

**Why:** pyproject.toml:45-50 pyright config; Makefile `typecheck` target; design.md File Summary
(design.md:198-208) has no stub entry and no pyright note.

**Consequence:** If pyright flags the missing module / dynamic import, `make check` fails in CI and
locally even when tests pass. Lower-likelihood than design-2 (the importorskip result is `Any`), but
unverified by the design. Worth a one-line confirmation in the implementation step.

**Fix:** Confirm `uv run pyright` passes with the new `test_native.py` before claiming "all checks
pass"; if it complains, add a targeted ignore or a minimal stub.

---

## design-4: Grammar baseline test verifies only class names + label-member names — does not detect the regression it is meant to guard

**Section:** Part B "Test strategy" (design.md:136-172).

**What's wrong:** The test compares the *set of class names* and the *set of `Label` enum member
names* per class. It does not compare child types, the `children` union type annotations, generated
method sets, or separators. The stated regression risk (design.md:229-232, "committed `fltk_cst.py`
was hand-edited post-generation" / "generation pipeline has drifted") would mostly manifest as
changed child types or methods, not as added/removed classes or relabeled enums. I executed the exact
proposed comparison: it passes today (14 classes, all label sets equal). That confirms it is
non-brittle, but it is also weak: a drift in, say, `Item`'s child union or a renamed method would not
trip it.

**Why:** Ran design.md:155-169 logic against `plumbing.parse_grammar(fegen.fltkg)` +
`plumbing.generate_parser` vs committed `fltk_cst` — `committed == generated` True, zero label
mismatches. So the test is grounded and passes, but its assertion surface is narrow.

**Consequence:** The test gives false confidence as the "baseline for Phase 3/4 API equivalence"
(phase-plan.md:23). A future regression in child types/methods passes this test, so Phase 3's
"API-equivalent output" claim rests on a baseline that never checked the API. Design itself hedges
("stricter byte-comparison test can be added later", design.md:172) — but byte comparison is the
opposite extreme (brittle to formatting). A middle option (compare each class's `children` field
annotation and method-name set) would actually catch drift.

**Fix:** Either accept the narrow check explicitly as "inventory-only smoke" and downscope the
phase-plan claim, or extend the comparison to per-class method-name sets and the `children` field
type annotation. Recommend the latter — cheap, and it is the actual regression surface.

---

## design-5: `python-source = "."` vs exploration's `python-packages = ["fltk"]` — pick one; flat-root with `python-source="."` has a footgun

**Section:** Part A pyproject (design.md:89-95) vs exploration.md:234 / 44.

**What's wrong:** Design uses `[tool.maturin] python-source = "."`. Exploration specifies
`python-packages = ["fltk"]`. These are different mechanisms; the design silently switched without
noting it. With `python-source = "."` maturin treats the *repo root* as the Python source dir and
auto-discovers top-level packages — which here includes `fltk`, but root-level loose `*.py` and any
other top-level dirs (`docs/`, `src/`) are in scope for discovery/packaging too. `python-source = "."`
is workable but is the less-targeted choice for a repo that keeps Rust `src/` and `docs/` at root.

**Why:** design.md:90 vs exploration.md:44,234. Repo root has `src/` (to be created), `docs/`,
loose files — confirmed by layout in exploration.md:31-42.

**Consequence:** Not a hard failure, but unverified packaging behavior: built wheels may pick up
unintended top-level content, or maturin may error on ambiguous discovery. The design asserts the
`python-source="."` semantics as fact ("tells maturin that the Python package `fltk/` lives at the
repo root") without reconciling against the exploration's explicit-package approach.

**Fix:** Use `python-source = "."` *with* an explicit package selection, or use the exploration's
explicit form, and verify a `maturin build` produces a wheel containing only `fltk/` + the `.so`.
Resolve the design/exploration divergence before implementing.

---

## design-6 (minor): `extension-module` feature declared twice

**Section:** Cargo.toml `features = ["extension-module"]` (design.md:46) and `[tool.maturin]
features = ["pyo3/extension-module"]` (design.md:92).

**What's wrong:** The pyo3 `extension-module` feature is enabled both as a default Cargo dependency
feature and via maturin's `features`. maturin's own guidance is to enable it in exactly one place
(commonly leaving it off Cargo defaults and letting maturin add it, so `cargo test` still links
libpython). Declaring it in Cargo defaults can break `cargo test`/`cargo build` outside maturin
because the extension-module feature omits libpython linkage.

**Consequence:** Low. Builds via maturin work. But any later `cargo test` (Phase 2+ hand-written Rust
tests) may fail to link. Harmless now, a latent papercut for later phases.

**Fix:** Enable `extension-module` in only one location — prefer the maturin `features` entry and drop
it from Cargo.toml's default features, per maturin convention.

---

## Coverage / consistency notes (no separate finding)

- Requirements mapping (phase-plan.md:25-36): Cargo.toml ✓, src/lib.rs ✓ (but see design-1),
  setuptools→maturin ✓ (but see design-2), Bazel TODO ✓ (MODULE.bazel rules_python-only confirmed),
  grammar round-trip test ✓ (passes, but see design-4), `Ping().pong()` smoke ✓ (gated by design-1).
- Scope discipline: appropriate. No bonus features. `.gitignore`, egg-info cleanup, CLAUDE.md doc are
  justified by the migration.
- TODO system: design adds a `bazel-rules-rust` TODO.md entry + `TODO(bazel-rules-rust)` comment —
  matches CLAUDE.md TODO convention (slug join). Current TODO.md has only the placeholder (verified).
- Grounded claims that checked out: pyproject lines (build-system 1-3, tool.setuptools 27-28),
  MODULE.bazel rules_python-only, `plumbing.parse_grammar`/`generate_parser` signatures and
  `ParserResult.cst_module`, 14 committed CST classes all with `Label`, `pytest.importorskip(reason=)`
  accepted (pytest 8.4.1), `genparser generate` command exists, fegen.fltkg matches exploration.
- Rust toolchain IS already installed on this machine (rustc/cargo 1.94 in ~/.cargo/bin) — design's
  "fresh machine without Rust" edge case (design.md:219-222) is a fine mitigation but not the local
  reality; the real gap is CI (design-2), which lacks Rust.
