//! Consumer-lane formatter binary.  A Bazel consumer building a formatter needs nothing
//! from fltk beyond its module: `fltk-fmt-cli` supplies the CLI scaffolding.

fltk_fmt_cli::fltk_formatter_main! {
    about: "Format consumer-lane sum expressions.",
    parser: consumer_fmt::parser::Parser,
    unparser: consumer_fmt::unparser::Unparser,
    parse: apply__parse_sum,
    unparse: unparse_sum,
}
