# Efficiency review — rust-bazel-packaging

Commit reviewed: fltk 36eda0d (base fafa6d7), clockwork 45bc7fe (base ece332a).

Scope: This is a build-system / packaging change (Bazel rules + Cargo wiring + a
PyO3 cdylib macro). There is no application runtime hot path here; the relevant
"per-invocation cost" is the Bazel build graph itself (action count, cache
granularity, glob breadth). Findings are framed accordingly.

---

## efficiency-1 — `generate_rust_parser` runs two actions but neither declares a
crate-source-stable output dir; the consuming genrule re-copies on every build

File: `rust.bzl:201-216` (`_assemble_crate` genrule) + `:25-72` (rule impl).

Problem: `generate_rust_parser` emits `cst.rs`/`parser.rs` into `<name>/`, then
`fltk_pyo3_cdylib`'s `_assemble_crate` genrule copies all three files
(`lib.rs` + the two generated) into a *third* directory with `cp` so the bare
`mod cst;`/`mod parser;` resolve. That is one extra full-file copy action per
cdylib on top of the two codegen actions. The copy is pure I/O with no
transformation — it exists only to relocate basenames.

Consequence: per-cdylib build cost is 3 actions where 2 would do; the copy
genrule is an extra cache entry that invalidates whenever *either* lib.rs or the
generated sources change, so editing lib.rs re-runs the copy even though the
generated sources are unchanged (and vice-versa). At Clockwork's scale (one
cdylib) this is negligible; it becomes a paper cut only if many grammars each get
a cdylib. Where it bites: incremental rebuild latency, not clean-build.

Direction: this is largely unavoidable given rustc's same-directory `mod`
resolution (the design §3.4 considered and rejected `#[path=...]`). Worth a
one-line note that the copy is deliberate. Lower-cost alternative: have
`generate_rust_parser` accept the `lib_rs` and emit all three co-located in a
single action's output dir, collapsing assembly into codegen (one fewer action,
and lib.rs edits no longer re-trigger a copy of the generated sources). Optional;
not blocking.

---

## efficiency-2 — `cp $< $@` ABI3-rename genrules copy the whole `.so` instead of
symlinking

File: `rust.bzl:239-244` (`name + "_so"`), `BUILD.bazel:47-54` (`native_so`).

Problem: the abi3 basename rebind is done with `cmd = "cp $< $@"`, a full byte
copy of the compiled shared object. The `.so` for a pyo3 cdylib linking
regex-automata + the CST core can be multiple MB. A `cp` materializes a second
full copy in the output tree on every (re)link.

Consequence: doubled disk footprint for the extension in `bazel-out`, plus the
copy time on every relink of the cdylib (the rename action is downstream of the
link, so any `.rs` change → relink → re-copy). For a multi-MB `.so` this is a
measurable chunk of incremental rebuild I/O and cache upload size on remote
cache. Where it bites: incremental rebuilds and remote-cache bandwidth, per
cdylib + per the FLTK `native` target.

Direction: prefer a symlink rule (e.g. `ln -sf` is unsafe in the sandbox; use a
`copy_file`/`ctx.actions.symlink`-based helper, or rules_rust's own
output-naming if available) so the rename is metadata-only. If `cp` must stay for
sandbox-portability, this is acceptable — but the cost should be a conscious
choice, and `copy_file` from bazel-skylib at least uses an optimized/declared
path over a shell `cp`.

---

## efficiency-3 — `Cargo.lock`-seeded `crate.from_cargo` hub may pull the full
transitive graph of the root manifest, not just the cdylib link set

File: `MODULE.bazel:30-43` (fltk), `crate.from_cargo(... manifests = [root +
two crate manifests])`.

Problem: `from_cargo` resolves every dependency reachable from the listed
manifests. The root `Cargo.toml` historically pulls in the `fltk-native` build
*and* dev/test machinery; the design (§3.1) explicitly wants only
`fltk-cst-core`, `fltk-parser-core`, `fltk-native` + their pyo3/regex-automata
graph, excluding spike + `tests/*` crates. Whether the checked-in `Cargo.lock`
and the three listed manifests actually exclude dev-dependencies of the root is
not verifiable from the diff alone.

Consequence: if dev/test-only crates leak into the `@fltk_crates` hub, every
clean Clockwork build compiles crates it never links — wasted first-build CPU and
a larger crate-universe lock to resolve/fetch. Where it bites: clean-build and CI
cold-cache time (the design's own §4 "build-time cost" caveat); cache is the
mitigation but the wasted compiles still happen once per cache key.

Direction: confirm (at impl/spike time) that the resolved `@fltk_crates` repo
contains only the link-set crates — e.g. inspect the generated
`crate_universe` lock or `bazel query @fltk_crates//...` — and trim the manifest
list or use a dedicated minimal manifest if dev-deps leak. Not provable from the
diff; flagged for validation, consistent with the design's own open items.

---

## Non-findings (checked, clean)

- `src/**/*.rs` glob on the `native` target (`BUILD.bazel:36`) is bounded: `src/`
  holds 4 files, no test sources — no over-broad input pull.
- The two codegen actions in `generate_rust_parser` are genuinely independent and
  Bazel will schedule them concurrently; no missed-parallelism here.
- No polling loops, no per-request state, no unbounded structures in scope.
- `crate_features = ["python"]` / `["extension-module"]` wiring adds no redundant
  recompilation beyond what feature unification requires.
</content>
</invoke>
