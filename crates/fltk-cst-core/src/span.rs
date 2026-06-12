#[cfg(feature = "python")]
use crate::cross_cdylib::{extract_source_text, FLTK_CST_CORE_ABI};
#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::impl_::pycell::PyClassObject;
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::sync::GILOnceCell;
#[cfg(feature = "python")]
use pyo3::types::PyType;
use std::fmt;
use std::hash::{Hash, Hasher};
use std::sync::Arc;

/// Error type for native Span operations that can fail (e.g., merge/intersect across sources).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum SpanError {
    /// The two spans carry different (non-identical) source references.
    SourceMismatch,
}

impl fmt::Display for SpanError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SpanError::SourceMismatch => write!(f, "cannot merge spans from different sources"),
        }
    }
}

impl std::error::Error for SpanError {}

/// Cached reference to `fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN`.
/// Fetched once on first `Span.kind` access; avoids a Python import per call.
/// ACYCLICITY: `terminalsrc` must never import `fltk._native` (verified at design time;
/// see design.md §2.2). If that invariant breaks, this import becomes a cycle.
#[cfg(feature = "python")]
static SPAN_KIND_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new();

/// Shared heap allocation holding source text.
///
/// Thin-pointer wrapper so that `Option<Arc<SourceInner>>` is 8 bytes
/// (vs 16 bytes for the fat pointer `Arc<str>`), keeping `Span` at 24 bytes.
/// The indirection also leaves room for future cached metadata (e.g. line-offset
/// tables) without changing the `Span` struct layout.
pub struct SourceInner {
    pub(crate) text: String,
}

/// Opaque handle to a shared source string, exposed to Python as ``fltk._native.SourceText``.
///
/// Constructing a ``SourceText`` from Python copies the string once (Python str → UTF-8).
/// All ``Span`` objects created from the same ``SourceText`` share the underlying allocation
/// via ``Arc``; cloning a span is a reference-count increment, not a string copy.
#[cfg_attr(feature = "python", pyclass(frozen))]
pub struct SourceText {
    pub inner: Arc<SourceInner>,
}

impl SourceText {
    /// Construct a ``SourceText`` from a Rust ``&str``.
    ///
    /// The string is copied once at this point (→ UTF-8 heap allocation).
    #[allow(clippy::should_implement_trait)] // Intentional: not `FromStr`; construction from &str is the natural API name.
    pub fn from_str(text: &str) -> Self {
        SourceText {
            inner: Arc::new(SourceInner {
                text: text.to_owned(),
            }),
        }
    }

    /// Borrow the underlying source text as a ``&str``.
    ///
    /// The returned reference is valid for the lifetime of this ``SourceText``.
    pub fn text(&self) -> &str {
        &self.inner.text
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl SourceText {
    /// Construct a ``SourceText`` from a Python ``str``.
    ///
    /// The string is copied once at this point (Python str → UTF-8 heap allocation).
    #[new]
    fn new(text: &str) -> Self {
        SourceText::from_str(text)
    }

    /// ABI marker: ``"fltk-cst-core/<version>"`` baked into the rlib at compile time.
    ///
    /// Every cdylib linking the same ``fltk-cst-core`` rlib with the same Cargo.toml
    /// version exposes this identical string on its locally-registered ``SourceText`` type.
    /// ``extract_source_text`` (``cross_cdylib.rs``) reads this classattr to gate
    /// ``downcast_unchecked`` across the cdylib boundary without relying on type-object
    /// identity (which is not available in the canonical→consumer direction; see design §2.1).
    ///
    /// The marker is a plain string (debuggable, mismatch message trivially constructible).
    /// It is deliberately *not* a PyCapsule: anything readable from Python is replayable,
    /// so a capsule adds API surface without removing the pure-Python-reachable UB path.
    #[classattr]
    fn _fltk_cst_core_abi() -> &'static str {
        FLTK_CST_CORE_ABI
    }

    /// Layout probe: ``size_of::<PyClassObject<SourceText>>()`` baked at compile time.
    ///
    /// Compared numerically (not by string equality) by ``extract_source_text``
    /// (``cross_cdylib.rs``) alongside ``_fltk_cst_core_abi``. A pyo3 version bump that
    /// changes ``PyClassObject`` layout will typically produce a different integer here,
    /// so a layout mismatch fails with ``TypeError`` instead of proceeding to
    /// ``downcast_unchecked`` UB.
    ///
    /// **Limitation**: size equality is necessary but not sufficient for layout identity —
    /// a pyo3 build that reorders internal fields while preserving total size passes the
    /// probe. The check narrows — not closes — the layout-skew window. Accepted risk: for
    /// frozen pyo3 types without dict/weakref, ``PyClassObject<T>`` reduces to
    /// ``{ffi::PyObject, T}`` (repr(C)); a size-preserving internal reorder is not
    /// constructible without changing ``ffi::PyObject`` itself, which changes the size.
    ///
    /// ``PyClassObject<T>`` is a pyo3 internal type; its layout is intentionally NOT
    /// stable across pyo3 minor versions — that instability is exactly what this probe
    /// is designed to detect.
    #[classattr]
    fn _fltk_cst_core_abi_layout() -> usize {
        std::mem::size_of::<PyClassObject<SourceText>>()
    }
}

/// Half-open **Unicode-codepoint** index range ``[start, end)`` into a shared UTF-8 source string.
///
/// Exposed to Python as ``fltk._native.Span``.  24 bytes on 64-bit platforms
/// (two ``i64`` fields + one 8-byte ``Arc`` pointer).
///
/// **Index semantics:** ``start`` and ``end`` are *codepoint* (Unicode character) indices,
/// matching Python's string indexing semantics.  ``text()`` / ``text_or_raise()`` translate
/// these to byte offsets internally.  This ensures spans produced by the Python-based
/// ``TerminalSource`` parser are interpreted identically on both Python and Rust backends.
///
/// **Equality and hashing** use only ``(start, end)``; the source reference is
/// excluded so that a sourceless sentinel compares equal to a source-bearing span
/// at the same position.
///
/// **Frozen:** assignment to any attribute raises ``AttributeError`` from Python.
#[cfg_attr(feature = "python", pyclass(frozen, eq, hash))]
#[derive(Clone)]
pub struct Span {
    pub(crate) start: i64,
    pub(crate) end: i64,
    pub(crate) source: Option<Arc<SourceInner>>,
}

impl fmt::Debug for Span {
    /// Format as `Span { start: <start>, end: <end>, has_source: <bool> }`.
    ///
    /// Source text is deliberately elided — it can be the entire input file.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Span")
            .field("start", &self.start)
            .field("end", &self.end)
            .field("has_source", &self.source.is_some())
            .finish()
    }
}

impl PartialEq for Span {
    fn eq(&self, other: &Self) -> bool {
        self.start == other.start && self.end == other.end
    }
}

impl Eq for Span {}

impl Hash for Span {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.start.hash(state);
        self.end.hash(state);
    }
}

impl Span {
    /// Sentinel "unknown span" with ``start = -1``, ``end = -1``, no source.
    ///
    /// This is the default span for nodes constructed without an explicit span.
    /// Value-equal to the Python-side ``UnknownSpan`` sentinel.
    pub fn unknown() -> Self {
        Span {
            start: -1,
            end: -1,
            source: None,
        }
    }

    /// Construct a sourceless span ``[start, end)``.
    ///
    /// ``start`` and ``end`` are codepoint (Unicode character) indices.
    /// ``text()`` on a sourceless span returns ``None``.
    pub fn new_sourceless(start: i64, end: i64) -> Self {
        Span {
            start,
            end,
            source: None,
        }
    }

    /// Construct a source-bearing span ``[start, end)`` tied to ``source``.
    ///
    /// ``start`` and ``end`` are codepoint (Unicode character) indices into ``source``'s text.
    pub fn new_with_source(start: i64, end: i64, source: &SourceText) -> Self {
        Span {
            start,
            end,
            source: Some(source.inner.clone()),
        }
    }

    /// Return the start codepoint index (Rust accessor — not a Python getter).
    pub fn start(&self) -> i64 {
        self.start
    }

    /// Extract the source as a ``SourceText`` Python object sharing the same ``Arc``, or
    /// ``None`` if sourceless.  Clones only the reference count (O(1)).
    ///
    /// Returns a ``SourceText`` registered with the *current* cdylib's type system.
    /// For cross-cdylib use (out-of-tree consumer crate building a ``fltk._native.Span``),
    /// pass the result to ``Span::_with_source_unchecked`` via ``span_to_pyobject``
    /// (``cross_cdylib.rs``), which accepts the locally-registered ``SourceText`` via the
    /// ABI-marker check in ``extract_source_text``.
    #[cfg(feature = "python")]
    pub fn source_as_py(&self, py: Python<'_>) -> PyResult<Option<Py<SourceText>>> {
        match &self.source {
            Some(arc) => Ok(Some(Py::new(
                py,
                SourceText {
                    inner: arc.clone(),
                },
            )?)),
            None => Ok(None),
        }
    }

    /// Return the full source text (the entire input string, not just the span slice), or ``None``
    /// if the span has no source attached.
    ///
    /// Retained for compatibility with previously-generated consumer ``cst.rs`` files that still
    /// call ``source_full_text_str()`` + ``get_source_text_type(py)?.call1(full_text)``.
    /// New generated code uses ``span_to_pyobject`` (``cross_cdylib.rs``) instead, which
    /// preserves Arc-sharing in O(1).
    pub fn source_full_text_str(&self) -> Option<String> {
        self.source.as_ref().map(|arc| arc.text.clone())
    }

    /// Return the end codepoint index (Rust accessor — not a Python getter).
    pub fn end(&self) -> i64 {
        self.end
    }

    /// Returns the shared source for two spans, or an error if they carry different sources.
    fn coerce_source(&self, other: &Span) -> Result<Option<Arc<SourceInner>>, SpanError> {
        match (&self.source, &other.source) {
            (Some(a), Some(b)) if !Arc::ptr_eq(a, b) => Err(SpanError::SourceMismatch),
            _ => Ok(self.source.clone().or_else(|| other.source.clone())),
        }
    }

    /// Return the source text slice ``[start, end)``, or ``None`` if:
    /// - no source is attached,
    /// - either index is negative,
    /// - ``start > end``,
    /// - ``end`` exceeds the number of Unicode codepoints in the source, or
    /// - ``start`` is greater than the number of codepoints.
    ///
    /// ``start`` and ``end`` are codepoint (Unicode character) indices, matching Python's
    /// string indexing semantics (same as ``source[start:end]`` in Python).
    pub fn text(&self) -> Option<String> {
        let inner = self.source.as_ref()?;
        if self.start < 0 || self.end < 0 {
            return None;
        }
        let start = self.start as usize;
        let end = self.end as usize;
        if start > end {
            return None;
        }
        let src = &inner.text;
        // Single forward pass: scan char_indices once to collect both byte offsets.
        // We need the byte offset of codepoint `start` (byte_start) and of codepoint
        // `end` (byte_end, where end == char_count means byte_end = src.len()).
        // The previous two-restart implementation rescanned from byte 0 for each index
        // and did a third O(src.len()) scan for the end-of-source case.
        let mut byte_start: Option<usize> = None;
        let mut byte_end: Option<usize> = None;
        let mut char_count = 0usize;
        for (byte_idx, _) in src.char_indices() {
            if char_count == start {
                byte_start = Some(byte_idx);
            }
            if char_count == end {
                byte_end = Some(byte_idx);
                break;
            }
            char_count += 1;
        }
        // Handle end == char_count (valid: slice to end of string).
        if byte_end.is_none() && char_count == end {
            byte_end = Some(src.len());
        }
        // Handle start == 0 on an empty source string (char_count stays 0, byte_start not set).
        if byte_start.is_none() && start == 0 && end == 0 {
            return Some(String::new());
        }
        match (byte_start, byte_end) {
            (Some(bs), Some(be)) => Some(src[bs..be].to_owned()),
            _ => None,
        }
    }

    /// Return ``True`` if a source string is attached to this span.
    pub fn has_source(&self) -> bool {
        self.source.is_some()
    }

    /// Return the span length in codepoints (``end - start``).
    ///
    /// Returns 0 for sentinel/unknown spans with negative indices.
    pub fn len(&self) -> i64 {
        if self.start < 0 || self.end < 0 {
            return 0;
        }
        (self.end - self.start).max(0)
    }

    /// Return ``True`` if the span covers no bytes (``start >= end``), including sentinel spans.
    pub fn is_empty(&self) -> bool {
        self.start >= self.end
    }

    /// Return the smallest span that covers both ``self`` and ``other``.
    ///
    /// Returns ``Err(SpanError::SourceMismatch)`` if both spans carry different (non-identical)
    /// source references.
    pub fn merge(&self, other: &Span) -> Result<Span, SpanError> {
        let source = self.coerce_source(other)?;
        Ok(Span {
            start: self.start.min(other.start),
            end: self.end.max(other.end),
            source,
        })
    }

    /// Return the overlapping region of ``self`` and ``other``, or the ``UnknownSpan`` sentinel
    /// (``Span(-1, -1)``) if they are disjoint.
    ///
    /// Returns ``Err(SpanError::SourceMismatch)`` if both spans carry different (non-identical)
    /// source references.
    pub fn intersect(&self, other: &Span) -> Result<Span, SpanError> {
        let source = self.coerce_source(other)?;
        let s = self.start.max(other.start);
        let e = self.end.min(other.end);
        if s >= e {
            return Ok(Span::unknown());
        }
        Ok(Span {
            start: s,
            end: e,
            source,
        })
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl Span {
    /// ABI marker for ``Span``: identical value to ``SourceText._fltk_cst_core_abi``.
    ///
    /// Checked once in ``get_span_type``'s ``GILOnceCell`` init (``cross_cdylib.rs``) so that
    /// version skew on the ``Span`` path fails with a clear ``TypeError`` naming both ABI
    /// strings instead of proceeding to ``downcast_unchecked`` UB in ``extract_span``.
    #[classattr]
    fn _fltk_cst_core_abi() -> &'static str {
        FLTK_CST_CORE_ABI
    }

    /// Layout probe for ``Span``: ``size_of::<PyClassObject<Span>>()`` baked at compile time.
    ///
    /// Checked numerically alongside ``_fltk_cst_core_abi`` in ``get_span_type``'s init.
    /// A pyo3 version bump that changes ``PyClassObject`` layout will typically produce a
    /// different integer here, catching pyo3-resolution skew that the version string alone
    /// cannot detect.
    ///
    /// **Limitation**: size equality is necessary but not sufficient for layout identity —
    /// a pyo3 build that reorders internal fields while preserving total size passes the
    /// probe. The check narrows — not closes — the layout-skew window. Accepted risk: for
    /// frozen pyo3 types without dict/weakref, ``PyClassObject<T>`` reduces to
    /// ``{ffi::PyObject, T}`` (repr(C)); a size-preserving internal reorder is not
    /// constructible without changing ``ffi::PyObject`` itself, which changes the size.
    #[classattr]
    fn _fltk_cst_core_abi_layout() -> usize {
        std::mem::size_of::<PyClassObject<Span>>()
    }

    /// Construct a sourceless span ``[start, end)``.
    ///
    /// ``start`` and ``end`` are codepoint (Unicode character) indices.
    /// Calling ``text()`` on a sourceless span returns ``None``.
    #[new]
    #[pyo3(signature = (start, end))]
    fn py_new(start: i64, end: i64) -> Self {
        Span::new_sourceless(start, end)
    }

    /// Construct a source-bearing span ``[start, end)`` tied to ``source``.
    ///
    /// ``start`` and ``end`` are codepoint (Unicode character) indices.
    #[classmethod]
    #[pyo3(signature = (start, end, source))]
    fn with_source(_cls: &Bound<'_, PyType>, start: i64, end: i64, source: &SourceText) -> Self {
        Span::new_with_source(start, end, source)
    }

    /// Private cross-cdylib constructor (generated-code use only): like ``with_source``,
    /// but accepts a ``SourceText`` registered by another fltk-cst-core-linking cdylib.
    ///
    /// "unchecked" = bypasses pyo3's registry-based type check; an ABI-marker check in
    /// ``extract_source_text`` still gates the cast (see ``cross_cdylib.rs``).
    ///
    /// Passing a forged-marker object (a Python class with ``_fltk_cst_core_abi`` set to the
    /// expected string but a mismatched memory layout) is **Undefined Behavior**. This is
    /// out-of-contract: this method is private by convention (leading underscore) and is
    /// intended to be called only by ``span_to_pyobject`` (``cross_cdylib.rs``) passing
    /// the result of ``source_as_py``, which always produces a genuine ``SourceText``.
    #[classmethod]
    #[pyo3(signature = (start, end, source))]
    fn _with_source_unchecked(
        _cls: &Bound<'_, PyType>,
        start: i64,
        end: i64,
        source: &Bound<'_, PyAny>,
    ) -> PyResult<Span> {
        Ok(Span::new_with_source(start, end, &extract_source_text(source)?))
    }

    /// Return the source text slice ``[start, end)``, or ``None`` — delegates to ``Span::text``.
    ///
    /// Python-visible wrapper preserving the original name via the native implementation.
    #[pyo3(name = "text")]
    fn py_text(&self) -> Option<String> {
        self.text()
    }

    /// Return the source text slice ``[start, end)``, raising ``ValueError`` if
    /// the text cannot be returned (same conditions as ``text()``).
    ///
    /// ``start`` and ``end`` are codepoint (Unicode character) indices.
    fn text_or_raise(&self) -> PyResult<String> {
        if self.source.is_none() {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) has no source",
                self.start, self.end
            )));
        }
        if self.start < 0 || self.end < 0 {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) has negative indices",
                self.start, self.end
            )));
        }
        if self.start > self.end {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) has inverted range",
                self.start, self.end
            )));
        }
        // Validate end <= char_count before delegating, to emit a specific OOB message.
        let inner = self.source.as_ref()
            .expect("invariant: source is Some — is_none() guard above returned Err already");
        let end = self.end as usize;
        let char_count = inner.text.chars().count();
        if end > char_count {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) is out of bounds for source with {} codepoints",
                self.start, self.end, char_count
            )));
        }
        // Pre-conditions confirmed; delegate to native text() which handles byte-offset translation.
        self.text().ok_or_else(|| {
            PyValueError::new_err(format!(
                "Span({}, {}) start index out of bounds for source with {} codepoints",
                self.start, self.end, char_count
            ))
        })
    }

    /// Return ``True`` if a source string is attached to this span.
    #[pyo3(name = "has_source")]
    fn py_has_source(&self) -> bool {
        self.has_source()
    }

    /// Return the span length in codepoints (``end - start``).
    ///
    /// Returns 0 for sentinel/unknown spans with negative indices.
    #[pyo3(name = "len")]
    fn py_len(&self) -> i64 {
        self.len()
    }

    /// Return ``True`` if the span covers no bytes (``start >= end``), including sentinel spans.
    #[pyo3(name = "is_empty")]
    fn py_is_empty(&self) -> bool {
        self.is_empty()
    }

    /// Return the smallest span that covers both ``self`` and ``other``.
    ///
    /// Raises ``ValueError`` if both spans carry different (non-identical) source references.
    #[pyo3(name = "merge", signature = (other,))]
    fn py_merge(&self, other: &Span) -> PyResult<Span> {
        self.merge(other)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Return the overlapping region of ``self`` and ``other``, or the ``UnknownSpan`` sentinel
    /// (``Span(-1, -1)``) if they are disjoint.
    ///
    /// Raises ``ValueError`` if both spans carry different (non-identical) source references.
    #[pyo3(name = "intersect", signature = (other,))]
    fn py_intersect(&self, other: &Span) -> PyResult<Span> {
        self.intersect(other)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Return the start codepoint index as a Python integer.
    ///
    /// Exposed for drop-in parity with ``fltk.fegen.pyrt.terminalsrc.Span.start``
    /// (the pure-Python span exposes ``start`` as a plain attribute; hasattr/getattr
    /// checks against child spans must find it on both backends).
    #[getter]
    fn get_start(&self) -> i64 {
        self.start
    }

    /// Return the end codepoint index as a Python integer.
    ///
    /// Exposed for drop-in parity with ``fltk.fegen.pyrt.terminalsrc.Span.end``.
    #[getter]
    fn get_end(&self) -> i64 {
        self.end
    }

    /// Return ``"Span(start=<start>, end=<end>)"`` — raw indices for debugging; source is not shown.
    fn __repr__(&self) -> String {
        format!("Span(start={}, end={})", self.start, self.end)
    }

    /// Return the shared Python ``SpanKind.SPAN`` discriminant from
    /// ``fltk.fegen.pyrt.terminalsrc``.
    ///
    /// Returns the *same* Python object as the pure-Python ``terminalsrc.Span.kind`` field,
    /// so identity holds and equality is trivially satisfied.  Uses a ``GILOnceCell`` cache
    /// to avoid a Python attribute lookup on every call.
    #[getter]
    fn kind(&self, py: Python<'_>) -> PyResult<PyObject> {
        SPAN_KIND_SPAN_CACHE
            .get_or_try_init(py, || -> PyResult<PyObject> {
                py.import("fltk.fegen.pyrt.terminalsrc")
                    .and_then(|m| m.getattr("SpanKind"))
                    .and_then(|sk| sk.getattr("SPAN"))
                    .map(|obj| obj.unbind())
                    .map_err(|e| {
                        PyValueError::new_err(format!(
                            "Span.kind: failed to load SpanKind.SPAN from \
                            fltk.fegen.pyrt.terminalsrc: {e}"
                        ))
                    })
            })
            .map(|obj| obj.clone_ref(py))
    }
}
