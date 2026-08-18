"""The Python interpreter version every fltk target pins, in one place.

`python.toolchain(is_default = True)` in MODULE.bazel is honored only while fltk is the root
module, so every public `py_binary` and every pyright config has to name the version itself or
a consumer's own default wins and the cp310-only wheels in @pypi have no matching
distribution.

One constant rather than a literal per target because a version spelled once cannot be bumped
in some targets and not others, and a target that kept the old spelling fails analysis in a
*consumer's* build, at a target the consumer never named — invisible to this repo's own lanes.

MODULE.bazel files cannot `load()`, so their `python.toolchain` tags are checked against this
constant by `make bazel-toolchain-guard` instead.
"""

FLTK_PYTHON_VERSION = "3.10"
