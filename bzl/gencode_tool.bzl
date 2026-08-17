"""The ruff plumbing every target that generates or lints Python code needs.

Generation normalizes its own output (`fltk/fegen/gencode_format.py`), so the generator
binaries, the tests that drive a generator CLI, and the lint rules all reach for the same two
things: the pinned `gencode-ruff.toml` and a runnable ruff.  Stated once here because the
awkward half — where the ruff *executable* lives — is a wheel-layout fact that has to be
repeated identically everywhere or not at all.

The `@pypi//ruff` py_library carries only the importable package; the executable ships under
`<wheel>.data/scripts/`, which reaches runfiles only through the extracted-wheel filegroup.
`gencode_format.find_ruff()` and `bzl/py_lint.bzl` both locate `bin/ruff` inside it.
"""

# The extracted wheel filegroup, as a label string so both a BUILD `data` list and a rule
# attribute default (which wraps it in `Label`) can name the one value.
RUFF_WHL_FILES = "@pypi//ruff:extracted_whl_files"

# `data` for anything that runs ruff: the pinned config plus the executable's wheel files.
# The config is a declared input rather than a discovered file precisely so a consumer's own
# pyproject.toml in the execroot cannot reshape what FLTK generates; every invocation passes it
# with an explicit `--config`.
GENCODE_TOOL_DATA = [
    "//:gencode-ruff.toml",
    RUFF_WHL_FILES,
]

# `deps` for anything that runs ruff through `gencode_format.find_ruff()`, which derives the
# executable's path from the imported package's location.
GENCODE_TOOL_DEPS = ["@pypi//ruff"]
