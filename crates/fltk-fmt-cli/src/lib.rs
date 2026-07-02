//! Reusable CLI scaffolding for standalone FLTK formatter binaries.
//!
//! Each FLTK grammar produces its own concrete `Parser`/`Unparser` types with
//! grammar-specific inherent methods, so this crate provides the grammar-independent
//! pieces a formatter binary needs (argument parsing, file/stdin I/O, check/in-place
//! modes, exit codes, error reporting) while the grammar-specific parse/unparse calls
//! are bound at the consumer's call site.

use std::fs;
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::{FromArgMatches, Parser};

// `RendererConfig` appears in the public `run_main`/`format_fn` signature, so it is part of
// this crate's public API.
pub use fltk_unparser_core::RendererConfig;

// `Renderer`/`resolve_spacing_specs` are re-exported only so `fltk_formatter_main!` can name
// the render API through `$crate` (a consumer needn't name `fltk-unparser-core` itself). They
// are macro-support implementation detail, not public API: `#[doc(hidden)]` keeps them out of
// rustdoc and signals they are not a supported entry point (visibility is unaffected, so
// `$crate::Renderer` / `$crate::resolve_spacing_specs` still resolve in macro expansions).
#[doc(hidden)]
pub use fltk_unparser_core::{resolve_spacing_specs, Renderer};

/// Command-line surface shared by every FLTK formatter binary.
///
/// The grammar and format spec are baked into each binary at code-generation time, so
/// this struct only carries the runtime knobs: which files to format, the output mode
/// (stdout / `--output` / `--in-place` / `--check`), and the render dimensions
/// (`--width`, `--indent`). clap supplies `--help`/`--version` automatically.
///
/// The per-consumer `--help` `about` text is not baked in here; it is threaded through
/// `run_main` (see `command_with_about`) so each formatter binary describes the language it
/// actually formats rather than inheriting one grammar's wording from this shared crate.
#[derive(Parser, Debug)]
// TODO(fmt-cli-per-consumer-version): `#[command(version)]` expands `CARGO_PKG_VERSION` where
// `FmtArgs` is defined, so every consumer binary reports this scaffolding crate's version rather
// than its own. Thread `version` (and possibly `name`) through `run_main`/`fltk_formatter_main!`
// so `<consumer> --version` prints the consumer's own version. Do NOT add a second bare
// `&'static str` positional next to `about` on `run_main` — two adjacent indistinguishable
// string params can be swapped silently (version rendered as the description). Introduce an
// identity struct (e.g. `FormatterInfo::new(about).version(..)`) so this and any later knob are
// non-breaking additions.
#[command(version)]
pub struct FmtArgs {
    /// Input files to format. With none (or a `-`), read from stdin.
    pub files: Vec<PathBuf>,

    /// Report whether inputs are already formatted without writing; exit non-zero if not.
    #[arg(long)]
    pub check: bool,

    /// Rewrite each input file in place. Requires at least one file argument.
    #[arg(long = "in-place")]
    pub in_place: bool,

    /// Maximum line width for the formatter.
    #[arg(short = 'w', long, default_value_t = 80)]
    pub width: usize,

    /// Indentation width.
    #[arg(short = 'i', long, default_value_t = 2)]
    pub indent: usize,

    /// Write output to this file instead of stdout (single input only).
    #[arg(short = 'o', long)]
    pub output: Option<PathBuf>,
}

/// Decide whether a parse covered the input.
///
/// Returns `true` if `pos` reaches the input's character count, or if the unconsumed
/// character suffix is entirely whitespace. A non-whitespace remainder is a genuine
/// partial parse and yields `false`.
///
/// `pos` is a character index (as produced by `TerminalSource`/`Span`), not a byte
/// index, so the comparison and suffix scan are both performed over characters.
///
/// Boundary behavior: a negative `pos` yields `false` (the parser never reports one, and
/// `pos as usize` would otherwise wrap). A `pos` at or beyond the character count yields
/// `true` — the suffix is empty, hence vacuously all-whitespace ("past the end ⇒
/// consumed"). The parser bounds `pos` by the input length, so an out-of-range positive
/// `pos` does not arise in practice; the vacuous-`true` result is the documented contract,
/// not a position-validity check.
pub fn fully_consumed(src: &str, pos: i64) -> bool {
    if pos < 0 {
        return false;
    }
    src.chars().skip(pos as usize).all(char::is_whitespace)
}

fn is_stdin(path: &Path) -> bool {
    path.as_os_str() == "-"
}

/// Reject the flag combinations the CLI does not support, returning the usage message
/// to print to stderr (exit code 2): `--in-place` with `--output`, `--in-place`
/// with `--check`, `--check` with `--output`, `--in-place` with no file (or a `-`), and
/// `--output` with more than one input.
fn validate(args: &FmtArgs) -> Result<(), String> {
    if args.in_place && args.output.is_some() {
        return Err("error: --in-place cannot be combined with --output".to_string());
    }
    if args.in_place && args.check {
        return Err("error: --in-place cannot be combined with --check".to_string());
    }
    // `--check` writes nothing, so `--output` would be silently ignored; reject it rather
    // than let the `check` branch win by dispatch order in `run_inner`.
    if args.check && args.output.is_some() {
        return Err("error: --check cannot be combined with --output".to_string());
    }
    if args.in_place {
        if args.files.is_empty() {
            return Err("error: --in-place requires at least one file argument".to_string());
        }
        if args.files.iter().any(|p| is_stdin(p)) {
            return Err("error: --in-place cannot read from stdin (`-`)".to_string());
        }
    }
    // `--output` writes a single result, so it accepts exactly one input source: zero files
    // means one implicit stdin input (allowed), two or more explicit files are rejected.
    if args.output.is_some() && args.files.len() > 1 {
        return Err("error: --output requires exactly one input".to_string());
    }
    Ok(())
}

/// Create a fresh sibling temp file for `base` in `dir`, returning the open handle and its
/// path.
///
/// The file is opened with `create_new` (`O_EXCL`): it never follows a planted symlink or
/// truncates an existing file, so it cannot be turned into an arbitrary-file-overwrite
/// primitive by an attacker who can write the target's directory (CWE-59/377/367). The
/// suffix carries a hard-to-guess component (pid + monotonic counter + sub-second nanos),
/// and a collision (or a hostile pre-planted path) makes `create_new` fail with
/// `AlreadyExists`, which we retry under a fresh name.
///
/// The marker is the generic crate name (`fltk-fmt`), not any one consumer binary, since
/// this scaffolding is shared by every FLTK formatter.
fn create_temp(dir: &Path, base: &str) -> io::Result<(fs::File, PathBuf)> {
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let pid = std::process::id();

    // Open the temp restrictively from the start. On Unix it is created mode 0o600 (rather than
    // the process default of `0o666 & ~umask`, typically 0o644 — world-readable); `write_atomic`
    // then *widens* it to the source file's mode via `set_permissions`. Narrowing-then-widening,
    // rather than widening a default-0o644 temp, means a *failed* permission copy leaves the temp
    // at 0o600 — so the failure direction errs toward keeping a private (e.g. 0o600) source's
    // contents private rather than silently exposing them to other local users (CWE-732).
    let mut opts = fs::OpenOptions::new();
    opts.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        opts.mode(0o600);
    }

    for _ in 0..1000 {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.subsec_nanos())
            .unwrap_or(0);
        let mut tmp = dir.to_path_buf();
        tmp.push(format!(".{base}.fltk-fmt.tmp.{pid}.{n}.{nanos}"));
        match opts.open(&tmp) {
            Ok(f) => return Ok((f, tmp)),
            Err(e) if e.kind() == io::ErrorKind::AlreadyExists => continue,
            Err(e) => return Err(e),
        }
    }
    Err(io::Error::new(
        io::ErrorKind::AlreadyExists,
        "could not create a unique temp file after repeated collisions",
    ))
}

/// Write `content` to `path` atomically: write a sibling temp file in the same directory,
/// then rename it over the target. A crash mid-write leaves the original intact (a
/// truncate-then-write would corrupt it).
///
/// The temp inherits the original file's permissions so an in-place rewrite does not
/// silently widen them (e.g. `0600` → `0644`). On a failed write or rename the temp is
/// removed; if that removal also fails the orphan path is reported to `stderr` (the primary
/// error is still returned unchanged) so the caller knows a stale temp may remain.
fn write_atomic(path: &Path, content: &str, stderr: &mut dyn Write) -> io::Result<()> {
    let dir = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    let file_name = path.file_name().ok_or_else(|| {
        io::Error::new(io::ErrorKind::InvalidInput, "input path has no file name")
    })?;

    let (mut f, tmp) = create_temp(dir, &file_name.to_string_lossy())?;

    // Best-effort: copy the original file's permissions onto the temp before rename so the
    // formatted file keeps the source's mode rather than the temp's default.
    if let Ok(meta) = fs::metadata(path) {
        let _ = fs::set_permissions(&tmp, meta.permissions());
    }

    let write_result = (|| {
        f.write_all(content.as_bytes())?;
        f.flush()
    })();
    if let Err(e) = write_result {
        if let Err(rm) = fs::remove_file(&tmp) {
            let _ = writeln!(
                stderr,
                "warning: failed to remove temp file {}: {rm}",
                tmp.display()
            );
        }
        return Err(e);
    }
    drop(f);

    if let Err(e) = fs::rename(&tmp, path) {
        if let Err(rm) = fs::remove_file(&tmp) {
            let _ = writeln!(
                stderr,
                "warning: failed to remove temp file {}: {rm}",
                tmp.display()
            );
        }
        return Err(e);
    }
    Ok(())
}

/// Build the clap `Command` for `FmtArgs` with a per-consumer `about` description.
///
/// clap's derive maps the first paragraph of the `FmtArgs` doc comment to `about` and the
/// full multi-paragraph comment to `long_about`; `--help` prefers `long_about` while `-h`
/// prefers `about`. Overriding only `.about(..)` would leave `--help` (the form users
/// actually read) showing the generic scaffolding prose, so `.long_about(None)` resets it —
/// making both `-h` and `--help` show the consumer's text.
///
/// Private on purpose: consumers go through `run_main`. It exists so unit tests can assert on
/// rendered help without spawning a process or letting clap exit.
fn command_with_about(about: &'static str) -> clap::Command {
    <FmtArgs as clap::CommandFactory>::command()
        .about(about)
        .long_about(None)
}

/// Entry point for a formatter binary: parse `FmtArgs` from the process environment, run
/// the format pipeline over every input, and return the process exit code.
///
/// `format_fn` is the grammar-specific stage: given the source text, the input filename
/// (`None` for stdin), and the render config, it returns the formatted string or an error
/// message. The `fltk_formatter_main!` macro supplies a closure that runs the proven
/// parse → unparse → resolve → render pipeline; `run_main` is also usable directly by a
/// consumer that hand-writes the closure.
///
/// All grammar-independent behavior — flag validation, file/stdin I/O, the output modes
/// (stdout / `--output` / `--in-place` / `--check`), error-path filename prefixing, and
/// exit codes — lives here.
///
/// `about` is the one-line description shown by `-h`/`--help` (e.g. "Format FLTK grammar
/// (.fltkg) files."); each consumer binary supplies its own so the help text describes the
/// language it formats rather than this shared scaffolding.
pub fn run_main<F>(about: &'static str, format_fn: F) -> ExitCode
where
    F: Fn(&str, Option<&str>, RendererConfig) -> Result<String, String>,
{
    // `get_matches()` preserves `FmtArgs::parse()`'s UX: prints help/version and exits 0 on
    // `-h`/`--help`/`--version`, prints a usage error and exits 2 on bad flags. After a
    // successful `get_matches` on a command built from `FmtArgs` itself, `from_arg_matches`
    // cannot realistically fail; `e.exit()` covers it identically to `parse()`.
    let matches = command_with_about(about).get_matches();
    let args = FmtArgs::from_arg_matches(&matches).unwrap_or_else(|e| e.exit());
    let mut stdin = io::stdin().lock();
    let mut stdout = io::stdout().lock();
    let mut stderr = io::stderr().lock();
    let code = run_inner(&args, format_fn, &mut stdin, &mut stdout, &mut stderr);
    ExitCode::from(code)
}

/// Generate the `fn main()` of a standalone FLTK formatter binary.
///
/// A consumer crate writes a single invocation naming its grammar's concrete
/// `Parser`/`Unparser` types and the start-rule `apply__parse_<rule>` / `unparse_<rule>`
/// method names, and gets a complete formatter binary. For example, the `fltkfmt` binary
/// for `fegen.fltkg` is just:
///
/// ```ignore
/// fltk_fmt_cli::fltk_formatter_main! {
///     about:    "Format FLTK grammar (.fltkg) files.",
///     parser:   fegen_rust_cst::parser::Parser,
///     unparser: fegen_rust_cst::unparser::Unparser,
///     parse:    apply__parse_grammar,
///     unparse:  unparse_grammar,
/// }
/// ```
///
/// The expansion is pure sugar over [`run_main`]: it builds a `format_fn` closure that runs
/// the proven pure-Rust pipeline — `Parser::new(src, filename, true)` → `parser.$parse(0)`
/// (`None` ⇒ `Err(parser.error_message())`) → [`fully_consumed`] check (a partial parse is
/// an error) → read-lock the CST → `Unparser::new().$unparse(&*guard)` (`None` ⇒ an internal
/// error, since a successfully parsed tree should always unparse) → [`resolve_spacing_specs`]
/// → [`Renderer::render`] — and hands it to `run_main`. Consumers who need to customize the
/// closure can call `run_main` directly instead.
///
/// A macro (rather than a trait or generic) is used because each grammar's generated
/// `Parser`/`Unparser` expose grammar-specific *inherent* methods and implement no shared
/// trait, and the start-rule method name varies per grammar; binding those names at the call
/// site is exactly what a macro does with minimal ceremony. Method names are taken as
/// identifiers, so no `paste`/`concat_idents` dependency is needed.
#[macro_export]
macro_rules! fltk_formatter_main {
    (
        about: $about:expr,
        parser: $parser:path,
        unparser: $unparser:path,
        parse: $parse:ident,
        unparse: $unparse:ident $(,)?
    ) => {
        fn main() -> ::std::process::ExitCode {
            $crate::run_main(
                $about,
                |src: &str,
                 filename: ::core::option::Option<&str>,
                 cfg: $crate::RendererConfig|
                 -> ::core::result::Result<::std::string::String, ::std::string::String> {
                    let mut parser = <$parser>::new(src, filename, true);
                    let result = parser.$parse(0);
                    // The parser-core contract (memo.rs) requires checking depth_exceeded()
                    // after parsing and discarding the result if set: a depth-rejected parse
                    // can still surface as `Some` with a wrong CST (e.g. a left-recursive
                    // rule's seed). Check before inspecting Some/None — matching the Python
                    // binding, which raises RecursionError unconditionally on the same input.
                    // error_message() already renders the depth-limit diagnostic.
                    if parser.depth_exceeded() {
                        return ::core::result::Result::Err(parser.error_message());
                    }
                    let parsed = match result {
                        ::core::option::Option::Some(p) => p,
                        ::core::option::Option::None => {
                            return ::core::result::Result::Err(parser.error_message());
                        }
                    };
                    // A successful parse that left non-whitespace unconsumed is a genuine
                    // partial parse; error_message() points at the furthest parse position.
                    if !$crate::fully_consumed(src, parsed.pos) {
                        return ::core::result::Result::Err(parser.error_message());
                    }
                    let guard = parsed.result.read();
                    let unparsed = match <$unparser>::new().$unparse(&*guard) {
                        ::core::option::Option::Some(u) => u,
                        ::core::option::Option::None => {
                            return ::core::result::Result::Err(::std::string::String::from(
                                "internal error: unparser returned None for a successfully parsed tree",
                            ));
                        }
                    };
                    let resolved = $crate::resolve_spacing_specs(unparsed.doc());
                    ::core::result::Result::Ok($crate::Renderer::new(cfg).render(&resolved))
                },
            )
        }
    };
}

/// The testable core of [`run_main`]: identical logic, but with the I/O streams injected
/// so unit tests can drive it with in-memory buffers and a stub `format_fn`.
///
/// Returns the process exit code as a `u8`: `2` for any error (usage, read failure,
/// format failure, write failure), `1` if `--check` found an input that would change, and
/// `0` otherwise. Processing continues across all inputs so one bad file does not mask the
/// rest; the returned code is the worst outcome seen (`2` > `1` > `0`).
fn run_inner<F>(
    args: &FmtArgs,
    format_fn: F,
    stdin: &mut dyn Read,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
) -> u8
where
    F: Fn(&str, Option<&str>, RendererConfig) -> Result<String, String>,
{
    if let Err(msg) = validate(args) {
        let _ = writeln!(stderr, "{msg}");
        return 2;
    }

    let cfg = RendererConfig {
        indent_width: args.indent,
        max_width: args.width,
    };

    // The ordered list of input sources. No files (or an explicit `-`) means stdin.
    let sources: Vec<&Path> = if args.files.is_empty() {
        vec![Path::new("-")]
    } else {
        args.files.iter().map(PathBuf::as_path).collect()
    };

    let mut worst: u8 = 0;
    for source in sources {
        let stdin_source = is_stdin(source);
        // Display name for error prefixing (the parser's error_message() never carries a
        // filename, so the CLI is what associates an error with its file).
        let display = if stdin_source {
            "<stdin>".to_string()
        } else {
            source.to_string_lossy().into_owned()
        };

        let content = if stdin_source {
            let mut buf = String::new();
            match stdin.read_to_string(&mut buf) {
                Ok(_) => buf,
                Err(e) => {
                    let _ = writeln!(stderr, "{display}: {e}");
                    worst = worst.max(2);
                    continue;
                }
            }
        } else {
            match fs::read_to_string(source) {
                Ok(s) => s,
                Err(e) => {
                    let _ = writeln!(stderr, "{display}: {e}");
                    worst = worst.max(2);
                    continue;
                }
            }
        };

        let filename: Option<&str> = if stdin_source { None } else { Some(&display) };
        let formatted = match format_fn(&content, filename, cfg) {
            Ok(s) => s,
            Err(msg) => {
                let _ = writeln!(stderr, "{display}: {msg}");
                worst = worst.max(2);
                continue;
            }
        };

        if args.check {
            if formatted != content {
                let _ = writeln!(stderr, "{display}");
                worst = worst.max(1);
            }
        } else if args.in_place {
            // Validation guarantees only real files reach this branch. Skip rewriting a
            // file that is already formatted: avoids a needless temp+rename and an mtime
            // bump that would re-trigger watchers / incremental builds on a stable tree.
            if formatted != content {
                if let Err(e) = write_atomic(source, &formatted, stderr) {
                    let _ = writeln!(stderr, "{display}: {e}");
                    worst = worst.max(2);
                }
            }
        } else if let Some(out_path) = &args.output {
            if let Err(e) = fs::write(out_path, formatted.as_bytes()) {
                let _ = writeln!(stderr, "{}: {e}", out_path.display());
                worst = worst.max(2);
            }
        } else if let Err(e) = stdout.write_all(formatted.as_bytes()) {
            let _ = writeln!(stderr, "{display}: {e}");
            worst = worst.max(2);
        }
    }

    worst
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_length_is_consumed() {
        let src = "rule := foo;";
        let pos = src.chars().count() as i64;
        assert!(fully_consumed(src, pos));
    }

    #[test]
    fn trailing_whitespace_suffix_is_accepted() {
        let src = "rule := foo;\n  \n\t";
        // Parser stopped right after the `;`, leaving only whitespace unconsumed.
        let pos = "rule := foo;".chars().count() as i64;
        assert!(fully_consumed(src, pos));
    }

    #[test]
    fn trailing_non_whitespace_is_rejected() {
        let src = "rule := foo; garbage";
        let pos = "rule := foo;".chars().count() as i64;
        assert!(!fully_consumed(src, pos));
    }

    #[test]
    fn char_index_not_byte_index() {
        // "é" is 2 bytes in UTF-8 but a single char. A parser that consumed only the
        // leading "é" reports char position 1; the equivalent *byte* offset is 2.
        let src = "éx  ";
        assert_eq!(src.chars().count(), 4);
        assert_eq!(src.len(), 5);

        // Correct char index (1): "x  " remains, which contains non-whitespace, so
        // this is a genuine partial parse.
        assert!(!fully_consumed(src, 1));

        // The same stop point as a *byte* offset is 2. That offset is a valid char
        // index here (the string has 4 chars), and skipping 2 chars leaves only "  ",
        // so the scan reports "consumed". Conflating the byte offset with a char index
        // would therefore skip past the unparsed "x" and silently mask a partial parse
        // — which is exactly why fully_consumed treats its argument as a char index and
        // why callers must pass char positions, not byte offsets.
        assert!(fully_consumed(src, 2));

        // Sanity: the full char count consumes everything.
        assert!(fully_consumed(src, 4));
    }

    #[test]
    fn multibyte_whitespace_suffix_is_accepted() {
        // Leading multibyte char then content, then a whitespace-only suffix.
        let src = "é := x\n";
        // After "é := x" (6 chars) only "\n" remains.
        let pos = "é := x".chars().count() as i64;
        assert_eq!(pos, 6);
        assert!(fully_consumed(src, pos));
    }

    #[test]
    fn negative_pos_is_not_consumed() {
        // A negative position is never "consumed": the guard must return false before
        // `pos as usize` would wrap to a huge index and vacuously report "consumed".
        assert!(!fully_consumed("foo", -1));
        assert!(!fully_consumed("", -1));
    }

    #[test]
    fn pos_past_end_is_consumed() {
        // Documented contract: a position at or beyond the char count leaves an empty
        // suffix, which is vacuously all-whitespace, so the parse counts as consumed.
        let src = "foo";
        assert_eq!(src.chars().count(), 3);
        assert!(fully_consumed(src, 3)); // exactly at the end
        assert!(fully_consumed(src, 1000)); // beyond the end
    }

    #[test]
    fn fmt_args_defaults() {
        let args = FmtArgs::try_parse_from(["fltkfmt"]).unwrap();
        assert!(args.files.is_empty());
        assert!(!args.check);
        assert!(!args.in_place);
        assert_eq!(args.width, 80);
        assert_eq!(args.indent, 2);
        assert!(args.output.is_none());
    }

    #[test]
    fn fmt_args_positional_files() {
        let args = FmtArgs::try_parse_from(["fltkfmt", "a.fltkg", "b.fltkg"]).unwrap();
        assert_eq!(
            args.files,
            vec![PathBuf::from("a.fltkg"), PathBuf::from("b.fltkg")]
        );
    }

    #[test]
    fn fmt_args_flags_and_dimensions() {
        let args = FmtArgs::try_parse_from([
            "fltkfmt",
            "--check",
            "--in-place",
            "-w",
            "100",
            "-i",
            "4",
            "-o",
            "out.fltkg",
            "in.fltkg",
        ])
        .unwrap();
        assert!(args.check);
        assert!(args.in_place);
        assert_eq!(args.width, 100);
        assert_eq!(args.indent, 4);
        assert_eq!(args.output, Some(PathBuf::from("out.fltkg")));
        assert_eq!(args.files, vec![PathBuf::from("in.fltkg")]);
    }

    #[test]
    fn fmt_args_long_dimension_flags() {
        let args = FmtArgs::try_parse_from(["fltkfmt", "--width", "120", "--indent", "8"]).unwrap();
        assert_eq!(args.width, 120);
        assert_eq!(args.indent, 8);
    }

    #[test]
    fn fmt_args_rejects_unknown_flag() {
        assert!(FmtArgs::try_parse_from(["fltkfmt", "--nope"]).is_err());
    }

    // --- per-consumer `about` help text (command_with_about) ---

    #[test]
    fn long_help_shows_consumer_about() {
        // `--help` renders `long_about`; the `.long_about(None)` reset must make it fall back
        // to the consumer's `about`, not the generic scaffolding doc comment. Pin the reset
        // directly (so this can't rot if the doc comment is reworded), then confirm the
        // rendered long help shows the consumer text and none of the derived scaffolding
        // long_about. The forbidden string is derived from the `FmtArgs` derive rather than
        // hard-coded, so rewording the doc comment updates the assertion automatically.
        assert!(<FmtArgs as clap::CommandFactory>::command()
            .long_about(None)
            .get_long_about()
            .is_none());
        let default_long_about = <FmtArgs as clap::CommandFactory>::command()
            .get_long_about()
            .expect("FmtArgs doc comment supplies a long_about")
            .to_string();
        let help = command_with_about("Format Foo files.")
            .render_long_help()
            .to_string();
        assert!(help.contains("Format Foo files."));
        assert!(!help.contains(&default_long_about));
    }

    #[test]
    fn short_help_shows_consumer_about() {
        // `-h` renders `about` directly. The forbidden scaffolding string is derived from the
        // `FmtArgs` derive rather than hard-coded, so it tracks any doc-comment rewording.
        let default_about = <FmtArgs as clap::CommandFactory>::command()
            .get_about()
            .expect("FmtArgs doc comment supplies an about")
            .to_string();
        let help = command_with_about("Format Foo files.")
            .render_help()
            .to_string();
        assert!(help.contains("Format Foo files."));
        assert!(!help.contains(&default_about));
    }

    #[test]
    fn command_with_about_parses_args_unchanged() {
        // Mutating the `Command`'s about/long_about must not disturb argument definitions or
        // defaults: parsing through `command_with_about` yields the same field values the
        // `fmt_args_*` tests check.
        let matches = command_with_about("Format Foo files.")
            .try_get_matches_from(["fltkfmt", "--check", "-w", "100", "in.fltkg"])
            .unwrap();
        let args = FmtArgs::from_arg_matches(&matches).unwrap();
        assert!(args.check);
        assert!(!args.in_place);
        assert_eq!(args.width, 100);
        assert_eq!(args.indent, 2);
        assert!(args.output.is_none());
        assert_eq!(args.files, vec![PathBuf::from("in.fltkg")]);
    }

    // --- run_inner integration tests (driven with stub format_fns, no parser) ---

    /// Create a unique temp directory for a test's fixture files.
    fn temp_dir(tag: &str) -> PathBuf {
        use std::sync::atomic::{AtomicUsize, Ordering};
        static COUNTER: AtomicUsize = AtomicUsize::new(0);
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let mut dir = std::env::temp_dir();
        dir.push(format!("fltk-fmt-cli-{}-{}-{}", tag, std::process::id(), n));
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    /// Stub format_fn: uppercases the source (a visible, non-identity transform).
    fn upper(src: &str, _filename: Option<&str>, _cfg: RendererConfig) -> Result<String, String> {
        Ok(src.to_uppercase())
    }

    /// No-op transform: used to verify `--check` exits 0 when input is already formatted.
    fn identity(
        src: &str,
        _filename: Option<&str>,
        _cfg: RendererConfig,
    ) -> Result<String, String> {
        Ok(src.to_string())
    }

    /// Stub format_fn: always fails (models a parse error).
    fn fail(_src: &str, _filename: Option<&str>, _cfg: RendererConfig) -> Result<String, String> {
        Err("boom".to_string())
    }

    #[test]
    fn default_writes_to_stdout() {
        let dir = temp_dir("default-stdout");
        let f = dir.join("a.fltkg");
        fs::write(&f, "abc").unwrap();
        let args = FmtArgs::try_parse_from(["fltkfmt", f.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert_eq!(String::from_utf8(out).unwrap(), "ABC");
        assert!(err.is_empty());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn multiple_files_concatenate_in_order() {
        let dir = temp_dir("concat");
        let a = dir.join("a.fltkg");
        let b = dir.join("b.fltkg");
        fs::write(&a, "ab").unwrap();
        fs::write(&b, "cd").unwrap();
        let args =
            FmtArgs::try_parse_from(["fltkfmt", a.to_str().unwrap(), b.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert_eq!(String::from_utf8(out).unwrap(), "ABCD");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn check_exits_1_when_input_would_change() {
        let dir = temp_dir("check-diff");
        let f = dir.join("a.fltkg");
        fs::write(&f, "abc").unwrap();
        let args = FmtArgs::try_parse_from(["fltkfmt", "--check", f.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 1);
        // --check writes nothing to stdout; the would-change path goes to stderr.
        assert!(out.is_empty());
        assert!(String::from_utf8(err)
            .unwrap()
            .contains(f.to_str().unwrap()));
        // The file is left untouched.
        assert_eq!(fs::read_to_string(&f).unwrap(), "abc");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn check_exits_0_when_already_formatted() {
        let dir = temp_dir("check-clean");
        let f = dir.join("a.fltkg");
        fs::write(&f, "abc").unwrap();
        let args = FmtArgs::try_parse_from(["fltkfmt", "--check", f.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, identity, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert!(out.is_empty());
        assert!(err.is_empty());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn in_place_rewrites_file_and_leaves_no_temp() {
        let dir = temp_dir("in-place");
        let f = dir.join("a.fltkg");
        fs::write(&f, "abc").unwrap();
        let args = FmtArgs::try_parse_from(["fltkfmt", "--in-place", f.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert!(out.is_empty());
        assert_eq!(fs::read_to_string(&f).unwrap(), "ABC");
        // The atomic temp file was renamed away, so only the original remains.
        let entries: Vec<_> = fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().file_name())
            .collect();
        assert_eq!(entries.len(), 1);
        let _ = fs::remove_dir_all(&dir);
    }

    /// Run `run_inner` with the `upper` stub and empty stdin, returning the exit code and the
    /// captured stderr text. Flag-conflict rejections must exit 2 *and* write a usage message to
    /// stderr (a silent exit 2 would be a regression), so each conflict test asserts both.
    fn run_args_only(args: &FmtArgs) -> (u8, String) {
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(args, upper, &mut stdin, &mut out, &mut err);
        (code, String::from_utf8(err).unwrap())
    }

    #[test]
    fn in_place_without_file_is_rejected() {
        let args = FmtArgs::try_parse_from(["fltkfmt", "--in-place"]).unwrap();
        let (code, err) = run_args_only(&args);
        assert_eq!(code, 2);
        assert!(err.contains("--in-place"));
    }

    #[test]
    fn in_place_with_stdin_sentinel_is_rejected() {
        let args = FmtArgs::try_parse_from(["fltkfmt", "--in-place", "-"]).unwrap();
        let (code, err) = run_args_only(&args);
        assert_eq!(code, 2);
        assert!(err.contains("--in-place"));
    }

    #[test]
    fn in_place_with_output_is_rejected() {
        let args =
            FmtArgs::try_parse_from(["fltkfmt", "--in-place", "-o", "out.fltkg", "in.fltkg"])
                .unwrap();
        let (code, err) = run_args_only(&args);
        assert_eq!(code, 2);
        assert!(err.contains("--in-place"));
    }

    #[test]
    fn in_place_with_check_is_rejected() {
        let args =
            FmtArgs::try_parse_from(["fltkfmt", "--in-place", "--check", "in.fltkg"]).unwrap();
        let (code, err) = run_args_only(&args);
        assert_eq!(code, 2);
        assert!(err.contains("--in-place"));
    }

    #[test]
    fn check_with_output_is_rejected() {
        let args =
            FmtArgs::try_parse_from(["fltkfmt", "--check", "-o", "out.fltkg", "in.fltkg"]).unwrap();
        let (code, err) = run_args_only(&args);
        assert_eq!(code, 2);
        assert!(err.contains("--check"));
    }

    #[test]
    fn output_with_multiple_inputs_is_rejected() {
        let args =
            FmtArgs::try_parse_from(["fltkfmt", "-o", "out.fltkg", "a.fltkg", "b.fltkg"]).unwrap();
        let (code, err) = run_args_only(&args);
        assert_eq!(code, 2);
        assert!(err.contains("--output"));
    }

    #[test]
    fn output_writes_to_file() {
        let dir = temp_dir("output");
        let f = dir.join("a.fltkg");
        let out_path = dir.join("formatted.fltkg");
        fs::write(&f, "hi").unwrap();
        let args = FmtArgs::try_parse_from([
            "fltkfmt",
            "-o",
            out_path.to_str().unwrap(),
            f.to_str().unwrap(),
        ])
        .unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert!(out.is_empty());
        assert_eq!(fs::read_to_string(&out_path).unwrap(), "HI");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn output_with_stdin_writes_to_file() {
        // No file args ⇒ stdin is the single input; `--output` accepts exactly one source, so
        // the formatted stdin content is written to the output file (not stdout). Guards the
        // `validate` count logic that treats zero files as one implicit stdin input.
        let dir = temp_dir("output-stdin");
        let out_path = dir.join("formatted.fltkg");
        let args = FmtArgs::try_parse_from(["fltkfmt", "-o", out_path.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"hi";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert!(out.is_empty());
        assert_eq!(fs::read_to_string(&out_path).unwrap(), "HI");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn check_stdin_exits_1_when_input_would_change() {
        // `--check` accepts stdin; a stub that changes the content ⇒ exit 1, nothing on stdout,
        // and the `<stdin>` display name reported to stderr.
        let args = FmtArgs::try_parse_from(["fltkfmt", "--check", "-"]).unwrap();
        let mut stdin: &[u8] = b"abc";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 1);
        assert!(out.is_empty());
        assert!(String::from_utf8(err).unwrap().contains("<stdin>"));
    }

    #[test]
    fn check_stdin_exits_0_when_already_formatted() {
        // `--check` on stdin with an identity stub ⇒ exit 0, no stdout, no stderr.
        let args = FmtArgs::try_parse_from(["fltkfmt", "--check"]).unwrap();
        let mut stdin: &[u8] = b"abc";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, identity, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert!(out.is_empty());
        assert!(err.is_empty());
    }

    #[test]
    fn in_place_identity_skips_rewrite_and_leaves_no_temp() {
        // `--in-place` with an identity stub: `formatted == content`, so run_inner skips
        // write_atomic entirely. The file is left byte-for-byte unchanged and no temp appears
        // (exercises the skip-when-unchanged guard, which avoids needless mtime churn).
        let dir = temp_dir("in-place-noop");
        let f = dir.join("a.fltkg");
        fs::write(&f, "abc").unwrap();
        let args = FmtArgs::try_parse_from(["fltkfmt", "--in-place", f.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, identity, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert_eq!(fs::read_to_string(&f).unwrap(), "abc");
        let entries: Vec<_> = fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().file_name())
            .collect();
        assert_eq!(entries.len(), 1);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn in_place_format_error_leaves_original_and_no_temp() {
        // `--in-place` with a failing stub: the Err branch `continue`s before write_atomic, so
        // the original file must remain untouched and no temp may be left behind — the exact
        // atomicity guarantee --in-place is meant to provide.
        let dir = temp_dir("in-place-err");
        let f = dir.join("a.fltkg");
        fs::write(&f, "abc").unwrap();
        let args = FmtArgs::try_parse_from(["fltkfmt", "--in-place", f.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, fail, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 2);
        assert_eq!(fs::read_to_string(&f).unwrap(), "abc");
        assert!(String::from_utf8(err)
            .unwrap()
            .contains(f.to_str().unwrap()));
        let entries: Vec<_> = fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().file_name())
            .collect();
        assert_eq!(entries.len(), 1);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn read_error_exits_2_but_other_inputs_still_processed() {
        let dir = temp_dir("read-error");
        let missing = dir.join("missing.fltkg");
        let good = dir.join("good.fltkg");
        fs::write(&good, "ok").unwrap();
        let args =
            FmtArgs::try_parse_from(["fltkfmt", missing.to_str().unwrap(), good.to_str().unwrap()])
                .unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        // Worst outcome is the read error (2); the good file is still formatted to stdout.
        assert_eq!(code, 2);
        assert_eq!(String::from_utf8(out).unwrap(), "OK");
        assert!(String::from_utf8(err)
            .unwrap()
            .contains(missing.to_str().unwrap()));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn format_error_exits_2_with_filename_prefix() {
        let dir = temp_dir("format-error");
        let f = dir.join("a.fltkg");
        fs::write(&f, "abc").unwrap();
        let args = FmtArgs::try_parse_from(["fltkfmt", f.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, fail, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 2);
        assert!(out.is_empty());
        let err_text = String::from_utf8(err).unwrap();
        // run_inner prepends the input path to the format_fn's error message.
        assert!(err_text.contains(f.to_str().unwrap()));
        assert!(err_text.contains("boom"));
        let _ = fs::remove_dir_all(&dir);
    }

    // --- stdin code path (no file arg / `-`) ---

    #[test]
    fn stdin_default_writes_transformed_to_stdout() {
        // No file args ⇒ read from stdin, format, write to stdout with `<stdin>` as display.
        let args = FmtArgs::try_parse_from(["fltkfmt"]).unwrap();
        let mut stdin: &[u8] = b"abc";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 0);
        assert_eq!(String::from_utf8(out).unwrap(), "ABC");
        assert!(err.is_empty());
    }

    /// A `Read` that always fails, to exercise the stdin read-error path.
    struct FailingReader;
    impl Read for FailingReader {
        fn read(&mut self, _buf: &mut [u8]) -> io::Result<usize> {
            Err(io::Error::other("stdin boom"))
        }
    }

    #[test]
    fn stdin_read_error_exits_2_with_stdin_display() {
        let args = FmtArgs::try_parse_from(["fltkfmt", "-"]).unwrap();
        let mut stdin = FailingReader;
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        assert_eq!(code, 2);
        assert!(out.is_empty());
        assert!(String::from_utf8(err).unwrap().contains("<stdin>"));
    }

    // --- filename argument delivered to format_fn ---

    #[test]
    fn filename_is_path_for_file_and_none_for_stdin() {
        use std::cell::RefCell;
        let seen: RefCell<Vec<Option<String>>> = RefCell::new(Vec::new());
        let record =
            |src: &str, filename: Option<&str>, _cfg: RendererConfig| -> Result<String, String> {
                seen.borrow_mut().push(filename.map(str::to_string));
                Ok(src.to_string())
            };

        // File input ⇒ format_fn receives Some(<path>).
        let dir = temp_dir("filename");
        let f = dir.join("a.fltkg");
        fs::write(&f, "x").unwrap();
        let args = FmtArgs::try_parse_from(["fltkfmt", f.to_str().unwrap()]).unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        assert_eq!(run_inner(&args, record, &mut stdin, &mut out, &mut err), 0);

        // Stdin input ⇒ format_fn receives None.
        let args2 = FmtArgs::try_parse_from(["fltkfmt"]).unwrap();
        let mut stdin2: &[u8] = b"y";
        let mut out2: Vec<u8> = Vec::new();
        let mut err2: Vec<u8> = Vec::new();
        assert_eq!(
            run_inner(&args2, record, &mut stdin2, &mut out2, &mut err2),
            0
        );

        let seen = seen.borrow();
        assert_eq!(seen[0], Some(f.to_string_lossy().into_owned()));
        assert_eq!(seen[1], None);
        let _ = fs::remove_dir_all(&dir);
    }

    // --- multi-file --check worst-of accumulation ---

    #[test]
    fn check_multi_file_reports_only_changed_and_exits_1() {
        let dir = temp_dir("check-multi");
        let clean = dir.join("clean.fltkg");
        let dirty = dir.join("dirty.fltkg");
        // upper("ABC") == "ABC" ⇒ no change; upper("abc") == "ABC" != "abc" ⇒ would change.
        fs::write(&clean, "ABC").unwrap();
        fs::write(&dirty, "abc").unwrap();
        let args = FmtArgs::try_parse_from([
            "fltkfmt",
            "--check",
            clean.to_str().unwrap(),
            dirty.to_str().unwrap(),
        ])
        .unwrap();
        let mut stdin: &[u8] = b"";
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_inner(&args, upper, &mut stdin, &mut out, &mut err);
        // Worst of {0 (clean), 1 (dirty)} is 1; both files are visited.
        assert_eq!(code, 1);
        assert!(out.is_empty());
        let err_text = String::from_utf8(err).unwrap();
        assert!(err_text.contains(dirty.to_str().unwrap()));
        assert!(!err_text.contains(clean.to_str().unwrap()));
        let _ = fs::remove_dir_all(&dir);
    }

    // --- write_atomic failure path ---

    #[test]
    fn write_atomic_fails_cleanly_when_dir_missing() {
        // A nonexistent parent directory makes create_new fail; write_atomic returns Err
        // and leaves nothing behind (no panic, no partial state).
        let missing = Path::new("/no/such/dir/definitely/missing/a.fltkg");
        let mut err: Vec<u8> = Vec::new();
        let res = write_atomic(missing, "data", &mut err);
        assert!(res.is_err());
    }

    #[test]
    fn write_atomic_preserves_no_temp_on_success() {
        let dir = temp_dir("atomic-ok");
        let f = dir.join("a.fltkg");
        fs::write(&f, "old").unwrap();
        let mut err: Vec<u8> = Vec::new();
        write_atomic(&f, "new", &mut err).unwrap();
        assert_eq!(fs::read_to_string(&f).unwrap(), "new");
        let entries: Vec<_> = fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().file_name())
            .collect();
        assert_eq!(entries.len(), 1);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn write_atomic_cleans_up_temp_when_rename_fails() {
        // Genuinely reach the rename-failure cleanup branch: the temp is created and
        // written successfully (so we get past create_temp and the write/flush step),
        // but the final rename fails because the target is an existing directory
        // (renaming a file over a directory yields EISDIR). The branch must remove the
        // sibling temp and propagate the error, leaving the target intact — the atomicity
        // invariant for --in-place.
        let dir = temp_dir("atomic-rename-fail");
        let target = dir.join("subdir");
        fs::create_dir(&target).unwrap();
        let mut err: Vec<u8> = Vec::new();
        let res = write_atomic(&target, "data", &mut err);
        assert!(res.is_err());
        // The cleanup removed the sibling temp: only `subdir` remains in `dir`.
        let entries: Vec<_> = fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().file_name())
            .collect();
        assert_eq!(entries, vec![std::ffi::OsString::from("subdir")]);
        // The original target is untouched on failure.
        assert!(target.is_dir());
        let _ = fs::remove_dir_all(&dir);
    }
}
