# Dispositions — prepass round 1

slop-1:
- Disposition: Fixed
- Action: Dropped `(design §2.1)` from the `gen_protocol_module` docstring (fltk/fegen/gsm2tree.py:722); states the behavior directly.
- Severity assessment: Minor. A design-doc section ref in a code docstring rots once the doc is gone/renumbered; harmless at runtime but poor standalone documentation.

slop-2:
- Disposition: Fixed
- Action: Removed `(design §2.1)` from the kind-discriminant comment (fltk/fegen/gsm2tree.py:921-923); comment now stands on its own.
- Severity assessment: Minor. Same doc-rot/context-dependency issue as slop-1.

slop-3:
- Disposition: Fixed
- Action: Rewrote the test docstring (fltk/fegen/test_cst_protocol.py:79-84) to state the invariant under test ("a Builtins-backed generator emits the precise Literal discriminant by default") without before/after diff narration.
- Severity assessment: Minor. Changelog-style narrative documents the diff rather than the test's purpose; dead once the "before" state is history.

slop-4:
- Disposition: Fixed
- Action: Dropped the `Per §1.2:` prefix from the test docstring (tests/test_gsm2tree_rs.py:1132).
- Severity assessment: Minor. Same doc-rot issue as slop-1/2.

slop-5:
- Disposition: Fixed
- Action: Removed the "rather than constructing a throwaway generator" diff-narration from the test docstring (tests/test_gsm2tree_rs.py:1152-1156); now describes what the test pins going forward.
- Severity assessment: Minor. Narrates the removed approach rather than documenting the test; confusing once the old throwaway-generator design is forgotten.

## scope

No findings reported. No action.
