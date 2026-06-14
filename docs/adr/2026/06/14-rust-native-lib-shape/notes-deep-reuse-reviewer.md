## reuse-1

**File:line**: `fltk/fegen/gsm2lib_rs.py:16-22`

```python
_RUST_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _validate_rust_ident(value: str, label: str) -> None:
    if not value or not _RUST_IDENT_RE.match(value):
        msg = f"Invalid Rust identifier for {label}: {value!r}"
        raise ValueError(msg)
```

**What's duplicated**: The single-segment Rust identifier pattern (`[A-Za-z_][A-Za-z0-9_]*`) is also the repeating unit of `_CST_MOD_PATH_RE` in `genparser.py:365`:

```python
_CST_MOD_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*$")
```

**Existing function/utility**: `_CST_MOD_PATH_RE` at `fltk/fegen/genparser.py:365`. Neither is a function that calls the other; the same character class is hand-written twice. A shared `_validate_rust_ident` in `gsm2lib_rs.py` could be imported by `genparser.py` for the single-segment validation in `gen-rust-parser`'s `--cst-mod-path` check; alternatively both could live in a shared module (none exists yet).

Note: `gsm2tree_rs.py` has a related `_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")` at line 22, but that is intentionally lowercase-only (it validates `.fltkg` grammar identifiers, which the grammar constrains to lowercase). It is not the same space as Rust module/function names and is not a duplicate.

**Consequence**: If the Rust identifier syntax definition ever needs to change (e.g. to reject leading underscores for non-`_`-prefixed names, or to add a keyword blocklist), the pattern must be updated in two places independently. Currently low risk because the validation is simple, but the duplication grows if more `gen-*` commands are added that also need single-segment Rust identifier validation.
