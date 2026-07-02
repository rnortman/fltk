# Slop review notes

Commit reviewed: 5ce1fd8f936240169be9dafafa4bc63e46274a9d..49f00cd806eb415b9dde70be29204c34aa7e49eb

## slop-1

- File: fltk/fegen/gsm2tree.py:722
- Quote: `emit_kind_literal controls the per-node ``kind`` discriminant (design §2.1). Default True`
- What's wrong: Docstring cites a design-doc section number (`design §2.1`).
- Consequence: Design docs are ephemeral workflow artifacts; a reader with the checked-in code but not the design doc can't resolve "§2.1", and the reference will rot once the doc is gone/renumbered. Code comments should stand on their own.
- Suggested fix: Drop the `(design §2.1)` citation; state the behavior/invariant directly.

## slop-2

- File: fltk/fegen/gsm2tree.py:921-923
- Quote: `# The discriminant form is controlled by the explicit emit_kind_literal parameter (design\n# §2.1); py_module plays no role in protocol output.`
- What's wrong: Same design-doc section reference, now split awkwardly across a comment line break ("design\n§2.1").
- Consequence: Same rot/context-dependency problem as slop-1; also reads as copy-pasted from a doc rather than authored as a standalone comment.
- Suggested fix: Remove the `(design §2.1)` reference.

## slop-3

- File: fltk/fegen/test_cst_protocol.py:81-84
- Quote: `Before the burndown, the Literal discriminant was gated on py_module.import_path truthiness, ... With the explicit emit_kind_literal parameter defaulting True, py_module no longer gates the discriminant.`
- What's wrong: Changelog-style docstring narrating what the code used to do before this change, rather than describing current behavior/invariant being tested.
- Consequence: Reads as the model talking through its own diff; once the "before" state is history, the docstring is dead narrative rather than useful documentation of the test's purpose.
- Suggested fix: State the invariant under test ("a Builtins-backed generator still emits the precise Literal discriminant") without the "before/after" framing.

## slop-4

- File: tests/test_gsm2tree_rs.py:1132
- Quote: `"""Per §1.2: the non-degraded 'kind: typing.Literal[NodeKind.*]' form is emitted.`
- What's wrong: Design-doc section reference (`Per §1.2`) in a test docstring.
- Consequence: Same doc-rot/context-dependency issue as slop-1/2.
- Suggested fix: Drop the `Per §1.2` prefix; the sentence stands fine without it.

## slop-5

- File: tests/test_gsm2tree_rs.py:1152-1153
- Quote: `generate_protocol now reuses the shared self._py_gen (which also backs .rs/.pyi emission) rather than constructing a throwaway generator.`
- What's wrong: Changelog-style comment describing the prior implementation ("rather than constructing a throwaway generator") instead of just describing current behavior.
- Consequence: Narrates the diff instead of documenting the test; becomes confusing once no reader recalls the old throwaway-generator approach.
- Suggested fix: Describe what the test pins going forward (repeated `generate_protocol()` calls on one instance are stable/side-effect-free) without referencing the removed approach.
