# Design Review Dispositions — Phase 0 Rust/PyO3 Infrastructure

Round 1. All findings from `notes-design-design-reviewer.md`.

---

design-1:
- Disposition: Fixed
- Action: Renamed `fn fltk_native` to `fn _native` in src/lib.rs code block. Added explanatory note about PyInit symbol naming requirement. (Part A, "src/lib.rs" section)
- Severity assessment: Hard failure — the sole Phase 0 acceptance criterion (`from fltk._native import Ping`) would produce ImportError at runtime.

design-2:
- Disposition: Fixed
- Action: Added "CI changes" subsection to Part A specifying `dtolnay/rust-toolchain@stable` + `maturin develop` steps. Added `.github/workflows/ci.yml` to File Summary. Removed the Open Question (now resolved — Rust is mandatory). Updated "Edge Cases" to correctly state Rust is required for all `uv run`, not just extension tests.
- Severity assessment: Total CI breakage — lint, typecheck, and test all fail because `uv run` cannot sync the project without Rust/maturin.

design-3:
- Disposition: Fixed
- Action: Added "Pyright compatibility" paragraph to Part C explaining that `importorskip` returns `Any` (so no pyright error expected) and prescribing fallback if pyright does complain.
- Severity assessment: Likely non-issue (`Any` return suppresses type errors), but unverified claim. Fix is to acknowledge and provide contingency.

design-4:
- Disposition: Fixed
- Action: Extended the test code in Part B to compare public method names per class (third assertion surface). Updated prose to describe all three comparison surfaces and the regressions they catch.
- Severity assessment: The test would pass but miss the primary regression scenario (child-type/method drift). Weakens Phase 3/4 baseline guarantee.

design-5:
- Disposition: Fixed
- Action: Replaced `python-source = "."` with `python-packages = ["fltk"]` in the `[tool.maturin]` config and updated the explanatory text. Matches exploration recommendation.
- Severity assessment: Potential unintended content in built wheels (docs, src dir). Not a hard failure but a packaging correctness issue.

design-6:
- Disposition: Fixed
- Action: Removed `features = ["extension-module"]` from Cargo.toml `[dependencies]` section. Added explanatory sentence about why it lives only in `[tool.maturin]`. Single declaration via maturin features entry.
- Severity assessment: Latent papercut — `cargo test` in later phases would fail to link libpython. No impact on Phase 0 maturin builds.
