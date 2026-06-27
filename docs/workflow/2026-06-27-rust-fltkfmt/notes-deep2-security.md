# Security review — rust-fltkfmt increments 4-6

Commit reviewed: 0718645d66cec435752a28094f0cd7631712b058 (base 762bbced)
Scope: `crates/fltk-fmt-cli/src/lib.rs`, `crates/fltkfmt/src/main.rs`, Cargo manifests.

This is a local developer CLI that formats `.fltkg` grammar files. No network, DB,
command execution, deserialization, or auth surface is introduced. Inputs are files/stdin
the invoking user names. The only trust-boundary issue is the in-place write path.

## security-1 — Predictable temp-file name + `File::create` enables symlink/TOCTOU overwrite

File: `crates/fltk-fmt-cli/src/lib.rs:120-150` (temp name built at :129-133, opened at :136)

The issue: `write_atomic` (the `--in-place` path) builds its temp file name from the
target file name plus only the process id:
`.{file_name}.fltkfmt.tmp.{std::process::id()}`, in the *same directory as the target*,
then opens it with `fs::File::create(&tmp)`. `File::create` opens with create-or-truncate
semantics and **follows symlinks**; the name is fully predictable (PID space is small and
guessable, and the rest is derived from the public target path). It does not use
`create_new`/`O_EXCL` and does not use a random suffix.

Trust boundary / data flow: the attacker is another local user (or any process) able to
write to the directory containing the file the victim formats — e.g. a shared or
world/group-writable directory, a checkout under `/tmp`, a CI workspace, a group project
dir. The victim runs `fltkfmt --in-place <dir>/grammar.fltkg`. The temp path is derived
entirely from data the attacker can observe (the target path) plus a guessable PID.

Consequence: the attacker pre-creates a symlink at the predicted temp path
(`.grammar.fltkg.fltkfmt.tmp.<pid>`) pointing at any file the *victim* can write but the
attacker cannot (e.g. `~/.bashrc`, `~/.config/...`, another repo file). When fltkfmt runs,
`File::create` follows the symlink and truncates+overwrites that target with the formatted
grammar text. Net effect: an attacker who can write the target's directory can destroy /
clobber arbitrary victim-writable files (a corruption / integrity / DoS primitive; content
is the formatted grammar, so not fully attacker-chosen, but the *which-file* is). PID
guessing is racy but cheap to brute-force (pre-plant symlinks across a PID range, or loop).
This is the classic insecure-temp-file pattern (CWE-377 / CWE-59 symlink following /
CWE-367 TOCTOU).

Suggested fix: create the temp file with `OpenOptions::new().write(true).create_new(true)`
(O_EXCL — fails instead of following/overwriting a planted symlink or existing file), and
make the name unpredictable (random suffix rather than PID; retry on collision), or use the
`tempfile` crate's `NamedTempFile::new_in(dir)` which does both. Keep the
write-then-`rename` step.

## security-2 — In-place write drops the original file's permissions

File: `crates/fltk-fmt-cli/src/lib.rs:120-150`

The issue: the temp file is created with `fs::File::create`, which uses default mode
(0666 & ~umask, typically 0644). After `fs::rename` over the original, the formatted file
carries the temp file's permissions, not the original's. A source file that was previously
mode 0600 (or had group/other restricted, or specific group ownership) becomes
world-readable 0644 after an in-place format.

Trust boundary / data flow: not externally triggered — it is a property of the in-place
rewrite applied to any file the user formats.

Consequence: a `.fltkg` file with intentionally restricted permissions silently widens to
world-readable after formatting. `.fltkg` files normally hold no secrets, so impact is low;
flagging because it is an over-permissive-default / permission-loss behavior in a
write-back path, and the rename-based approach is exactly where permission preservation is
easy to forget. (CWE-732-adjacent.)

Suggested fix: copy the original file's mode (and ideally uid/gid) onto the temp file before
rename (`fs::set_permissions` from the source's `metadata().permissions()`), or use a
temp-file helper that preserves them.
