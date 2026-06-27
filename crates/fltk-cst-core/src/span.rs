#[cfg(feature = "python")]
use crate::cross_cdylib::{extract_source_text, FLTK_CST_CORE_ABI};
#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::sync::PyOnceLock;
#[cfg(feature = "python")]
use pyo3::types::PyType;
use std::fmt;
use std::hash::{Hash, Hasher};
use std::sync::{Arc, OnceLock};

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
static SPAN_KIND_SPAN_CACHE: PyOnceLock<Py<PyAny>> = PyOnceLock::new();

/// Shared heap allocation holding source text.
///
/// Thin-pointer wrapper so that `Option<Arc<SourceInner>>` is 8 bytes
/// (vs 16 bytes for the fat pointer `Arc<str>`), keeping `Span` at 24 bytes.
/// The indirection also leaves room for future cached metadata (e.g. line-offset
/// tables) without changing the `Span` struct layout.
pub struct SourceInner {
    pub(crate) text: String,
    /// Optional filename associated with this source (e.g. ``"foo.fltkg"``).
    /// Stored once at construction; never interpreted by the runtime.
    pub(crate) filename: Option<String>,
    /// Lazy codepoint count of `text`.  Populated on first `line_col()` call
    /// (together with `line_ends`) so that warm-cache domain checks are O(1).
    pub(crate) char_count: OnceLock<i64>,
    /// Lazy codepoint indices of `\n` chars plus a final sentinel.
    /// Built on first `line_col()` call; shared across all spans over this `Arc`.
    /// TODO(linecol-cache-consolidate): TerminalSource also maintains its own
    /// `line_ends` over the same immutable text — two independent caches over
    /// identical data. A future consolidation could have TerminalSource read
    /// source_inner.line_ends instead of maintaining its own field. Out of scope
    /// for the span-line-col-api change.
    pub(crate) line_ends: OnceLock<Vec<i64>>,
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
    /// Construct a ``SourceText`` from a Rust ``&str`` with an optional filename.
    ///
    /// The string is copied once at this point (→ UTF-8 heap allocation).
    #[allow(clippy::should_implement_trait)] // Intentional: not `FromStr`; construction from &str is the natural API name.
    pub fn from_str(text: &str, filename: Option<&str>) -> Self {
        SourceText {
            inner: Arc::new(SourceInner {
                text: text.to_owned(),
                filename: filename.map(|s| s.to_owned()),
                char_count: OnceLock::new(),
                line_ends: OnceLock::new(),
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
    /// Construct a ``SourceText`` from a Python ``str`` with an optional filename.
    ///
    /// The string is copied once at this point (Python str → UTF-8 heap allocation).
    #[new]
    #[pyo3(signature = (text, filename = None))]
    fn new(text: &str, filename: Option<&str>) -> Self {
        SourceText::from_str(text, filename)
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

    /// Layout probe: ``size_of::<<SourceText as pyo3::impl_::pyclass::PyClassImpl>::Layout>()``
    /// baked at compile time.
    ///
    /// Compared numerically (not by string equality) by ``extract_source_text``
    /// (``cross_cdylib.rs``) alongside ``_fltk_cst_core_abi``. A pyo3 version bump that
    /// changes the allocation layout will typically produce a different integer here,
    /// so a layout mismatch fails with ``TypeError`` instead of proceeding to
    /// ``cast_unchecked`` UB.
    ///
    /// **Limitation**: size equality is necessary but not sufficient for layout identity —
    /// a pyo3 build that reorders internal fields while preserving total size passes the
    /// probe. The check narrows — not closes — the layout-skew window. Accepted risk: for
    /// frozen pyo3 types without dict/weakref, ``PyClassImpl::Layout`` (``PyStaticClassObject<T>``)
    /// reduces to ``{ffi::PyObject, T}`` (repr(C)); a size-preserving internal reorder is not
    /// constructible without changing ``ffi::PyObject`` itself, which changes the size.
    ///
    /// ``PyClassImpl::Layout`` is a pyo3 internal type; its layout is intentionally NOT
    /// stable across pyo3 minor versions — that instability is exactly what this probe
    /// is designed to detect.
    #[classattr]
    fn _fltk_cst_core_abi_layout() -> usize {
        source_text_abi_layout_probe()
    }
}

/// Returns the ABI layout probe value for `SourceText` — exposed `pub(crate)` so that
/// `lib.rs` tests can assert the classattr body delegates to this, not a hardcoded stub.
#[cfg(feature = "python")]
pub(crate) fn source_text_abi_layout_probe() -> usize {
    std::mem::size_of::<<SourceText as pyo3::impl_::pyclass::PyClassImpl>::Layout>()
}

/// Line-and-column position within a source text.
///
/// Mirrors `LineColPos` in `terminalsrc.py` and the former `LineColPos` in
/// `fltk-parser-core/src/terminalsrc.rs` (now moved here so both `fltk-cst-core`
/// and `fltk-parser-core` share a single definition).
///
/// `line` and `col` are 0-based codepoint indices.
/// `line_span` covers the entire line (exclusive of the trailing `\n`).
/// `line_span` is source-bearing when returned from `Span::line_col_inner`;
/// equality is source-ignoring (``Span`` equality omits the source reference).
#[cfg_attr(feature = "python", pyclass(frozen, eq, skip_from_py_object))]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LineColPos {
    pub line: i64,
    pub col: i64,
    pub line_span: Span,
}

#[cfg(feature = "python")]
#[pymethods]
impl LineColPos {
    /// 0-based line index.
    #[getter]
    fn line(&self) -> i64 {
        self.line
    }

    /// 0-based column index (codepoint offset within the line).
    #[getter]
    fn col(&self) -> i64 {
        self.col
    }

    /// The span covering the entire offending line (exclusive of the trailing `\n`).
    ///
    /// Returns an owned clone — the source `Arc` pointer count is bumped (O(1), no string copy).
    #[getter]
    fn line_span(&self) -> Span {
        self.line_span.clone()
    }

    fn __repr__(&self) -> String {
        format!("LineColPos(line={}, col={}, line_span=Span(start={}, end={}))",
            self.line, self.col, self.line_span.start, self.line_span.end)
    }
}

/// Shared bisect function: compute line and column for a codepoint position within `text`.
///
/// **Preconditions** (caller is responsible):
/// - `pos >= -1`: `pos = -1` is accepted and produces `LineColPos(line=0, col=-1)`.
///   This is the intended path for: (a) empty text after the EOF clamp
///   (`start == len == 0 → pos = start - 1 = -1`), and (b) the `ErrorTracker.longest_parse_len`
///   initial sentinel on non-empty text (passed through by `TerminalSource::pos_to_line_col`
///   because the `pos < -1` guard only rejects values below -1).
///   Values `pos < -1` are not meaningful and will produce incorrect results.
/// - `pos < text.chars().count()` after any EOF clamp (i.e., the caller must decrement
///   `start == len` to `len - 1` before calling; the value `len` itself is not accepted).
///
/// The `line_ends` cache is built lazily on first call and reused thereafter.
/// It stores codepoint indices of `\n` characters plus a final sentinel equal to `len`
/// (exclusive end of the last line) for non-empty text without a trailing `\n`, or `-1`
/// for empty input (preserving the `col = -1` corner case documented in §3 of the design).
///
/// Returns a `LineColPos` with a **sourceless** `line_span`; callers that need a source-bearing
/// `line_span` (e.g. `Span::line_col_inner`) must attach the source themselves after calling.
pub fn resolve_line_col(text: &str, pos: i64, line_ends: &OnceLock<Vec<i64>>) -> Option<LineColPos> {
    let ends = line_ends.get_or_init(|| {
        // Compute len only inside get_or_init so warm-cache calls skip this O(N) scan.
        let len = text.chars().count() as i64;
        let mut ends: Vec<i64> = text
            .chars()
            .enumerate()
            .filter(|(_, c)| *c == '\n')
            .map(|(cp_idx, _)| cp_idx as i64)
            .collect();
        // Add sentinel for the final line if the text doesn't end with '\n' (or is empty).
        //
        // The sentinel is the exclusive end of the last line's span:
        // - Normal text without trailing '\n': sentinel = `len` so that
        //   `Span(line_start, len)` covers all characters including the last one.
        // - Empty text (len=0): sentinel = -1, which makes `pos=-1` (from the EOF clamp)
        //   land in the sentinel entry and yield `col=-1` — the inherited corner case
        //   documented in the design (§3 "empty-source note").
        let ends_with_newline = ends.last() == Some(&(len - 1));
        if !ends_with_newline {
            // For non-empty text: push `len` (exclusive end past last char).
            // For empty text (len=0): push `-1` to preserve the col=-1 corner case.
            ends.push(if len > 0 { len } else { -1 });
        }
        ends
    });

    // bisect_left equivalent: find leftmost index where ends[idx] >= pos.
    let idx = ends.partition_point(|&e| e < pos);
    if idx >= ends.len() {
        return None;
    }

    let (col, line_start, line_end) = if idx > 0 {
        let col = pos - ends[idx - 1] - 1;
        let line_start = ends[idx - 1] + 1;
        let line_end = ends[idx];
        (col, line_start, line_end)
    } else {
        let col = pos;
        let line_end = ends[0];
        (col, 0i64, line_end)
    };

    Some(LineColPos {
        line: idx as i64,
        col,
        line_span: Span::new_sourceless(line_start, line_end),
    })
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
#[cfg_attr(feature = "python", pyclass(frozen, eq, hash, from_py_object))]
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
        self.text_str().map(str::to_owned)
    }

    /// Return the source text slice ``[start, end)`` as a borrowed ``&str``, or ``None`` under
    /// the same conditions as [`text`](Self::text).
    ///
    /// This is the allocation-free analogue of [`text`](Self::text) (which is implemented in terms
    /// of it): the returned reference borrows directly from the attached source rather than copying
    /// into an owned `String`. Use it where the slice is only inspected and immediately dropped
    /// (e.g. counting newlines in inter-token trivia); use [`text`](Self::text) where an owned
    /// `String` is retained. The reference borrows from `&self`, which holds the source `Arc` alive.
    pub fn text_str(&self) -> Option<&str> {
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
            return Some("");
        }
        match (byte_start, byte_end) {
            (Some(bs), Some(be)) => Some(&src[bs..be]),
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

    /// Return the line/column position for the span's start, or ``None`` if the span
    /// is sourceless, has a negative start, or has a start beyond the source length.
    ///
    /// Applies the following guards before delegating to `resolve_line_col`:
    /// - No source attached → `None`.
    /// - `start < 0` → `None` (negative-index sentinels).
    /// - `start > len(source)` → `None` (out of domain).
    /// - `start == len(source)` → EOF clamp: position decremented to `len - 1`.
    ///
    /// The returned `LineColPos.line_span` is **source-bearing** (shares the same `Arc`).
    pub fn line_col_inner(&self) -> Option<LineColPos> {
        let source = self.source.as_ref()?;
        if self.start < 0 {
            return None;
        }
        // Obtain the source codepoint length via the `char_count` OnceLock so that
        // warm-cache calls (after the first `line_col()`) are O(1) rather than O(N).
        // `char_count` is populated together with `line_ends` on the first call to
        // `line_col_inner` or `line_col_or_raise`.
        let len = *source.char_count.get_or_init(|| source.text.chars().count() as i64);
        if self.start > len {
            return None;
        }
        // EOF clamp: pos == len is valid; decrement to len-1.
        let pos = if self.start == len { self.start - 1 } else { self.start };
        let mut lc = resolve_line_col(&source.text, pos, &source.line_ends)?;
        // Attach source to the line_span (resolve_line_col returns a sourceless line_span).
        lc.line_span = Span {
            start: lc.line_span.start,
            end: lc.line_span.end,
            source: Some(source.clone()),
        };
        Some(lc)
    }

    /// Return the optional filename associated with this span's source.
    ///
    /// Returns ``None`` when the span is sourceless or the source has no filename.
    pub fn filename_inner(&self) -> Option<&str> {
        self.source.as_ref()?.filename.as_deref()
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl Span {
    /// ABI marker for ``Span``: identical value to ``SourceText._fltk_cst_core_abi``.
    ///
    /// Checked once in ``get_span_type``'s ``PyOnceLock`` init (``cross_cdylib.rs``) so that
    /// version skew on the ``Span`` path fails with a clear ``TypeError`` naming both ABI
    /// strings instead of proceeding to ``cast_unchecked`` UB in ``extract_span``.
    #[classattr]
    fn _fltk_cst_core_abi() -> &'static str {
        FLTK_CST_CORE_ABI
    }

    /// Layout probe for ``Span``: ``size_of::<<Span as pyo3::impl_::pyclass::PyClassImpl>::Layout>()``
    /// baked at compile time.
    ///
    /// Checked numerically alongside ``_fltk_cst_core_abi`` in ``get_span_type``'s init.
    /// A pyo3 version bump that changes the allocation layout will typically produce a
    /// different integer here, catching pyo3-resolution skew that the version string alone
    /// cannot detect.
    ///
    /// **Limitation**: size equality is necessary but not sufficient for layout identity —
    /// a pyo3 build that reorders internal fields while preserving total size passes the
    /// probe. The check narrows — not closes — the layout-skew window. Accepted risk: for
    /// frozen pyo3 types without dict/weakref, ``PyClassImpl::Layout`` (``PyStaticClassObject<T>``)
    /// reduces to ``{ffi::PyObject, T}`` (repr(C)); a size-preserving internal reorder is not
    /// constructible without changing ``ffi::PyObject`` itself, which changes the size.
    #[classattr]
    fn _fltk_cst_core_abi_layout() -> usize {
        span_abi_layout_probe()
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
    /// "unchecked" = bypasses pyo3's registry-based type check; ``extract_source_text``
    /// (``cross_cdylib.rs``) gates the cast via two checks:
    ///   1. ABI-marker pair (``_fltk_cst_core_abi`` string + ``_fltk_cst_core_abi_layout``
    ///      attribute) — version-skew diagnostic.
    ///   2. Layout-genuineness gate: first rejects types with a custom metaclass (which could
    ///      shadow ``__basicsize__`` via a metaclass property), then reads ``__basicsize__``
    ///      via the immutable built-in ``type.__basicsize__`` descriptor (unforgeable once the
    ///      metaclass is confirmed to be exactly ``type``).
    ///
    /// A pure-Python object that fails either gate raises ``TypeError``; it does **not** cause
    /// Undefined Behavior.  The Python backend's equivalent (``terminalsrc.with_source``) raises
    /// ``TypeError`` for non-``SourceText`` input; this method now matches that contract for
    /// the most common forgery patterns (trivial copies, metaclass-property overrides).
    ///
    /// **Residual (documented, not closed)**: a ``__slots__``-padded forge whose
    /// ``tp_basicsize`` exactly matches the expected value passes both gates and reaches
    /// ``cast_unchecked`` — still UB.  This residual is identical in kind to the one
    /// accepted and documented throughout ``cross_cdylib.rs``.  This method is private by
    /// convention (leading underscore) and is intended to be called only by
    /// ``span_to_pyobject`` (``cross_cdylib.rs``) passing the result of ``source_as_py``,
    /// which always produces a genuine ``SourceText``.
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
    /// so identity holds and equality is trivially satisfied.  Uses a ``PyOnceLock`` cache
    /// to avoid a Python attribute lookup on every call.
    #[getter]
    fn kind(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        SPAN_KIND_SPAN_CACHE
            .get_or_try_init(py, || -> PyResult<Py<PyAny>> {
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

    /// Return the line/column position for the span's start, or ``None``.
    ///
    /// Returns ``None`` when the span is sourceless, has a negative start, or has a
    /// start that exceeds the source length. Delegates to `line_col_inner`.
    #[pyo3(name = "line_col")]
    fn py_line_col(&self, py: Python<'_>) -> PyResult<Option<Py<LineColPos>>> {
        match self.line_col_inner() {
            Some(lc) => Ok(Some(Py::new(py, lc)?)),
            None => Ok(None),
        }
    }

    /// Return the line/column position for the span's start, raising ``ValueError`` if
    /// it cannot be resolved (same conditions as ``line_col()``).
    fn line_col_or_raise(&self, py: Python<'_>) -> PyResult<Py<LineColPos>> {
        if self.source.is_none() {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) has no source",
                self.start, self.end
            )));
        }
        if self.start < 0 {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) has negative indices",
                self.start, self.end
            )));
        }
        let source = self.source.as_ref()
            .expect("invariant: source is Some — is_none() guard above returned Err already");
        // Use the char_count cache for O(1) warm-call domain checks.
        let len = *source.char_count.get_or_init(|| source.text.chars().count() as i64);
        if self.start > len {
            return Err(PyValueError::new_err(format!(
                "Span({}, {}) is out of bounds for source of length {}",
                self.start, self.end, len
            )));
        }
        match self.line_col_inner() {
            Some(lc) => Py::new(py, lc),
            None => Err(PyValueError::new_err(format!(
                "Span({}, {}) line_col_inner returned None despite passing all guards — \
                internal invariant violation; start={}, source_len={}",
                self.start, self.end, self.start, len
            ))),
        }
    }

    /// Return the optional filename associated with this span's source, or ``None``.
    #[pyo3(name = "filename")]
    fn py_filename(&self) -> Option<String> {
        self.source.as_ref()?.filename.clone()
    }
}

/// Returns the ABI layout probe value for `Span` — exposed `pub(crate)` so that
/// `lib.rs` tests can assert the classattr body delegates to this, not a hardcoded stub.
#[cfg(feature = "python")]
pub(crate) fn span_abi_layout_probe() -> usize {
    std::mem::size_of::<<Span as pyo3::impl_::pyclass::PyClassImpl>::Layout>()
}

#[cfg(test)]
mod text_str_tests {
    use super::*;

    #[test]
    fn text_str_matches_text_for_ascii() {
        let src = SourceText::from_str("hello world", None);
        let span = Span::new_with_source(0, 5, &src);
        assert_eq!(span.text_str(), Some("hello"));
        // text() is now defined in terms of text_str(): same content, owned.
        assert_eq!(span.text(), Some("hello".to_owned()));
    }

    #[test]
    fn text_str_uses_codepoint_indices_for_multibyte() {
        // "héllo": 'é' is two UTF-8 bytes, so a codepoint slice [0,2) ("hé") differs from a byte
        // slice [0,2) ("h" + a partial 'é'); this confirms text_str uses codepoint indexing.
        let src = SourceText::from_str("héllo", None);
        let span = Span::new_with_source(0, 2, &src);
        assert_eq!(span.text_str(), Some("hé"));
        assert_eq!(span.text(), Some("hé".to_owned()));
    }

    #[test]
    fn text_str_slices_to_end_of_source() {
        let src = SourceText::from_str("abc", None);
        let span = Span::new_with_source(1, 3, &src);
        assert_eq!(span.text_str(), Some("bc"));
    }

    #[test]
    fn text_str_empty_span_on_empty_source() {
        let src = SourceText::from_str("", None);
        let span = Span::new_with_source(0, 0, &src);
        assert_eq!(span.text_str(), Some(""));
    }

    #[test]
    fn text_str_none_for_sourceless_span() {
        let span = Span::new_sourceless(0, 3);
        assert_eq!(span.text_str(), None);
        assert_eq!(span.text(), None);
    }

    #[test]
    fn text_str_counts_newlines_without_allocating() {
        let src = SourceText::from_str(" \n\n ", None);
        let span = Span::new_with_source(0, 4, &src);
        let count = span.text_str().map(|t| t.matches('\n').count()).unwrap_or(0);
        assert_eq!(count, 2);
    }
}
