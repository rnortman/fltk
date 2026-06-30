# Dispositions: design review (round 1)

Design: `design.md` (this directory). Reviewer notes: `notes-design-design-reviewer.md`.

All four findings were fact-checked against source at the working tree. All four are valid and all four
are **Fixed** in `design.md`.

---

design-1:
- Disposition: Fixed
- Action: Confirmed against source — the CLI requires `--pyi-output`-style coupling
  (`genparser.py:382-384` rejects `--pyi-output` without `--protocol-module`; the design's new
  `--protocol-output` mirrors this), so the design genuinely diverges from requirement Change-2
  condition 1 ("enabling protocol output ... is sufficient ... does not separately pass a
  `--protocol-module` flag"), and §2.2's "single opt-in (§2.4)" cross-ref was both wrong (§2.4 is the
  Python rule) and contradicted by §2.5's two-knob table. Three edits to `design.md`:
  (1) §2.2 Condition 1 bullet rewritten to state the Bazel layer needs **two coupled knobs**
  (`protocol_module` + `generate_protocol`), not a single opt-in;
  (2) added a "Deliberate deviation from requirement Change-2 condition 1" paragraph in §2.2 with the
  structural rationale (the `.pyi` `import {protocol_module} as _proto` line needs the dotted import
  path, which is not derivable from the output file path — independent strings, cf. the Makefile
  pairing), and fixed the residual "single opt-in" wording in §2.2's first bullet;
  (3) added Open Question 2 surfacing the (a) two-flag-coupling vs (b) single-flag-carries-import-path
  decision for the user to confirm (design written assuming (a)).
- Severity assessment: High. As drafted the design silently contradicted an explicit requirement and
  itself; an implementer would have shipped a CLI/Bazel surface that hard-errors on the exact workflow
  the requirement says should "just work," with no record that this was deliberate.

design-2:
- Disposition: Fixed
- Action: Confirmed the §1.2 claim was factually wrong. `tests/test_gsm2tree_py.py:14` imports
  `make_generator`, and `:239-240` calls it then `gen_protocol_module()`; `tests/gsm2tree_helpers.py:69`
  constructs `CstGenerator(..., py_module=pyreg.Builtins, ...)` and `reg.py:16` defines
  `Builtins = Module(import_path=())` (falsy) — so that caller *does* emit the degraded `kind: object`
  form. (`test_cst_protocol.py:62-73` does use a non-empty path, so that half was correct.) Verified via
  grep that `tests/test_gsm2tree_py.py` contains no `kind` reference, so the safety conclusion survives.
  Rewrote the §1.2 paragraph to state the two callers differ, name the empty-path caller explicitly, and
  add an **Implementer hazard** note that `generate_protocol()` and its tests must not be built on
  `make_generator` / `pyreg.Builtins`.
- Severity assessment: Medium. The conclusion (byte-identity is safe) was correct, but the stated basis
  was wrong in the central risk section, and it undercounted the reachable empty-path helper that an
  implementer could accidentally build on, which would reintroduce the degraded form.

design-3:
- Disposition: Fixed
- Action: Confirmed the test-plan self-contradiction. `test_generate_protocol_only_matches_full_run`
  lives at `test_genparser.py:287-319` (inside the claimed-unchanged range 258-341); `:300` is a bare
  `generate` (no `--protocol`) and `:317` reads `full_dir / "simple_cst_protocol.py"`, which under the
  new default raises `FileNotFoundError`. Rewrote the §5 bullets: the byte-identity bullet now states it
  **modifies** `:287-319` (full-run arm at `:300` must gain `--protocol`), and the "unchanged" bullet is
  scoped to the two genuinely-unchanged tests (`:258-284` and `:322-341`), explicitly excluding
  `:287-319`.
- Severity assessment: Medium. An implementer following the unscoped "258-341 still pass unchanged"
  bullet would have left a now-failing test in place or missed adding `--protocol` to its full-run arm.

design-4:
- Disposition: Fixed
- Action: Confirmed §2.6's "the `.pyi` ... must not enter the crate assembly genrule" was false given
  §2.5. `rust.bzl:318` is `srcs = [lib_rs, rs_srcs]` and `:324-326` copies every `$(locations rs_srcs)`
  by basename; once §2.5 adds `cst.pyi` to `generate_rust_parser`'s `DefaultInfo` (`:149`), `cst.pyi`
  *does* flow into the genrule. Verified it is benign: genrule `outs` are only lib/cst/parser `.rs`
  (`:319`), so the stray copy is discarded; rustc never reads `.pyi`; the `test -f` guards (`:327-328`)
  still pass. Rewrote §2.6 to describe the actual data flow, drop the false "must not enter" claim, note
  the benign-discard, and direct the implementer to confirm the `fltk_pyo3_cdylib` round-trip builds
  with `cst.pyi` in `rs_srcs` (with filtering as the fallback if a future maintainer needs `rs_srcs` to
  yield only `.rs`).
- Severity assessment: Low. Benign at build time, but the design asserted a guarantee it did not provide;
  left unaddressed, a maintainer relying on "`rs_srcs` yields only `.rs`" would be silently wrong.

---

Cleanup-editor was re-invoked after the edits (substantial: corrected the central-risk claim, added a
deviation paragraph + open question, rewrote §2.6, fixed the test plan). It also removed two stray
`</content>` / `</invoke>` draft artifacts at the end of the file and reconciled the residual "single
opt-in" wording in §2.2.
