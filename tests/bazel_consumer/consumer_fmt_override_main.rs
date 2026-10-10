//! Consumer-lane formatter binary that overrides both identity keys, so `--version` prints the
//! given `name`/`version` rather than this target's name and `version` attribute.

fltk_fmt_cli::fltk_formatter_main! {
    about: "Format consumer-lane sum expressions.",
    name: "consumer-fmt",
    version: "9.8.7-override",
    parser: consumer_fmt::parser::Parser,
    unparser: consumer_fmt::unparser::Unparser,
    parse: apply__parse_sum,
    unparse: unparse_sum,
}
