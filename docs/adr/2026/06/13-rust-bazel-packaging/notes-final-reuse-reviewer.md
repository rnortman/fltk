# Reuse Review — Rust Bazel Packaging

Commit range reviewed: fltk fafa6d7..9657025, Clockwork ece332a..6717614

## reuse-1 — Duplicated `cp $< $@` genrule for ABI3 rename

**File:line**: `BUILD.bazel:58-63` (fltk `native_so` genrule) and `rust.bzl:262-268` (step 3 inside `fltk_pyo3_cdylib`).

**What's duplicated**: Both sites issue a one-line `cmd = "cp $< $@"` Bazel genrule whose only job is to rename `lib<crate_name>.so` to `<name>.abi3.so`. The shell logic is identical; the only difference is the input target and output path.

**Existing function/utility**: There is no pre-existing Starlark helper, but the pattern could be extracted into a `_abi3_rename(name, src, out)` function defined in `rust.bzl` and called from both `fltk_pyo3_cdylib` and `BUILD.bazel`. `BUILD.bazel` would then `load("//:rust.bzl", "_abi3_rename")`.

**Consequence**: Two copies of the same rename recipe diverge if the rename semantics ever need to change (e.g. adding `--strip-unneeded`, preserving permissions via `install`, or adopting `rules_rust`'s native abi3 support when it becomes available). The second copy (`rust.bzl`) is the generalised macro form; the first (`BUILD.bazel`) is a hand-written duplicate of the same recipe rather than a call into the macro.

---

## reuse-2 — Identical `ValueError` message format in two adjacent collision-check branches

**File:line**: `fltk/fegen/gsm2tree_rs.py:171-178` — two consecutive `if class_name in ...` blocks that raise `ValueError` with the identical f-string template `f"Rule {rule.name!r} derives class name {class_name!r}, which collides with {collision_target}"`.

**What's duplicated**: The error-message construction is character-for-character identical across both branches (`_RESERVED_CLASS_NAMES` and `_RESERVED_CLASS_NAMES_SEEDED`). The two dicts are intentionally separate (the invariant check at module-load time enforces that `_RESERVED_CLASS_NAMES` must not contain `Py{CN}`-form names, which is the whole population of `_RESERVED_CLASS_NAMES_SEEDED`), so the dicts cannot be merged. But the lookup-and-raise block is pure duplication.

**Existing function/utility**: None. The duplication could be removed by combining the lookup into a single expression: `collision_target = _RESERVED_CLASS_NAMES.get(class_name) or _RESERVED_CLASS_NAMES_SEEDED.get(class_name)` with a single `if collision_target:` raise, or by iterating over `(_RESERVED_CLASS_NAMES, _RESERVED_CLASS_NAMES_SEEDED)`.

**Consequence**: If the error message format is updated in one branch and not the other, collision diagnostics become inconsistent depending on which dict matched. This has already happened in spirit: a future maintainer adding a new reserved name to either dict might not notice the other branch has a differently-worded format.
