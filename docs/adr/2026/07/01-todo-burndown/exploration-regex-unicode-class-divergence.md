# Exploration: `TODO(regex-unicode-class-divergence)`

Facts and source ground truth only. No prescriptions.

## 1. TODO.md entry (verbatim ground truth)

`TODO.md:46-48`:

```
## `regex-unicode-class-divergence`

The regex portability lint admits `\d`/`\w`/`\s` (and negations), `\b`/`\B` word
boundaries, and `(?i)` as ASCII-portable constructs. However, these constructs have a
non-ASCII semantic residual: the Unicode-class tables and case-folding tables differ
between Python `re` and `regex-automata` by Unicode DB version. A grammar using these
constructs with non-ASCII input may get different parse results on the two backends
without any error. This is documented as a permanent limit of any static approach (both
engines agree on syntax but differ on semantics for non-ASCII). Tracking here to ensure
the `document-scope-boundary` burndown item covers the full ledger: `\d`/`\D`/`\w`/`\W`/
`\s`/`\S`, `\b`/`\B`, and `(?i)` over non-ASCII. Location: `fltk/fegen/regex_portability.py`
(module-level docstring), `fltk/fegen/regex.fltkg` (comments on `class_shorthand`,
`assertion`, `anchor_escape`, `flag_chars`).
```

## 2. Code-level `TODO(slug)` markers found

Repo-wide grep for the literal string `TODO(regex-unicode-class-divergence)` returns
exactly **one** hit:

- `fltk/fegen/regex_portability.py:29` — `TODO(regex-unicode-class-divergence): track the
  full non-ASCII residual ledger.` (inside the module docstring, lines 1-30).

`fltk/fegen/regex.fltkg` contains **no** `TODO(regex-unicode-class-divergence)` marker
anywhere, despite TODO.md's "Location:" line naming it as a second location. It has
descriptive prose comments (see §3) but none carry the `TODO(slug)` tag.

## 3. Is the non-ASCII residual already documented at the cited locations?

### `fltk/fegen/regex_portability.py` module docstring (lines 22-29)

```
Documented limits (constructs admitted by syntax but with a non-ASCII semantic
residual):
  \d/\w/\s and their negations -- Unicode-class tables differ by engine DB.
  (?i) case-folding over non-ASCII -- fold tables differ by engine DB version.
  \b/\B word boundaries -- defined in terms of \w, same residual.
These are admitted as ASCII-portable; the divergence is documented-only and cannot
be caught by a static syntax checker (any static approach shares this limit).
TODO(regex-unicode-class-divergence): track the full non-ASCII residual ledger.
```

This explicitly names `\d`/`\w`/`\s` (+ negations), `(?i)`, and `\b`/`\B` — i.e. the full
ledger the TODO asks to be covered, modulo shorthand (`\d` implying `\D` too, etc.,
matching the TODO's own informal phrasing).

### `fltk/fegen/regex.fltkg` — production-by-production

- `class_shorthand` (line 273): `// \d \D \w \W \s \S -- ASCII-portable; non-ASCII
  semantic residual documented (section 6).` — covers `\d\D\w\W\s\S`.
- `assertion` (lines 275-276): `// \b \B word boundaries -- ASCII-portable; defined in
  terms of \w, same residual. // Top-level only: inside a class these are non-portable
  (see class_escape).` — covers `\b`/`\B`.
- `inline_flags` (lines 146-147): `// Standalone inline flag toggle, e.g. (?i), (?ms).
  Portable as ASCII syntax; the non-ASCII (?i) semantic residual is documented-only
  (design.md section 6).` — covers `(?i)`.
- `flag_chars` (line 159, comment at 150-158): the comment at this production is about
  the deliberate exclusion of the `x` (verbose) flag; it does **not** mention the
  non-ASCII residual. The `(?i)` residual comment TODO.md attributes to `flag_chars` is
  actually on `inline_flags`, a different (adjacent) production.
- `anchor_escape` (lines 279-287): comment covers `\A`/`\z`/`\Z` cross-engine
  syntax-acceptance divergence (Python rejects `\z`/`Rust rejects `\Z`, etc.) — an
  unrelated, ASCII-only syntax-divergence topic. It does **not** mention the non-ASCII
  semantic-residual ledger (Unicode-class tables / case-folding). `anchor_escape` is not
  a location where the residual is documented.

So of the four `regex.fltkg` locations TODO.md names (`class_shorthand`, `assertion`,
`anchor_escape`, `flag_chars`): two (`class_shorthand`, `assertion`) do carry the
residual documentation; `anchor_escape` does not (it documents a different, unrelated
divergence); the `(?i)` residual comment lives on `inline_flags`, not `flag_chars` as
named.

## 4. Status of the `document-scope-boundary` burndown item this TODO defers to

`document-scope-boundary` is **done** and on `main` (ancestor of current HEAD `8fd5ecf`
via `git merge-base --is-ancestor`), landed as two squashed commits:

- `61df5ff` — "document-scope-boundary: record user decision (versions->0.2.0, neutral
  pin guidance)"
- `e813764` — "document-scope-boundary: standardize shipping versions on 0.2.0; neutral
  consumer-guide pin"

`e813764`'s commit message states verbatim: *"The obsolete scope-boundary docs
(no-unparser/regex/INLINE) were intentionally not added."* Its diff (`Cargo.lock`,
`Cargo.toml`, `docs/rust-cst-extension-guide.md`, `pyproject.toml`, `uv.lock`, plus
ADR working-doc artifacts) contains no changes to `regex_portability.py`, `regex.fltkg`,
or any regex-scope-boundary prose.

`docs/adr/2026/06/14-rust-backend-assessment/recommended-actions.md:169-178`'s
`document-scope-boundary` item description (the spec this fast-track item implemented
against) lists three things to document as explicit called-out decisions: the Rust
backend is parse+CST only (no unparser), "the regex subset is a **permanent semantic
boundary**", and INLINE disposition/Invocation terms being unsupported on both backends
— plus the version-skew reconciliation. Only the version-skew reconciliation was
actually done in `e813764`; the regex/unparser/INLINE scope-boundary prose was
explicitly declined as "obsolete."

## 5. Chronological ordering (why `document-scope-boundary` called the regex doc "obsolete")

`git log --oneline main` order (newest first) places these commits as:

```
dba6a4b  regex-portability-lint: fail codegen on non-portable regexes in grammars   (newer)
e813764  document-scope-boundary: standardize shipping versions on 0.2.0; ...
61df5ff  document-scope-boundary: record user decision ...                          (older)
```

So `document-scope-boundary` (`61df5ff`/`e813764`) was completed *before*
`regex-portability-lint` (`dba6a4b`) landed. `dba6a4b` is the commit that:

- Added `fltk/fegen/regex_portability.py` and its module docstring (§3 above).
- Added the `regex.fltkg` comments cited in §3.
- Added the `TODO(regex-unicode-class-divergence)` entry to `TODO.md` and the matching
  `TODO(slug)` code comment (`git show dba6a4b -- TODO.md` shows the addition of this
  exact TODO.md block).

So the same commit that created this TODO (asking future work to make sure
`document-scope-boundary` covers the ledger) also directly added the ledger
documentation at the module-docstring/grammar-comment level — the thing
`document-scope-boundary` had already (chronologically earlier) declined to do at the
consumer-guide level, calling it obsolete.

## 6. Is there any other `document-scope-boundary` remnant elsewhere?

`grep -rn "document-scope-boundary"` across the repo returns only:
- `TODO.md:48` (this TODO's own prose reference).
- The `docs/adr/2026/06/14-rust-backend-assessment/` ADR tree (design/judge/handoff/
  recommended-actions working documents and the `burndown/document-scope-boundary/`
  review-artifact directory, all dated 2026-06-14, pre-dating and used during the
  now-squashed implementation).

No other TODO.md entry, code comment, or doc references `document-scope-boundary` as an
open/pending item outside this historical ADR tree.
