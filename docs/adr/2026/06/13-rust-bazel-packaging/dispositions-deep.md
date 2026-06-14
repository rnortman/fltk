# Dispositions — Deep Review Round 1
# rust-bazel-packaging

---

## correctness-1
- Disposition: Fixed
- Action: `clockwork/dsl/clockwork_rust_roundtrip_test.py:56` — changed `result.value` to `result.result`. `PyApplyResult` exposes `.result` and `.pos` getters only; `.value` raises `AttributeError`.
- Severity assessment: The test's primary AC #4 assertion (read CST node/span data) never executes because `AttributeError` is raised at the `.value` access; the span assertions are dead code as shipped.

## correctness-2
- Disposition: Fixed
- Action: `rust.bzl:227` — changed `crate_features = ["extension-module"] + crate_features` to `["extension-module", "python"] + crate_features`. Added explanatory comment. Bazel `crate_features` do not forward (unlike Cargo's `extension-module = ["python", "pyo3/extension-module"]` feature definition), so `"python"` must be set explicitly; without it, the generated `register_classes` symbols (gated on `#[cfg(feature = "python")]`) are compiled out and the cdylib fails to link.
- Severity assessment: The cdylib target does not build as shipped; AC #2 ("cdylib compiles with extension-module") is not satisfied. This is a build-blocking defect.

## correctness-3
- Disposition: TODO(verify-pyo3-ext-module)
- Action: Added `TODO(verify-pyo3-ext-module)` comment at `MODULE.bazel` in the `crate.from_cargo` block documenting that pyo3's `extension-module` feature activation via `from_cargo` must be confirmed empirically at spike time, with a `crate.annotation` fallback if it is unset.
- Severity assessment: If `extension-module` is not activated on `@fltk_crates//:pyo3`, both `:native` and every `fltk_pyo3_cdylib` consumer link libpython and fail at link or import time — the exact silent failure mode the design warns about in §4.

## correctness-4
- Disposition: Fixed
- Action: `clockwork/dsl/clockwork_rust_roundtrip_test.py:45` — removed trailing `\n` from test source string (`"cpu_domain main;"` not `"cpu_domain main;\n"`). Added comment explaining the change.
- Severity assessment: Minor; the assertion `result.pos == len(src)` would fail loudly if trailing-trivia handling does not consume the newline, so this is a fail-loud risk rather than a silent wrong answer.

## errhandling-1
- Disposition: Won't-Do
- Action: No change. The correctness reviewer independently verified: "`$<` is the sole `.so`" for `rust_shared_library` outputs (correctness reviewer "Checked and OK" section). The risk is future `rules_rust` versions adding sidecar files.
- Rationale: The correctness reviewer's independent analysis confirms the current implementation is correct. The future-risk concern is speculative and adding defensive shell scripting to a genrule that currently works correctly would add complexity without present benefit. A follow-up TODO would also be premature — if `rules_rust` ever changes this, the failure is a loud `ImportError: dynamic module does not define init function`, not a silent wrong answer, and is easily diagnosed.

## errhandling-2
- Disposition: Won't-Do
- Action: No change.
- Rationale: The correctness reviewer verified the crate-source assembly genrule as sound ("Module resolution logic is sound"). The risk is future additions to `generate_rust_parser` outputs. The rule's `DefaultInfo` currently emits exactly two files (`cst.rs` and `parser.rs`); adding a future third output would be a deliberate design change to `generate_rust_parser`, at which point the macro's assembly loop would be an obviously necessary update site. This is a future-maintenance note, not a current defect. The assembly genrule has explicit declared `outs` (`cst.rs`, `parser.rs`, `lib.rs`), so any unexpected extra copy causing a name collision would fail at compile time (loud, not silent).

## errhandling-3
- Disposition: Fixed (subsumed by quality-1/errhandling-5 fix)
- Action: The `Label("@fltk//:native_py")` fix in `rust.bzl:256` (applied for quality-1/errhandling-5) also resolves the self-reference risk for in-FLTK use: `Label()` is evaluated at `.bzl` load time in FLTK's module context, so the label is unambiguously bound to FLTK's `native_py` target regardless of where the macro is called from.
- Severity assessment: Potential for confusing circular-dep or no-op behavior when `fltk_pyo3_cdylib` is called from within FLTK's own BUILD files (e.g., for the `TODO(fltk-pyo3-cdylib-smoke)` test). The `Label()` fix removes the ambiguity.

## errhandling-4
- Disposition: Fixed
- Action: `clockwork/dsl/clockwork_rust_roundtrip_test.py:15-32` — rewrote `test_fltk_native_span_is_rust_path` to remove the `warnings.catch_warnings` block (which never captured span.py warnings because importing `fltk._native` directly does not import span.py). Now imports `fltk._native` directly (loud `ImportError` if `.so` absent) and asserts `fltk._native.Span.__module__ == "fltk._native"` to distinguish the Rust type from the pure-Python fallback.
- Severity assessment: The `catch_warnings` check was vacuous — `span_fallback_warnings` was always empty regardless of whether the Rust path was live. The AC #3 guard ("assert native span path is live") was effectively absent. The new check correctly distinguishes the Rust path from the pure-Python fallback via the type's `__module__` attribute.

## errhandling-5
- Disposition: Fixed (same fix as quality-1)
- Action: `rust.bzl:229-231, 256` — wrapped cross-repo dep labels in `Label()`. See quality-1.
- Severity assessment: Without `Label()`, every out-of-tree consumer (`fltk_pyo3_cdylib` called from Clockwork or any future downstream) gets "no such target" or "no such repository" build errors — the macro is broken for its primary use case.

## test-1
- Disposition: Fixed
- Action: `clockwork/dsl/BUILD.bazel` — added `load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")`, added `py_pytest_main(name = "__rust_test__", deps = ["@clockwork_pip//pytest"])`, and updated `py_test` to include `":__rust_test__"` in `srcs`, `":__rust_test__.py"` as `main`, and `":__rust_test__"` in `deps`. Matches the pattern used by `clockwork/dsl/tests/BUILD.bazel`.
- Severity assessment: The `py_test` target fails at Bazel analysis time (before any test code runs) because Clockwork's `py_test` wrapper calls `fail()` when pytest boilerplate is absent. AC #4 is never exercised.

## test-2
- Disposition: Fixed (same fix as errhandling-4)
- Action: See errhandling-4.
- Severity assessment: The `catch_warnings` mechanism is vacuous for the import path used in this test. The check that is supposed to guard AC #3 could be silently bypassed by a refactor that wraps the bare import in `try/except`. Fixed by asserting on `Span.__module__` instead.

## test-3
- Disposition: TODO(fltk-pyo3-cdylib-smoke)
- Action: Added `TODO(fltk-pyo3-cdylib-smoke)` comment at `fltk/BUILD.bazel` after the `bootstrap_rust_srcs` target, documenting that a `fltk_pyo3_cdylib` invocation against a fixture grammar + minimal lib.rs is needed so FLTK CI covers the full macro path independent of Clockwork.
- Severity assessment: The `fltk_pyo3_cdylib` macro's crate-source assembly, cdylib compilation, abi3 rename, and py_library wrapper steps have no FLTK-side test coverage; bugs in those steps are only caught transitively by Clockwork's build. This is a CI coverage gap for new public Bazel surface, not a runtime correctness issue.

## quality-1
- Disposition: Fixed
- Action: `rust.bzl:229-231, 256` — replaced bare string labels with `Label("//crates/fltk-cst-core")`, `Label("//crates/fltk-parser-core")`, `Label("@fltk_crates//:pyo3")`, and `Label("@fltk//:native_py")`. Added an explanatory comment. `Label()` is evaluated at `.bzl` load time in the defining module's context, pinning these labels to FLTK's repository regardless of the macro call site.
- Severity assessment: Without this fix, `fltk_pyo3_cdylib` produces "no such target" or "no such repository" errors when called from any out-of-tree consumer (Clockwork or any future downstream). The macro's primary use case is broken.

## quality-2
- Disposition: Fixed
- Action: `rust.bzl:150` — changed `@fltk//:native_so` to `@fltk//:native_py` in the Step 4 docstring line.
- Severity assessment: The docstring names the wrong target, making the invariant chain (fltk._native importable because native_py carries native_so as data and sets imports) harder to audit. Cosmetic but misleading to maintainers.

## quality-3
- Disposition: Fixed
- Action: `MODULE.bazel` crate extension comment — updated to accurately state that `fltk-cst-spike` IS included as a workspace member in the `fltk_crates` hub (since root `Cargo.toml [workspace]` includes `crates/fltk-cst-spike`), and that `tests/*` fixture crates are correctly excluded (they have their own `[workspace]` declarations). Added `TODO(bazel-cst-spike-hub)` for future consideration if spike acquires large deps.
- Severity assessment: The inaccurate comment could cause maintainers to incorrectly assume spike and its transitive deps are absent from the hub, leading to confusion when hub resolution or dep graph queries reveal spike membership.

## efficiency-1
- Disposition: Won't-Do
- Action: No change. Design §3.4 explicitly considered and rejected the `#[path=...]` alternative; the extra copy action is the accepted cost of same-directory `mod` resolution.
- Rationale: The design correctly documents this trade-off. The extra action is one genrule copy per cdylib, negligible at Clockwork's current scale. Eliminating it would require changing `generate_rust_parser`'s interface (accepting `lib_rs` as an input) — a design change beyond this review's scope.

## efficiency-2
- Disposition: Won't-Do
- Action: No change. `cp` used instead of symlink.
- Rationale: Symlinks in Bazel sandboxes require platform-specific handling; `cp` is the safe, portable default. The disk-footprint cost is acknowledged and acceptable for a single cdylib + one `fltk._native` target. If remote-cache bandwidth becomes a concern, a `copy_file` from bazel-skylib (which uses an optimized path) can replace the genrule `cmd = "cp $< $@"` in a future cleanup.

## efficiency-3
- Disposition: TODO(verify-pyo3-ext-module)
- Action: Subsumed by correctness-3's `TODO(verify-pyo3-ext-module)` at the `crate.from_cargo` block — spike validation will also reveal whether dev-dep crates leak into the hub.
- Severity assessment: If dev/test-only crates from the root workspace leak into `@fltk_crates`, every clean Clockwork build compiles unneeded crates. Confirmed only at spike time; not a correctness issue, only a build-efficiency concern.
