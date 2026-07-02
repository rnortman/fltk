No findings.

Verified: the two new `*_broken_native_propagates` tests (tests/test_span_protocol.py:59-83)
genuinely fail against the pre-fix `except Exception:` code (DID NOT RAISE OSError) and pass
after the narrowing fix — not vacuous. The third new test
(`test_span_protocol_absent_native_falls_back_silently`) correctly mirrors the pre-existing
`test_reload_without_native_emits_no_warning` for the span_protocol.py lockstep site, pinning
the silent-fallback contract with `warnings.simplefilter("error")` plus an identity assertion
on `AnySpan`. Both lockstep sites (span.py, span_protocol.py) are covered for both the
broken-native (propagate) and absent-native (silent fallback) paths. Cleanup follows the
sys.modules save/restore/reload pattern correctly (restores the saved real module object
before the restorative reload, never delete-and-reimport). Full test suite
(tests/test_span_protocol.py) passes, 49/49. Existing tests left unmodified, consistent with
the diff being purely additive to that file.
