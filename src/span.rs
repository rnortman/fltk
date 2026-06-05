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
pub(crate) struct SourceInner {
    text: String,
}

/// Opaque handle to a shared source string, exposed to Python as ``fltk._native.SourceText``.
///
/// Constructing a ``SourceText`` from Python copies the string once (Python str → UTF-8).
/// All ``Span`` objects created from the same ``SourceText`` share the underlying allocation
/// via ``Arc``; cloning a span is a reference-count increment, not a string copy.
#[pyclass(frozen)]
pub struct SourceText {
    pub(crate) inner: Arc<SourceInner>,
}

#[pymethods]
impl SourceText {
    /// Construct a ``SourceText`` from a Python ``str``.
    ///
    /// The string is copied once at this point (Python str → UTF-8 heap allocation).
    #[new]
    fn new(text: &str) -> Self {
        SourceText {
            inner: Arc::new(SourceInner {
                text: text.to_owned(),
            }),
        }
    }
}

/// Half-open byte-index range ``[start, end)`` into a shared UTF-8 source string.
///
/// Exposed to Python as ``fltk._native.Span``.  24 bytes on 64-bit platforms
/// (two ``i64`` fields + one 8-byte ``Arc`` pointer).
///
/// **Index semantics:** ``start`` and ``end`` are *byte* offsets into the UTF-8
/// text held by the attached ``SourceText``.  They are intentionally not exposed
/// as Python attributes — all text access goes through ``text()`` / ``text_or_raise()``.
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
    /// ``start`` and ``end`` are byte offsets.
    /// Calling ``text()`` on a sourceless span returns ``None``.
    #[new]
    #[pyo3(signature = (start, end))]
    fn new(start: i64, end: i64) -> Self {
        Span {
            start,
            end,
            source: None,
        }
    }

    /// Construct a source-bearing span ``[start, end)`` tied to ``source``.
    #[classmethod]
    #[pyo3(signature = (start, end, source))]
    fn with_source(_cls: &Bound<'_, PyType>, start: i64, end: i64, source: &SourceText) -> Self {
        Span {
            start,
            end,
            source: Some(source.inner.clone()),
        }
    }

    /// Return the source text slice ``[start, end)``, or ``None`` if:
    /// - no source is attached,
    /// - either index is negative,
    /// - ``start > end``,
    /// - ``end`` exceeds the source length, or
    /// - either index does not land on a UTF-8 character boundary.
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
        if end > src.len() {
            return None;
        }
        if !src.is_char_boundary(start) || !src.is_char_boundary(end) {
            return None;
        }
        Some(src[start..end].to_owned())
    }

    /// Return the source text slice ``[start, end)``, raising ``ValueError`` if
    /// the text cannot be returned (same conditions as ``text()``).
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
        let inner = self.source.as_ref().unwrap();
        let start = self.start as usize;
        let end = self.end as usize;
        let src = &inner.text;
        if end > src.len() {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) is out of bounds for source of length {}",
                self.start,
                self.end,
                src.len()
            )));
        }
        if !src.is_char_boundary(start) || !src.is_char_boundary(end) {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) does not land on UTF-8 character boundaries",
                self.start, self.end
            )));
        }
        Ok(src[start..end].to_owned())
    }

    /// Return ``True`` if a source string is attached to this span.
    fn has_source(&self) -> bool {
        self.source.is_some()
    }

    /// Return the span length in bytes (``end - start``).
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
            return Ok(Span {
                start: -1,
                end: -1,
                source: None,
            });
        }
        Ok(Span {
            start: s,
            end: e,
            source,
        })
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
                Ok(py
                    .import("fltk.fegen.pyrt.terminalsrc")?
                    .getattr("SpanKind")?
                    .getattr("SPAN")?
                    .unbind())
            })
            .map(|obj| obj.clone_ref(py))
    }
}
