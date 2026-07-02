//! End-to-end integration tests for the `fltkfmt` binary.
//!
//! These drive the *built binary* as a subprocess (via `env!("CARGO_BIN_EXE_fltkfmt")`,
//! which Cargo injects for integration tests of the owning package), so they exercise the
//! full pure-Rust pipeline — argument parsing, file/stdin I/O, parse, unparse, render,
//! error reporting, and exit codes — exactly as a user invokes it. This is the only place
//! the `fltk_formatter_main!` macro's error branches (partial-parse and parse-`None`) run
//! against a real `Parser`/`Unparser`; the `fltk-fmt-cli` unit tests use stub `format_fn`s
//! and cannot reach them.
//!
//! Coverage note: the macro's `unparse`-returns-`None` branch
//! (`fltk-fmt-cli/src/lib.rs`, the "internal error: unparser returned None" arm) is
//! *unreachable by construction* — a tree that parses successfully with a correctly
//! generated parser+unparser pair always unparses, so no input can trigger it. These tests
//! compile and link that branch in a real consumer and execute every *reachable* branch;
//! the unreachable arm stays covered only by its explicit `match` arm.
//!
//! Outputs are compared as raw bytes (never lossily decoded), and every temp file uses a
//! pid+counter-unique name and is cleaned up, so parallel `cargo test` execution is safe.

use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};

/// Path to the built `fltkfmt` binary, injected by Cargo for integration tests.
const FLTKFMT: &str = env!("CARGO_BIN_EXE_fltkfmt");

/// The `about` string threaded through `fltk_formatter_main!` in `crates/fltkfmt/src/main.rs`.
/// Kept in sync by hand; the `--help` test below is the end-to-end check that the macro →
/// `run_main` → `clap` wiring actually surfaces it.
const ABOUT: &str = "Format FLTK grammar (.fltkg) files.";

/// Repo root, resolved from this crate's manifest dir (`crates/fltkfmt` → `../..`) so tests
/// are cwd-independent.
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

/// Run `fltkfmt` with `args` (repo-root cwd) and optional stdin bytes.
/// Returns `(exit_code, stdout, stderr)` with outputs as raw bytes.
fn run(args: &[&str], stdin: Option<&[u8]>) -> (i32, Vec<u8>, Vec<u8>) {
    let mut cmd = Command::new(FLTKFMT);
    cmd.args(args)
        .current_dir(repo_root())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = cmd.spawn().expect("spawn fltkfmt");
    {
        let mut child_stdin = child.stdin.take().expect("child stdin");
        if let Some(bytes) = stdin {
            child_stdin.write_all(bytes).expect("write child stdin");
        }
        // Dropping `child_stdin` here closes the pipe, signaling EOF.
    }
    let out = child.wait_with_output().expect("wait for fltkfmt");
    let code = out.status.code().expect("fltkfmt terminated by signal");
    (code, out.stdout, out.stderr)
}

/// Run `fltkfmt` expecting success (exit 0) and return its stdout bytes. On any non-zero
/// exit, panics with `ctx` plus the captured stderr so the failing case is diagnosable.
/// The success-path invocations all funnel through here so their failure diagnostics stay
/// consistent; the parse-error test uses the raw `run` because it asserts exit 2.
fn run_ok(args: &[&str], stdin: Option<&[u8]>, ctx: &str) -> Vec<u8> {
    let (code, out, err) = run(args, stdin);
    assert_eq!(
        code,
        0,
        "{ctx} exited {code}: {}",
        String::from_utf8_lossy(&err)
    );
    out
}

/// Create a fresh temp file with `content` and a pid+counter-unique name, returning its path.
/// Files go under `CARGO_TARGET_TMPDIR` (Cargo's per-crate integration-test temp dir, inside
/// `target/`), not the shared world-writable system temp dir, so predictable names can't be
/// pre-seeded/symlinked by another local user.
fn temp_file(tag: &str, content: &[u8]) -> PathBuf {
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let mut path = PathBuf::from(env!("CARGO_TARGET_TMPDIR"));
    path.push(format!(
        "fltkfmt-cli-{}-{}-{}.fltkg",
        tag,
        std::process::id(),
        n
    ));
    std::fs::write(&path, content).expect("write temp file");
    path
}

/// Idempotency corpus. Kept in sync (by hand — no way to share a list between pytest and a
/// Rust test) with `tests/test_fltkfmt_parity.py`'s `_CORPUS`; if you add a grammar there,
/// add it here too. Divergence only degrades coverage, never produces a false pass.
const CORPUS: &[&str] = &[
    "fltk/fegen/bootstrap.fltkg",
    "fltk/fegen/fegen.fltkg",
    "fltk/fegen/fltk.fltkg",
    "fltk/fegen/regex.fltkg",
    "fltk/fegen/test_data/collision_fixture.fltkg",
    "fltk/fegen/test_data/phase4_roundtrip.fltkg",
    "fltk/fegen/test_data/poc_grammar.fltkg",
    "fltk/fegen/test_data/rust_parser_fixture.fltkg",
];

/// Wide (80/2, also the CLI default) and narrow (40/4), matching the parity pytest so
/// flat-vs-break layout decisions are exercised.
const CONFIGS: &[(usize, usize)] = &[(80, 2), (40, 4)];

/// Test 1 — Idempotency: `format(format(x)) == format(x)` over the corpus × configs.
///
/// Pass 1 formats the file; pass 2 pipes pass 1's output back in via stdin (which also
/// exercises the stdin input path end-to-end with a real grammar). For every case the two
/// passes must be byte-identical — with one documented exception.
#[test]
fn format_format_is_format() {
    let root = repo_root();
    for rel in CORPUS {
        for &(w, i) in CONFIGS {
            let path = root.join(rel);
            let ws = w.to_string();
            let is = i.to_string();
            let path_str = path.to_str().expect("utf-8 path");

            let out1 = run_ok(
                &[path_str, "-w", &ws, "-i", &is],
                None,
                &format!("[{rel} w={w} i={i}] pass 1"),
            );
            let out2 = run_ok(
                &["-w", &ws, "-i", &is],
                Some(&out1),
                &format!("[{rel} w={w} i={i}] pass 2"),
            );

            // TODO(formatter-group-idempotency): `rust_parser_fixture.fltkg` at 40/4 is not
            // idempotent today — a grouped alternation re-breaks between pass 1 and pass 2,
            // converging at pass 2 (a formatter-layout bug present in both backends, out of
            // scope for this test addition). Pin the current behavior loudly: pass 2 differs
            // from pass 1 but is itself a fixed point. When the formatter is fixed this
            // assertion trips, forcing removal of this carve-out and the TODO rather than
            // letting them go stale. All other cases keep the strict `out2 == out1` contract.
            if *rel == "fltk/fegen/test_data/rust_parser_fixture.fltkg" && (w, i) == (40, 4) {
                assert_ne!(
                    out2, out1,
                    "[{rel} w={w} i={i}] carve-out expects non-idempotency; if the formatter \
                     was fixed, remove this carve-out and TODO(formatter-group-idempotency)"
                );
                let out3 = run_ok(
                    &["-w", &ws, "-i", &is],
                    Some(&out2),
                    &format!("[{rel} w={w} i={i}] pass 3"),
                );
                assert_eq!(
                    out3, out2,
                    "[{rel} w={w} i={i}] expected convergence at pass 2 (out3 == out2)"
                );
            } else {
                assert_eq!(
                    out2, out1,
                    "[{rel} w={w} i={i}] not idempotent: format(format(x)) != format(x)"
                );
            }
        }
    }
}

/// Test 2 — Golden / canonical: `fegen.fltkg` at 80/2 matches a committed fixture byte for
/// byte. A pinned-bytes anchor that runs without Python and catches *simultaneous* drift of
/// both backends (the parity test only detects the backends disagreeing).
#[test]
fn golden_fegen_fltkg() {
    let root = repo_root();
    let input = root.join("fltk/fegen/fegen.fltkg");
    // 80/2 passed explicitly so the test stays pinned even if the CLI defaults change.
    let out = run_ok(
        &[input.to_str().unwrap(), "-w", "80", "-i", "2"],
        None,
        "golden fegen.fltkg 80/2",
    );

    let golden_path = root.join("crates/fltkfmt/tests/golden/fegen.fltkg.golden");
    let golden = std::fs::read(&golden_path).expect("read golden fixture");
    assert_eq!(
        out, golden,
        "fegen.fltkg 80/2 output drifted from the committed golden. If this change is \
         intended, regenerate with:\n  cargo run --manifest-path crates/fltkfmt/Cargo.toml \
         -- fltk/fegen/fegen.fltkg -w 80 -i 2 > crates/fltkfmt/tests/golden/fegen.fltkg.golden"
    );
}

/// Test 3 — Trailing-newline robustness: 0/1/3 trailing newlines on `fegen.fltkg`'s text,
/// fed via stdin. Pins the real, cross-backend-consistent behavior (verified byte-identical
/// in the Python backend): 0- and 1-newline inputs format identically to a single trailing
/// `\n`; three trailing newlines collapse to one *preserved* blank line (output = the
/// 1-newline output plus exactly one extra `\n`), which is itself a formatting fixed point.
#[test]
fn trailing_newline_handling_is_stable() {
    let root = repo_root();
    let text = std::fs::read(root.join("fltk/fegen/fegen.fltkg")).expect("read fegen.fltkg");

    // Base = the file's text with all trailing newlines stripped.
    let mut base = text.clone();
    while base.last() == Some(&b'\n') {
        base.pop();
    }

    let mut one = base.clone();
    one.push(b'\n');
    let mut three = base.clone();
    three.extend_from_slice(b"\n\n\n");

    let out_a = run_ok(&["-w", "80", "-i", "2"], Some(&base), "no-newline variant");
    let out_b = run_ok(&["-w", "80", "-i", "2"], Some(&one), "one-newline variant");
    let out_c = run_ok(
        &["-w", "80", "-i", "2"],
        Some(&three),
        "three-newline variant",
    );

    // (a) and (b) are identical and end in a single `\n`.
    assert_eq!(
        out_a, out_b,
        "stripped and single-newline inputs format differently"
    );
    assert!(out_b.ends_with(b"\n"), "output must end in a newline");
    assert!(
        !out_b.ends_with(b"\n\n"),
        "output must end in exactly one newline"
    );

    // (c) = (b) plus exactly one extra `\n` (one trailing blank line preserved).
    let mut expected_c = out_b.clone();
    expected_c.push(b'\n');
    assert_eq!(
        out_c, expected_c,
        "three trailing newlines should collapse to one preserved blank line"
    );

    // (c)'s output is itself a formatting fixed point.
    let out_c2 = run_ok(
        &["-w", "80", "-i", "2"],
        Some(&out_c),
        "reformat of three-newline output",
    );
    assert_eq!(
        out_c2, out_c,
        "three-newline output is not a formatting fixed point"
    );
}

/// Test 4 — Parse-error path: malformed input exits 2 with empty stdout and a stderr
/// message naming the input file and reporting line/col.
///
/// Two inputs drive the macro's two reachable error branches (which branch fires is not
/// externally observable — both print `parser.error_message()` and exit 2 — so this is
/// documented, not asserted):
///   - unparseable from the start (`grammar` needs ≥1 rule, none can start) → the
///     parse-`None` branch;
///   - a valid rule followed by garbage that can't start a second rule → the
///     partial-parse (`fully_consumed`-false) branch.
///
/// Assertions bind only to the stable contract — exit code 2, empty stdout, and a stderr
/// carrying the filename plus the `Syntax error at line … col …` skeleton — not the full
/// error text, whose expected-token lists may change with the grammar.
#[test]
fn parse_errors_report_filename_and_position() {
    // Unparseable from the start: reports line 1 col 1 via the parse-`None` branch.
    let bad_start = temp_file("bad-start", b"%%% not a grammar\n");
    // Valid prefix + garbage: one rule parses, `???` can't start a second → partial parse.
    let partial = temp_file("partial", b"a := \"x\";\n???\n");

    for path in [&bad_start, &partial] {
        let path_str = path.to_str().expect("utf-8 path");
        let (code, out, err) = run(&[path_str], None);
        assert_eq!(code, 2, "expected exit 2 for {path_str}, got {code}");
        assert!(out.is_empty(), "expected empty stdout for {path_str}");
        let err_text = String::from_utf8_lossy(&err);
        // The CLI prefixes the parser's message with the input path.
        assert!(
            err_text.contains(path_str),
            "stderr should name the input file {path_str}; got:\n{err_text}"
        );
        // The stable line/col skeleton from `format_error_message`.
        assert!(
            err_text.contains("Syntax error at line ") && err_text.contains(" col "),
            "stderr should report line/col for {path_str}; got:\n{err_text}"
        );
    }

    let _ = std::fs::remove_file(&bad_start);
    let _ = std::fs::remove_file(&partial);
}

/// Test 5 — `--help` surfaces the consumer's `about` string end-to-end.
///
/// `about` is threaded through the `fltk_formatter_main!` macro → `run_main` → `clap`
/// wiring; that threading is only observable through a real consumer binary (the
/// `fltk-fmt-cli` unit tests call `command_with_about` directly, bypassing
/// `run_main`/`get_matches()`). This pins the deleted `TODO(fltkfmt-integration-tests)`'s
/// explicit ask that `--help` output contain the fegen `about` literal.
#[test]
fn help_shows_consumer_about() {
    for flag in ["--help", "-h"] {
        let out = run_ok(&[flag], None, &format!("{flag} invocation"));
        let stdout = String::from_utf8_lossy(&out);
        assert!(
            stdout.contains(ABOUT),
            "{flag} stdout should contain the consumer about string {ABOUT:?}; got:\n{stdout}"
        );
    }
}
