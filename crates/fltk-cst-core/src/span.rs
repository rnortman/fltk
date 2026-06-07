use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use pyo3::types::PyType;
use std::hash::{Hash, Hasher};
use std::sync::Arc;

/// Cached reference to `fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN`.
/// Fetched once on first `Span.kind` access; avoids a Python import per call.
/// ACYCLICITY: `terminalsrc` must never import `fltk._native` (verified at design time;
/// see design.md §2.2). If that invariant breaks, this import becomes a cycle.
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
#[pyclass(frozen)]
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
}

#[pymethods]
impl SourceText {
    /// Construct a ``SourceText`` from a Python ``str``.
    ///
    /// The string is copied once at this point (Python str → UTF-8 heap allocation).
    #[new]
    fn new(text: &str) -> Self {
        SourceText::from_str(text)
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
#[pyclass(frozen, eq, hash)]
#[derive(Clone)]
pub struct Span {
    pub(crate) start: i64,
    pub(crate) end: i64,
    pub(crate) source: Option<Arc<SourceInner>>,
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
    /// This is usable when caller and callee share the same cdylib (i.e., generated code
    /// inside ``fltk._native`` itself).  For cross-cdylib use (out-of-tree consumer crate
    /// passing the result to ``fltk._native.Span.with_source``), the caller must use an
    /// ``extract_source_text`` helper analogous to ``extract_span`` to bridge the type
    /// registration boundary.
    ///
    /// TODO(span-source-as-py-crosscdylib): wire cross-cdylib ``extract_source_text`` in the
    /// generator preamble so generated code can use this method instead of
    /// ``source_full_text_str`` + full-string reconstruction (efficiency-deep-1).
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
    /// Used by generated accessor code to construct a canonical ``fltk._native.SourceText`` for
    /// cross-cdylib span construction: ``fltk._native.Span.with_source(start, end, SourceText(full))``.
    pub fn source_full_text_str(&self) -> Option<String> {
        self.source.as_ref().map(|arc| arc.text.clone())
    }

    /// Return the end codepoint index (Rust accessor — not a Python getter).
    pub fn end(&self) -> i64 {
        self.end
    }

    /// Returns the shared source for two spans, or an error if they carry different sources.
    fn coerce_source(&self, other: &Span) -> PyResult<Option<Arc<SourceInner>>> {
        match (&self.source, &other.source) {
            (Some(a), Some(b)) if !Arc::ptr_eq(a, b) => Err(PyValueError::new_err(
                "cannot merge spans from different sources",
            )),
            _ => Ok(self.source.clone().or_else(|| other.source.clone())),
        }
    }
}

#[pymethods]
impl Span {
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

    /// Return the source text slice ``[start, end)``, or ``None`` if:
    /// - no source is attached,
    /// - either index is negative,
    /// - ``start > end``,
    /// - ``end`` exceeds the number of Unicode codepoints in the source, or
    /// - ``start`` is greater than the number of codepoints.
    ///
    /// ``start`` and ``end`` are codepoint (Unicode character) indices, matching Python's
    /// string indexing semantics (same as ``source[start:end]`` in Python).
    fn text(&self) -> Option<String> {
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
        // Translate codepoint indices to byte offsets.
        let byte_start = src.char_indices().nth(start).map(|(b, _)| b);
        let byte_end = if end == 0 {
            Some(0)
        } else {
            src.char_indices().nth(end).map(|(b, _)| b).or_else(|| {
                // end == char_count is valid: byte_end = src.len()
                if src.chars().count() == end {
                    Some(src.len())
                } else {
                    None
                }
            })
        };
        match (byte_start, byte_end) {
            (Some(bs), Some(be)) => Some(src[bs..be].to_owned()),
            (None, Some(0)) if start == 0 => Some(String::new()),
            _ => None,
        }
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
        let inner = self.source.as_ref()
            .expect("invariant: source is Some — is_none() guard above returned Err already");
        let start = self.start as usize;
        let end = self.end as usize;
        let src = &inner.text;
        // Translate codepoint indices to byte offsets.
        let byte_start = src.char_indices().nth(start).map(|(b, _)| b);
        let char_count = src.chars().count();
        if end > char_count {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) is out of bounds for source with {} codepoints",
                self.start, self.end, char_count
            )));
        }
        let byte_start = byte_start.ok_or_else(|| {
            PyValueError::new_err(format!(
                "Span({}, {}) start index out of bounds for source with {} codepoints",
                self.start, self.end, char_count
            ))
        })?;
        let byte_end = src.char_indices().nth(end).map(|(b, _)| b).unwrap_or(src.len());
        Ok(src[byte_start..byte_end].to_owned())
    }

    /// Return ``True`` if a source string is attached to this span.
    fn has_source(&self) -> bool {
        self.source.is_some()
    }

    /// Return the span length in codepoints (``end - start``).
    ///
    /// Returns 0 for sentinel/unknown spans with negative indices.
    fn len(&self) -> i64 {
        if self.start < 0 || self.end < 0 {
            return 0;
        }
        (self.end - self.start).max(0)
    }

    /// Return ``True`` if the span covers no bytes (``start >= end``), including sentinel spans.
    fn is_empty(&self) -> bool {
        self.start >= self.end
    }

    /// Return the smallest span that covers both ``self`` and ``other``.
    ///
    /// Raises ``ValueError`` if both spans carry different (non-identical) source references.
    #[pyo3(signature = (other,))]
    fn merge(&self, other: &Span) -> PyResult<Span> {
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
    /// Raises ``ValueError`` if both spans carry different (non-identical) source references.
    #[pyo3(signature = (other,))]
    fn intersect(&self, other: &Span) -> PyResult<Span> {
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
