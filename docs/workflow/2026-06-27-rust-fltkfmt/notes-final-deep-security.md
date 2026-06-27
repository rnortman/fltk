# Security review — rust-fltkfmt (final deep)

Commit reviewed: f89c80930a8799aaf476077b572fea449e3024d2 (base 6f975ebf)
Scope: full feature diff, excluding the EDTC workflow records under
`docs/workflow/2026-06-27-rust-fltkfmt/`. `TODO(fltkfmt-integration-tests)` treated as
accepted deferral, not flagged.

## Trust model

`fltkfmt` is a local CLI run with the invoking user's privileges. The runtime trust
boundary is the **content of the `.fltkg` file being formatted** (potentially attacker-
supplied), which flows: file → `read_to_string` → generated Rust parser → CST →
generated unparser → Doc → renderer → stdout / `--output` / in-place rewrite. File
*paths* are operator-supplied (trusted). The grammar/format-spec inputs to the code
generator (`fegen.fltkg`, `fegen.fltkfmt`) are build-time developer inputs, not a runtime
boundary. No network, deserialization, auth, secret, or SSRF surface exists in this
change.

Overall the change is defensively written: untrusted-content DoS via deep nesting is
bounded by the parser `depth_exceeded()` check (`crates/fltk-fmt-cli/src/lib.rs:298`),
the atomic in-place write uses `create_new`/`O_EXCL` to defeat symlink-/collision-based
overwrite (CWE-59/377/367), and flag-combination validation is thorough. The subprocess
calls in `tests/test_fltkfmt_parity.py` use literal argv (no shell), no injection.

## Findings

### security-1 — in-place temp may keep world-readable mode if `set_permissions` fails

- File: `crates/fltk-fmt-cli/src/lib.rs:186-197` (`write_atomic`, via `create_temp`).
- Issue: the temp file is created through `fs::OpenOptions::new().write(true)
  .create_new(true)` with no explicit Unix mode, so it lands at the process default
  (`0666 & ~umask`, typically `0644` — world-readable). The original file's mode is then
  copied onto it with `let _ = fs::set_permissions(&tmp, meta.permissions());` — whose
  result is intentionally discarded — *before* the content is written. On the normal path
  this is safe (content is written after the narrowing). But if `set_permissions` fails,
  the failure is swallowed and `write_all` then writes the formatted content into a
  temp that is still `0644`, which is renamed over the target.
- Trust boundary / data flow: the asset is the *content* of a grammar file the operator
  deliberately kept private (mode `0600`) and formats with `--in-place`. The exposure
  requires a local same-host actor with traverse/read access to the file's directory.
- Consequence: a private (`0600`) `.fltkg` file's contents can be silently widened to
  world-readable after an in-place format if the permission-copy step fails — i.e. the
  failure mode errs toward *more* permissive, leaking file contents to other local users.
  Likelihood is low (`set_permissions` on a just-created, process-owned file rarely
  fails), so this is a minor hardening gap, not a likely live leak.
- Suggested fix: create the temp restrictively from the start and only widen afterward,
  so any failure errs private rather than public — on Unix, set
  `OpenOptions::mode(0o600)` (via `std::os::unix::fs::OpenOptionsExt`) at creation in
  `create_temp`, then let the existing `set_permissions` widen to the source's mode. That
  inverts the failure direction (a failed widen leaves the temp at `0600`, never `0644`).

## No other findings

- Temp creation: `create_new` (`O_EXCL`) + unpredictable suffix (pid + atomic counter +
  subsec-nanos) + bounded retry correctly prevents symlink-follow and existing-file
  truncation as an arbitrary-overwrite primitive.
- `--in-place` on a symlink replaces the link with a regular file (rename targets the
  path, not the link destination); the link target is not modified — acceptable, standard
  formatter behavior, operator-named path.
- Untrusted-content handling: recursion is depth-bounded; `fully_consumed` correctly
  guards negative/char-vs-byte positions; partial parse and unparser-`None` map to errors,
  not panics.
- Code generator (`fltk/unparse/gsm2unparser_rs.py`): emits Rust at build time from
  trusted grammar inputs; no runtime trust boundary, and any mis-escaped literal would
  fail compilation (caught by `make check`), not produce a runtime exploit.
- No hardcoded secrets in the diff (Cargo.lock hashes are normal).
