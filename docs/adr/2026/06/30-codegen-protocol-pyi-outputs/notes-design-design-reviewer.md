# Design review: codegen protocol + .pyi outputs

Reviewed `design.md` against `requirements.md`, `exploration.md`, and source at base commit
`1e9e402`. The central technical analysis is sound and well-grounded: the `import_path`
truthiness gate (`gsm2tree.py:891`), the `pyreg.Builtins`/empty-`import_path` trap
(`gsm2tree_rs.py:177-181`, `reg.py:16`), the byte-identity reachability argument (the value of
`import_path` reaches protocol output nowhere — only line 90 reads it, on the concrete-CST
`in_module` path, not the protocol's `protocol_annotation_for_model_types`), and the
"generate all text before opening any file" ordering all check out against code. Four findings below.

---

## design-1 — Design contradicts requirement Change-2 condition 1, and §2.2 is internally inconsistent with §2.5

Section: §2.2 ("Mapping to requirements §Change 2", Condition 1) and §2.5 (the `generate_rust_parser`
table).

What's wrong: `requirements.md` Change 2, condition 1 states verbatim: *"The caller does not separately
pass a `--protocol-module` flag; enabling protocol output on the Rust generator is sufficient to also
get the `.pyi`."* The design does the opposite. At the CLI, `--protocol-output` **requires**
`--protocol-module` ("`--protocol-output` without `--protocol-module` → CLI error", §2.2). At Bazel,
the §2.5 table row `("" , True)` is a hard `fail()` ("generate_protocol requires protocol_module"), so
`generate_protocol = True` alone is rejected — the `.pyi` is gated on `protocol_module` being set, not
on protocol output being enabled. So "enabling protocol output is sufficient" is false in the design;
the import path must always be supplied separately, even in condition 1.

Internal inconsistency: §2.2 claims "At the Bazel/Make layer this is a single opt-in (§2.4) — the caller
turns on protocol output and the `.pyi` comes with it." This (a) cross-references §2.4, which is the
*Python* `generate_parser` rule, not the Rust condition-1 path it is describing (that is §2.5); and
(b) is contradicted by §2.5's own table, where producing the protocol requires **two** coupled knobs
(`protocol_module` non-empty *and* `generate_protocol = True`), not a single opt-in.

Why / source: requirement text (Change 2, condition 1) vs design §2.2/§2.5. The design's own
validation rule and §2.5 table are the contradicting evidence. Note the deviation has a real technical
justification the design half-articulates elsewhere (§2.2: the `.pyi`'s `import {protocol_module} as
_proto` line needs the *dotted import path*, which is genuinely not derivable from the output *file
path* — see the Makefile pairing `--protocol-module fltk.fegen.fltk_cst_protocol --pyi-output
fltk/_stubs/fegen_rust_cst/cst.pyi`, two unrelated strings). So the requirement's "single opt-in supplies
the import path" model may itself be under-specified. But the design neither reconciles this nor flags
it as a deliberate deviation — it instead claims (incorrectly) to satisfy condition 1 as "a single opt-in."

Consequence: Implemented as written, the requirement's two-condition structure collapses — both
conditions reduce to "`--protocol-module` is set," with `--protocol-output`/`generate_protocol` only
additionally writing the `.py`. A user following the requirement's mental model ("just turn on protocol
output on the Rust generator and the `.pyi` comes too") hits a hard CLI/analysis-time error. This is a
user-intent question that should be surfaced and confirmed: either (a) accept the two-flag coupling and
record it as a justified deviation from condition 1 (recommended given file-path ≠ import-path), or
(b) make protocol output carry the import path so a single opt-in truly suffices. As drafted the design
silently diverges from an explicit requirement and contradicts its own §2.2 claim.

---

## design-2 — §1.2 factual claim about `gen_protocol_module()` callers is contradicted by source

Section: §1.2, "No existing test depends on the degraded `kind: object` form: the only
`gen_protocol_module()` unit callers (`test_cst_protocol.py:62-73`, `tests/test_gsm2tree_py.py:240`)
construct their `CstGenerator` with a non-empty module path."

What's wrong: `tests/test_gsm2tree_py.py:239-240` builds its generator via `_make_generator(grammar)`,
which is `tests.gsm2tree_helpers.make_generator` (imported at `test_gsm2tree_py.py:14`).
`tests/gsm2tree_helpers.py:69` constructs `CstGenerator(grammar=grammar, py_module=pyreg.Builtins, ...)`
— `pyreg.Builtins = Module(import_path=())` (`reg.py:16`), an **empty/falsy** `import_path`. So that
caller produces exactly the degraded `kind: object` form, contradicting the design's statement that it
uses a non-empty module path. (`test_cst_protocol.py:62` does use a non-empty path —
`pyreg.Module(["fltk", "fegen", "fltk_cst"])` — so that half of the claim is correct.)

Why / source: `tests/gsm2tree_helpers.py:69`, `tests/test_gsm2tree_py.py:14,239-240`, `reg.py:16`,
`gsm2tree.py:891`.

Consequence: The §1.2 safety argument ("byte-identity is safe; the degraded form is untested") rests on
a mis-statement. The *conclusion* happens to survive — I confirmed `tests/test_gsm2tree_py.py` contains
no `kind` assertions, so no test asserts the degraded form and nothing breaks — but the design's
groundedness is compromised on a load-bearing claim in its central risk section. The practical hazard for
the implementer: the protocol-generation machinery is reachable through a `pyreg.Builtins`-backed helper
(`make_generator`) that yields the degraded form, so the new `generate_protocol()` (and any test infra)
must *not* be built on that helper. The design's §5 test ("contains `kind: typing.Literal[NodeKind.*]`,
not `kind: object`") is the right guardrail; this finding is that §1.2's stated basis for safety is
factually wrong and undercounts the empty-path callers.

---

## design-3 — Test-plan §4 contradicts itself on `test_generate_protocol_only_matches_full_run`

Section: §4 / §5 (Test plan). Two bullets: (1) "`generate --protocol` and `generate --protocol-only`
emit byte-identical `_cst_protocol.py` (extends `test_generate_protocol_only_matches_full_run`,
`test_genparser.py:287-319`)"; (2) "Existing `--protocol-only` tests (`test_genparser.py:258-341`) still
pass unchanged."

What's wrong: `test_generate_protocol_only_matches_full_run` lives at lines 287-319, which is **inside**
the range 258-341. As written, that test invokes a bare full `generate` run with **no** `--protocol`
(`test_genparser.py:300`) and then reads `full_dir / "simple_cst_protocol.py"` (`:317`). Under the new
default (§2.1, protocol off unless `--protocol`/`--protocol-only`), the full run no longer writes the
protocol file, so `.read_text()` raises `FileNotFoundError` and the test fails. So the same test cannot
both be "extended" (bullet 1) and "still pass unchanged" (bullet 2).

Why / source: `test_genparser.py:287-319` (esp. `:300` bare `generate`, `:317` reads the protocol);
design §2.1 inverts the default.

Consequence: Ambiguity in the test plan. The design clearly *intends* to update this test (bullet 1),
but bullet 2's blanket "258-341 still pass unchanged" is false for the 287-319 sub-range and could lead
an implementer to leave a now-broken test in place (or to miss adding `--protocol` to its full-run arm).
Fix: scope bullet 2 to the two genuinely-unchanged tests (258-284 emits-only-protocol, 322-341
rejects-trivia-flags) and call out 287-319 as modified.

---

## design-4 — §2.6 ("`.pyi` must not enter the crate assembly genrule") is unenforced given §2.5

Section: §2.5 (adds `cst.pyi` to `generate_rust_parser`'s `DefaultInfo` depset, "adds it to the outputs
(`rust.bzl:...149`)") vs §2.6 ("the `.pyi` ... must not enter the crate assembly genrule
(`rust.bzl:316-335`)").

What's wrong: `fltk_pyo3_cdylib` consumes the `generate_rust_parser` target via its `rs_srcs` argument,
and the assembly genrule does `srcs = [lib_rs, rs_srcs]` (`rust.bzl:318`) then
`for f in $(locations {rs_srcs}); do cp $$f $$OUTDIR/$$(basename $$f); done` (`rust.bzl:324-326`).
`$(locations {rs_srcs})` expands to the target's full `DefaultInfo` files depset. Once §2.5 adds
`cst.pyi` to that depset, `cst.pyi` *is* passed into the genrule and copied into the crate gendir — the
exact thing §2.6 says must not happen. The design states the constraint but adds nothing to enforce it.

Why / source: `rust.bzl:318,324-326,149`; design §2.5 (DefaultInfo addition) vs §2.6 (the prohibition).

Consequence: Benign at build time — the genrule's `outs` are only `crate_lib_rs/crate_cst_rs/crate_parser_rs`
(`rust.bzl:319`), so the stray `cst.pyi` copy is an undeclared sandbox file Bazel discards, and rustc
ignores `.pyi`; the `test -f cst.rs/parser.rs` guards still pass. But the design's claim that the `.pyi`
"must not enter" the genrule is not actually true under §2.5, and the interaction is unaddressed. If a
maintainer later relies on "`rs_srcs` yields only `.rs`," adding `cst.pyi` silently changes that contract.
The implementer should either confirm the `fltk_pyo3_cdylib` round-trip still builds with the `.pyi` in
`rs_srcs`, or filter the `.pyi` out of what flows into the assembly genrule. Worth an explicit note since
§2.6 currently reads as if the separation were already guaranteed.

---

Notes path: docs/adr/2026/06/30-codegen-protocol-pyi-outputs/notes-design-design-reviewer.md
