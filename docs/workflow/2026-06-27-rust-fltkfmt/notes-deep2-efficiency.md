# Efficiency review — rust-fltkfmt increments 4-6

Commit reviewed: 0718645d66cec435752a28094f0cd7631712b058 (base 762bbced)
Scope: `crates/fltk-fmt-cli/src/lib.rs` (`run_main`/`run_inner`/`write_atomic`/`fully_consumed`/macro) and `crates/fltkfmt/src/main.rs`.

## efficiency-1 — `--in-place` rewrites unchanged files (no-op write)

`crates/fltk-fmt-cli/src/lib.rs:329-334`. The `--in-place` branch calls
`write_atomic(source, &formatted)` unconditionally — even when `formatted == content`.
`write_atomic` always creates a sibling temp file, writes the bytes, and renames it over
the target, so a file that is already correctly formatted still gets fully rewritten and
its mtime bumped on every run.

Consequence: when the formatter is wired into a save-hook, pre-commit, or a tree-wide
invocation (`fltkfmt --in-place **/*.fltkg`), every already-formatted file incurs a
needless temp-create + write + rename, and — more costly downstream — an mtime bump that
re-triggers `make`, file watchers, and incremental-build/CI caches even though nothing
changed. Bites on repeated runs over a stable tree, which is the normal steady state.

Fix: guard the write — `if formatted != content { write_atomic(source, &formatted) }` in
the in-place branch. The design (§3, "`--in-place` on an unchanged file") already names
this as the intended optimization ("skip writing when output == input"); the `content`
value is already in hand, so the change-detection comparison is free (it is already
performed in the `--check` branch a few lines up).

## efficiency-2 — per-file pipeline runs fully serial; files are independent

`crates/fltk-fmt-cli/src/lib.rs:283-344`. `run_inner` processes inputs in a sequential
`for` loop; each iteration does an independent read → parse → unparse → resolve → render.
Nothing is shared across iterations (each file builds its own `Parser`/`Unparser`/`Doc`).

The design (§3, "Concurrency / Send") justifies "no threading" by noting
`fltk_unparser_core::Doc` uses `Rc` internally. That argument only forbids sharing one
`Doc` across threads; it does not forbid running each *file's* pipeline on its own thread,
where the `Rc` stays thread-local. So cross-file parallelism is available and the stated
rationale does not actually rule it out.

Consequence: `fltkfmt --check` in CI or formatting/checking a large corpus scales linearly
with file count on a single core; available cores sit idle. Bites whenever the input set
is more than a handful of files — the common batch/CI use.

Fix direction: parallelize across files (e.g. a worker pool), each worker owning its own
parser/unparser, then collect results. For stdout (default) mode, buffer per-file output
and emit in input order to preserve the gofmt-style concatenation contract; `--check` and
`--in-place` are order-independent. Note this requires `format_fn: Fn + Send + Sync` and
contradicts the design's explicit "No threading is introduced" decision, so it is a
deliberate-tradeoff call, not a clear defect — flagged because the design's justification
for serial is weaker than it appears.

## Not flagged (considered)

- `fully_consumed` (lib.rs:74-79) does `src.chars().skip(pos).all(...)`, which walks the
  char prefix `[0,pos)` to advance the iterator before scanning the suffix. This is O(n),
  but it is one pass per file, dominated by the parse (already O(n)+) and the file read;
  no cheaper correct option exists without a byte-index from the parser. Not worth changing.
- `display` String allocation per file (lib.rs:287-291) is used as the parser filename /
  error prefix; once per file, negligible.
- Whole-file `read_to_string` is required (formatting needs the full input); not overly broad.
