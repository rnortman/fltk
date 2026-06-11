# Dispositions: design review round 1 — parse depth limit

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Design: `design.md` (this dir). Notes: `notes-design-design-reviewer.md`.

design-1:
- Disposition: Fixed
- Action: Verified against `tests/test_rust_parser_bindings.py:13-16` (`importorskip("fegen_rust_cst")`; every test constructs `fegen_rust_cst.Parser`) — the file cannot host tests needing `nest`/`nest_sum`. Design updated: Test plan bindings section now targets a **new file** `tests/test_rust_parser_fixture_bindings.py` with its own `importorskip("rust_parser_fixture")` guard, with an explicit rationale for why the existing bindings file is wrong (module mismatch; error-vs-skip when only one extension is built). §8 table row replaced accordingly. T7 unaffected (it asserts existing suites pass unchanged, no new file).
- Severity assessment: As written, the test plan forced mid-implementation rework — T5/T6 against `fegen_rust_cst` would `AttributeError` (no `apply__parse_nest`), or an added import would break skip behavior. Caught at design time, zero residual cost.

design-2:
- Disposition: Fixed
- Action: Verified the scenario — `fltk-parser-core` is a separate crate (`0.1.0`, `crates/fltk-parser-core/Cargo.toml`; in-tree consumers use path deps) and the design's §1 compile-compat argument is precisely about the not-regenerated case, whose behavioral semantics were unaddressed. Design updated: new subsection "Versioning: old-generated parser + new core is a deliberate behavior break" (end of §2) — declares the change semver-breaking, bumps `fltk-parser-core` `0.1.0` → `0.2.0` (0.x breaking signal, so `cargo update` cannot silently mix versions), requires the lockstep-regeneration rule in the §7 `memo.rs` doc rewrite, and notes in-tree fixtures regenerate in this change. §1 bullet now cross-references it; Edge cases gains a mixed-versions bullet; §8 table gains the `Cargo.toml` version-bump row.
- Severity assessment: Without this, an out-of-tree consumer upgrading the core without regenerating could silently receive truncated wrong parses (the §2 truncated-`Some` shapes) on deep inputs that previously parsed correctly, with no API to detect or configure the limit — exactly the incidental-breakage CLAUDE.md forbids. Highest-consequence finding of the round; resolved as a deliberate, documented versioning decision with no code-shape change.
