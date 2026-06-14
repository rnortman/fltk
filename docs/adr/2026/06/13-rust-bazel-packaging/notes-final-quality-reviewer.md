## quality-1

**File:** `fltk/fegen/gsm2tree_rs.py:217`

```python
name: [("(pyo3 import)", f"pyo3 method trait import ({desc[:40]}...)")]
```

The cross-rule collision diagnostic for `_RESERVED_CLASS_NAMES_SEEDED` entries stores a
`desc[:40]` truncation as the family description.  This code path IS reachable: the
per-rule check (lines ~172–139) tests `class_name in _RESERVED_CLASS_NAMES_SEEDED` where
`class_name` is the data-struct name (e.g. `AnyMethods` for rule `any_methods`), while the
seeded names are in Py-handle form (`PyAnyMethods`).  So the per-rule check silently passes
and the cross-rule check fires — with the truncated text.

A user whose rule `any_methods` gets rejected sees:

> "Generated Rust identifier 'PyAnyMethods' collides: pyo3 method trait import (pyo3::PyAnyMethods (unqualified method t... vs Python handle struct for rule 'any_methods'"

The reason why the name is reserved (needed for `.extract()` / `.is_instance_of()` method
syntax) is cut off.

**Consequence:** When a grammar author hits this collision, the error gives them the reserved
name but not the rationale, forcing them to hunt through the generator source to understand
why `PyAnyMethods` cannot be used.  As more consumers write grammars against the Bazel Rust
backend, this diagnostic gap will surface repeatedly.

**Fix:** Store the full description in the claims tuple.  The `family_description` field is a
free-form string; just drop the `[:40]` slice and the trailing `"..."`:

```python
name: [("(pyo3 import)", f"pyo3 method trait import: {desc}")]
```

---

## quality-2

**File:** `crates/fltk-cst-core/BUILD.bazel`

```starlark
rust_library(
    name = "fltk-cst-core",
    ...
    crate_features = ["python"],
    ...
)
```

The Cargo.toml for `fltk-cst-core` explicitly documents: *"Pure-Rust consumers omit pyo3
entirely by NOT enabling this feature."*  The Bazel BUILD hardcodes `python` unconditionally,
making it impossible for a Bazel consumer to depend on `fltk-cst-core` without pulling in
pyo3.  Cargo supports the pure-Rust path; Bazel does not.

**Consequence:** The inconsistency between Cargo and Bazel grows silently.  Any future
pure-Rust Bazel consumer (e.g. a Bazel-built CLI tool or test that uses CST data structures
without Python) is forced to link pyo3, violating the design intent stated in the Cargo.toml
comment.  Because the current BUILD expresses only the single "always python-on" configuration,
each new Bazel consumer written against the Cargo intent of python-optional will need a
workaround or a BUILD amendment.

**Fix:** Add a comment in the BUILD.bazel explaining why `python` is hardcoded (`all current
Bazel-built consumers are PyO3 cdylibs; a separate config_setting-based variant is needed
if a pure-Rust consumer is ever added`).  This prevents the discrepancy from becoming a
silent trap while being honest that the restriction exists.

---

## quality-3

**File:** `rust.bzl` — `fltk_pyo3_cdylib` macro, `_assemble_crate` genrule

```starlark
for f in $(locations {rs_srcs}); do
    cp $$f $$OUTDIR/$$(basename $$f)
done
```

The assembly loop copies every file from `rs_srcs` into the gendir by basename, after the
lib.rs has already been written (via `printf ... > lib.rs` then `cat ... >> lib.rs`).  If a
caller passes a label whose outputs include a file named `lib.rs`, that file silently
overwrites the carefully assembled crate root that prepended `#![recursion_limit]` and
concatenated the consumer's `lib_rs`.  Bazel macros cannot enforce provider types, so there
is no compile-time guard on the `rs_srcs` label.

**Consequence:** A future caller who accidentally passes a wrong target (e.g. one that
produces `lib.rs` alongside `cst.rs` / `parser.rs`) gets a silent overwrite; the resulting
Rust source may still compile (if the file is a valid crate root) but produce an unexpected
binary missing the `recursion_limit` attribute — manifesting as cryptic E0275 errors rather
than a clear diagnostic.  As the macro is shared across all Rust-backend consumers, each new
consumer represents a new exposure point.

**Fix:** Document the overwrite hazard explicitly in the `rs_srcs` arg docstring.  Long-term,
convert `generate_rust_parser` from a macro (def) to a `rule` that returns a custom provider
(e.g. `RustParserSrcsInfo`) and have `fltk_pyo3_cdylib` accept only that provider — giving
Bazel a type-level guarantee and a clear error if the wrong label is passed.
