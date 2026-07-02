# Exploration: `TODO(submodule-register-fn-convention)`

## TODO.md entry (verbatim)

`TODO.md:25-27`:

> ## `submodule-register-fn-convention`
>
> `Submodule.register_fn` is validated for Rust identifier syntax but not for the convention that it should be `register_classes` (the name the codegenned `pub fn register_classes` uses). A caller with a non-standard name gets a Rust compile error rather than a Python-level error. Document or enforce the `register_classes` convention in `Submodule.validate()`. Location: `fltk/fegen/gsm2lib_rs.py` (`Submodule.validate()`).

## `TODO(submodule-register-fn-convention)` comment locations

Exactly one, at `fltk/fegen/gsm2lib_rs.py:82-83`, embedded inside the `Submodule.validate()` docstring (`fltk/fegen/gsm2lib_rs.py:76-87`):

```python
    def validate(self) -> None:
        """Raise ValueError if any field is not a valid Rust identifier.

        Note: validation is limited to Rust identifier syntax.  A register_fn that is a
        valid identifier but not a reachable function in the Rust crate will produce a
        Rust compile error rather than a Python-level error here.
        # TODO(submodule-register-fn-convention): document or enforce the convention that
        # register_fn should be 'register_classes' to match the codegenned crate shape.
        """
        _validate_rust_ident(self.mod_name, "mod_name")
        _validate_rust_ident(self.submodule_name, "submodule_name")
        _validate_rust_ident(self.register_fn, "register_fn")
```

No other occurrence of `TODO(submodule-register-fn-convention)` exists in the repo (checked with a recursive grep from repo root); a stray worktree directory `/home/rnortman/src/fltk/.claude/worktrees/agent-ab295be24eef6e7ce/` contains a pre-change copy of `gsm2tree_rs.py`/`gsm2parser_rs.py` etc. but no copy of `gsm2lib_rs.py` itself, so it contributes no additional TODO comment.

## `Submodule` shape and field default

`fltk/fegen/gsm2lib_rs.py:63-87`:

```python
@dataclass(frozen=True)
class Submodule:
    """Describes one Rust submodule registered into the #[pymodule]."""

    mod_name: str
    """Rust `mod <mod_name>;` — the .rs file basename stem."""

    submodule_name: str
    """Python submodule name passed to register_submodule."""

    register_fn: str = "register_classes"
    """Registration entry point function name within the Rust module."""

    def validate(self) -> None:
        ...
        _validate_rust_ident(self.mod_name, "mod_name")
        _validate_rust_ident(self.submodule_name, "submodule_name")
        _validate_rust_ident(self.register_fn, "register_fn")
```

`register_fn` defaults to the literal string `"register_classes"` and is validated only for Rust-identifier syntax (`_validate_rust_ident`, `fltk/fegen/gsm2lib_rs.py:20-24`), matching the TODO's description exactly.

## Where `register_fn` is consumed

The only use of `register_fn` is in `RustLibGenerator.generate()`, `fltk/fegen/gsm2lib_rs.py:213-214`:

```python
        for sub in spec.submodules:
            body.append(f'    register_submodule(m, "{sub.submodule_name}", {sub.mod_name}::{sub.register_fn})?;')
```

This emits a Rust path expression `{mod_name}::{register_fn}` referencing a function inside the declared `mod {mod_name};`. If no function of that name exists in the module, `rustc` fails to compile — this is the "Rust compile error rather than Python-level error" the TODO references, and it is accurate: `Submodule.validate()` has no way to introspect the actual Rust source, so it cannot check that the named function exists or has the right signature — only that the string is a syntactically valid identifier.

## Who constructs `Submodule` instances, and with what `register_fn` value

Every `Submodule(...)` construction in the non-test, non-worktree codebase is inside `LibSpec.standard()`, `fltk/fegen/gsm2lib_rs.py:106-126`:

```python
    @staticmethod
    def standard(module_name: str, *, with_parser: bool = True, with_unparser: bool = False) -> LibSpec:
        ...
        submodules: list[Submodule] = [Submodule("cst", "cst")]
        if with_parser:
            submodules.append(Submodule("parser", "parser"))
        if with_unparser:
            submodules.append(Submodule("unparser", "unparser"))
        return LibSpec(module_name=module_name, submodules=tuple(submodules))
```

All three calls use the two-positional-arg form (`mod_name`, `submodule_name`), leaving `register_fn` at its dataclass default of `"register_classes"`. None of the three passes `register_fn` explicitly.

`LibSpec.standard()` is the only production call site that builds `Submodule` values reachable from the CLI. `fltk/fegen/genparser.py:790-842` (the `gen-rust-lib` typer command) calls either:
- `gsm2lib_rs.LibSpec(module_name=..., submodules=(), ...)` (the `--no-cst` runtime-only path, zero submodules — `register_fn` is moot), or
- `gsm2lib_rs.LibSpec.standard(module_name, with_parser=not no_parser, with_unparser=unparser)` (`fltk/fegen/genparser.py:834`).

There is no CLI flag in `gen-rust-lib` (or anywhere else in `genparser.py`) that exposes `register_fn` for override — grepped for `register.fn`/`register_fn` in `genparser.py` with zero hits. So no caller, CLI or programmatic, in this repository ever sets `register_fn` to anything other than the default `"register_classes"`. The only route to a non-default value is direct, hand-written Python construction of `Submodule(..., register_fn="something_else")` — a capability that exists in the type signature but is exercised nowhere in-tree (including tests: `fltk/fegen/test_gsm2lib_rs.py`'s two `Submodule.validate()` tests, lines 290-303, only vary `mod_name`/`submodule_name`, never `register_fn`).

## Whether the generated Rust side ever uses a different function name

Every code generator that emits a pyo3 registration entry point hardcodes the literal name `register_classes` (never parameterized):
- `fltk/fegen/gsm2tree_rs.py:2426`: `lines.append("pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> pyo3::PyResult<()> {")`
- `fltk/fegen/gsm2parser_rs.py:1016`: `pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {`
- `fltk/unparse/gsm2unparser_rs.py:1882`: `lines.append("    pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {")`

Every generated/checked-in `.rs` file that defines this entry point (`crates/fegen-rust/src/{cst,parser,unparser}.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_parser_fixture/src/*.rs`, `tests/rust_poc_cst/src/cst.rs`) names it `register_classes` — grepped for `fn register_classes` across the repo and found no other function name playing this role. There is no known generator or hand-written crate in-tree that names this entry point anything else.

`LibSpec.standard()`'s docstring, `fltk/fegen/gsm2lib_rs.py:117-119`, states the convention explicitly: "The unparser uses the same register_classes entry point as cst/parser (existing two-submodule convention)."

## Net finding

The TODO's factual claims check out against the code as written:
- `Submodule.validate()` (`fltk/fegen/gsm2lib_rs.py:76-87`) validates `register_fn` only via `_validate_rust_ident`, with no check against the literal `"register_classes"`.
- `register_fn`'s only consumer (`fltk/fegen/gsm2lib_rs.py:214`) splices it unchecked into a Rust path expression; a mismatched name is a `rustc` compile-time error in the generated `lib.rs`'s consuming crate, not a Python-side `ValueError`.
- In the current codebase, `register_fn` is a dataclass field with a hardcoded-matching default (`"register_classes"`) that every call site (`LibSpec.standard()`'s three `Submodule` constructions, `fltk/fegen/gsm2lib_rs.py:121,123,125`) leaves untouched, and every Rust-side generator (`gsm2tree_rs.py`, `gsm2parser_rs.py`, `gsm2unparser_rs.py`) hardcodes the matching function name `register_classes`. No in-tree caller — CLI or Python — ever constructs a `Submodule` with a non-default `register_fn`, and no CLI flag exists to set one.
