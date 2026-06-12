No findings.

All new code in this diff is purpose-built test plumbing with no existing equivalent
anywhere in the codebase: the `registry_introspection.rs` wrappers are the first
Python-callable exposure of the registry introspection API; `addr_of`, `_synthetic_addr`,
`_Obj`, and `_next_addr` have no prior counterparts in any test file; `gc.collect()` is
not used anywhere else in the test suite; and `itertools.count` use in the test file does
not overlap with its two existing uses (rule-ID sequencing in `gsm2parser.py` /
`gsm2parser_rs.py`). No inline logic could be replaced by an existing utility.
