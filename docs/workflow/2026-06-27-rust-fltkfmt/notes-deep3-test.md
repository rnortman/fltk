Commit reviewed: 25cd5dcab7489fc1cb05c6c3e29009a170130d0f

Scope: increments 7-8 — `tests/test_fltkfmt_parity.py` (cross-backend parity) and Makefile gating additions.  `crates/fltk-fmt-cli/src/lib.rs` tests are not in this diff; the `TODO(fltkfmt-integration-tests)` deferred item is not flagged per instructions.

---

test-1: `tests/test_fltkfmt_parity.py:129`

`rust_out = proc.stdout.decode("utf-8")` lacks an error mode, while the stderr decode on the line above uses `'replace'`: `proc.stderr.decode('utf-8', 'replace')`. If the Rust formatter emits non-UTF-8 output (a possible sign of a formatter bug), this line raises a bare `UnicodeDecodeError` — no file name, no config, no comparison context — instead of propagating through the `assert py_out == rust_out` path that carries full context.

Consequence: a non-UTF-8 output bug surfaces as an opaque exception traceback rather than a clear assertion failure naming the corpus file and config.

Fix: `proc.stdout.decode("utf-8", errors="replace")` or `proc.stdout.decode("utf-8", errors="strict")` wrapped in a try/except that re-raises as `AssertionError` with the file/config context string already built for the return-code assertion above.

---

test-2: `tests/test_fltkfmt_parity.py:54-55` (comment on `_CONFIGS`)

The comment reads: "Wide (everything fits flat) and narrow (groups break) so the flat-vs-break decisions are exercised cross-backend, plus the CLI default (width 80 / indent 2)." `(80, 2)` is the first (wide) entry — the phrase "plus the CLI default" implies a third config that does not exist. A future developer reading this to understand coverage could mistakenly believe the CLI default is tested separately from the wide case and wonder why there are only two entries.

Consequence: documentation misleads about the coverage set; no regression risk, but adds confusion for the next person adjusting the corpus or config list.

Fix: remove "plus the CLI default" or rewrite as: "Wide (80/2, which is also the CLI default) and narrow (40/4), so flat-vs-break decisions are exercised cross-backend."
