# ELI5 Assessment: `rust-ident-dedup`

**Item:** `TODO.md` lines 33–35, confirmed `TODO(rust-ident-dedup)` comment at
`fltk/fegen/gsm2lib_rs.py:16`.

---

## What is this actually about?

Two places in the codebase each contain a short hand-written pattern that
describes what a valid Rust name looks like: a letter or underscore, followed
by any number of letters, digits, or underscores.  No exotic cases — just plain
ASCII.

- `gsm2lib_rs.py:19` — `_RUST_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")`  
  Used by `_validate_rust_ident()` to check that module names and registration
  function names are legal Rust identifiers before generating a `lib.rs` file.

- `genparser.py:365` — `_CST_MOD_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*$")`  
  Validates the `--cst-mod-path` CLI argument (e.g. `"super::cst"`) before
  generating a Rust parser file.  The pattern is a single-segment identifier
  optionally repeated with `::` between segments — a Rust module path.

The TODO proposes unifying them: pull the single-segment rule from
`gsm2lib_rs.py` into a shared helper and build the path pattern in
`genparser.py` on top of that helper, rather than having two independent copies
of the same character class.

`genparser.py` already imports `gsm2lib_rs` (line 14), so there is no
import-cycle issue.

---

## Is the duplication real?

Yes, exactly as claimed.  The character classes are **byte-for-byte identical**:
`[A-Za-z_][A-Za-z0-9_]*` in both places.  There is no subtle difference
between them.  Neither regex handles Unicode identifiers (Rust's `XID_Start` /
`XID_Continue` rules, which technically allow non-ASCII), raw identifiers
(`r#keyword`), or leading-digit rejection beyond what `[A-Za-z_]` already
implies.  Both patterns are equivalent, minimal, ASCII-only.

---

## Would consolidating change any behavior?

No.  Because the patterns are character-for-character identical, replacing the
inline copy in `genparser.py`'s `_CST_MOD_PATH_RE` with a reference to
`_validate_rust_ident` from `gsm2lib_rs.py` would not change which strings are
accepted or rejected at either call site.  There is no hidden behavioral
difference to worry about.

---

## What would actually need to happen?

The path regex in `genparser.py` is not a direct call to `_validate_rust_ident`
— it is a composite pattern (one or more `::` -separated segments) compiled
once as a module-level constant.  Consolidating would mean either:

- Re-implementing `_CST_MOD_PATH_RE` in terms of the string form of the
  single-segment pattern (extract `_RUST_IDENT_PAT = r"[A-Za-z_][A-Za-z0-9_]*"`
  from `gsm2lib_rs.py`, import it, build the `_CST_MOD_PATH_RE` from it), or
- Adding a separate `validate_rust_mod_path` function to `gsm2lib_rs.py` and
  calling that from `genparser.py`.

Neither is hard.  It is a few lines of change in two files with no logic shift.

---

## Honest two-sided case

**The case for doing it:**  
A duplicated character class is a maintenance trap.  If the identifier rule ever
needed widening (say, to accept leading `r#` for raw identifiers, or to tighten
ASCII vs. Unicode policy), you would need to update both places and remember
they are coupled.  Having one source of truth is cleaner and the connection is
currently invisible in the code.

**The case against / why it might be cruft:**  
The "problem" is fourteen ASCII characters repeated twice across two files.
These patterns are extremely unlikely to change.  The Rust identifier character
class has been stable since Rust 1.0 for the ASCII subset used here.  Real-world
risk of the two copies diverging is close to zero.  The TODO itself hedges with
"if more gen-* commands need single-segment validation" — a conditional that is
not currently true.  Right now there are exactly two call sites: one in
`gsm2lib_rs.py` and one in `genparser.py`.  The TODO was written prophylactically,
not to fix an actual observed problem.

There is also a mild awkwardness in the proposed fix: `_validate_rust_ident` is
a function that raises an exception, not a string pattern — so constructing the
composite `_CST_MOD_PATH_RE` from it requires first extracting the underlying
pattern string, which means the "shared" part becomes a module-level string
constant rather than the existing function.  That is a slightly different API
surface than the TODO implies.

**Downstream / public-API impact:**  
None.  Both regexes are internal validation guards on CLI arguments.  They do
not appear in generated output, in Python public APIs, or in any contract visible
to downstream consumers.

---

## Bottom line

**Cruft.**  The duplication is real but trivially small, carries near-zero
divergence risk, and the TODO was written as a forward-looking "if we ever need
more of these" note rather than to fix an observed bug.  There is no concrete
harm from leaving the two copies in place.  Doing the cleanup would not be
harmful, but it is not worth the context-switch cost to pick it up unless
someone is already editing one of these two files.  This item should be dropped
from TODO.md.
