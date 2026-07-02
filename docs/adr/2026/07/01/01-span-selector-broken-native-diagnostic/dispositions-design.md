# Dispositions: design review round 1 (span-selector-broken-native-diagnostic)

Notes: `notes-design-design-reviewer.md`. Design: `design.md`. Both findings were
independently fact-checked against HEAD c03a801 before dispositioning:
`git log` confirms HEAD is c03a801 and `grep -n` puts the TODO.md entry header at line 35
(design-1); `src/lib.rs:19-21` contains the `PyOnceLock` + `.expect("UNKNOWN_SPAN already
set; module initialized twice")` double-init panic, and the existing cleanup at
`tests/test_span_protocol.py:36-39` indeed restores the saved module object via
`sys.modules.update(saved)` before its restorative reload (design-2).

design-1:
- Disposition: Fixed
- Action: Design header now cites base commit c03a801 and notes the exploration was
  written at 8fd5ecf with `TODO.md` renumbering as the only relevant drift (all cited
  code byte-identical between the commits). Both `TODO.md:77` references corrected to
  the header at `TODO.md:35` — in "Root cause / context" and in the "### TODO.md"
  section, the latter now also instructing to locate the entry by slug rather than line
  number.
- Severity assessment: Low. Worst case was an implementer landing at the wrong TODO.md
  line and a stale base-commit pin; the slug made a wrong deletion unlikely. Now
  eliminated.

design-2:
- Disposition: Fixed
- Action: Test plan's shared-fixture paragraph now states the load-bearing cleanup
  constraint explicitly: restore the saved original `fltk._native` module object into
  `sys.modules` before the restorative reload, never delete-and-reimport, because the
  native extension cannot initialize twice in one process (PyO3
  `PanicException: UNKNOWN_SPAN already set; module initialized twice`, `src/lib.rs:21`,
  a `BaseException` that escapes `except Exception`). It points at the existing safe
  pattern (`tests/test_span_protocol.py:36-39`) as the template. The "Test-induced
  reload state" edge-case bullet cross-references the same constraint.
- Severity assessment: Real trap. A slightly-deviating implementer (pop + fresh reimport,
  a reasonable-looking cleanup) would hit a `BaseException` panic in `finally` that masks
  the actual test outcome and poisons `fltk._native` state for every later test in the
  pytest process; all three new tests manipulate `sys.modules["fltk._native"]`, so
  exposure was per-test. The one-paragraph constraint removes it.

No Won't-Do or TODO dispositions. Edits were localized fix-ups (line-number/base-commit
corrections plus one constraint paragraph), not a substantial revision, so cleanup-editor
was not re-invoked.
