//! Scalar coercions: the parse and canonical-render halves of a `type:` builtin.
//!
//! Every coercion passes a shared format gate before any native parse runs. The native
//! parses of the two backends are lax in different places — Rust's `f64::from_str` takes
//! `inf` and `NaN`, Python's `uuid.UUID` takes braced and URN spellings, Python's `int`
//! takes digit separators — so a gate written once is what makes both backends accept and
//! reject the same lexemes. These functions are the counterparts of the helpers in
//! `fltk.fegen.pyrt.astrt`, one for one.
//!
//! Rendering is the inverse: one canonical text per value, chosen so that both backends
//! render a given value to the same bytes and so that the text re-parses to the value it
//! came from.

use std::str::FromStr;
use std::sync::LazyLock;

use fltk_cst_core::Span;

use crate::error::AstError;
use crate::terminal::TerminalPattern;

/// Optional sign, then digits. Rejects the digit separators Python's `int` accepts.
static INTEGER_FORMAT: LazyLock<TerminalPattern> = LazyLock::new(|| TerminalPattern::new("[+-]?[0-9]+"));

/// Optional sign, digits with an optional fraction, or a bare fraction. The decimal gate
/// on its own, and the mantissa of the float gate.
const PLAIN_NUMBER: &str = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)";

/// [`PLAIN_NUMBER`] with an optional exponent. Rejects the `inf`/`infinity`/`NaN`
/// spellings a native float parse accepts.
static FLOAT_FORMAT: LazyLock<TerminalPattern> =
    LazyLock::new(|| TerminalPattern::new(&format!("{PLAIN_NUMBER}(?:[eE][+-]?[0-9]+)?")));

/// Canonical 8-4-4-4-12 hex, case-insensitive. Braced and URN spellings are rejected.
#[cfg(feature = "uuid")]
static UUID_FORMAT: LazyLock<TerminalPattern> = LazyLock::new(|| {
    TerminalPattern::new("[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
});

/// A coercion failed on `text`, which is not `expected`.
fn coercion_error(text: &str, expected: &str, rule: &str, span: &Span) -> AstError {
    AstError::new(format!("rule {rule:?}: {text:?} is not {expected}"), span.clone())
}

/// A rendered value is not `expected`. Unlike a parse failure the offender is a typed
/// value, so it renders through `Display` rather than as quoted text.
fn render_error(value: impl std::fmt::Display, expected: &str, rule: &str, span: &Span) -> AstError {
    AstError::new(format!("rule {rule:?}: {value} is not {expected}"), span.clone())
}

/// `text`, once the gate has accepted it.
fn gated<'a>(
    text: &'a str,
    gate: &TerminalPattern,
    expected: &str,
    rule: &str,
    span: &Span,
) -> Result<&'a str, AstError> {
    if gate.matches(text) {
        return Ok(text);
    }
    Err(coercion_error(text, expected, rule, span))
}

/// The gated text as an `i128`, range-checked against one width.
///
/// Widening to `i128` keeps both backends agreeing on which lexemes are out of range:
/// `"-0"` is a valid `u8` of zero, and a magnitude past `u64::MAX` is a range failure
/// rather than a syntax error.
fn integer_value(text: &str, rule: &str, span: &Span, width: &str, low: i128, high: i128) -> Result<i128, AstError> {
    let accepted = gated(text, &INTEGER_FORMAT, &format!("a valid {width}"), rule, span)?;
    let out_of_range = || coercion_error(text, &format!("in range for {width} ({low} to {high})"), rule, span);
    let value = i128::from_str(accepted).map_err(|_| out_of_range())?;
    if value < low || value > high {
        return Err(out_of_range());
    }
    Ok(value)
}

macro_rules! integer_coercion {
    ($name:ident, $ty:ty, $width:literal) => {
        #[doc = concat!("Coerce a terminal's text to an `", $width, "`.")]
        pub fn $name(text: &str, rule: &str, span: &Span) -> Result<$ty, AstError> {
            let value = integer_value(
                text,
                rule,
                span,
                $width,
                i128::from(<$ty>::MIN),
                i128::from(<$ty>::MAX),
            )?;
            Ok(<$ty>::try_from(value).expect("integer_value range-checks against this width"))
        }
    };
}

integer_coercion!(parse_i8, i8, "i8");
integer_coercion!(parse_i16, i16, "i16");
integer_coercion!(parse_i32, i32, "i32");
integer_coercion!(parse_i64, i64, "i64");
integer_coercion!(parse_u8, u8, "u8");
integer_coercion!(parse_u16, u16, "u16");
integer_coercion!(parse_u32, u32, "u32");
integer_coercion!(parse_u64, u64, "u64");

/// The gated text as an `f64`, before any narrowing.
///
/// A magnitude past `f64::MAX` parses to infinity; the caller rejects it, so overflow is
/// reported as a range failure rather than a malformed lexeme.
fn float_value(text: &str, rule: &str, span: &Span, width: &str) -> Result<f64, AstError> {
    let expected = format!("a valid {width}");
    let accepted = gated(text, &FLOAT_FORMAT, &expected, rule, span)?;
    f64::from_str(accepted).map_err(|_| coercion_error(text, &expected, rule, span))
}

/// Coerce a terminal's text to an `f64`.
///
/// An infinity is out of range rather than a value: the gate rejects the `inf` lexeme, so
/// accepting one by overflow would make a value with no spelling to render back to.
pub fn parse_f64(text: &str, rule: &str, span: &Span) -> Result<f64, AstError> {
    let value = float_value(text, rule, span, "f64")?;
    if !value.is_finite() {
        return Err(coercion_error(text, "in range for f64", rule, span));
    }
    Ok(value)
}

/// Coerce a terminal's text to an `f32`.
///
/// The text is read at 64 bits and then narrowed, so a lexeme that rounds differently
/// through 64 bits lands on the same value on both backends.
pub fn parse_f32(text: &str, rule: &str, span: &Span) -> Result<f32, AstError> {
    let narrowed = float_value(text, rule, span, "f32")? as f32;
    if !narrowed.is_finite() {
        return Err(coercion_error(text, "in range for f32", rule, span));
    }
    Ok(narrowed)
}

/// An `f64` coercion's canonical text.
pub fn render_f64(value: f64, rule: &str, span: &Span) -> Result<String, AstError> {
    if !value.is_finite() {
        return Err(render_error(value, "a finite float", rule, span));
    }
    Ok(canonical_float(&format!("{value:e}")))
}

/// An `f32` coercion's canonical text: the shortest spelling that round-trips *at 32 bits*.
///
/// The field is an `f32`, so the value is already what the width holds and the shortest
/// spelling of it is shorter than the same number's `f64` spelling — which is what keeps a
/// parsed `3.14` rendering as `3.14` rather than in seventeen digits.
pub fn render_f32(value: f32, rule: &str, span: &Span) -> Result<String, AstError> {
    if !value.is_finite() {
        return Err(render_error(value, "a finite float", rule, span));
    }
    Ok(canonical_float(&format!("{value:e}")))
}

/// Rust's exponential form respelled the way CPython's `repr` spells a float.
///
/// The input is `[-]d[.ddd]e[-]dd`, whose digits are already the shortest decimal that
/// round-trips the value at its own width. Only the layout differs between the two
/// languages: CPython switches to exponent notation outside a fixed decimal-point window
/// and pads the exponent to two digits, and an integral value keeps a trailing `.0`.
fn canonical_float(exponential: &str) -> String {
    let (sign, rest) = match exponential.strip_prefix('-') {
        Some(rest) => ("-", rest),
        None => ("", exponential),
    };
    let (mantissa, exponent) = rest
        .split_once('e')
        .expect("Rust's exponential float format always carries an exponent");
    let exponent: i32 = exponent.parse().expect("the exponent is a decimal integer");
    let digits: String = mantissa.chars().filter(|c| *c != '.').collect();

    // Where the decimal point falls, counted in digits from the left.
    let point = exponent + 1;
    if point <= -4 || point > 16 {
        let mut out = format!("{sign}{}", &digits[..1]);
        if digits.len() > 1 {
            out.push('.');
            out.push_str(&digits[1..]);
        }
        let exponent = point - 1;
        let symbol = if exponent < 0 { '-' } else { '+' };
        out.push_str(&format!("e{symbol}{:02}", exponent.abs()));
        return out;
    }
    if point <= 0 {
        let zeros = "0".repeat(usize::try_from(-point).expect("a non-negative count"));
        return format!("{sign}0.{zeros}{digits}");
    }
    let point = usize::try_from(point).expect("a positive count");
    if point >= digits.len() {
        let zeros = "0".repeat(point - digits.len());
        return format!("{sign}{digits}{zeros}.0");
    }
    format!("{sign}{}.{}", &digits[..point], &digits[point..])
}

/// Coerce a terminal's text to a UUID, in the canonical 8-4-4-4-12 spelling only.
#[cfg(feature = "uuid")]
pub fn parse_uuid(text: &str, rule: &str, span: &Span) -> Result<uuid::Uuid, AstError> {
    let expected = "a canonical 8-4-4-4-12 UUID";
    let accepted = gated(text, &UUID_FORMAT, expected, rule, span)?;
    uuid::Uuid::parse_str(accepted).map_err(|_| coercion_error(text, expected, rule, span))
}

/// A UUID coercion's canonical text: lowercase, hyphenated.
#[cfg(feature = "uuid")]
pub fn render_uuid(value: &uuid::Uuid) -> String {
    value.hyphenated().to_string()
}

/// [`PLAIN_NUMBER`]: the float gate without its exponent.
#[cfg(feature = "decimal")]
static DECIMAL_FORMAT: LazyLock<TerminalPattern> = LazyLock::new(|| TerminalPattern::new(PLAIN_NUMBER));

/// The domain of the decimal type: a 96-bit mantissa scaled by at most 10^28.
///
/// Wider than this is refused rather than rounded, because a rounded value would render
/// back to different text than it was read from. Both backends narrow to this domain so
/// a `type: decimal` lexeme one accepts is never one the other refuses.
#[cfg(feature = "decimal")]
pub const DECIMAL_DOMAIN: &str = "a decimal of at most 28 fractional digits and 96 bits of mantissa";

/// Coerce a terminal's text to a decimal; exponent forms are not accepted.
#[cfg(feature = "decimal")]
pub fn parse_decimal(text: &str, rule: &str, span: &Span) -> Result<rust_decimal::Decimal, AstError> {
    let accepted = gated(text, &DECIMAL_FORMAT, "a plain decimal number", rule, span)?;
    // A trailing point is significant to the gate and not to the decimal parser.
    let trimmed = accepted.strip_suffix('.').unwrap_or(accepted);
    rust_decimal::Decimal::from_str_exact(trimmed).map_err(|_| coercion_error(text, DECIMAL_DOMAIN, rule, span))
}

/// A decimal coercion's canonical text: plain notation, keeping the value's scale.
#[cfg(feature = "decimal")]
pub fn render_decimal(value: &rust_decimal::Decimal) -> String {
    value.to_string()
}

/// Coerce a terminal's text through a `type: custom(...)` parse function.
///
/// The contract is an `Err(String)` on bad input, which becomes the message of an error
/// carrying the node's span — the function itself has no way to know where its text came
/// from.
pub fn parse_custom<T, E: std::fmt::Display>(
    parse: impl FnOnce(&str) -> Result<T, E>,
    text: &str,
    rule: &str,
    span: &Span,
) -> Result<T, AstError> {
    parse(text).map_err(|error| AstError::new(format!("rule {rule:?}: {error}"), span.clone()))
}

#[cfg(test)]
// Intentional: these lints police float literals a reader might have meant differently, but
// here the literal *is* the case — `3.14` is the value whose rendering is asserted, not an
// approximation of pi, and `123456.789` is asserted precisely because 32 bits cannot hold it.
#[allow(clippy::approx_constant, clippy::excessive_precision)]
mod tests {
    use super::*;
    use fltk_cst_core::SourceText;

    fn span() -> Span {
        Span::unknown()
    }

    #[test]
    fn every_width_reads_its_own_range() {
        assert_eq!(parse_i8("-128", "n", &span()), Ok(-128));
        assert_eq!(parse_i8("127", "n", &span()), Ok(127));
        assert_eq!(parse_i16("-32768", "n", &span()), Ok(-32768));
        assert_eq!(parse_i32("2147483647", "n", &span()), Ok(2147483647));
        assert_eq!(parse_i64("-9223372036854775808", "n", &span()), Ok(i64::MIN));
        assert_eq!(parse_u8("255", "n", &span()), Ok(255));
        assert_eq!(parse_u16("65535", "n", &span()), Ok(65535));
        assert_eq!(parse_u32("4294967295", "n", &span()), Ok(4294967295));
        assert_eq!(parse_u64("18446744073709551615", "n", &span()), Ok(u64::MAX));
    }

    #[test]
    fn a_leading_plus_and_leading_zeros_are_accepted() {
        assert_eq!(parse_i32("+42", "n", &span()), Ok(42));
        assert_eq!(parse_u8("007", "n", &span()), Ok(7));
        // Negative zero is in range for an unsigned width.
        assert_eq!(parse_u8("-0", "n", &span()), Ok(0));
    }

    #[test]
    fn the_gate_rejects_what_a_native_parse_would_take() {
        for text in ["1_000", " 42", "42 ", "0x2a", "", "4.0", "1e3", "+", "inf"] {
            let error = parse_i32(text, "n", &span()).unwrap_err();
            assert_eq!(
                error.message,
                format!("rule \"n\": {text:?} is not a valid i32"),
                "for {text:?}"
            );
        }
    }

    #[test]
    fn out_of_range_names_the_width_and_its_bounds() {
        let error = parse_i8("128", "count", &span()).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"count\": \"128\" is not in range for i8 (-128 to 127)"
        );
        assert_eq!(
            parse_u8("-1", "count", &span()).unwrap_err().message,
            "rule \"count\": \"-1\" is not in range for u8 (0 to 255)"
        );
    }

    #[test]
    fn a_magnitude_past_every_width_is_still_a_range_failure() {
        // Wider than i128 itself, so the widened parse is what fails, not the comparison.
        let text = "9".repeat(60);
        let error = parse_u64(&text, "n", &span()).unwrap_err();
        assert!(
            error.message.contains("in range for u64 (0 to 18446744073709551615)"),
            "{}",
            error.message
        );
    }

    #[test]
    fn a_coercion_error_carries_the_nodes_span() {
        let source = SourceText::from_str("x = 300", None);
        let error = parse_i8("300", "n", &Span::new_with_source(4, 7, &source)).unwrap_err();
        assert_eq!(error.to_string(), format!("{} at line 1, column 5", error.message));
    }

    #[test]
    fn floats_read_the_forms_the_gate_allows() {
        assert_eq!(parse_f64("3.14", "r", &span()), Ok(3.14));
        assert_eq!(parse_f64("-0.5", "r", &span()), Ok(-0.5));
        assert_eq!(parse_f64("+2.", "r", &span()), Ok(2.0));
        assert_eq!(parse_f64(".5", "r", &span()), Ok(0.5));
        assert_eq!(parse_f64("1e3", "r", &span()), Ok(1000.0));
        assert_eq!(parse_f64("1E-3", "r", &span()), Ok(0.001));
        assert_eq!(parse_f64("42", "r", &span()), Ok(42.0));
    }

    #[test]
    fn the_float_gate_rejects_the_non_finite_spellings() {
        for text in ["inf", "-inf", "infinity", "NaN", "nan", "1_0.5", "0x1p3", ""] {
            let error = parse_f64(text, "r", &span()).unwrap_err();
            assert_eq!(
                error.message,
                format!("rule \"r\": {text:?} is not a valid f64"),
                "for {text:?}"
            );
        }
    }

    #[test]
    fn an_overflowing_magnitude_is_out_of_range_for_its_width() {
        assert_eq!(
            parse_f64("1e400", "r", &span()).unwrap_err().message,
            "rule \"r\": \"1e400\" is not in range for f64"
        );
        assert_eq!(
            parse_f32("1e40", "r", &span()).unwrap_err().message,
            "rule \"r\": \"1e40\" is not in range for f32"
        );
        // The same text is an ordinary f64.
        assert_eq!(parse_f64("1e40", "r", &span()), Ok(1e40));
    }

    #[test]
    fn an_f32_holds_what_the_narrower_width_holds() {
        assert_eq!(parse_f32("3.14", "r", &span()), Ok(3.14f32));
        assert_eq!(f64::from(parse_f32("0.1", "r", &span()).unwrap()), 0.10000000149011612);
        // Subnormals survive; only an overflow is refused.
        assert!(parse_f32("1e-45", "r", &span()).unwrap() > 0.0);
    }

    #[test]
    fn f64_rendering_is_cpython_repr() {
        // The same value/text pairs are asserted against the Python renderer by
        // `F64_RENDERINGS` in `fltk/fegen/test_gsm2ast.py`; the two tables must stay in step.
        let cases: &[(f64, &str)] = &[
            (0.0, "0.0"),
            (-0.0, "-0.0"),
            (1.0, "1.0"),
            (3.14, "3.14"),
            (0.1, "0.1"),
            (-2.75, "-2.75"),
            (123456.789, "123456.789"),
            (1e15, "1000000000000000.0"),
            (1e16, "1e+16"),
            (1e17, "1e+17"),
            (1e22, "1e+22"),
            (1e-4, "0.0001"),
            (1e-5, "1e-05"),
            (1.5e300, "1.5e+300"),
            (2.5e-300, "2.5e-300"),
            (5e-324, "5e-324"),
            (f64::MAX, "1.7976931348623157e+308"),
        ];
        for (value, expected) in cases {
            assert_eq!(render_f64(*value, "r", &span()).as_deref(), Ok(*expected), "for {value:?}");
        }
    }

    #[test]
    fn f32_rendering_is_the_shortest_spelling_at_32_bits() {
        // Mirrored by `F32_RENDERINGS` in `fltk/fegen/test_gsm2ast.py`, row for row.
        let cases: &[(f32, &str)] = &[
            (0.0, "0.0"),
            (1.0, "1.0"),
            (3.14, "3.14"),
            (0.1, "0.1"),
            (1e15, "1000000000000000.0"),
            (1e16, "1e+16"),
            (1e-5, "1e-05"),
            (123456.789, "123456.79"),
            (16777216.0, "16777216.0"),
            (f32::MAX, "3.4028235e+38"),
            (f32::MIN_POSITIVE, "1.1754944e-38"),
        ];
        for (value, expected) in cases {
            assert_eq!(render_f32(*value, "r", &span()).as_deref(), Ok(*expected), "for {value:?}");
        }
    }

    #[test]
    fn a_parsed_float_renders_back_to_the_text_it_came_from() {
        for text in ["0.0", "3.14", "0.1", "123456.789", "1e+16", "1e-05", "-2.75"] {
            let value = parse_f64(text, "r", &span()).unwrap();
            assert_eq!(render_f64(value, "r", &span()).as_deref(), Ok(text), "for {text:?}");
        }
        for text in ["0.0", "3.14", "0.1", "1e+16", "1e-05"] {
            let value = parse_f32(text, "r", &span()).unwrap();
            assert_eq!(render_f32(value, "r", &span()).as_deref(), Ok(text), "for {text:?}");
        }
    }

    #[test]
    fn a_wide_spelling_renders_short_at_the_narrow_width() {
        // The f64-exact spelling of 3.14 rounds to the same f32 as "3.14" does.
        let value = parse_f32("3.140000104904175", "r", &span()).unwrap();
        assert_eq!(render_f32(value, "r", &span()).as_deref(), Ok("3.14"));
        // At 64 bits the same text is a distinct value and keeps its digits.
        let wide = parse_f64("3.140000104904175", "r", &span()).unwrap();
        assert_eq!(render_f64(wide, "r", &span()).as_deref(), Ok("3.140000104904175"));
    }

    #[test]
    fn a_non_finite_value_has_no_canonical_text() {
        assert_eq!(
            render_f64(f64::INFINITY, "r", &span()).unwrap_err().message,
            "rule \"r\": inf is not a finite float"
        );
        assert!(render_f32(f32::NAN, "r", &span()).is_err());
        assert!(render_f32(f32::NEG_INFINITY, "r", &span()).is_err());
    }

    #[test]
    fn a_custom_parse_functions_message_becomes_the_error() {
        fn parse_money(text: &str) -> Result<i64, String> {
            text.strip_prefix('$')
                .ok_or_else(|| format!("{text:?} is not an amount"))
                .and_then(|rest| rest.parse::<i64>().map_err(|e| e.to_string()))
        }
        assert_eq!(parse_custom(parse_money, "$12", "money", &span()), Ok(12));
        let error = parse_custom(parse_money, "12", "money", &span()).unwrap_err();
        assert_eq!(error.message, "rule \"money\": \"12\" is not an amount");
    }

    #[test]
    fn a_custom_parse_failure_carries_the_nodes_span() {
        let source = SourceText::from_str("pay 12", None);
        let error = parse_custom(
            |_: &str| Err::<i64, _>("bad".to_string()),
            "12",
            "money",
            &Span::new_with_source(4, 6, &source),
        )
        .unwrap_err();
        assert_eq!(error.to_string(), "rule \"money\": bad at line 1, column 5");
    }

    #[cfg(feature = "uuid")]
    #[test]
    fn a_uuid_reads_in_the_canonical_spelling_only() {
        let text = "F81D4FAE-7DEC-11D0-A765-00A0C91E6BF6";
        let value = parse_uuid(text, "id", &span()).unwrap();
        assert_eq!(render_uuid(&value), text.to_lowercase());
        for rejected in [
            "{f81d4fae-7dec-11d0-a765-00a0c91e6bf6}",
            "urn:uuid:f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
            "f81d4fae7dec11d0a76500a0c91e6bf6",
            "f81d4fae-7dec-11d0-a765-00a0c91e6bf",
            "",
        ] {
            let error = parse_uuid(rejected, "id", &span()).unwrap_err();
            assert_eq!(
                error.message,
                format!("rule \"id\": {rejected:?} is not a canonical 8-4-4-4-12 UUID"),
                "for {rejected:?}"
            );
        }
    }

    #[cfg(feature = "uuid")]
    #[test]
    fn a_uuid_round_trips_through_its_canonical_text() {
        let text = "00000000-0000-0000-0000-000000000000";
        assert_eq!(render_uuid(&parse_uuid(text, "id", &span()).unwrap()), text);
    }

    #[cfg(feature = "decimal")]
    #[test]
    fn a_decimal_keeps_its_scale_through_a_round_trip() {
        for text in ["1.50", "0.0", "-3", "12345.6789", "0.000001"] {
            let value = parse_decimal(text, "amount", &span()).unwrap();
            assert_eq!(render_decimal(&value), text, "for {text:?}");
        }
    }

    #[cfg(feature = "decimal")]
    #[test]
    fn a_negative_zero_decimal_renders_unsigned() {
        // The sign carries no value; both backends normalize to the same unsigned bytes.
        for (text, expected) in [("-0", "0"), ("-0.0", "0.0"), ("-0.00", "0.00")] {
            let value = parse_decimal(text, "amount", &span()).unwrap();
            assert_eq!(render_decimal(&value), expected, "for {text:?}");
        }
    }

    #[cfg(feature = "decimal")]
    #[test]
    fn a_decimals_leading_plus_and_trailing_point_normalize() {
        assert_eq!(render_decimal(&parse_decimal("+1.5", "a", &span()).unwrap()), "1.5");
        assert_eq!(render_decimal(&parse_decimal("007.5", "a", &span()).unwrap()), "7.5");
        assert_eq!(render_decimal(&parse_decimal("5.", "a", &span()).unwrap()), "5");
    }

    #[cfg(feature = "decimal")]
    #[test]
    fn the_decimal_gate_rejects_exponent_forms() {
        for text in ["1e3", "1E3", "inf", "1_0", ""] {
            let error = parse_decimal(text, "amount", &span()).unwrap_err();
            assert_eq!(
                error.message,
                format!("rule \"amount\": {text:?} is not a plain decimal number"),
                "for {text:?}"
            );
        }
    }

    #[cfg(feature = "decimal")]
    #[test]
    fn a_decimal_too_wide_to_hold_exactly_is_refused_not_rounded() {
        let text = "1.00000000000000000000000000000001";
        let error = parse_decimal(text, "amount", &span()).unwrap_err();
        assert_eq!(error.message, format!("rule \"amount\": {text:?} is not {DECIMAL_DOMAIN}"));
    }

    #[cfg(feature = "decimal")]
    #[test]
    fn the_edges_of_the_decimal_domain() {
        // 2^96 - 1 fits the mantissa; one more does not.
        assert!(parse_decimal("79228162514264337593543950335", "a", &span()).is_ok());
        assert!(parse_decimal("79228162514264337593543950336", "a", &span()).is_err());
        // 28 fractional digits are the most a scale can hold; a 29th is not.
        assert!(parse_decimal("0.0000000000000000000000000001", "a", &span()).is_ok());
        assert!(parse_decimal("0.00000000000000000000000000001", "a", &span()).is_err());
        // Trailing zeros count toward both bounds, being part of the scale and the mantissa.
        assert!(parse_decimal("1.0000000000000000000000000000", "a", &span()).is_ok());
        assert!(parse_decimal("7922816251426433759354395033.5", "a", &span()).is_ok());
    }
}
