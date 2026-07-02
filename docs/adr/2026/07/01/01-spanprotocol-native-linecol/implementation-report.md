# Implementation report: `spanprotocol-native-linecol`

## Deviations from design

- **Re-export form for `LineColPos`.** Design offered "redundant-alias form
  (`from ... import LineColPos as LineColPos`) or `# noqa: F401` — whichever satisfies ruff." The
  repo's ruff config rejects the redundant-alias form (PLC0414), so the shipped code uses the plain
  import with `# noqa: F401` and an explanatory re-export comment. This is an explicitly-sanctioned
  design alternative, not a true deviation.

- **Guard string-annotation check scoped to annotation contexts, not all string constants.** The
  design's native-free guard says to fail on `_native` appearing in "any identifier, attribute
  chain, or string annotation anywhere within either class body." Implemented literally against all
  string *constants*, this would reject the `LineColPosProtocol` docstring, which deliberately names
  `fltk._native.LineColPos` to explain what the protocol bridges. Resolution: the string-`_native`
  assertion (`test_protocol_class_bodies_name_no_native`) inspects only actual annotation
  expressions (function arg/return annotations and `AnnAssign` targets), while identifier/attribute
  references are still checked across the entire class body. A docstring mentioning native is
  therefore allowed; a native reference in the structural surface (annotation, identifier, attribute,
  or import-bound alias) is not. This matches the design's stated intent ("string annotation"), keeps
  the informative docstring, and does not weaken the guard against the leak it exists to catch (the
  alias-channel test independently covers native-import-bound names used in class bodies).

## TODOs created

None. This change closes `TODO(spanprotocol-native-linecol)`; the entry was removed from `TODO.md`
and the inline comment block deleted from `span_protocol.py`.
