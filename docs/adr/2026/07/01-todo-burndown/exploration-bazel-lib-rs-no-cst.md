# Exploration: `TODO(bazel-lib-rs-no-cst)`

## TODO.md entry (verbatim)

`TODO.md:29-31`:

> ## `bazel-lib-rs-no-cst`
>
> `fltk_pyo3_cdylib`'s assembly genrule unconditionally declares `cst.rs` and `parser.rs` as required outputs, even when `lib_rs=None` (auto-generated path). Every current caller is a grammar crate and supplies both files. A future runtime-only (span-only) crate built via this macro would hit the `test -f` guards with a misleading error. At that point, split into grammar and span-only assembly variants. Location: `rust.bzl` (`_assemble_crate` genrule, line ~239).

## `TODO(bazel-lib-rs-no-cst)` comment locations

Exactly one occurrence in the live codebase, at `rust.bzl:452-456` (checked with a recursive grep across `/home/rnortman/src/fltk` and `/home/rnortman/tps/clockwork`):

```python
    # TODO(bazel-lib-rs-no-cst): the assembly genrule unconditionally requires cst.rs and
    # parser.rs in rs_srcs, even when lib_rs=None (auto-generated span-only path).  Currently
    # every _build_pyo3_cdylib caller is a grammar crate and always provides both files.  If a
    # runtime-only (span-only) crate is ever built via this macro, the test -f guards will fail
    # misleadingly.  At that point, split into grammar and span-only assembly variants.
    native.genrule(
        name = name + "_assemble_crate",
        srcs = [lib_rs, rs_srcs],
        outs = [crate_lib_rs, crate_cst_rs, crate_parser_rs],
        cmd = """
            OUTDIR=$$(dirname $(location {crate_lib_rs}))
            printf '#![recursion_limit = "{recursion_limit}"]\\n' > $$OUTDIR/lib.rs
            cat $(location {lib_rs}) >> $$OUTDIR/lib.rs
            for f in $(locations {rs_srcs}); do
                cp $$f $$OUTDIR/$$(basename $$f)
            done
            test -f $$OUTDIR/cst.rs || {{ echo "ERROR: cst.rs not produced by rs_srcs (expected basename cst.rs in outputs)"; exit 1; }}
            test -f $$OUTDIR/parser.rs || {{ echo "ERROR: parser.rs not produced by rs_srcs (expected basename parser.rs in outputs)"; exit 1; }}
        """...
```
(`rust.bzl:457-476` is the genrule; the `test -f` guards are at `rust.bzl:468-469`.)

The guards are real and match the TODO's description exactly: a hard `test -f` check on `$OUTDIR/cst.rs` and `$OUTDIR/parser.rs`, each failing the genrule with an `ERROR:` message if the file is missing.

## Effect of the 8fd5ecf unification commit on this TODO

Commit `8fd5ecf` ("bazel: unify generate_rust_parser into a single macro with pure-Rust + Python modes") renamed the public macro `fltk_pyo3_cdylib` (introduced in `c018206`) to the private helper `_build_pyo3_cdylib`. The rename is confirmed by `git show 3b95f0a:rust.bzl` (previous commit, still `def fltk_pyo3_cdylib(`) vs. the current `def _build_pyo3_cdylib(` at `rust.bzl:333`.

The TODO comment's own text was updated as part of that rename — it says `_build_pyo3_cdylib caller` (new name), not `fltk_pyo3_cdylib caller`. This is corroborated by `docs/workflow-bazel-protocol/implementation-log.md:79`: "rust.bzl:427: `TODO(bazel-lib-rs-no-cst)` comment reference updated to the new helper name," and by `docs/adr/2026/07/01-bazel-rust-parser-unification/README.md:225-226`: "The pre-existing `TODO(bazel-lib-rs-no-cst)` (span-only / `no_trivia` `lib.rs`) is unaffected and carried into the internal helper verbatim."

**`TODO.md`'s own copy of the text was not updated** — it still reads `fltk_pyo3_cdylib`'s assembly genrule (line 31), a symbol that no longer exists in `rust.bzl` as of `8fd5ecf` (same-day commit). The in-code comment and the TODO.md prose have diverged on this point.

## Location citation: `line ~239` was never accurate

`TODO.md` says "Location: `rust.bzl` (`_assemble_crate` genrule, line ~239)." Checking every commit that has touched this comment:

- At introduction (`c018206`, `fltk-native-lib-shape` work), the comment was already at `rust.bzl:311` (`git show c018206:rust.bzl`), not 239.
- At `3b95f0a` (previous to the unification), it was at `rust.bzl:382`.
- At current HEAD (`8fd5ecf`), it is at `rust.bzl:452`.

So the `line ~239` citation in `TODO.md` was stale from the moment the TODO was written — it never matched the comment's actual location in any commit checked — and the gap has only widened (239 → 311 → 382 → 452) as the file grew. Other exploration/audit docs in this repo already cite different (also since-superseded) line numbers for the same comment: `docs/adr/2026/06/14-rust-native-lib-shape/audit-native-path-removal.md:85` and `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/exploration.md:234` both say `rust.bzl:311`, matching the pre-unification location, not the current one.

## Is "every current caller is a grammar crate and supplies both files" true?

`_build_pyo3_cdylib` (`python_extension = True` mode of `generate_rust_parser`) has exactly two known call chains:

1. In-tree: `BUILD.bazel:130-136`, `generate_rust_parser(name = "bootstrap_native", src = "fltk/fegen/test_data/rust_parser_fixture.fltkg", python_extension = True, protocol_module = ..., protocol = True)`. This routes through `_generate_rust_srcs` (`rust.bzl:641-648`), whose implementation (`_generate_rust_srcs_impl`, `rust.bzl:122-238`) unconditionally runs both the `gen-rust-cst` action (producing `cst_out`, `rust.bzl:151` / `165-208`, no flag gates it off) and the `gen-rust-parser` action (`rust.bzl:210-224`). There is currently no attribute on `_generate_rust_srcs` or knob on `generate_rust_parser` that skips `cst.rs` generation.
2. Out-of-tree: `/home/rnortman/tps/clockwork/clockwork/dsl/BUILD.bazel:6,70-82` calls `generate_rust_parser(name = "clockwork_rs_srcs", src = "clockwork.fltkg")` then `fltk_pyo3_cdylib(name = "clockwork_native", rs_srcs = ":clockwork_rs_srcs")` — also a grammar crate supplying both files via the same `_generate_rust_srcs` path.

So the factual claim holds for every caller reachable through the public macro today: `_generate_rust_srcs` has no code path that omits `cst.rs`, so `rs_srcs` passed to `_build_pyo3_cdylib` always contains both files when it originates from the macro.

**However**, clockwork's `BUILD.bazel:6` still does `load("@fltk//:rust.bzl", "fltk_pyo3_cdylib", "generate_rust_parser")` and calls `fltk_pyo3_cdylib(...)` at line 77. `fltk_pyo3_cdylib` no longer exists in `rust.bzl` as of `8fd5ecf` (renamed to private `_build_pyo3_cdylib`). This means clockwork's Bazel build, as checked out right now, would fail to load `rust.bzl` at all (undefined symbol), not merely fail the `_assemble_crate` guard. This is a known, accepted, and documented consequence of the unification, not an oversight: `docs/adr/2026/07/01-bazel-rust-parser-unification/README.md:207-208` states "Downstream Bazel call sites must migrate (breaking change). This is accepted and out of scope here." It is unrelated to the `bazel-lib-rs-no-cst` TODO's substance but bears on "every current caller" as a literal, present-tense claim: one of the two nominal callers is presently non-functional pending a downstream migration that has not yet happened in the clockwork checkout inspected.

## Plausibility of the hypothesized "future runtime-only (span-only) crate"

This is not a purely speculative hypothetical — an analogous artifact already exists in-tree, built by a different (hand-rolled) path:

- FLTK's own `:native` target (`BUILD.bazel:34-50`) is a `rust_shared_library` with `srcs = glob(["src/**/*.rs"])` (`src/lib.rs`, `src/span.rs` — checked via `ls src/`), built directly via `rust_shared_library`, **not** via `generate_rust_parser` / `_build_pyo3_cdylib`.
- `src/lib.rs` documents itself as generated by the exact runtime-only CLI invocation the TODO envisions: `fltk/fegen/genparser.py:817` — `genparser gen-rust-lib src/lib.rs --module-name _native --no-cst --register-span-types --unknown-span-static`.
- The `generate_rust_lib` Bazel rule (`rust.bzl:78-118`, used internally by `_build_pyo3_cdylib` when `lib_rs = None`) already exposes a `no_cst` attribute (`rust.bzl:85-88`) that forwards `--no-cst` to `gen-rust-lib`, i.e., generating a span-only `lib.rs` is already plumbed at the `generate_rust_lib` rule level.
- What is *not* plumbed: `_build_pyo3_cdylib`'s call to `generate_rust_lib` (`rust.bzl:430-433`) never sets `no_cst`, and there is no attribute on `_generate_rust_srcs` / `generate_rust_parser` to produce `rs_srcs` without `cst.rs`. So today, going through the public macro, a span-only crate cannot be built at all (not merely blocked by the `test -f` guard) — the guard would only be reachable by a caller who feeds `_build_pyo3_cdylib` a hand-written `rs_srcs` target directly, bypassing `_generate_rust_srcs` entirely (an internal helper not intended to be called directly, per its docstring at `rust.bzl:317-318`).

## Prior review disposition (from an earlier review cycle, same subsystem)

`docs/adr/2026/06/14-rust-native-lib-shape/judge-verdict-deep.md:23-26` (quality-1 finding, same underlying issue, filed when the TODO was introduced in `c018206`) recorded: "there is no in-tree runtime-only Bazel consumer yet (`bootstrap_native` supplies grammar srcs, so it does not trip the guard)," and judged the choice among three proposed fixes (parse `lib.rs` for `mod cst;`; add a Starlark `fail()` guard; split the genrule into two variants) to be "a Bazel-macro-design decision" appropriately deferred until a concrete caller exists. That assessment's premise (no in-tree caller trips the guard) still holds after `8fd5ecf`: `bootstrap_native` (`BUILD.bazel:130`) is still a grammar-fixture target that supplies both `cst.rs` and `parser.rs`.
