#[cfg(any(feature = "python", test))]
/// Derive the user-facing qualified name for a `#[pymodule]`.
///
/// Maturin's default package layout nests the extension module one level
/// deeper than the user-visible package name: a crate named `fegen_rust_cst`
/// produces `fegen_rust_cst/fegen_rust_cst.abi3.so`, so at `#[pymodule]` init
/// time pyo3 reports `__name__ = "fegen_rust_cst.fegen_rust_cst"`.
///
/// If the last two dotted segments of `raw_name` are identical (the maturin
/// double-nested pattern), strip the redundant inner segment so that
/// `sys.modules` keys use the clean package name (`"fegen_rust_cst.cst"` rather
/// than `"fegen_rust_cst.fegen_rust_cst.cst"`).
///
/// For modules whose final two segments differ (e.g. `"fltk._native"`), the
/// raw name is returned unchanged.
///
/// # Limitation
///
/// This heuristic has a false-positive: a genuine three-segment module path
/// `a.b.b` (e.g. a non-maturin build placing an extension at `a/b/b.abi3.so`
/// inside a regular package `b`) is indistinguishable from the maturin
/// double-nesting pattern and would produce the wrong `sys.modules` key
/// `a.b.cst` instead of `a.b.b.cst`. Use
/// [`register_submodule_with_parent_name`] to bypass this heuristic when the
/// caller knows the correct qualified parent name.
pub(crate) fn user_facing_name(raw_name: &str) -> &str {
    // Find the last dot.
    let Some(last_dot) = raw_name.rfind('.') else {
        return raw_name; // no dots — top-level, use as-is
    };
    let leaf = &raw_name[last_dot + 1..];
    let prefix = &raw_name[..last_dot];

    // Check if the segment before the last dot also equals `leaf`.
    let penultimate_leaf = match prefix.rfind('.') {
        Some(i) => &prefix[i + 1..],
        None => prefix, // prefix has no dot: prefix itself is the penultimate segment
    };

    if penultimate_leaf == leaf {
        // Double-nested maturin pattern: strip the redundant inner leaf.
        prefix
    } else {
        raw_name
    }
}

/// Create a named submodule, run the provided registration function, attach it to
/// `parent` via `add_submodule`, and insert it into `sys.modules` under
/// `"{user_facing_parent_name}.{name}"`.
///
/// ## Parameters
///
/// - `parent` — the parent `#[pymodule]` module being initialized.
/// - `name` — the submodule leaf name, e.g. `"cst"` or `"parser"`.
/// - `register` — called with the new submodule; adds classes/functions to it.
///
/// ## Return value
///
/// Returns the newly-created submodule. Callers that do not need it may discard it.
///
/// ## sys.modules key
///
/// The key is `"{user_facing_parent_name}.{name}"`.  `user_facing_parent_name` is
/// derived from `parent.name()?` with the maturin double-nesting stripped when
/// applicable: for `fegen_rust_cst/fegen_rust_cst.abi3.so` (where `parent.name()`
/// is `"fegen_rust_cst.fegen_rust_cst"`), the effective parent name is
/// `"fegen_rust_cst"`, so the submodule is registered as `"fegen_rust_cst.cst"`.
/// For `fltk/_native.abi3.so` (where `parent.name()` is `"fltk._native"`), the
/// effective parent name is `"fltk._native"` unchanged.
///
/// ## Maturin heuristic limitation
///
/// `user_facing_name` cannot distinguish maturin double-nesting (`a.b.b` →
/// `a.b`) from a genuine package path that ends in a repeated segment. If your
/// extension's qualified name ends in a repeated segment but is *not* a maturin
/// double-nested layout, use [`register_submodule_with_parent_name`] and pass
/// the correct parent name explicitly.
///
/// ## Failure behaviour
///
/// `sys.modules` insertion is the final step: if `register` or `add_submodule` fails,
/// no entry is left for this submodule in `sys.modules`. Registration failures are
/// deterministic build bugs, not data-dependent conditions; no cleanup of earlier
/// entries is performed if a later submodule fails.
// TODO(native-submodule-error-context): register_submodule propagates errors from
// register_classes via `?` with no added context naming which submodule failed.
// A future improvement: annotate the error with the submodule name before propagating,
// so an ImportError at module initialization names "cst" or "parser" as the culprit.
#[cfg(feature = "python")]
pub fn register_submodule<'py>(
    parent: &pyo3::Bound<'py, pyo3::types::PyModule>,
    name: &str,
    register: impl FnOnce(&pyo3::Bound<'py, pyo3::types::PyModule>) -> pyo3::PyResult<()>,
) -> pyo3::PyResult<pyo3::Bound<'py, pyo3::types::PyModule>> {
    use pyo3::prelude::*;

    let py = parent.py();
    let raw_parent_name: String = parent
        .name()
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "register_submodule({name:?}): failed to get parent module name: {e}"
            ))
        })?
        .to_string();
    let parent_name = user_facing_name(&raw_parent_name);
    register_submodule_impl(py, parent, name, parent_name, register)
}

/// Create a named submodule with an explicit parent qualified name, bypassing
/// the [`user_facing_name`] heuristic.
///
/// Use this variant when your extension module's `#[pymodule]` name ends in a
/// repeated segment (e.g. `"a.b.b"`) and is *not* a maturin double-nested
/// layout — the heuristic in [`register_submodule`] would incorrectly strip the
/// repeated segment, producing the wrong `sys.modules` key.
///
/// ## Parameters
///
/// - `parent` — the parent `#[pymodule]` module being initialized.
/// - `parent_qualified_name` — the exact qualified name to use for the parent
///   (e.g. `"a.b.b"`); the submodule will be registered as
///   `"{parent_qualified_name}.{name}"`.
/// - `name` — the submodule leaf name, e.g. `"cst"` or `"parser"`.
/// - `register` — called with the new submodule; adds classes/functions to it.
///
/// ## Return value
///
/// Returns the newly-created submodule. Callers that do not need it may discard it.
///
/// ## Failure behaviour
///
/// Same as [`register_submodule`]: `sys.modules` insertion is the final step.
#[cfg(feature = "python")]
pub fn register_submodule_with_parent_name<'py>(
    parent: &pyo3::Bound<'py, pyo3::types::PyModule>,
    parent_qualified_name: &str,
    name: &str,
    register: impl FnOnce(&pyo3::Bound<'py, pyo3::types::PyModule>) -> pyo3::PyResult<()>,
) -> pyo3::PyResult<pyo3::Bound<'py, pyo3::types::PyModule>> {
    let py = parent.py();
    register_submodule_impl(py, parent, name, parent_qualified_name, register)
}

#[cfg(feature = "python")]
fn register_submodule_impl<'py>(
    py: pyo3::Python<'py>,
    parent: &pyo3::Bound<'py, pyo3::types::PyModule>,
    name: &str,
    parent_name: &str,
    register: impl FnOnce(&pyo3::Bound<'py, pyo3::types::PyModule>) -> pyo3::PyResult<()>,
) -> pyo3::PyResult<pyo3::Bound<'py, pyo3::types::PyModule>> {
    use pyo3::prelude::*;

    let qualified_name = format!("{parent_name}.{name}");

    let sub = pyo3::types::PyModule::new(py, name)?;
    register(&sub).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "register_submodule: register fn for submodule {qualified_name:?} failed: {e}"
        ))
    })?;
    parent.add_submodule(&sub).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "register_submodule: add_submodule({qualified_name:?}) failed: {e}"
        ))
    })?;
    sub.setattr("__name__", &qualified_name)?;

    // Insert into sys.modules so `from <parent>.<name> import X` and
    // `importlib.import_module("<parent>.<name>")` work without a separate
    // filesystem import. This must be done after add_submodule succeeds so
    // the parent attribute is consistent with sys.modules.
    py.import("sys")?
        .getattr("modules")?
        .set_item(&qualified_name, &sub)
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "register_submodule: failed to insert {qualified_name:?} into sys.modules: {e}"
            ))
        })?;

    Ok(sub)
}

#[cfg(test)]
mod tests {
    use super::user_facing_name;

    #[test]
    fn double_nested_stripped() {
        // Maturin package layout: strip the redundant inner leaf.
        assert_eq!(user_facing_name("fegen_rust_cst.fegen_rust_cst"), "fegen_rust_cst");
        assert_eq!(
            user_facing_name("phase4_roundtrip_cst.phase4_roundtrip_cst"),
            "phase4_roundtrip_cst"
        );
        assert_eq!(
            user_facing_name("rust_parser_fixture.rust_parser_fixture"),
            "rust_parser_fixture"
        );
    }

    #[test]
    fn different_segments_unchanged() {
        // fltk._native: last two segments differ, keep as-is.
        assert_eq!(user_facing_name("fltk._native"), "fltk._native");
        // Three distinct segments: none stripped.
        assert_eq!(user_facing_name("fltk._native.sub"), "fltk._native.sub");
        assert_eq!(user_facing_name("a.b.c"), "a.b.c");
    }

    #[test]
    fn top_level_unchanged() {
        // No dot: top-level module, return as-is.
        assert_eq!(user_facing_name("mymod"), "mymod");
    }

    #[test]
    fn triple_nested_double_match() {
        // "a.b.b" — last two segments match, strip to "a.b".
        // This is the known heuristic false-positive: a genuine non-maturin
        // layout placing an extension at a.b.b is indistinguishable from a
        // maturin double-nesting. Callers in that situation must use
        // register_submodule_with_parent_name to bypass the heuristic.
        assert_eq!(user_facing_name("a.b.b"), "a.b");
    }
}
