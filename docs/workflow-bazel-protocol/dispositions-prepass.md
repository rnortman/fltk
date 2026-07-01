# Dispositions — prepass review (round 1)

scope-1:
- Disposition: Fixed
- Action: Recorded the design's "Misconfiguration coverage" test-plan item as
  verified manual `bazel` expectations in
  docs/workflow-bazel-protocol/implementation-log.md (new "Misconfiguration
  coverage" section at end). Both `fail()` paths were actually exercised via a
  throwaway bazel package (removed after; no repo change) and the captured
  error messages are documented and matched against rust.bzl:583-600:
  `python_extension = False` + `protocol_module` set, and `protocol = True` +
  empty `protocol_module`. No source-code change was required — the guards
  already existed and were confirmed correct.
- Severity assessment: Low. The finding was a verification/documentation gap,
  not a code defect; the guards were present and correct. Absent the note, a
  future reader had no record the test-plan item was considered. Now both the
  behavior is confirmed and the record exists.
