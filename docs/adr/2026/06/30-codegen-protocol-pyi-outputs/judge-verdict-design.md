# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 4 findings, all dispositioned Fixed.

## Other findings walk

### design-1 — Fixed
Claim: design contradicts `requirements.md` Change-2 condition 1 ("enabling protocol output on the Rust
generator is sufficient to also get the `.pyi`; the caller does not separately pass `--protocol-module`"),
and §2.2 is internally inconsistent with §2.5 (cross-refs §2.4, the *Python* rule; claims "single opt-in"
while §2.5's table needs two coupled knobs). Consequence: design silently diverges from an explicit
requirement and itself; user-intent question that should be surfaced and confirmed.
Source check: `requirements.md:15` quoted verbatim confirms the requirement text. The divergence is real
(the CLI's `--protocol-output requires --protocol-module` mirrors the existing `--pyi-output` coupling at
`genparser.py:382-384`).
Design inspection: §2.2 Condition 1 (lines 162-164) now states the Bazel layer needs **two coupled knobs**
(`protocol_module` + `generate_protocol`), "not a single opt-in." A "Deliberate deviation from requirement
Change-2 condition 1" paragraph (lines 171-182) explicitly states the design does **not** honor condition 1
literally and gives the structural rationale (the `.pyi`'s `import {protocol_module} as _proto` line needs
the dotted import path, not derivable from the output file path — independent strings, cf. the Makefile
pairing). §2.2 first bullet (lines 152-154) disclaims "This is not a *lone* opt-in." Open Question 2
(lines 415-423) surfaces (a) two-flag coupling vs (b) single-flag-carries-import-path for user confirmation,
recommending (a).
Assessment: the deviation is now acknowledged, justified, and surfaced as an open question — the
design-phase mechanism for a user-intent decision. Reviewer recommended (a); design recommends (a); both
agree, the rationale is sound (file path ≠ import path), so no fundamental disagreement and no escalation.
Internal inconsistency removed. Accept.

### design-2 — Fixed
Claim: §1.2's statement that both `gen_protocol_module()` unit callers construct with a non-empty module
path is false — `tests/test_gsm2tree_py.py:239-240` goes through `make_generator`
(`tests/gsm2tree_helpers.py:69`, `py_module=pyreg.Builtins`, `reg.py:16` `import_path=()` falsy), which
emits the degraded `kind: object` form. Consequence: a load-bearing claim in the central risk section is
wrong (conclusion survives — no `kind` assertion exists — but the basis is mis-stated), and the empty-path
helper is a reachable implementer trap.
Design inspection: §1.2 (lines 76-86) now states the two callers do **not** both use a non-empty path and
names the empty-path caller explicitly (`test_gsm2tree_py.py:239-240` via `make_generator` →
`pyreg.Builtins`, degraded form), keeps the corrected safety conclusion (neither test asserts `kind`), and
adds an **Implementer hazard** note that `generate_protocol()` and its test infra must not be built on
`make_generator` / `pyreg.Builtins`.
Assessment: factual correction made, the empty-path caller is now counted, and the trap is called out. The
§5 guardrail test (asserts `kind: typing.Literal[NodeKind.*]`, not `kind: object`) backs it. Accept.

### design-3 — Fixed
Claim: §4/§5 test plan contradicts itself — one bullet "extends" `test_generate_protocol_only_matches_full_run`
(`test_genparser.py:287-319`) while another says "258-341 still pass unchanged"; the test's full-run arm
(`:300`, bare `generate`) reads `simple_cst_protocol.py` (`:317`), which under the new default raises
`FileNotFoundError`. Consequence: ambiguity could leave a now-broken test in place.
Design inspection: §5 (lines 362-370) now states the byte-identity bullet **modifies** `:287-319` (its
full-run arm at `:300` must gain `--protocol`), and the "unchanged" bullet is scoped to the two genuinely
unchanged tests (`:258-284`, `:322-341`), explicitly excluding `:287-319`.
Assessment: contradiction resolved; the modified vs unchanged tests are now correctly partitioned. Accept.

### design-4 — Fixed
Claim: §2.6's "the `.pyi` must not enter the crate assembly genrule" is false given §2.5 — once `cst.pyi`
is added to `generate_rust_parser`'s `DefaultInfo` (`rust.bzl:149`), the `fltk_pyo3_cdylib` genrule's
`srcs=[lib_rs, rs_srcs]` (`:318`) + copy loop (`:324-326`) pulls it into the crate gendir. Consequence:
benign (genrule `outs` are only the `.rs` files, stray `.pyi` discarded; rustc ignores `.pyi`;
`test -f` guards pass) but the design asserted a guarantee it does not provide.
Design inspection: §2.6 (lines 271-281) now describes the actual data flow ("`cst.pyi` flows into the
assembly genrule, harmlessly"), explains the discard mechanism, retracts the false "must not enter" claim
("was therefore inaccurate — it *does* enter, and is discarded"), and directs the implementer to confirm
the `fltk_pyo3_cdylib` round-trip builds with `cst.pyi` in `rs_srcs`, with `.pyi` filtering as the fallback.
Assessment: false guarantee removed, real data flow documented, implementer action specified. Accept.

## Approved

4 findings: 4 Fixed verified.

---

## Verdict: APPROVED

All four findings were valid; all four are Fixed in `design.md`, each verified against the design doc and
source (requirement text at `requirements.md:15` confirms design-1's divergence is real and now properly
surfaced as Open Question 2, not silently diverged). No disposition wrong; the divergence on design-1 is an
acknowledged, justified, user-confirmable open question — not a fundamental disagreement requiring
escalation.
