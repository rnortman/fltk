# Deep efficiency review — r11 (final batch: committed .pyi + protocol module + Makefile wiring, OQ-3)

Commit reviewed: fabdc5a2ea6f4ca1ecc42386a4a5f40a8e776dd4 (base 0494f3127dd09141e7bc0f0b918862feaf449f46)

Scope: only code present in the diff. The diff is almost entirely typing/build wiring —
the committed fixture `unparser.pyi` + `__init__.pyi`, the generated
`rust_parser_fixture_cst_protocol.py` (a pyright-only typing module, no runtime path),
the `generate_pyi` change swapping `typing.Optional[X]` for `X | None`, the pyright
consumer test, and the `gencode` Makefile step. None of this runs in a parser/render
hot path. The generator changes are O(rules) string building, executed once per
`make gencode`.

## efficiency-1: `gencode` generates the full Python CST + parser suite only to keep one protocol file

File: `Makefile`, the new `gencode` step (the `tmpdir=$$(mktemp -d); uv run python -m
fltk.fegen.genparser generate ... --output-dir $$tmpdir; cp
$$tmpdir/rust_parser_fixture_cst_protocol.py ...; rm -rf $$tmpdir` block).

The problem: the `generate` subcommand (`fltk/fegen/genparser.py:128`) always emits
`<base>_cst.py`, `<base>_cst_protocol.py`, and the parser module(s). The step needs
only `rust_parser_fixture_cst_protocol.py` and discards the rest via the temp dir. So
every `gencode` run does the full CST-class + parser codegen (and file writes) purely to
extract the one Python protocol module the committed `.pyi` types its `node` params
against. The protocol itself is producible alone via `cstgen.gen_protocol_module()`
(genparser.py:206), so the surrounding work is strictly redundant. This is also a fourth
independent `uv run` + grammar re-parse for the same `rust_parser_fixture.fltkg` already
parsed by the sibling `gen-rust-cst` / `gen-rust-parser` / `gen-rust-unparser` targets.

Consequence: extra Python codegen + throwaway file writes on every `make gencode`. Cost
shows up only in the developer regen workflow (gencode is dev-only and infrequent), over
one small fixture grammar, so the wall-clock impact is small — this is a cleanliness /
"overly broad operation" note, not a runtime regression. The comment in the Makefile
already acknowledges the discard.

Fix direction (out of this diff's file set, so optional): add a `--protocol-only` flag to
the `generate` subcommand (or a tiny dedicated subcommand) that calls
`cstgen.gen_protocol_module()` and writes just `<base>_cst_protocol.py`, then point the
`gencode` step at it and drop the temp-dir dance. If left as-is, the current approach is
correct and the cost is negligible.

## Non-findings (checked, clean)

- `RustUnparserGenerator.generate_pyi` builds the stub in a single O(rules) pass and is
  called once per generation; the `Optional` -> `X | None` change is text-only with no
  cost effect.
- `tests/test_rust_unparser_pyi.py` runs pyright exactly once per module: the two consumer
  fixtures (`consumer_ok.py`, `consumer_bad.py`) are batched into one
  `_run_pyright_over_dir` call via a module-scoped fixture, and the `pyright --version`
  probe is a session-scoped fixture. This is the efficient shape for an expensive
  subprocess; no per-test pyright spawning.
- `tests/rust_parser_fixture_cst_protocol.py` is a generated pyright-only protocol module
  with no runtime execution path — no efficiency surface.
</content>
</invoke>
