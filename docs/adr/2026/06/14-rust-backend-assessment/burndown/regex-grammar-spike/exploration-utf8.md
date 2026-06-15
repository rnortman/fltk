# UTF-8 / Unicode Character Model — Exploration

Scope: how FLTK reads grammar files, how the Python and Rust parser runtimes
index into their input, and what that means for the regex-grammar adversarial
test suite.

---

## 1. Grammar-file reading

### Python path

`plumbing.py:54-56` opens the bundled `fegen.fltkg` with `Path.open()` — no
`encoding=` argument.  `genparser.py:42-43` does the same for user-supplied
`.fltkg` files.  `bootstrap.py:493,497` writes generated files the same way.

Python 3's `open()` with no `encoding` argument defaults to
`locale.getpreferredencoding(False)`.  On the development and CI system (Linux
UTF-8 locale) that is `UTF-8`.  On Windows it can be `cp1252` or any other
code page.

Consequence: grammar files are decoded as UTF-8 on Linux/macOS but as
the platform code-page on Windows.  There is no explicit `encoding='utf-8'`
guard at any of the four call sites.  All current `.fltkg` files in the repo
are pure ASCII (confirmed by `file` and byte inspection), so this gap is
currently latent.

### No separate Rust file-reading path

The Rust Rust native parser (`fegen-rust/src/parser.rs`) is a pure in-memory
parser; it accepts a `&str` or `SourceText` at construction
(`parser.rs:57-58`).  File I/O is always done by the Python layer before the
string is handed to Rust.

---

## 2. Position unit: codepoint vs. byte

Both backends explicitly use **Unicode codepoints** as the position unit,
matching Python's native `str` indexing.

### Python runtime (`fltk/fegen/pyrt/terminalsrc.py`)

`TerminalSource.__init__` stores the input as a Python `str`
(`terminalsrc.py:163-165`).

```python
self.terminals: Final = terminals          # Python str (codepoints)
self.terminals_len: Final = len(terminals) # len() counts codepoints
```

`consume_literal` indexes character-by-character:
`self.terminals[pos + i] != literal[i]` (`terminalsrc.py:173`).

`consume_regex` passes the whole `str` plus a codepoint `pos`:
`re.compile(regex).match(self.terminals, pos=pos)` (`terminalsrc.py:178`).
Python `re.match(string, pos=N)` interprets `N` as a codepoint offset.

`Span.start` and `Span.end` (`terminalsrc.py:50-55`) are therefore codepoint
indices.  `Span.text()` returns `self._source[start:end]` — Python string
slicing by codepoints (`terminalsrc.py:67`).

### Rust runtime (`crates/fltk-cst-core/src/span.rs`, `crates/fltk-parser-core/src/terminalsrc.rs`)

The Rust `Span` doc-comment states the design explicitly:

> Half-open **Unicode-codepoint** index range `[start, end)` into a shared
> UTF-8 source string. `start` and `end` are *codepoint* (Unicode character)
> indices, matching Python's string indexing semantics.
> (`span.rs:140-148`)

`TerminalSource::from_source_text` builds a `cp_to_byte` lookup table:
one entry per codepoint, `cp_to_byte[i]` = byte offset of codepoint `i`
(`terminalsrc.rs:58-66`).  All external `pos` values are codepoint indices;
internal methods convert to byte offsets via this table.

`consume_literal` iterates char-by-char after converting `pos` to a byte
offset (`terminalsrc.rs:110-126`).  `consume_regex` passes the full haystack
with `Input::span(byte_pos..text.len())` so that assertions like `\b`/`\B`
see preceding characters; the returned match end is converted back to a
codepoint index via binary search on `cp_to_byte` (`terminalsrc.rs:141-165`).

`Span::text()` in Rust also works by codepoint index: it calls
`src.char_indices()` to translate codepoint `start`/`end` to byte offsets,
then slices the underlying UTF-8 `String` (`span.rs:286-327`).

**Summary:** position units are identical — codepoints — across both backends.
A span `(3, 7)` refers to codepoints 3–6 on both sides.

---

## 3. Regex engine Unicode modes

### Python — `re` module

`re.compile(pattern)` with no flags defaults to `re.UNICODE` (flag value 32).
Verified:

```python
>>> re.compile('[a-z]+').flags
32        # re.UNICODE active, re.ASCII not active
```

This means `\w`, `\d`, `\s`, `\b` etc. match Unicode categories.  `\w`
matches any Unicode letter/digit/underscore.  `\s` matches Unicode whitespace.
Word boundaries `\b`/`\B` are Unicode-word-character boundaries.

The `pos=` keyword to `re.match` is a codepoint offset — verified empirically:
matching `'monde'` in `'café monde'` at `pos=5` (after the 4-codepoint `café`
plus the space) succeeds; at `pos=4` it fails.

### Rust — `regex-automata`

`fltk-parser-core/Cargo.toml:17-25` requests:

```toml
regex-automata = { version = "0.4", default-features = false, features = [
    "std", "syntax", "perf",
    "unicode",           # <- meta-feature
    "meta", "nfa-backtrack", "nfa-pikevm", "hybrid", "dfa-onepass",
] }
```

The `"unicode"` meta-feature in `regex-automata` 0.4 enables the full Unicode
suite: `unicode-age`, `unicode-bool`, `unicode-case`, `unicode-gencat`,
`unicode-perl`, `unicode-script`, `unicode-segment`.  This makes `\w`, `\s`,
`\b` etc. Unicode-aware — identical to Python's default `re.UNICODE` mode.

The Rust parser stores compiled `Regex` objects in `OnceLock`s and calls
`regex_at(idx)` at runtime (`parser.rs:28-33`).  The `Regex::new` call uses
default `regex_automata` settings with the `unicode` feature active —
no flags are set to restrict to ASCII.

---

## 4. Non-ASCII content in grammars

### Current grammar files

All three built-in `.fltkg` files (`fegen.fltkg`, `bootstrap.fltkg`,
`fltk.fltkg`) are pure ASCII.  No non-ASCII bytes appear in any grammar file
currently in the repo.

### Can non-ASCII appear in grammar content?

The grammar format (`fegen.fltkg:17-18`) defines literals and raw-strings with
the patterns:

```
literal    := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/ ;
raw_string := value:/([^\/\n\\]|\\.)+/ ;
```

`[^"\n\\]` is a negated character class.  On Python `re` (Unicode mode), this
matches any Unicode codepoint except `"`, `\n`, and `\`.  On Rust
`regex-automata` (unicode feature active), it behaves identically.  Non-ASCII
literal content like `"café"` or `'αβγ'` is syntactically valid in a `.fltkg`
file under both engines.

The identifier rule (`fegen.fltkg:16`) restricts to `[_a-z][_a-z0-9]*` —
ASCII only.  So rule names, labels, and referenced-rule names cannot contain
non-ASCII characters.  Only literal string values and regex patterns in a
grammar can contain non-ASCII.

### Flow through to generated parsers

When `fltk2gsm.py` extracts a literal value, it calls `span.text()` which
returns a Python `str` slice (`fltk2gsm.py:31-41`).  That string — potentially
containing non-ASCII codepoints — is stored in `gsm.Literal.value` or
`gsm.Regex.value` and then emitted verbatim as a Python string literal via
`iir.LiteralString(term.value)` in `gsm2parser.py:334,350`.

The generated parser's `consume_literal` passes this string directly to
`terminalsrc.consume_literal(literal=...)`, which compares character-by-character
(`terminalsrc.py:173`).  The generated `consume_regex` passes the pattern string
to `re.compile(regex).match(...)` with Unicode mode active.

On the Rust side, the same pattern string would be compiled by `Regex::new`
with `unicode` features; non-ASCII chars in the pattern are valid Unicode.

---

## 5. Differences between Python and Rust backends that affect non-ASCII

The two backends agree on codepoints as the position unit and both run regex
in full-Unicode mode.  However:

**`\w`, `\s` boundary semantics** — Python `re` and `regex-automata` should
agree (both Unicode), but the exact Unicode tables may differ across library
versions and between CPython and Rust `regex-syntax`.  For patterns using
`\w`, `\d`, `\s` with non-ASCII inputs, subtle differences in which codepoints
are classified as word-characters or whitespace are possible.

**Regex features supported** — `regex-automata` does not support lookahead
(`(?=...)`, `(?!...)`, `(?<=...)`, `(?<!...)`) or backreferences.  A grammar
regex using these would compile under Python `re` but panic at startup under
the Rust backend (`parser.rs:1346-1347`):

```rust
if let Err(e) = fltk_parser_core::regex_automata::meta::Regex::new(pat) {
    panic!("grammar regex {pat:?} is not supported ...: {e}")
}
```

**File-reading encoding** — only on non-UTF-8-locale Windows (no `encoding=`
argument at any open() call site); irrelevant on Linux/macOS.

**Literal comparison** — Python `consume_literal` compares Python `str`
characters, so `é` (U+00E9) and `é` (U+0065 U+0301, composed vs. decomposed)
are different codepoint sequences and would not match each other.  Rust
`consume_literal` iterates `char` (scalar values), which is also NFC-unaware.
Neither backend performs Unicode normalization.

---

## 6. Conclusion — what the adversarial suite must probe

The system is fully Unicode-aware at every layer: grammar files decoded as
Unicode strings, positions counted in codepoints, regex in Unicode mode on both
backends.  Non-ASCII content is legal and structurally reachable.

**The adversarial regex test suite must include non-ASCII / UTF-8 cases.**
Specifically:

1. **Multi-byte codepoints in grammar literals**: a grammar rule whose literal
   term contains characters like `é`, `中`, `→`.  Verify span start/end are
   codepoint indices (not byte offsets) on both backends.

2. **Multi-byte codepoints at non-zero offsets**: input with multi-byte
   characters *before* the position under test.  This exercises the
   `cp_to_byte` table in the Rust backend and the `pos=` parameter in Python
   `re.match`.  A off-by-one in codepoint-to-byte conversion would produce
   wrong spans or silent mismatches.

3. **Regex patterns matching non-ASCII input**: patterns like `\w+` matching
   Unicode letters (e.g., `naïve`, `αβγ`).  Both backends claim full Unicode
   `\w`; test that they agree on which codepoints are matched.

4. **Combining marks / NFC vs. NFD**: `é` as precomposed U+00E9 vs. decomposed
   U+0065 U+0301 (two codepoints).  A literal `"é"` (NFD, 2 codepoints) will
   not match input `"é"` (NFC, 1 codepoint) under either backend.  The suite
   should document this and probe that both backends reject consistently (not
   diverge).

5. **Astral-plane codepoints** (codepoint > U+FFFF): e.g., emoji `𝄞` (U+1D11E,
   2 UTF-16 surrogate units but 1 Unicode codepoint).  Python `str` counts
   these as 1 codepoint; Rust `char` also counts them as 1 scalar value.
   `cp_to_byte` maps each to a 4-byte UTF-8 sequence.  A span `(0, 1)` should
   yield the emoji on both backends.

6. **Right-to-left and bidirectional characters**: no parser logic is
   direction-sensitive, but span text extraction with bidirectional text should
   return the raw codepoint slice, not reordered text.

7. **`\s` and whitespace trivia**: Unicode whitespace beyond ASCII space/tab/LF
   (e.g., U+00A0 NO-BREAK SPACE, U+2028 LINE SEPARATOR).  Python `re.UNICODE`
   and `regex-automata` with `unicode` may classify these differently.

The key potential divergence point is item 7 (Unicode category tables) and any
regex feature that `regex-automata` rejects (lookahead, backreferences).  The
rest of the behavior is aligned by design.
