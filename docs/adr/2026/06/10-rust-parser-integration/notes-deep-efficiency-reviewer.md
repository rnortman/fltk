# Efficiency review — deep

Reviewed: 8b3e92b..f1423a2 (HEAD f1423a2)

No findings.

Verified before clearing: the two new `cargo tree` stanzas in `check-no-pyo3` measure ~16ms each (metadata-only, no compile); the self-hosting test's redundant pure-Python reference parse of fegen.fltkg (also parsed by the pre-existing AC8 test) measures ~17ms — caching not warranted; `assert ..., parser.error_message()` messages are lazily evaluated, so no per-pass FFI cost. Remaining changes are docs and a module docstring.
