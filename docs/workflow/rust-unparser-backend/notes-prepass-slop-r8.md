slop-1
File: fltk/fegen/test_genparser.py
Near: `def test_gen_rust_unparser_format_config_is_applied`
Quote: `assert "pub fn unparse_word(" in src`

The test name promises that the format config is verified to be applied, and the docstring says
it "produces different output than default." The docstring also admits the simple grammar "has
a single regex token," so `ws_allowed: nbsp;` has nothing to act on — the generated output is
identical to the no-config case. The only assertions are exit code 0, file exists, and presence
of `pub fn unparse_word(` — the same assertions as `test_gen_rust_unparser_happy_path`.

Consequence: A bug that silently ignores `--format-config` would pass this test. The test
name signals behavioral coverage that isn't there; a reviewer would reasonably trust it and
miss the gap.

Suggested fix: Either rename the test to `test_gen_rust_unparser_format_config_path_succeeds`
to match what it actually verifies, or use a grammar with a WS-allowed separator (`,`) and
assert that the config-applied output contains a spacing spec that the no-config output does
not (e.g. `Nbsp` or similar).
