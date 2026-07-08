# Deep error-handling review — step4 (M3 prefix-CST / degraded serving)

Commit reviewed: `1060867` (diff `dcac826..1060867`).

## errhandling-1

- **File:line**: `fltk/lsp/engine.py:177-180`
- **Broken error path**: the inner `except RecursionError` around prefix
  `symbols.extract` + `classify.classify` swallows the recursion event entirely and
  returns the *parse* error (`error`) built from the tail failure. The recursion signal
  is neither logged nor surfaced anywhere.
- **Why**: unlike the outer `except RecursionError` (line 197), which produces a
  distinct, informative message ("Input exceeds the maximum nesting depth the parser can
  handle"), the inner handler replaces the recursion condition with a message about the
  *tail* parse. engine.py has no logger, so nothing records that classification blew the
  stack on a prefix that actually parsed.
- **Consequence**: two structurally different failures — (a) the document has a genuine
  syntax error past the prefix, and (b) the prefix parsed fine but the classifier/symbol
  walk recursed past the limit (i.e. a classifier or grammar-depth bug on well-formed
  input) — become indistinguishable to the CLI, the server diagnostics, and any on-call
  reader. A developer investigating "my valid construct won't highlight" sees only
  "parse error at offset X" and has no signal that the classifier itself hit RecursionError
  on the prefix; there is no trace to point at the classify hot path.
- **What must change**: emit a debug/warning log at the inner catch recording that prefix
  classification overflowed (and, if cheap, that the surfaced error is being substituted).
  Reporting the recursion event does not require changing the returned outcome — the
  degrade-to-parse-error decision can stand — but the event must not vanish silently.

## errhandling-2

- **File:line**: `fltk/lsp/server.py:218`
- **Broken error path**: `boundary = line_index.offset_to_position(analysis.prefix_end or 0, enc)`
  in `_analyze_blocking`. This block runs only when `analysis.tokens is not None and
  analysis.error is not None` — the *partial* outcome, whose documented invariant
  (engine.py `DocumentAnalysis`) is `prefix_end is not None`. The `or 0` silently converts
  a `None` (invariant violation) into boundary `(0, 0)`.
- **Why**: if `prefix_end` were ever `None` in this branch (an engine invariant break), the
  code does not crash or assert — it computes a zero boundary, so `merge_stale_segments`
  keeps the *entire* stale segment list and prepends the fresh prefix segments (which span
  an unknown range). The fresh and stale segments can then overlap.
- **Consequence**: an invariant violation is masked as silently corrupted output rather
  than a loud failure. Overlapping segments fed to `delta_encode_segments` can yield
  negative `deltaStartChar` values — malformed LSP `SemanticTokens.data` — producing
  garbled client-side highlighting with no error logged anywhere. On-call would see only
  "highlighting looks wrong on partial parses," with no crash, log, or diagnostic pointing
  at the broken `prefix_end` contract.
- **What must change**: this is an invariant, not expected-bad-input; assert it
  (`assert analysis.prefix_end is not None`) so a contract break crashes loudly at the
  seam rather than corrupting the wire payload. If a defaulted `0` is genuinely intended
  as tolerated behavior, that intent should be stated; as written it is an unannounced
  swallow of a "can't happen" case.
