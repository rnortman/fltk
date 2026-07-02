# Deep test review — protocol-module-truthiness-gate

Base `5ce1fd8f936240169be9dafafa4bc63e46274a9d`, HEAD `cc1e869c09866461a967f1b39e3e187c87400baf`.

## Coverage vs. design §4 test plan

All four planned new tests are present and match the design 1:1:

1. `fltk/fegen/test_cst_protocol.py::test_builtins_backed_generator_emits_literal_kind_by_default`
   — trap regression, asserts `Literal[NodeKind.` present and `kind: object` absent from a
   `Builtins`-backed generator's default output.
2. `fltk/fegen/test_cst_protocol.py::test_protocol_text_independent_of_py_module` — byte-identity
   between `Builtins`-backed and real-module-backed output; pins the core invariant the whole
   change rests on.
3. `fltk/fegen/test_cst_protocol.py::test_emit_kind_literal_false_produces_degraded_form` — explicit
   opt-out actually gates the discriminant (asserts `kind: object` present, `Literal[NodeKind.`
   absent).
4. `tests/test_gsm2tree_rs.py::TestGenerateProtocol::test_same_instance_py_gen_reuse_is_stable` —
   calls `generate_protocol()`, then `generate_pyi()`, then `generate_protocol()` again on one
   instance, asserts byte-identity. Genuinely exercises the new state-sharing surface (shared
   `_py_gen`/context) that the pre-existing cross-instance determinism test cannot reach.

Required-keyword threading (`_protocol_class_for_model_with_assignments` /
`_protocol_class_for_model`) is exercised indirectly by the updated
`tests/test_gsm2tree_py.py::TestMutatorsEmittedPyProtocol.protocol_klass` fixture (now passes
`emit_kind_literal=True`); its downstream assertions are unaffected by the discriminant change, as
the design correctly predicts (they check mutator stubs/ordering only, never the `kind` line).

Existing guardrail tests confirmed unchanged in the diff (`git diff` over `fltk/fegen/test_genparser.py`
is empty) and, on inspection at HEAD, still assert exactly what the design claims:
`test_gen_rust_cst_protocol_output_matches_python_protocol` still asserts byte-identity plus the
`Literal[NodeKind.` / no-`kind: object` guard, now exercising the reused-`_py_gen` code path through
the CLI. `tests/gsm2tree_helpers.py:make_generator` is confirmed `Builtins`-backed, matching the
design's claim about `TestProtocolModuleAll`'s fixture.

Ran the full set (`fltk/fegen/test_cst_protocol.py`, `tests/test_gsm2tree_rs.py`,
`tests/test_gsm2tree_py.py`) before the working tree was disturbed (see incident note below):
304 passed.

## Quality

No vacuous assertions found. Each new test asserts on the actual rendered text (substring
presence/absence or byte-equality), not "ran without throwing." Test 4 is a meaningful
regression pin for exactly the risk called out in the design's edge-cases section (§3,
"Context coupling from `_py_gen` reuse") — the existing cross-instance test builds fresh
generators per call and structurally cannot catch same-instance state bleed, so test 4 is not
redundant with it.

No gaps identified against the design's edge-case list: the "empty `rule_name`" path is
explicitly and correctly left untested per the design (unreachable via any public call site,
would only test Python's own keyword-argument enforcement).

## Findings

No findings.

## Incident: working tree corrupted mid-review (not a test-coverage finding)

While gathering `git diff` context I ran `git stash && ... && git stash pop`. `git stash` reported
"No local changes to save" (my session had none), but `git stash pop` popped a **pre-existing**
stash (`stash@{0}`, message "WIP on main: ee4a59b Native span field in generated Rust CST node
structs (§2.2)") that belongs to another process — this repo directory is shared with a live,
concurrent review-chain run (sibling `notes-deep-*-reviewer.md` / `judge-verdict-prepass.md` files
were appearing in this same directory throughout my session). The pop produced merge conflicts;
git kept the stash (did not drop it — `stash@{0}`/`stash@{1}` are both still present, so no stash
content was lost), but the working tree is now left with unresolved conflicts (`UU`) in tracked
files including `fltk/fegen/gsm2tree.py`, `fltk/fegen/gsm2tree_rs.py`, `fltk/fegen/fltk_parser.py`,
and others, plus two files deleted-by-us (`src/cst_fegen.rs`, `src/cst_generated.rs`).

I attempted `git reset --hard HEAD` to restore the tree to clean HEAD (stash contents would remain
safe since git never dropped them) but this was denied by the permission system as an irreversible
destructive action outside my task scope. I did not attempt further git commands that discard
working-tree state, since that would bypass the intent of that denial.

**Net effect: the shared working tree currently has unresolved merge-conflict markers in several
tracked source files.** This does not affect the findings above (all gathered via `git show`/`git
diff` against commit objects, and the pytest run completed before the corruption), but it may
affect any sibling agent that reads those files from the working tree rather than from git
objects. Someone with permission should run `git reset --hard HEAD` (the pre-existing stash will
be preserved, untouched, at `stash@{0}`/`stash@{1}`) to restore the tree.
