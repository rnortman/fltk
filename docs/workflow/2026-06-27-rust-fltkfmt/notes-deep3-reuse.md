## reuse-1

File: `tests/test_fltkfmt_parity.py:56` and `tests/test_rust_unparser_parity_fixture.py:168`

The render-config ID formula `[f"w{w}i{i}" for (w, i) in _CONFIGS]` appears verbatim in both
files under the same name `_CONFIG_IDS`. The two `_CONFIGS` lists hold different values (the
test selection differs between the two test modules), so the constant itself cannot be shared,
but the ID-generation formula can only live in two places. If the format string is changed in
one file — for example to add units or change the separator — it silently diverges in the other,
breaking any CI test-ID filters or cross-file test references that rely on stable IDs. The formula
could be extracted into `tests/unparser_parity.py` as a small helper (e.g.,
`def render_config_ids(configs)`) that both files import.
