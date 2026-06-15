# Exploration: `regex-portability-lint`

**Scope:** Where grammars carry regexes, how each backend uses its regex engine, where
compilation/validation happens today, where a lint could be inserted, and what it would
take to swap either backend's regex engine. Covers both option (a) generation-time lint and
option (b) standardizing both backends on a single regex library/standard.

---

## Code surface

### How grammars carry regexes

Regexes enter the system through the `.fltkg` grammar format. The grammar rule:

```
term :=
  identifier | literal | "/" . regex:raw_string . "/" | "(" , alternatives , ")" ;
```
(`fltk/fegen/fegen.fltkg:13`)

A `raw_string` is the content between the two `/` delimiters:

```
raw_string := value:/([^\/\n\\]|\\.)+/ ;
```
(`fltk/fegen/fegen.fltkg:17`)

`fltk/fegen/fltk2gsm.py:168-170` converts a parsed `RawString` CST node into a `gsm.Regex`
object carrying the raw pattern string:

```python
def visit_regex(self, regex: cst.RawString) -> gsm.Regex:
    span = regex.child_value()
    return gsm.Regex(self._span_text(span))
```

`gsm.Regex` is a frozen dataclass (`fltk/fegen/gsm.py:151-172`) that holds `value: str`. No
validation of the pattern string happens at this stage — the raw text from between the slashes
is stored verbatim.

### Python backend regex engine

The Python runtime's regex execution site is `fltk/fegen/pyrt/terminalsrc.py:177-181`:

```python
def consume_regex(self, pos: int, regex: str) -> Span | None:
    if match := re.compile(regex).match(self.terminals, pos=pos):
        assert match.start() == pos
        return Span(pos, match.end())
    return None
```

This calls `re.compile(regex).match(...)` with the `pos=` argument, which anchors the match
at the given codepoint index without slicing the string (so `\b`/`\B` see the character before
`pos`). The `re` module is Python's built-in PCRE-like engine with its own Unicode database.

The Python parser generator (`fltk/fegen/gsm2parser.py:340-354`) does not validate or
pre-compile regex patterns. It emits a `consume_regex` call carrying the pattern string as a
`LiteralString` IIR node. There is no regex-pattern validation step in the Python generator.
The only implicit validation is `gsm.Regex.can_be_nil()` (`gsm.py:165-172`), which compiles
the pattern with `re.compile` to test for empty-string matches — but this only runs at
grammar-load time and only tests emptiness, not portability.

### Rust backend regex engine

The Rust runtime's regex execution site is
`crates/fltk-parser-core/src/terminalsrc.rs:141-166`:

```rust
pub fn consume_regex(&self, pos: i64, regex: &Regex) -> Option<Span> {
    ...
    let input = Input::new(text)
        .anchored(Anchored::Yes)
        .span(byte_pos..text.len());
    let m = regex.search(&input)?;
    ...
}
```

The `Regex` type is `regex_automata::meta::Regex`. The crate is declared in
`crates/fltk-parser-core/Cargo.toml:17-27`:

```toml
regex-automata = { version = "0.4", default-features = false, features = [
    "std", "syntax", "perf", "unicode", "meta",
    "nfa-backtrack", "nfa-pikevm", "hybrid", "dfa-onepass",
] }
```

`fltk-parser-core/src/lib.rs:23` re-exports `regex_automata` as a pub use so generated parsers
reference `fltk_parser_core::regex_automata::meta::Regex` without a separate direct dependency
(version coherence guarantee documented at `src/lib.rs:7-14`).

The Rust generator (`fltk/fegen/gsm2parser_rs.py`) does not call any Python regex API at
generation time. It inserts pattern strings into a deduplicating table (`_regex_idx`,
`gsm2parser_rs.py:136-141`), then emits those patterns verbatim as string literals in
`REGEX_PATTERNS` (`gsm2parser_rs.py:291-319`). Regex compilation happens at first use via
`OnceLock<Regex>` / `regex_at()` at parser runtime.

### The existing "do all regexes compile" check

`gsm2parser_rs.py:976-996` emits a `#[cfg(test)]` block into every generated parser:

```rust
fn all_regex_patterns_compile() {
    for pat in super::REGEX_PATTERNS.iter() {
        if let Err(e) = fltk_parser_core::regex_automata::meta::Regex::new(pat) {
            panic!("grammar regex {pat:?} is not supported by regex_automata::meta::Regex: {e}");
        }
    }
}
```

This test runs under `cargo test` and catches patterns that `regex-automata` rejects at
compile time (lookahead, lookbehind, backreferences). It does **not** catch patterns that
compile on both engines but produce different match results (POSIX classes, `\p{}`, `\d`/`\w`
Unicode table differences, `(?i)` case-folding differences). The docstring at
`gsm2parser_rs.py:6-15` acknowledges the lookaround restriction but does not mention the
silent-divergence classes.

The referenced ADR `docs/adr/2026/06/10-rust-parser-codegen/README.md:48-60` describes this
as enforcing "the common subset of Python `re` and the Rust `regex` crate," limited to
rejecting lookaround/backreferences. It states the `fancy_regex` crate "is added only if a
concrete need arises."

### Verified divergence: POSIX classes

`docs/adr/2026/06/14-rust-backend-assessment/a2-parity.md:75-122` records a verified
concrete divergence:

- Pattern `[[:alpha:]]`: `regex-automata` matches it as the POSIX alpha class (any letter);
  Python `re` treats `[[:alpha:]]` as a malformed nested set and matches nothing (emits a
  `FutureWarning`). Result: same grammar, same input, opposite parse outcome, no error.
- POSIX classes `[[:digit:]]`, `[[:space:]]`, `[[:alnum:]]` all exhibit this.
- `\p{...}` Unicode property classes and `\d`/`\w` Unicode table differences are also noted
  but not separately confirmed by direct execution in the assessment.

The assessment also notes the hardcoded internal `\s+` trivia pattern was verified to agree
across the two engines for 10 representative whitespace codepoints
(`a2-parity.md:101-104`).

---

## Where a portability lint could be inserted (option a)

### Insertion points

**Option a.1 — at `gsm.Regex` construction** (`fltk/fegen/fltk2gsm.py:168-170`): The
`visit_regex` method creates the `gsm.Regex` object. A lint here would fire for all
downstream consumers of the GSM regardless of which generator is called. The method has
access only to the pattern string; it has no way to know whether the Rust generator will be
used later.

**Option a.2 — at `gsm.Regex` can_be_nil** (`fltk/fegen/gsm.py:165-172`): The existing
emptiness test already calls `re.compile` on the pattern. A portability scan could be added
here. However, this method is called lazily (on demand) and is not guaranteed to run over
all patterns in all code paths.

**Option a.3 — in `RustParserGenerator._regex_idx`** (`fltk/fegen/gsm2parser_rs.py:136-141`):
This is the point where every regex pattern used in the Rust parser is registered. Every
`gsm.Regex` term that reaches the Rust generator calls `_regex_idx` exactly once. This is the
current recommended insertion point named in the assessment
(`recommended-actions.md:107-121`): "Add a generation-time regex-portability lint in
`gsm2parser_rs.py` that rejects non-portable constructs... at generation time with a clear
error."

**Option a.4 — in the generated `all_regex_patterns_compile` test**: Adding a Python-side
lint alongside the existing Rust compile-only check. This would run at `cargo test` time, not
at generation time, and would require shipping Python alongside Rust test infrastructure.

The cleanest single-insertion option is a.3 (`_regex_idx`): it fires once per unique pattern,
only when the Rust generator is running, and `ValueError` from it propagates through
`RustParserGenerator.__init__` → `generate()` to `genparser.py:389`:

```python
except (ValueError, RuntimeError, NotImplementedError) as e:
    typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(1) from e
```

(`fltk/fegen/genparser.py:388-391`)

### What constructs need detection

From the assessment (`a2-parity.md:83-100`):

- POSIX character classes: `[[:alpha:]]`, `[[:digit:]]`, `[[:space:]]`, `[[:alnum:]]`, etc.
  Pattern: `\[\[:[a-z]+:\]\]` inside a character class.
- Unicode property classes: `\p{...}`, `\P{...}`.
- Nested character sets: `[[a-z]&&[^aeiou]]` (intersection/difference syntax).
- Lookahead: `(?=...)`, `(?!...)`.
- Lookbehind: `(?<=...)`, `(?<!...)`.
- Backreferences: `\1`, `\2`, …, `(?P=name)`.

Note: `regex-automata` already rejects lookaround and backreferences at compile time (the
`all_regex_patterns_compile` test catches those). POSIX classes and `\p{}` are the primary
sources of **silent** divergence — they compile on both engines but match differently.

A Python-side lint for POSIX classes can be implemented as a regex on the pattern string:
`re.search(r'\[\[:[a-z]+:\]\]', pattern)`. For `\p{}` a simple `re.search(r'\\[pP]\{', pattern)`
suffices. Nested sets with `&&` or `--` are less common but detectable by static scan.

---

## What it would take to swap either backend's regex engine (option b)

### Swapping the Python backend from `re` to something else

The Python regex execution is isolated to one method:
`fltk/fegen/pyrt/terminalsrc.py:177-181` (`TerminalSource.consume_regex`). Replacing `re`
here would require:

1. Changing the import at `terminalsrc.py:3` from `import re` to another module.
2. Adapting the call at line 178: `re.compile(regex).match(self.terminals, pos=pos)`.
   The `pos=` argument to `.match()` is a Python `re`-specific feature. Most Python regex
   alternatives (`regex` PyPI module, etc.) support the same API. The `regex` PyPI module
   (`python-regex`) is a drop-in replacement for `re` that adds POSIX classes, `\p{}`,
   nested sets, and other features — its API is `re`-compatible including `pos=`.
3. Adding the new dependency to `pyproject.toml:25` (`dependencies = ["astor", "typer"]`).
   Currently the Python regex module is not in `dependencies` at all — `re` is stdlib.

The `regex` PyPI module is not currently installed (confirmed: `python3 -c "import regex"` →
`ModuleNotFoundError`).

The second implicit site where Python compiles regexes is `gsm.Regex._test_regex_empty`
(`gsm.py:165-172`), which calls `re.compile(self.value)` to test empty-match behavior. This
would also need updating.

There are no other `re.compile` / `re.match` / `re.search` calls on grammar-authored pattern
strings in the production path (only tool/generator-internal patterns like `_RUST_IDENT_RE`,
`_IDENTIFIER_RE`, `_CST_MOD_PATH_RE` which are not grammar-user regexes).

### Swapping the Rust backend from `regex-automata` to something else

The Rust regex engine is declared in one place: `crates/fltk-parser-core/Cargo.toml:17-27`.
The `Regex` type from `regex_automata::meta` is used in:

- `crates/fltk-parser-core/src/terminalsrc.rs:8` (`use regex_automata::meta::Regex`) and
  `terminalsrc.rs:141` in `consume_regex`
- `crates/fltk-parser-core/src/lib.rs:23` (`pub use regex_automata`) — the re-export that
  generated parsers depend on

Generated parsers reference `fltk_parser_core::regex_automata::meta::Regex` (e.g.
`crates/fegen-rust/src/parser.rs:4`: `use fltk_parser_core::regex_automata::meta::Regex;`).
Changing the engine would require:

1. Replacing the `regex-automata` dependency in `Cargo.toml` with another crate.
2. Updating `terminalsrc.rs` imports and the `consume_regex` implementation.
3. Updating `lib.rs:23` to re-export the new crate.
4. Updating the `all_regex_patterns_compile` test template in `gsm2parser_rs.py:980-995` to
   call the new crate's compile API.
5. Regenerating all committed generated parsers (`crates/fegen-rust/src/parser.rs`,
   `tests/rust_parser_fixture/src/parser.rs`, `tests/rust_cst_fegen/src/parser.rs`,
   `tests/rust_parser_fixture/src/collision_parser.rs`).

The `Input`/`Anchored` types in `terminalsrc.rs:9` (`use regex_automata::{Anchored, Input}`)
are `regex-automata`-specific — a different engine would need its own anchoring API adapted.

Candidate Rust engines with broader feature sets:
- `fancy_regex` crate: adds lookahead/lookbehind/backreferences on top of `regex`. Already
  considered and deferred in `docs/adr/2026/06/10-rust-parser-codegen/README.md:58-60`.
  Its API is closer to `regex::Regex` than `regex_automata`, so the `TerminalSource`
  implementation would need rewriting.
- `oniguruma` / `onig` crate: Oniguruma C library bindings. Supports POSIX, Unicode
  properties, lookaround. C FFI dependency.
- `pcre2` crate: PCRE2 C library bindings. Closest to Python's `re` feature set. C FFI
  dependency.

### The cross-language standardization question

The STATUS note asks about standardizing Python and Rust on "some regex library/standard
that has identical feature set and semantics across languages." No current cross-language
regex standard with identical behavior across Python and Rust exists as a shipping library.
Candidates:

**PCRE2 (both backends via FFI):**
- Python: `python-pcre2` or `pcre2` PyPI packages.
- Rust: `pcre2` crate.
- Risk: PCRE2 itself has Unicode table versioning differences between releases; "identical"
  semantics requires matching PCRE2 versions.
- Both would be C FFI dependencies.

**`regex-automata` syntax in Python:**
- No Python binding for `regex-automata` exists. The Rust `regex` crate syntax is close to
  but not identical to Python `re`.

**Python `regex` module as the common ground:**
- The PyPI `regex` module supports POSIX classes, `\p{}`, and most of `regex-automata`'s
  Unicode property syntax. It is a Python-only package; Rust cannot use it.
- This narrows the option to: use `regex` PyPI on the Python side and determine what
  `regex`/`regex-automata` syntax subset is actually identical between them. That subset is
  larger than `re` vs `regex-automata` but still not perfectly identical (Unicode DB versions
  could differ between the two crates' embedded tables).

**Restricting to a portable subset (option a refined):**
- If the set of "safe" constructs is documented and enforced at generation time, both engines
  can use their native libraries — the portability constraint is applied to what the grammar
  author is allowed to write, not to the engines themselves. This is the spirit of option (a).

---

## Summary of insertion-point facts

| Option | Where | File | Line | Fires | Catches silent divergences |
|--------|-------|------|------|-------|---------------------------|
| a.3 (recommended) | `_regex_idx` | `gsm2parser_rs.py` | 136-141 | Rust generator only, at gen time | Yes, if lint is implemented |
| a.1 | `visit_regex` | `fltk2gsm.py` | 168-170 | All backends, at parse time | Yes, if lint is implemented |
| a.2 | `Regex.can_be_nil` | `gsm.py` | 165-172 | On demand only | Yes, if lint is implemented |
| existing | `all_regex_patterns_compile` | generated `parser.rs` | `gsm2parser_rs.py:980` | `cargo test` only | No (compile-only check) |

The existing `all_regex_patterns_compile` test is emitted for every generated Rust parser
(confirmed in `crates/fegen-rust/src/parser.rs:1341-1351`,
`tests/rust_parser_fixture/src/parser.rs:1225`, and two other generated files). It is a Rust
`#[cfg(test)]` function; it does not run at generation time and does not catch POSIX class
divergences.

---

## Open factual questions

- Whether the `regex` PyPI module's `\p{}` Unicode table and the `regex-automata` crate's
  embedded Unicode tables are derived from the same source and version — this would determine
  whether option (b) via the PyPI `regex` module achieves genuinely identical semantics or
  merely a larger common subset.
- Which specific `\d`/`\w`/`\s` Unicode codepoints differ between Python `re`, Python
  `regex`, and `regex-automata` at the versions currently in use — the assessment notes the
  divergence exists but does not enumerate the exact codepoints.
