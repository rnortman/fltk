# Error-handling review — round 11

Commit reviewed: fabdc5a2ea6f4ca1ecc42386a4a5f40a8e776dd4

---

## errhandling-1

**File:line**: `Makefile:288–293`

**The broken error path**:

```makefile
tmpdir=$$(mktemp -d); \
uv run python -m fltk.fegen.genparser generate \
    fltk/fegen/test_data/rust_parser_fixture.fltkg rust_parser_fixture rust_parser_fixture_cst \
    --output-dir $$tmpdir; \
cp $$tmpdir/rust_parser_fixture_cst_protocol.py tests/rust_parser_fixture_cst_protocol.py; \
rm -rf $$tmpdir
```

The `\` continuation joins these into a single shell invocation with `;`-separated
commands (not `&&`). Bash runs all four commands in sequence regardless of intermediate
exit codes. The exit code Make receives is the exit code of the final command
(`rm -rf $tmpdir`), which is essentially always 0 — the temp directory was created by
`mktemp -d` moments earlier and will exist.

**Why — where the error goes**:

If `uv run python -m fltk.fegen.genparser generate` fails (grammar change, import error,
generator bug, disk full), the generated file is never written to `$tmpdir`. The `cp`
command then fails with "No such file or directory", printing a message to stderr. Then
`rm -rf $tmpdir` runs and exits 0. Make records the recipe step as successful. The
`gencode` target continues into the subsequent `gen-rust-unparser` invocation and the
ruff normalization pass without stopping. The stale (or absent)
`tests/rust_parser_fixture_cst_protocol.py` is left in place with no Make-level failure.

**Consequence**:

`make gencode` exits 0 despite the generator crashing. The protocol module committed to
`tests/` is silently stale. The committed `fltk/_stubs/rust_parser_fixture/unparser.pyi`
continues to `import tests.rust_parser_fixture_cst_protocol as _proto`, so pyright type-
checks it against the old protocol classes rather than the ones matching the current
grammar. The mismatch is invisible until a downstream consumer or the pyright tests
manually detect the drift — there is no on-call-diagnosable error, no failed Make step,
and no stderr output that Make captures or surfaces in CI logs in a way that stops the
build.

The `cp` error message does appear in the terminal, but because Make did not fail, CI
pipelines that gate on `make gencode` exit code would pass and proceed to commit or
deploy the stale artifact.

**What must change**:

Replace `;` with `&&` between each command so that any failure in the chain immediately
stops execution and propagates a non-zero exit to Make:

```makefile
tmpdir=$$(mktemp -d) && \
uv run python -m fltk.fegen.genparser generate \
    fltk/fegen/test_data/rust_parser_fixture.fltkg rust_parser_fixture rust_parser_fixture_cst \
    --output-dir $$tmpdir && \
cp $$tmpdir/rust_parser_fixture_cst_protocol.py tests/rust_parser_fixture_cst_protocol.py; \
rm -rf $$tmpdir
```

The final `rm -rf` should remain `;`-separated (cleanup should run even on failure) but
the generator invocation and `cp` must be `&&`-gated so Make fails fast when either step
fails. Alternatively, prefix with `set -e;` to catch all failures including the `mktemp`
itself.
