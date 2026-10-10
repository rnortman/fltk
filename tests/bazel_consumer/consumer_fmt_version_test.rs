//! `--version` / `-V` of the consumer-lane formatter binaries. Through the macro's default arm,
//! `consumer_fmt_bin` prints its Bazel target name and its `version` attribute, never the
//! `fltk-fmt-cli` scaffolding's name or version. Through the `name:`/`version:` override keys,
//! `consumer_fmt_override_bin` prints the given values, not its target name or attribute.

use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

/// Absolute path to a built binary: the `rootpath` the target supplies has no directory
/// component, which `Command::new` would otherwise look up on `PATH`.
fn binary(env_var: &str) -> PathBuf {
    let var = std::env::var(env_var)
        .unwrap_or_else(|_| panic!("{env_var} is not set; the test target must supply it"));
    std::fs::canonicalize(&var).unwrap_or_else(|e| panic!("resolve {var}: {e}"))
}

/// Runs the binary named by `env_var` with each version flag and asserts stdout is exactly
/// `expected`. The nonexistent file and the unparseable stdin would each yield exit 2 and a
/// stderr line if the format pipeline ran, so exit 0 with empty stderr proves clap exited first.
fn assert_version_output(env_var: &str, expected: &[u8]) {
    for flag in ["--version", "-V"] {
        let mut child = Command::new(binary(env_var))
            .args([flag, "/nonexistent/input.txt"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap_or_else(|e| panic!("spawn {env_var}: {e}"));
        {
            let mut stdin = child.stdin.take().expect("child stdin");
            // The binary may exit before reading; a broken pipe here is expected and harmless.
            let _ = stdin.write_all(b"((( not a sum\n");
        }
        let out = child
            .wait_with_output()
            .unwrap_or_else(|e| panic!("wait for {env_var}: {e}"));
        let stdout = String::from_utf8_lossy(&out.stdout);
        let stderr = String::from_utf8_lossy(&out.stderr);
        assert_eq!(out.status.code(), Some(0), "{flag} failed; stderr: {stderr}");
        assert!(
            !stdout.contains("fltk-fmt-cli"),
            "{flag} printed the scaffolding crate's name: {stdout:?}"
        );
        assert_eq!(
            out.stdout,
            expected,
            "{flag} stdout {stdout:?}, expected {:?}",
            String::from_utf8_lossy(expected)
        );
        assert!(out.stderr.is_empty(), "{flag} stderr: {stderr}");
    }
}

#[test]
fn version_is_the_consumer_binary_identity() {
    assert_version_output("CONSUMER_FMT_BIN", b"consumer_fmt_bin 0.0.1-consumer\n");
}

#[test]
fn version_overrides_replace_the_defaults() {
    assert_version_output("CONSUMER_FMT_OVERRIDE_BIN", b"consumer-fmt 9.8.7-override\n");
}
