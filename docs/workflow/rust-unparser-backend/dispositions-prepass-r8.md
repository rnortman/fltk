# Dispositions — prepass round 8

slop-1:
- Disposition: Fixed
- Action: Rewrote `test_gen_rust_unparser_format_config_is_applied`
  (`fltk/fegen/test_genparser.py:501`). The old test reused the module
  `simple_grammar_file` (`word := value:/[a-z]+/ ;`), which has no separator for
  `ws_allowed: nbsp;` to act on, so its only assertion (`pub fn unparse_word(`)
  was identical to the happy-path test and a config that was silently ignored
  would still pass. The rewrite uses a grammar with a WS-allowed (`,`) separator
  (`pair := first:/[a-z]+/ , second:/[a-z]+/ ;`), generates the unparser both
  with and without `--format-config`, and asserts the config output bakes
  `Doc::Nbsp` separator spacing while the no-config output does not (and that the
  two outputs differ). Verified empirically: default emits `Doc::Nil` (3x, no
  `Doc::Nbsp`); config emits `Doc::Nbsp` (3x, no `Doc::Nil`). Test passes; ruff
  check/format clean; full `make check` gate passed on commit.
- Severity assessment: A test asserting behavior it does not actually exercise is
  worse than no test — a reviewer trusts the name/docstring and a regression that
  silently drops `--format-config` would ship green. Low blast radius (test-only)
  but a real coverage gap in the feature's headline config path.
