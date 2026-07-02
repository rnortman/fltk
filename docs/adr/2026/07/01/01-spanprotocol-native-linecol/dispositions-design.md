# Dispositions — design review round 1 (`spanprotocol-native-linecol`)

Reviewer notes: `notes-design-design-reviewer.md`. Design: `design.md`.

design-1:
- Disposition: Fixed
- Action: Fact-checked against `fltk/fegen/pyrt/span_protocol.py` — the aliased try-import
  `from fltk._native import Span as _RustSpan` exists at line 120 inside the try-block
  (119-124), exactly as the reviewer states, and the evasion is real: extending that import
  with `LineColPos as _RustLineColPos` and referencing the alias in a class-body string
  annotation passes both originally specified assertions (alias name contains no `_native`
  substring; import is try-enclosed, not under TYPE_CHECKING), while being precisely the
  stub-sensitivity leak the guard exists to catch. Applied the reviewer's suggested third
  assertion to `design.md` § "New stub-stability guard": collect every name bound by any
  `fltk._native` import in the module (asname-or-name of each alias) and assert none is
  referenced within either protocol class body — as an `ast.Name`, attribute-chain root, or
  identifier token inside a string annotation — scoped to class bodies so the legitimate
  `AnySpan` use of `_RustSpan` below the classes stays legal. Also updated Test plan item 2
  to include the new assertion.
- Severity assessment: Without the fix, the guard test would pass while the exact regression
  it exists to prevent — `SpanProtocol`/`LineColPosProtocol` becoming native-dependent and
  making every generated-pipeline consumer's pyright behavior stub-sensitive — landed
  silently; the request.md load-bearing guard constraint would be satisfied in letter only.
  The evading edit works at runtime when the extension is present, so it is a plausible
  accidental change, not merely adversarial.
