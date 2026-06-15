# ruff: noqa: E501
r"""Adversarial test suite for the FLTK regex grammar (fltk/fegen/regex.fltkg).

Purpose: **try to fool the parser** — find inputs where the grammar accepts something
it should reject (over-admission, the dangerous direction) or rejects something it
should accept (over-rejection, the annoying direction). The corpus tests prove the
grammar handles *real* patterns; this suite proves it handles *hostile* ones.

Structure (§4.1 of design.md):

- Each case is a ``(pattern, expected, rationale)`` triple.
- ``expected`` is ``ACCEPT`` or ``REJECT``.
- ``rationale`` is a non-empty one-line string that explains *why* that disposition is
  correct, citing the ``regex.fltkg`` line or cross-engine behavior where applicable.
- ACCEPT-direction cases are cross-checked against Python ``re.compile``: if ``re``
  rejects a pattern we expect to ACCEPT, the test fails with a mis-spec error.
- REJECT-direction cases are NOT cross-checked against ``re.compile`` (§4.1): most
  of them are "Python re accepts, Rust regex-automata rejects," and we have no inline
  Rust oracle. REJECT-case correctness rests on the mandatory Rust-aware rationale string.

All assertions are accept/reject booleans only; no ``longest_parse_len`` assertions (§4.1).

Findings discovered during authoring are flagged with ``FINDING`` in the rationale.

SCOPE-BOUNDARY GAPS (the spike's deliverable for the downstream regex-portability-lint
go/no-go). These are cases where the grammar's accept/reject disposition does NOT match the
Python ``re`` / Rust ``regex-automata`` portable intersection. Each is pinned with a
``FINDING`` rationale and (where the grammar accepts a Python-invalid pattern)
``skip_re_check=True``. ALL are *over-admissions* (grammar accepts something at least one
engine rejects) -- the dangerous direction; no over-rejections of a portable construct were
found. The grammar fails CLOSED on most divergent shapes probed below (see F6 for the
one exception: ``&&`` set-intersection look-alikes are over-admitted).

  F1 -- ``\0N`` octal family (``\07``, ``\00``, ``\012`` ...): grammar accepts ``\0`` +
        literal; Python re reads octal (different meaning); Rust rejects octal. Cannot be
        fixed without removing ``\0`` from ``control_escape`` or adding a lookahead.
  F2 -- ``U`` inline flag (``(?U)``, ``(?iU)``, ``(?U:a)``): grammar admits ``U`` via
        ``flag_chars /[imsU]+/``; Python re rejects ``U`` as an unknown extension/flag.
        Rust-only flag, admitted by design.
  F3 -- ``\z`` top-level anchor: grammar admits it via ``anchor_escape /[Az]/``; Rust
        accepts ``\z`` (end-of-text) but Python re rejects it ('bad escape'). The grammar
        comment 'verified on both engines' (regex.fltkg:276-280) is wrong for Python >= 3.6.
  F4 -- inverted bound ``a{2,1}`` (min>max): grammar admits it (``bounded`` is purely
        syntactic, no min<=max check); BOTH engines reject. Intrinsic to a context-free
        recognizer -- needs a downstream semantic check.
  F5 -- reversed class range ``[z-a]`` (lo>hi): grammar admits it (``class_range`` is purely
        syntactic, no lo<=hi check); BOTH engines reject. The class-range analogue of F4.
  F6 -- ``&&`` set-intersection look-alike (``[a-z&&b]``, ``[a&&b]``): ``&`` is an ordinary
        ``class_char`` (not excluded from ``class_char := /[^\\\]\[\-\n]/``), so ``&&``
        parses as two literal ``&`` characters inside a class.  Python ``re`` raises
        ``FutureWarning: Possible set intersection`` on these; Rust ``regex-automata``
        treats ``&&`` as the actual set-intersection operator (different semantics).  This
        is the ``&&`` analogue of the ``--`` door -- ``--`` is closed (interior ``-``
        excluded by class_char), but ``&&`` is open.  The only existing ``&&`` case
        ``[a-z&&[^aeiou]]`` rejects for an *unrelated* reason (inner ``[`` excluded by
        class_char), so the ``&&`` gap was previously unpinned.

F1/F2/F3 are the three originally-documented findings; F4/F5 are added by the opus
corrective pass; F6 is pinned by the respond-round review.  None is fixed here --
``regex.fltkg`` is unchanged; these feed the downstream lint design's go/no-go (do
NOT 'fix' the grammar in this spike).
"""

from __future__ import annotations

import re

import pytest

from fltk.fegen.regex_corpus import classify_pattern

ACCEPT = True
REJECT = False


# ---------------------------------------------------------------------------
# Test table
# ---------------------------------------------------------------------------
# fmt: off
# The optional 4th element is a bool ``skip_re_check``. Set to True for cases where
# the grammar accepts a pattern that Python re rejects -- i.e., documented grammar
# over-admissions relative to the Python engine. These cases are pinned as ACCEPT
# (because that is the grammar's actual behavior) with a FINDING: rationale, and the
# re.compile cross-check is suppressed because it would trivially fail on these.
CASES: list[tuple[str, bool, str] | tuple[str, bool, str, bool]] = [

    # =========================================================================
    # OVER-ADMISSION PROBES
    # Try to slip a non-portable construct past the grammar.
    # =========================================================================

    # -------------------------------------------------------------------------
    # POSIX-class look-alikes
    # -------------------------------------------------------------------------
    (
        "[[:alpha:]]",
        REJECT,
        "POSIX class [[:alpha:]]: class_char excludes '[', so inner '[' has no production; parser stalls -> reject (regex.fltkg:179-181).",
    ),
    (
        "[[:^digit:]]",
        REJECT,
        "Negated POSIX class [[:^digit:]]: same as [[:alpha:]] -- inner '[' excluded by class_char -> reject.",
    ),
    (
        r"[\[:alpha:]]",
        ACCEPT,
        r"Escaped-bracket near-miss [\[:alpha:]]: class_char_escape admits \[, so the class body is literal-[ then ':alpha:' then literal-]; the trailing ']' closes the class. Both engines accept this as a class with those literal chars (regex.fltkg:316-322 / literal_char admits ']').",
    ),
    (
        r"[\[]",
        ACCEPT,
        r"Escaped open-bracket in class: \[ is a meta_escape -> class_char_escape -> ACCEPT. Both engines accept it.",
    ),
    (
        "[[]",
        REJECT,
        "Literal open-bracket in class [[] is REJECTED: class_char excludes '[' (regex.fltkg:223), so the inner unescaped '[' has no class_char production -> the class body parse stalls before the closing ']' -> reject. This is the SAME mechanism that rejects POSIX [[:alpha:]] -- excluding '[' from class_char is what closes both doors. Python re accepts [[] as a class matching literal '['; Rust regex-automata rejects an unescaped nested '[' -> divergent -> correctly fail-closed (the escaped form [\\[] is the portable way, accepted above).",
    ),
    (
        "[]",
        REJECT,
        "Empty class [] is REJECTED: char_class := '[' negated? class_body ']' and class_body requires at least one item or a lead/trail dash (regex.fltkg:186-190); the immediate ']' yields an empty body -> reject. BOTH engines reject [] (Python: 'unterminated character set' since it reads ']' as a class member; Rust: empty class error) -> correctly excluded (regex.fltkg:167-168).",
    ),
    (
        "[^]",
        REJECT,
        "Negated empty class [^] is REJECTED: '^' is consumed as the optional negation prefix, leaving an EMPTY class_body before ']' -> body requires >=1 item -> reject. BOTH engines reject [^] (the negation does not supply a member) -> correctly excluded (regex.fltkg:166-168).",
    ),
    (
        "[]a]",
        REJECT,
        "Bracket-first class []a] is REJECTED: the parser sees '[' then immediately ']' as the class close -> empty body -> char_class fails; then the leftover 'a]' cannot be consumed at top level after a failed class -> stall -> reject. Python re reads []a] as the GNU/Perl idiom 'class containing ] and a' (']' first is a literal member); Rust regex-automata rejects a literal ']'-first class (requires \\]) -> DIVERGENT -> correctly fail-closed. The portable spelling is [\\]a] (escaped).",
    ),

    # -------------------------------------------------------------------------
    # Set-operation look-alikes
    # -------------------------------------------------------------------------
    (
        "[a-z&&[^aeiou]]",
        REJECT,
        "Set intersection [a-z&&[^aeiou]]: first '&' is class_char, but second '&' is also class_char, then inner '[' has no class_char production -> parser stalls short of ']' -> reject.",
    ),
    (
        r"[\w--_]",
        REJECT,
        r"Set difference [\w--_]: \w is class_shorthand, first '-' could start trail_dash but then second '-' is not ']' and class body is exhausted early -> stall before second '-' -> reject.",
    ),
    (
        "[a-z-0]",
        REJECT,
        "Interior literal dash [a-z-0]: the class body sees range a-z, then '-' as trail_dash, but '0' follows and is not ']', so trail_dash + remaining input -> stall -> reject. This closes the '--' set-op look-alike door (regex.fltkg:172-184).",
    ),
    (
        "[-a]",
        ACCEPT,
        "Leading dash [-a]: class_body lead_dash path: '-' is lead_dash, 'a' is one class_item, no trail_dash -> ACCEPT. Both engines accept [-a] as a class with '-' and 'a' (regex.fltkg:189).",
    ),
    (
        "[a-]",
        ACCEPT,
        "Trailing dash [a-]: class_body items+ trail_dash? path: 'a' is class_item, '-' is trail_dash -> ACCEPT. Both engines accept [a-] as a class with 'a' and '-' (regex.fltkg:190).",
    ),
    (
        "[a-z-]",
        ACCEPT,
        "Trailing dash after range [a-z-]: class_body sees range a-z as class_item, then '-' as trail_dash -> ACCEPT. Both engines accept this common idiom (regex.fltkg:190).",
    ),
    (
        "[-]",
        ACCEPT,
        "Class with only a dash [-]: class_body lead_dash path with empty items* and no trail_dash -> ACCEPT. Both engines accept this as a class matching literal '-'.",
    ),
    (
        "[a-z&&b]",
        ACCEPT,
        "FINDING (F6, scope-boundary gap -- grammar over-admits): [a-z&&b] is ACCEPTED. '&' is an ordinary class_char (class_char := /[^\\\\\\]\\[\\-\\n]/ does not exclude '&'), so '&&' parses as two literal '&' class members -> ACCEPT. Python re raises FutureWarning: 'Possible set intersection' on [a-z&&b]; Rust regex-automata treats '&&' as the real set-intersection operator (semantically different from two literal '&' chars). The '&&' door is open: the grammar distinguishes '--' (closed, interior '-' excluded by class_char) from '&&' (open, '&' is a valid class_char). The earlier [a-z&&[^aeiou]] case rejects for an UNRELATED reason (inner '[' excluded). This pins the '&&'-without-inner-bracket form as a documented over-admission for the lint go/no-go.",
        True,  # skip_re_check: Python re raises FutureWarning (and may error with warnings-as-errors) -- documented over-admission finding
    ),
    (
        "[a&&b]",
        ACCEPT,
        "FINDING (F6 family): [a&&b] is ACCEPTED for the same reason as [a-z&&b] -- '&' is class_char, so '&&' is two ordinary literals -> ACCEPT. Confirms the F6 over-admission is not range-specific: any '&&' inside a class is admitted.",
        True,  # skip_re_check: Python re warns/errors on [a&&b] -- documented over-admission finding
    ),

    # -------------------------------------------------------------------------
    # Class-range ordering and shorthand-endpoint divergence
    # -------------------------------------------------------------------------
    (
        "[z-a]",
        ACCEPT,
        "FINDING (F5, scope-boundary gap -- grammar over-admits relative to BOTH engines): reversed range [z-a] (lo>hi) is ACCEPTED. class_range := lo:class_range_atom '-' hi:class_range_atom (regex.fltkg:201) is purely SYNTACTIC -- 'z' and 'a' both parse as class_range_atom, no lo<=hi check -> ACCEPT. Python re rejects it ('bad character range z-a'); Rust regex-automata also rejects an out-of-order class range at compile time. Non-portable on BOTH engines but admitted by the grammar -- the dangerous over-admission direction, the class-range analogue of the {2,1} inverted-bound gap (F4). lo<=hi is a semantic predicate a context-free grammar cannot express; must be caught by a downstream semantic check. Documented for the regex-portability-lint go/no-go.",
        True,  # skip_re_check: Python re rejects [z-a] -- documented over-admission finding
    ),
    (
        r"[\d-z]",
        REJECT,
        r"Shorthand as range start [\d-z] is REJECTED: class_range_atom := class_char_escape | class_char (regex.fltkg:212-214) -- a class SHORTHAND (\d) is deliberately NOT a valid range endpoint (class_char_escape draws from char_escape only, excluding class_shorthand). \d is parsed as a standalone class_member, then '-' as trail_dash, then 'z' is left over -> stall before ']' -> reject. BOTH engines reject \d as a range endpoint ('bad character range') -> correctly excluded (regex.fltkg:197-201).",
    ),
    (
        r"[a-\d]",
        REJECT,
        r"Shorthand as range end [a-\d] is REJECTED: class_range needs hi:class_range_atom, but \d is a class_shorthand, not in class_char_escape -> class_range fails for the 'a-\d' shape; the body cannot consume \d as a range hi and stalls -> reject. BOTH engines reject \d as a range endpoint -> correctly excluded.",
    ),

    # -------------------------------------------------------------------------
    # Unicode property escapes
    # -------------------------------------------------------------------------
    (
        r"\p{L}",
        REJECT,
        r"Unicode property \p{L}: escape_body has no 'p' alternative (not in class_shorthand/assertion/anchor_escape/char_escape) -> stalls -> reject (regex.fltkg:248-267).",
    ),
    (
        r"\P{N}",
        REJECT,
        r"Unicode property \P{N}: same as \p{L} -- escape_body has no 'P' alternative -> reject.",
    ),
    (
        r"\pL",
        REJECT,
        r"Short unicode property \pL: escape_body has no 'p' alternative -> reject.",
    ),
    (
        chr(92) + chr(92) + "p",  # 3-char string \\p (escaped-backslash + literal-p)
        ACCEPT,
        r"Escaped backslash then p (\\p as subject pattern): meta_escape admits '\\' (regex.fltkg:308), then 'p' is literal_char -> ACCEPT. Both engines accept \\p as a literal-p match.",
    ),

    # -------------------------------------------------------------------------
    # Lookaround, backreferences, named groups
    # -------------------------------------------------------------------------
    (
        "(?=x)",
        REJECT,
        "Lookahead (?=x): group tries non_capturing '(?:', flag_group '(?'+flags+':', capturing '(' -- none match '(?=' -> reject (regex.fltkg:134-148).",
    ),
    (
        "(?!x)",
        REJECT,
        "Negative lookahead (?!x): same as (?=x) -- no production for '(?!' -> reject.",
    ),
    (
        "(?<=x)",
        REJECT,
        "Lookbehind (?<=x): '(?<' not matched by any group alternative -> reject.",
    ),
    (
        "(?<!x)",
        REJECT,
        "Negative lookbehind (?<!x): '(?<!' not matched by any group alternative -> reject.",
    ),
    (
        r"\1",
        REJECT,
        r"Backreference \1: escape_body has no digit alternative; '1' is not in class_shorthand/assertion/anchor_escape/char_escape -> reject (regex.fltkg:263-267).",
    ),
    (
        "(?P<name>x)",
        REJECT,
        "Named group (?P<name>x): '(?P' not matched by any group alternative -> reject.",
    ),
    (
        "(?P=name)",
        REJECT,
        "Named backreference (?P=name): '(?P' not matched -> reject.",
    ),

    # -------------------------------------------------------------------------
    # Divergent escape sequences
    # -------------------------------------------------------------------------
    (
        r"\Z",
        REJECT,
        r"\Z: anchor_escape := /[Az]/ -- 'Z' (uppercase) is NOT in [Az] -> escape_body has no match for 'Z' -> reject. Python accepts \Z (end of string), Rust regex-automata rejects it -> non-portable, correctly excluded (regex.fltkg:278-280).",
    ),
    (
        r"\x{41}",
        REJECT,
        r"\x{41} braced hex: hex_escape := %'x' . /[0-9A-Fa-f][0-9A-Fa-f]/ -- '{' is not a hex digit, so hex_escape fails; no other escape_body alternative matches 'x' -> reject. Rust accepts braced form, Python rejects it -> non-portable (regex.fltkg:295).",
    ),
    (
        r"\u{41}",
        REJECT,
        r"\u{41} braced unicode: unicode_escape tries %'u' . 4-hex-digits -- '{' is not a hex digit -> unicode_escape fails -> reject. Rust accepts braced form, Python rejects -> non-portable (regex.fltkg:297-303).",
    ),
    (
        r"\x41",
        ACCEPT,
        r"\x41 hex escape: hex_escape := %'x' . /[0-9A-Fa-f][0-9A-Fa-f]/ -- 'x' then '41' (2 hex digits) -> ACCEPT. Both engines accept \xHH (regex.fltkg:295).",
    ),
    (
        "\\u0041",  # 6-char string: backslash, u, 0, 0, 4, 1 -- NOT r"A" which Python evaluates as chr(0x41)='A'
        ACCEPT,
        r"A unicode escape (4-hex): unicode_escape %'u' . 4hex digits '0041' -> ACCEPT. Both engines accept \uHHHH (regex.fltkg:302-303).",
    ),
    (
        "\\u00E9",  # backslash, u, 0, 0, E, 9 -- confirms the rule fires on digit+letter hex sequences
        ACCEPT,
        r"é unicode escape (4-hex with letter digit): unicode_escape %'u' . 4hex digits '00E9' -> ACCEPT. Confirms the hex-digit class /[0-9A-Fa-f]/ admits letter digits, not just all-numeric sequences (regex.fltkg:302-303).",
    ),
    (
        r"\U00000041",
        ACCEPT,
        r"\U00000041 unicode escape (8-hex): unicode_escape %'U' . 8hex digits '00000041' -> ACCEPT. Both engines accept \UHHHHHHHH (regex.fltkg:302).",
    ),
    (
        r"\07",
        ACCEPT,
        r"FINDING (F1, scope-boundary gap -- grammar over-admits relative to BOTH engines): \07 is ACCEPTED. The grammar parses \0 as a control_escape (null, via /[nrtfv0a]/) then '7' as a literal_char -> ACCEPT. Python re treats \07 as octal 7 (BEL=chr(7)), and Rust regex-automata rejects octal sequences entirely. The grammar cannot distinguish \07 (octal) from \0 (null) + 7 (literal) because \0 is a valid control_escape. This over-admits the WHOLE family \0N (any digit/char after \0) -- see the \00, \012, \0a cases below -- treating them as \0 + literal rather than octal. Note re.compile does NOT reject \07 (Python reads it as octal chr(7), a valid pattern), so the ACCEPT cross-check passes here; the divergence is that the two engines assign DIFFERENT MEANINGS to \07 (Python octal-BEL vs the grammar's \0+'7'), and Rust rejects it outright. This is a documented gap fed to the downstream regex-portability-lint go/no-go; fixing it (remove \0 from control_escape, or add a not-a-digit lookahead) is the lint increment's call, not the spike's.",
    ),
    (
        r"\00",
        ACCEPT,
        r"FINDING (F1 family): \00 is ACCEPTED as \0 (control_escape null) + '0' (literal_char). Python re reads \00 as octal chr(0); Rust regex-automata rejects octal. Same \0N over-admission as \07; pinned to show the gap is the general \0-followed-by-octal-digit family, not a single pattern. re.compile accepts \00 (valid Python octal), so the ACCEPT cross-check holds; the gap is the semantic split + Rust rejection.",
    ),
    (
        r"\012",
        ACCEPT,
        r"FINDING (F1 family): \012 is ACCEPTED as \0 + '1' + '2' (control_escape null then two literal_chars). Python re reads \012 as octal chr(10)=newline; Rust regex-automata rejects octal. Demonstrates the gap extends to multi-digit octal-look sequences. re.compile accepts \012, ACCEPT cross-check holds.",
    ),
    (
        r"\0a",
        ACCEPT,
        r"\0a is ACCEPTED as \0 (control_escape null) + 'a' (literal_char). This one is genuinely portable: \0 (null) is in control_escape and BOTH engines accept \0, and a following non-digit 'a' is an ordinary literal on both. Pinned alongside the \0N findings to show that \0 + non-digit is the BENIGN case (no octal ambiguity) and the gap is specifically \0 + OCTAL-DIGIT (\00..\07).",
    ),
    (
        r"\7",
        REJECT,
        r"Bare \7 (no leading 0) is REJECTED: escape_body has no '7' alternative (not in class_shorthand/assertion/anchor_escape/char_escape) -> stall -> reject. Python re reads \7 as a backreference/octal ('invalid group reference' when group 7 is absent); Rust rejects. Correctly excluded -- confirms the grammar admits ONLY \0-prefixed control escapes, not bare-digit escapes (regex.fltkg:263-267).",
    ),
    (
        r"\8",
        REJECT,
        r"\8 is REJECTED: '8' is not an octal digit and escape_body has no '8' alternative -> reject. Python re rejects \8 ('bad escape'); both engines reject. Correctly excluded.",
    ),

    # -------------------------------------------------------------------------
    # Invalid / non-portable escapes (must reject)
    # -------------------------------------------------------------------------
    (
        r"\q",
        REJECT,
        r"Invalid escape \q is REJECTED: 'q' is in none of class_shorthand/assertion/anchor_escape/char_escape -> escape_body has no match -> reject. Python re rejects \q ('bad escape \q', for unknown ASCII-letter escapes since 3.6); Rust regex-automata also rejects \q -> both reject -> correctly excluded (regex.fltkg:263-267).",
    ),
    (
        r"\e",
        REJECT,
        r"Escape-char \e is REJECTED: 'e' (ESC, chr 27) is not in control_escape /[nrtfv0a]/ nor any escape_body alternative -> reject. Python re rejects \e ('bad escape'); Rust regex-automata accepts \e as the ESC character -> DIVERGENT -> correctly fail-closed (the grammar admits only the cross-portable control escapes).",
    ),
    (
        r"\c",
        REJECT,
        r"Control escape \c is REJECTED: 'c' is in no escape_body alternative -> reject. Python re rejects bare \c ('bad escape'); Perl-style \cX control escapes are non-portable -> correctly excluded.",
    ),
    (
        "\\",
        REJECT,
        "Lone trailing backslash is REJECTED: escape := '\\\\' . escape_body requires an escape_body after the backslash (regex.fltkg:260-261); end-of-input after '\\\\' -> escape_body fails -> reject. BOTH engines reject a trailing backslash ('bad escape (end of pattern)') -> correctly excluded.",
    ),

    # -------------------------------------------------------------------------
    # Escaped metacharacters at top level (meta_escape coverage)
    # -------------------------------------------------------------------------
    (
        r"\.",
        ACCEPT,
        r"Escaped dot \.: escape -> escape_body -> char_escape -> meta_escape /[.*+?()\[\]{}|^$\/\\\-]/ matches '.' -> ACCEPT. Both engines accept \. as a literal dot (regex.fltkg:308).",
    ),
    (
        r"\*",
        ACCEPT,
        r"Escaped star \*: meta_escape matches '*' -> ACCEPT. Both engines accept \* as a literal star.",
    ),
    (
        r"\(",
        ACCEPT,
        r"Escaped open-paren \(: meta_escape matches '(' -> ACCEPT. Both engines accept \( as a literal paren. Confirms the escape path handles structural-metacharacter escapes.",
    ),
    (
        r"\{",
        ACCEPT,
        r"Escaped open-brace \{: meta_escape matches '{' -> ACCEPT. Both engines accept \{ as a literal brace (the escaped form is portable even though bare '{' is not).",
    ),
    (
        r"\}",
        ACCEPT,
        r"Escaped close-brace \}: meta_escape matches '}' -> ACCEPT. Both engines accept \}.",
    ),
    (
        r"\-",
        ACCEPT,
        r"Escaped dash \- (top level): meta_escape matches '-' -> ACCEPT. Both engines accept \- as a literal dash outside a class.",
    ),
    (
        r"\/",
        ACCEPT,
        r"Escaped slash \/: meta_escape matches '/' -> ACCEPT. This is the IN-TREE corpus pattern (fegen's block-comment regexes contain \/); the portable subset admits it and the grammar's own self-escaping documents it (regex.fltkg:32-37,305-308).",
    ),
    (
        "\\\\",
        ACCEPT,
        r"Escaped backslash \\ (subject is one backslash + one backslash): meta_escape matches '\\' -> ACCEPT. Both engines accept \\ as a literal backslash (regex.fltkg:308).",
    ),

    # -------------------------------------------------------------------------
    # Bare-brace divergence (§4.2)
    # -------------------------------------------------------------------------
    (
        "a{",
        REJECT,
        "Bare open brace a{: literal_char excludes '{' (regex.fltkg:316-328); bounded tries '{' + number + ... but '{' is not followed by a valid number sequence if the pattern ends there -> bounded fails -> atom falls through all alternatives, then 'a' is parsed, '{' has no production -> stall after 'a' -> reject (short parse).",
    ),
    (
        "{",
        REJECT,
        "Bare brace alone {: literal_char excludes '{' and no other atom production matches '{' -> reject. Rust regex-automata errors on bare '{'; Python treats it as a literal (non-portable).",
    ),
    (
        "a{2}",
        ACCEPT,
        "Bounded {2}: repetition -> atom('a') . quantifier(bound(bounded('{' '2' '}'))) -> ACCEPT. Both engines accept {m} (regex.fltkg:95).",
    ),
    (
        "a{2,}",
        ACCEPT,
        "Bounded {2,}: bounded := '{' min:number ',' '}' -> ACCEPT. Both engines accept {m,} (regex.fltkg:94).",
    ),
    (
        "a{2,4}",
        ACCEPT,
        "Bounded {2,4}: bounded := '{' min:number ',' max:number '}' -> ACCEPT. Both engines accept {m,n} (regex.fltkg:93).",
    ),
    (
        "a{2,1}",
        ACCEPT,
        "FINDING (F4, scope-boundary gap -- grammar over-admits relative to BOTH engines): inverted bound {2,1} (min>max) is ACCEPTED. bounded := '{' min:number ',' max:number '}' (regex.fltkg:93) is purely SYNTACTIC -- it does no min<=max ordering check, so '2' and '1' both parse as numbers -> ACCEPT. Python re rejects it ('min repeat greater than max'); Rust regex-automata also rejects an out-of-order bound at compile time. So this is non-portable on BOTH engines but the grammar admits it -- the dangerous over-admission direction. A grammar cannot express min<=max (that is a semantic predicate, not a context-free constraint), so this gap is intrinsic to the recognizer approach and must be caught by a downstream semantic check, not the grammar. Documented for the regex-portability-lint go/no-go.",
        True,  # skip_re_check: Python re rejects {2,1} -- documented over-admission finding
    ),
    (
        "a{,3}",
        REJECT,
        "Open-min bound {,3} is REJECTED: bounded's three alternatives all require min:number immediately after '{' (regex.fltkg:93-95); ',' right after '{' matches none -> bounded fails -> '{' falls through to literal_char which EXCLUDES '{' -> stall after 'a' -> reject. Python re accepts a{,3} (treats it as {0,3}); Rust regex-automata treats a{,3} as a LITERAL '{,3}' (no special meaning) -> the two engines DIVERGE on a{,3}, so rejecting it is the correct fail-closed behavior (safe over-rejection of a non-portable form).",
    ),
    (
        "a{}",
        REJECT,
        "Empty braces a{} is REJECTED: bounded requires a number after '{' (regex.fltkg:93-95) -> fails; '{' excluded by literal_char -> stall after 'a' -> reject. Python re treats a{} as a literal '{}'; Rust regex-automata also treats it as a literal here, but a bare '{' is the non-portable opener this grammar fails closed on (regex.fltkg:85-91). Safe over-rejection.",
    ),
    (
        "a{2",
        REJECT,
        "Unterminated bound a{2 is REJECTED: bounded requires a closing '}' (regex.fltkg:93-95); end-of-input before '}' -> bounded fails -> '{' excluded by literal_char -> stall after 'a' -> reject. Rust regex-automata errors on an unterminated repetition; Python treats it as a literal '{2'. Non-portable -> correctly rejected.",
    ),
    (
        "}",
        ACCEPT,
        "Bare close brace }: literal_char admits '}' (it is not in the excluded set, regex.fltkg:328) -> ACCEPT. Both engines treat bare '}' as a literal (portable).",
    ),
    (
        "a}b",
        ACCEPT,
        "Close brace in middle a}b: each char parsed as literal_char -> ACCEPT. Both engines treat bare '}' outside a bounded group as a literal (portable).",
    ),
    (
        "]",
        ACCEPT,
        "Bare close bracket ]: literal_char includes ']' (only '[' is excluded) -> ACCEPT. Both engines treat bare ']' outside a class as a literal (portable, regex.fltkg:316-328).",
    ),
    (
        "a]b",
        ACCEPT,
        "Close bracket in middle a]b: each char is literal_char -> ACCEPT. Both engines treat ']' outside a class as a literal (portable).",
    ),

    # -------------------------------------------------------------------------
    # Flag divergence
    # -------------------------------------------------------------------------
    (
        "(?x)",
        REJECT,
        "Verbose flag (?x): flag_chars := /[imsU]+/ -- 'x' is NOT in [imsU] -> flag_chars fails -> inline_flags fails -> group tries non_capturing/flag_group/capturing, none match '(?x)' -> reject. (?x) changes body semantics (strips whitespace, '#' comments) which this grammar cannot model (regex.fltkg:150-158).",
    ),
    (
        "(?-i)",
        REJECT,
        "Flag negation (?-i): '(?' then '-' -- '-' is not in flag_chars /[imsU]+/ -> flag_chars fails -> inline_flags/flag_group both fail; '(?-' is not '(?:' so non_capturing fails; '(?' consumed but remaining '-i)' is not a valid group body -> reject. Python re rejects (?-i); Rust accepts it -> non-portable (regex.fltkg:127-130).",
    ),
    (
        "(?i-s:a)",
        REJECT,
        "Flag negation scoped (?i-s:a): flag_group sees '(?' then tries flag_chars /[imsU]+/ which matches 'i', then expects ':' but sees '-' -> flag_group fails; no other group matches '(?i-s:a)' -> reject. Rust accepts (?i-s:...) negation forms; Python does not -> non-portable.",
    ),
    (
        "(?i)",
        ACCEPT,
        "Inline flag (?i): inline_flags := %'(?' . flags:flag_chars . %')' -- flag_chars matches 'i' -> ACCEPT. Both engines accept (?i) (regex.fltkg:148).",
    ),
    (
        "(?ms)",
        ACCEPT,
        "Inline flags (?ms): flag_chars /[imsU]+/ matches 'ms' -> ACCEPT. Both engines accept (?ms) (regex.fltkg:148).",
    ),
    (
        "(?i:a)",
        ACCEPT,
        "Flag group (?i:a): flag_group := %'(?' . flags:flag_chars . %':' . body . %')' -- 'i' then ':' then 'a' then ')' -> ACCEPT. Both engines accept (?i:...) (regex.fltkg:142).",
    ),
    (
        "(?ms:a)",
        ACCEPT,
        "Flag group (?ms:a): flag_chars 'ms' then ':' -> flag_group -> ACCEPT. Both engines accept (?ms:...) (regex.fltkg:142).",
    ),
    (
        "(?U)",
        ACCEPT,
        "FINDING: (?U) is ACCEPTED by grammar (flag_chars /[imsU]+/ includes 'U') but Python re rejects it ('unknown extension ?U'). The 'U' flag is a Rust regex-automata concept (swaps greedy/non-greedy globally) not supported inline by Python re. This is a grammar over-admission relative to Python: the grammar accepts (?U) but it cannot be used portably in a Python-backend FLTK grammar. The grammar author chose to include U because the regex.fltkg grammar is intended for the portability-lint recognizer running on the Rust side; FLTK grammars intended for the Python backend should not use (?U) inline. Documented here for awareness rather than as a grammar fix, since the design explicitly lists U as an admitted flag.",
        True,  # skip_re_check: Python re rejects (?U) -- this is the documented over-admission finding
    ),
    (
        "(?iU)",
        ACCEPT,
        "FINDING (F2 family): (?iU) is ACCEPTED (flag_chars /[imsU]+/ matches 'iU') but Python re rejects it ('unknown flag' at the U). Confirms the U over-admission is not limited to bare (?U): U combined with a Python-valid flag still produces a Python-invalid inline-flag group. Same disposition as (?U) -- Rust-only flag admitted by design.",
        True,  # skip_re_check: Python re rejects 'U' flag
    ),
    (
        "(?U:a)",
        ACCEPT,
        "FINDING (F2 family): (?U:a) is ACCEPTED as a flag_group (flag_chars 'U' then ':' then body 'a' then ')'). Python re rejects '(?U:...)' ('unknown extension ?U'). Confirms the U over-admission reaches the SCOPED flag-group form too, not just inline (?U). Documented; the grammar admits U by design for the Rust-side recognizer.",
        True,  # skip_re_check: Python re rejects (?U:...) scoped flag group
    ),
    (
        "(?)",
        REJECT,
        "Empty inline flags (?) is REJECTED: inline_flags := '(?' flag_chars ')' and flag_chars := /[imsU]+/ requires at least one flag char (regex.fltkg:148,159); ')' immediately after '(?' gives no flag char -> inline_flags fails; flag_group/non_capturing/capturing also fail on '(?)' -> reject. Python re also rejects (?) ('unknown extension ?)') -> both reject -> correctly excluded.",
    ),

    # -------------------------------------------------------------------------
    # In-class escape divergence
    # -------------------------------------------------------------------------
    (
        r"[\b]",
        REJECT,
        r"In-class \b: class_escape_body := class_shorthand | char_escape; assertion (/[bB]/) is NOT in class_escape_body -> escape_body alternative fails -> class body stalls -> reject. Python re treats [\b] as backspace; Rust regex-automata rejects [\b] -> divergent -> correctly excluded (regex.fltkg:228-239).",
    ),
    (
        r"[\B]",
        REJECT,
        r"In-class \B: same as [\b] -- assertion /[bB]/ not in class_escape_body -> reject. Rust regex-automata rejects [\B]; Python re matches on non-word-boundary position -> divergent.",
    ),
    (
        r"[\A]",
        REJECT,
        r"In-class \A: anchor_escape /[Az]/ is NOT in class_escape_body (class_escape only allows class_shorthand + char_escape) -> reject. Both Python re and Rust regex-automata reject [\A] inside a class -> correctly excluded (regex.fltkg:228-239).",
    ),
    (
        r"[\z]",
        REJECT,
        r"In-class \z: anchor_escape /[Az]/ not in class_escape_body -> reject. Both engines reject [\z] inside a class -> correctly excluded.",
    ),
    (
        r"[\d]",
        ACCEPT,
        r"In-class \d: class_escape_body -> class_shorthand /[dDwWsS]/ matches 'd' -> ACCEPT. Both engines accept [\d] (regex.fltkg:270).",
    ),
    (
        r"[\w\s]",
        ACCEPT,
        r"In-class \w\s: two class_escape items, each via class_shorthand -> ACCEPT. Both engines accept [\w\s] (regex.fltkg:270).",
    ),
    (
        r"[\n-\r]",
        ACCEPT,
        r"In-class range \n-\r: class_range with lo=class_char_escape(\n via control_escape) and hi=class_char_escape(\r via control_escape) -> ACCEPT. Both engines accept this range (regex.fltkg:201).",
    ),
    (
        r"[\x41-\x5a]",
        ACCEPT,
        r"In-class hex range [\x41-\x5a]: class_range with lo=class_char_escape(\x41 via hex_escape) and hi=class_char_escape(\x5a via hex_escape) -> ACCEPT. Both engines accept this range (regex.fltkg:201).",
    ),
    (
        r"[\07]",
        ACCEPT,
        r"FINDING (F1 family -- in-class): [\07] is ACCEPTED via the SAME over-admission as top-level \07. The class_escape_body path (regex.fltkg:234-239) uses char_escape -> control_escape /[nrtfv0a]/ which matches '\0', leaving '7' to be consumed as an ordinary class_char -> ACCEPT. Python re reads [\07] as a class containing octal chr(7); Rust regex-automata rejects octal inside a class too. The F1 finding (control_escape admits \0 + following digit) applies identically in-class and at top-level; this pins the in-class reachable path so the documented gap is complete.",
    ),
    (
        r"[\0]",
        ACCEPT,
        r"In-class \0 (null, no following digit): class_escape_body -> char_escape -> control_escape /[nrtfv0a]/ matches '\0'; no trailing digit -> genuinely portable (\0 = null, both engines accept). Pinned alongside [\07] to show the gap is specifically \0 + octal-digit inside a class, not \0 alone.",
    ),

    # =========================================================================
    # OVER-REJECTION / BOUNDARY PROBES
    # Try to make the grammar choke on something portable or degenerate but legal.
    # =========================================================================

    # -------------------------------------------------------------------------
    # Empty / nilable shapes (§6 edge case)
    # -------------------------------------------------------------------------
    (
        "",
        ACCEPT,
        "Empty pattern: regex := alternation; alternation has seed 'branch:concatenation?' where concatenation is optional -> alternation can match empty -> result.pos=0==len('') -> ACCEPT. The lint's check_regex_portable treats '' as portable and special-cases it; here we pin what the bare parser actually does (regex.fltkg:51-52, §6 of design).",
    ),
    (
        "()",
        ACCEPT,
        "Empty capturing group: capturing := %'(' . body:alternation . %')' -- alternation matches empty -> ACCEPT. Both engines accept () (regex.fltkg:144).",
    ),
    (
        "(?:)",
        ACCEPT,
        "Empty non-capturing group: non_capturing := %'(?:' . body:alternation . %')' -- alternation matches empty -> ACCEPT. Both engines accept (?:) (regex.fltkg:139).",
    ),
    (
        "a|",
        ACCEPT,
        "Trailing alternation a|: alternation := left:alternation . %'|' . right:concatenation? -- concatenation is optional (right may be empty) -> ACCEPT. Both engines accept a| (regex.fltkg:69).",
    ),
    (
        "|a",
        ACCEPT,
        "Leading alternation |a: alternation seed 'branch:concatenation?' matches empty (empty left branch), then left-recursive step picks up '|' . 'a' -> ACCEPT. Both engines accept |a.",
    ),
    (
        "a||b",
        ACCEPT,
        "Empty middle branch a||b: alternation is left-recursive; first pass: a| (right=empty), second: (a|)|b -> ACCEPT. Both engines accept empty middle branches.",
    ),

    # -------------------------------------------------------------------------
    # PEG first-match / shadowing probes
    # -------------------------------------------------------------------------
    (
        "(?:ab)",
        ACCEPT,
        "Non-capturing group (?:ab): atom -> group -> non_capturing (tried first) matches '(?:' -> ACCEPT. Confirms that '(?:' opener is recognized before bare '(' (regex.fltkg:134-137).",
    ),
    (
        "(?i:ab)",
        ACCEPT,
        "Flag-scoped group (?i:ab): atom -> group -> non_capturing fails ('(?i' != '(?:'); flag_group '(?' + flag_chars 'i' + ':' -> ACCEPT. Confirms flag_group is tried before bare capturing (regex.fltkg:134-137, 142).",
    ),
    (
        "(ab)",
        ACCEPT,
        "Bare capturing group (ab): atom -> group -> non_capturing fails ('(a' != '(?:'); flag_group fails ('a' not in flag_chars); capturing '(' . alternation . ')' -> ACCEPT (regex.fltkg:144).",
    ),
    (
        "(?i)",
        ACCEPT,
        "Inline flags (?i) -- not shadowed by flag_group: atom -> group tries non_capturing '(?:' -> fail; flag_group '(?' + 'i' + ':' -> fail (')' is not ':'); then inline_flags '(?' + 'i' + ')' -> ACCEPT. Confirms disambiguation between flag_group and inline_flags (regex.fltkg:148).",
    ),
    (
        r"\d",
        ACCEPT,
        r"Shorthand escape \d: atom -> escape -> escape_body -> class_shorthand /[dDwWsS]/ matches 'd' -> ACCEPT. Confirms escape path preferred over literal_char (which does not admit '\') (regex.fltkg:264,270).",
    ),
    (
        "d",
        ACCEPT,
        "Bare literal 'd': atom -> literal_char /[^.*+?()[|^$\\{\\n]/ matches 'd' -> ACCEPT. Pins that 'd' alone (without backslash) is just a literal.",
    ),

    # -------------------------------------------------------------------------
    # Deep / awkward nesting
    # -------------------------------------------------------------------------
    (
        "a|b|c|d|e|f|g|h|i|j|k|l|m|n|o|p|q|r|s|t|u|v|w|x|y|z",
        ACCEPT,
        "Long 26-way alternation: left-recursive alternation rule grows through all 26 branches -> ACCEPT. Stresses packrat seed-growing for alternation (regex.fltkg:68-70).",
    ),
    (
        "(((((a)))))",
        ACCEPT,
        "Deeply nested capturing groups: 5 levels of capturing -> ACCEPT. Stresses left-recursive concatenation and capturing group parsing (regex.fltkg:75-77, 144).",
    ),
    (
        "((((a|b)c)d)e)",
        ACCEPT,
        "Complex nested alternation+concatenation: 4-level nesting with alternation at inner level -> ACCEPT. Stresses both left-recursion dimensions (regex.fltkg:68-70, 75-77).",
    ),

    # -------------------------------------------------------------------------
    # Whitespace-significant patterns (§6, §4.2)
    # -------------------------------------------------------------------------
    (
        " a",
        ACCEPT,
        "Leading literal space: literal_char /[^.*+?()[|^$\\\\{\\n]/ admits space (not in excluded set) -> ' ' is literal_char, 'a' is literal_char -> ACCEPT. Guards that the NO_WS separator contract holds and the auto-injected _trivia rule is NOT stripping the leading space (regex.fltkg:26-30).",
    ),
    (
        " *",
        ACCEPT,
        "Space-star ' *': space is literal_char -> atom; '*' is quantifier(zero_or_more) -> repetition -> ACCEPT. This is clockwork's actual ` *` pattern. Guards whitespace-significance (regex.fltkg:26-30).",
    ),
    (
        "\ta",
        ACCEPT,
        "Leading literal tab: tab is not in literal_char's excluded set -> literal_char -> ACCEPT. Guards that tabs are not stripped by _trivia (same NO_WS property).",
    ),
    (
        "a b",
        ACCEPT,
        "Space in the middle of a pattern 'a b': each char is literal_char -> concatenation of three atoms -> ACCEPT. Guards that interior whitespace is not stripped.",
    ),

    # -------------------------------------------------------------------------
    # Pathological dashes and carets in classes
    # -------------------------------------------------------------------------
    (
        "[a^b]",
        ACCEPT,
        "Non-leading caret in class [a^b]: 'a' is class_char, '^' is class_char (class_char /[^\\\\\\]\\[\\-\\n]/ does not exclude '^'), 'b' is class_char -> class_body items -> ACCEPT. Both engines accept [a^b] (regex.fltkg:216-219).",
    ),
    (
        "[a^]",
        ACCEPT,
        "Caret at end of class [a^]: 'a' and '^' are both class_char -> ACCEPT.",
    ),
    (
        "[^^]",
        ACCEPT,
        "Leading caret then caret [^^]: char_class %'[' . negated:'^'? . class_body . %']' -- first '^' is consumed as negated, then class_body sees '^' as class_char (non-empty body) -> ACCEPT. Both engines accept [^^] (regex.fltkg:186, 216-219).",
    ),
    (
        "[+\\-]",
        ACCEPT,
        r"Escaped dash in class [+\-]: '+' is class_char, then class_escape_body -> meta_escape admits '\-' (dash is in meta_escape set, regex.fltkg:308) -> ACCEPT. Both engines accept [\-] as a literal dash.",
    ),

    # -------------------------------------------------------------------------
    # Quantifier-on-quantifier and lazy markers (§4.2)
    # -------------------------------------------------------------------------
    (
        "a*?",
        ACCEPT,
        "Lazy star a*?: quantifier := (zero_or_more:'*') . lazy:'?'? -- '*' then '?' as lazy marker -> ACCEPT. Both engines support lazy quantifiers (regex.fltkg:83).",
    ),
    (
        "a+?",
        ACCEPT,
        "Lazy plus a+?: quantifier := (one_or_more:'+') . lazy:'?'? -> ACCEPT. Both engines support lazy plus.",
    ),
    (
        "a??",
        ACCEPT,
        "Lazy optional a??: quantifier := (optional:'?') . lazy:'?'? -> ACCEPT. Both engines support lazy optional.",
    ),
    (
        "a{2,4}?",
        ACCEPT,
        "Lazy bounded a{2,4}?: quantifier := bound:bounded . lazy:'?'? -> ACCEPT. Both engines support lazy bounded quantifiers.",
    ),
    (
        "a**",
        REJECT,
        "Stacked star-star a**: repetition := atom . quantifier? -- first quantifier '?' is optional and consumed as the single quantifier for 'a'; second '*' is NOT part of any production following the quantifier -> stall after 'a*' -> reject (short parse). repetition allows exactly one quantifier? (regex.fltkg:80).",
    ),
    (
        "a*+",
        REJECT,
        "Stacked star-plus a*+: same as a** -- parser matches 'a*' (complete repetition), then '+' has no production -> short parse -> reject.",
    ),
    (
        "a+*",
        REJECT,
        "Stacked plus-star a+*: same as a** -- 'a+' is a complete repetition, then '*' -> short parse -> reject.",
    ),
    (
        "*",
        REJECT,
        "Dangling quantifier '*' (no atom): repetition := atom . quantifier? requires a leading atom (regex.fltkg:80); a bare '*' is not literal_char (excluded) and has no atom production -> reject. BOTH engines reject a leading '*' ('nothing to repeat') -> correctly excluded.",
    ),
    (
        "+",
        REJECT,
        "Dangling quantifier '+' (no atom): same as '*' -- '+' has no atom production and repetition needs an atom first -> reject. Both engines reject leading '+' ('nothing to repeat').",
    ),
    (
        "?",
        REJECT,
        "Dangling quantifier '?' (no atom): '?' has no atom production -> reject. Both engines reject leading '?' ('nothing to repeat').",
    ),
    (
        "{2}",
        REJECT,
        "Dangling bound '{2}' (no atom): repetition needs an atom before the quantifier; '{' is excluded from literal_char and there is no preceding atom -> reject. Both engines reject a leading bound ('nothing to repeat').",
    ),

    # =========================================================================
    # UTF-8 / NON-ASCII PROBES (REQUIRED — §4.2, §4.3)
    # All non-ASCII patterns are parsed as Unicode codepoints; positions are
    # codepoints on both backends (Python TerminalSource len() + re.match(pos=),
    # Rust Span start/end in codepoints via cp_to_byte). These cases are
    # *required* (not optional) because the in-tree corpus grammars are pure ASCII
    # so this is the only place the codepoint-vs-byte hazard class is probed.
    # =========================================================================

    # -------------------------------------------------------------------------
    # Multi-byte literal characters (2-byte, 3-byte, 4-byte/astral)
    # -------------------------------------------------------------------------
    (
        "café",
        ACCEPT,
        "Multi-byte literal chars 'café': 'c','a','f' are ASCII literal_char; 'é' (U+00E9, 2 UTF-8 bytes) is non-ASCII and NOT in literal_char's excluded set (only ASCII metacharacters excluded) -> each codepoint is a literal_char -> ACCEPT. Non-ASCII literal_chars are portable on both engines (§4.3).",
    ),
    (
        "αβγ",
        ACCEPT,
        "Greek letters 'αβγ': each is a 2-byte non-ASCII codepoint admitted as literal_char -> ACCEPT. Both engines accept non-ASCII literal chars.",
    ),
    (
        "中文",
        ACCEPT,
        "CJK characters '中文': each is a 3-byte non-ASCII codepoint admitted as literal_char -> ACCEPT.",
    ),
    (
        "a\U0001d11eb",
        ACCEPT,
        "Astral-plane codepoint in the middle 'a\U0001d11eb': U+1D11E (MUSICAL SYMBOL G CLEF, 4 UTF-8 bytes) is one Python str codepoint, one Rust char, admitted as literal_char -> ACCEPT. Stresses codepoint-vs-byte position handling with a 4-byte character (§4.3).",
    ),

    # -------------------------------------------------------------------------
    # Multi-byte characters at non-zero offsets (the key codepoint/byte hazard)
    # -------------------------------------------------------------------------
    (
        "é+",
        ACCEPT,
        "'é+': U+00E9 (2 UTF-8 bytes) as literal_char atom, then '+' quantifier -> ACCEPT. The accept predicate checks result.pos == len(terminals) in codepoints; a Rust cp_to_byte indexing bug would yield a wrong end position -> short parse -> reject. This directly guards the §4.3 hazard.",
    ),
    (
        "中*",
        ACCEPT,
        "'中*': U+4E2D (3 UTF-8 bytes) as literal_char atom, then '*' quantifier -> ACCEPT. Same codepoint/byte guard as 'é+' with a 3-byte character.",
    ),
    (
        "café\\d",
        ACCEPT,
        r"'café\d': 3 ASCII + 1 two-byte codepoint, then \d shorthand -> ACCEPT. The multi-byte character at position 3 must not corrupt the escape parse at position 4 (codepoint index).",
    ),
    (
        "αβγ{2}",
        ACCEPT,
        "'αβγ{2}': 3 two-byte codepoints then bounded quantifier {2} -> ACCEPT. Non-zero offset bounded quantifier after multi-byte chars stresses codepoint indexing in bounded parsing.",
    ),
    (
        "a\U0001d11eb?",
        ACCEPT,
        "'a\U0001d11eb?': ASCII + 4-byte astral codepoint + '?' quantifier -> ACCEPT. The '?' lazy-check at position 3 (codepoint) must not mistake the 4-byte boundary.",
    ),

    # -------------------------------------------------------------------------
    # Multi-byte characters inside classes
    # -------------------------------------------------------------------------
    (
        "[é]",
        ACCEPT,
        "[é]: U+00E9 is class_char (not in excluded ASCII set) -> class_body items -> ACCEPT. Non-ASCII class members are portable on both engines.",
    ),
    (
        "[中-中]",
        ACCEPT,
        "[中-中]: class_range with lo=class_char(中) and hi=class_char(中) -> ACCEPT. Non-ASCII range endpoint accepted as class_char; the range is trivially satisfied. Codepoint-correct class range parsing.",
    ),
    (
        "[a-zé]",
        ACCEPT,
        "[a-zé]: class_range a-z as class_item, then é as class_char class_member -> ACCEPT. Non-ASCII after a range is valid. Both engines accept non-ASCII class members.",
    ),
    (
        "[αβγ]",
        ACCEPT,
        "[αβγ]: three non-ASCII class_char items -> ACCEPT. Pure non-ASCII class body.",
    ),

    # -------------------------------------------------------------------------
    # Unicode shorthands (grammar acceptance, not runtime match-set parity)
    # -------------------------------------------------------------------------
    (
        r"\w+",
        ACCEPT,
        r"\w+ word shorthand with quantifier: escape_body -> class_shorthand /[dDwWsS]/ matches 'w' -> \w admitted; '+' quantifier -> ACCEPT. Grammar-level acceptance proven; note: cross-engine match-set parity for \w on non-ASCII input (e.g. whether 'é' matches \w) is a Unicode category-table divergence risk owned by the differential harness (lint §9), NOT proven here.",
    ),
    (
        r"\s",
        ACCEPT,
        r"\s space shorthand: class_shorthand 's' -> escape -> ACCEPT. Cross-engine match-set parity on non-ASCII whitespace (U+00A0 NO-BREAK SPACE, U+2028 LINE SEPARATOR) is a documented divergence risk, not asserted here.",
    ),
    (
        r"\b",
        ACCEPT,
        r"\b word-boundary assertion (top-level): escape_body -> assertion /[bB]/ matches 'b' -> ACCEPT. Note: \b behavior on non-ASCII input depends on each engine's Unicode category tables; parity is documented risk, not asserted here.",
    ),
    (
        r"\w",
        ACCEPT,
        r"\w word shorthand alone: class_shorthand 'w' -> ACCEPT. Grammar admits all class shorthands at top level (regex.fltkg:270).",
    ),

    # -------------------------------------------------------------------------
    # Combining marks / NFC vs NFD normalization
    # -------------------------------------------------------------------------
    (
        "é",  # U+00E9 é precomposed (NFC, 1 codepoint)
        ACCEPT,
        "NFC precomposed é (U+00E9, 1 codepoint): admitted as single literal_char -> ACCEPT. Neither backend normalizes: a pattern authored NFC will not match NFD input at runtime, but both backends agree on this non-match (no divergence). This pins that the grammar accepts both NFC and NFD forms as valid patterns; normalization is a documented-consistent non-issue.",
    ),
    (
        "é",  # U+0065 e + U+0301 combining acute (NFD, 2 codepoints)
        ACCEPT,
        "NFD decomposed é (U+0065 e + U+0301 combining acute, 2 codepoints): each codepoint is admitted as literal_char -> two-atom concatenation -> ACCEPT. Python str len=2; neither backend normalizes. Pins that the grammar handles NFD content without error.",
    ),

    # -------------------------------------------------------------------------
    # Astral-plane / supplementary codepoints (4-byte in UTF-8)
    # -------------------------------------------------------------------------
    (
        "\U0001d11e",  # G clef, U+1D11E, 4 UTF-8 bytes
        ACCEPT,
        "Astral-plane codepoint alone 𝄞 (U+1D11E, 4 UTF-8 bytes): one Python str codepoint, one Rust char scalar, admitted as literal_char -> ACCEPT. The strongest exerciser of the 4-byte cp_to_byte path; result.pos==1==len confirms single-codepoint treatment.",
    ),
    (
        "\U0001d11e?",
        ACCEPT,
        "Astral codepoint with optional quantifier 𝄞?: literal_char(𝄞) . quantifier(optional:'?') -> ACCEPT. Quantifier at position 1 (codepoint) must not be mis-addressed as byte position 4.",
    ),
    (
        "\U0001d11e+",
        ACCEPT,
        "Astral codepoint with plus quantifier 𝄞+: literal_char(𝄞) . quantifier(one_or_more:'+') -> ACCEPT. Same position-indexing guard as 𝄞?.",
    ),
    (
        "a\U0001f600b",  # ASCII + emoji U+1F600 + ASCII
        ACCEPT,
        "Emoji in the middle a😀b (U+1F600, 4 UTF-8 bytes): a=literal_char, 😀=literal_char, b=literal_char -> three-atom concatenation -> ACCEPT. result.pos==3==len confirms each codepoint counted once regardless of byte width.",
    ),

    # -------------------------------------------------------------------------
    # Bidirectional / RTL text in literals
    # -------------------------------------------------------------------------
    (
        "שלום",  # shalom Hebrew (4 x 2-byte codepoints)
        ACCEPT,
        "Hebrew RTL codepoints shalom (4 x U+05xx, 2 UTF-8 bytes each): each is literal_char -> ACCEPT. No parser logic is direction-sensitive; result.pos==4==len confirms codepoint-correct counting. Span.text() extraction (if used) returns the raw codepoint range, not visually reordered.",
    ),
    (
        "مرحبا",  # marhaba Arabic (5 x 2-byte codepoints)
        ACCEPT,
        "Arabic RTL codepoints marhaba (5 x U+06xx, 2 UTF-8 bytes each): each is literal_char -> ACCEPT. Same direction-agnostic property as Hebrew.",
    ),

    # =========================================================================
    # ANCHORS AND TOP-LEVEL ASSERTIONS
    # =========================================================================
    (
        "^abc",
        ACCEPT,
        "Caret anchor ^abc: anchor := caret:'^' -> atom -> then 'abc' as literals -> ACCEPT. Both engines accept ^ (regex.fltkg:121).",
    ),
    (
        "abc$",
        ACCEPT,
        "Dollar anchor abc$: '$' -> anchor(dollar) -> ACCEPT. Both engines accept $ (regex.fltkg:121).",
    ),
    (
        r"\A",
        ACCEPT,
        r"\A anchor escape (top-level): escape_body -> anchor_escape /[Az]/ matches 'A' -> ACCEPT. Both engines accept \A at top level (not inside a class) (regex.fltkg:278-280).",
    ),
    (
        r"\z",
        ACCEPT,
        r"FINDING: \z anchor escape (top-level): anchor_escape /[Az]/ matches 'z' -> grammar ACCEPTS. Rust regex-automata accepts \z as 'end of text' anchor; Python re rejects \z ('bad escape \z'). The grammar's anchor_escape /[Az]/ was designed to accept both \A and \z as portable anchors, but Python re only accepts \Z (uppercase) for end-of-text, not \z (lowercase). This is an over-admission relative to Python: \z is Rust-portable but not Python-portable. The grammar comment (regex.fltkg:278-280) says 'portable at top level on both engines (verified)' which appears incorrect for Python re >= 3.6 (which raises 'bad escape' for unknown backslash sequences). Documented as a FINDING; fixing would require removing 'z' from anchor_escape or using /[A]/ + separate \z rule, which is the downstream lint increment's call.",
        True,  # skip_re_check: Python re rejects \z ('bad escape') -- documented over-admission finding
    ),
    (
        r"\B",
        ACCEPT,
        r"\B non-word-boundary assertion: escape_body -> assertion /[bB]/ matches 'B' -> ACCEPT. Both engines accept \B at top level (regex.fltkg:274).",
    ),

    # =========================================================================
    # DOT METACHARACTER
    # =========================================================================
    (
        ".",
        ACCEPT,
        "Dot metacharacter: atom -> dot := value:'.' -> ACCEPT. Both engines accept '.' (regex.fltkg:117).",
    ),
    (
        "a.b",
        ACCEPT,
        "Dot in middle a.b: a=literal_char, .=dot, b=literal_char -> ACCEPT.",
    ),
]
# fmt: on

# ---------------------------------------------------------------------------
# Parametric test
# ---------------------------------------------------------------------------

_IDS = [row[0][:30].replace("[", "(").replace("]", ")").replace("\n", "\\n").replace("\t", "\\t") for row in CASES]

# Unpack rows uniformly (the optional 4th element defaults to False).
_UNPACKED = [(row[0], row[1], row[2], row[3] if len(row) == 4 else False) for row in CASES]  # type: ignore[misc]


@pytest.mark.parametrize("pattern,expected,rationale,skip_re_check", _UNPACKED, ids=_IDS)
def test_adversarial_case(
    pattern: str,
    expected: bool,  # noqa: FBT001
    rationale: str,
    skip_re_check: bool,  # noqa: FBT001
) -> None:
    """Assert the grammar's accept/reject disposition matches the expected value.

    - For ACCEPT cases: also cross-check with Python ``re.compile`` (§4.1), unless
      ``skip_re_check=True`` (used only for documented grammar over-admissions where
      the grammar accepts a pattern that Python re rejects -- these carry a FINDING: rationale).
    - For REJECT cases: rationale string is the only oracle (§4.1 asymmetry note).
    - Rationale is asserted non-empty so every case is self-documenting.
    """
    assert rationale, "Every adversarial case must have a non-empty rationale string."

    actual = classify_pattern(pattern)

    if actual != expected:
        disposition = "ACCEPT" if expected else "REJECT"
        actual_str = "ACCEPT" if actual else "REJECT"
        pytest.fail(f"Pattern {pattern!r}: expected {disposition}, got {actual_str}.\nRationale: {rationale}")

    # ACCEPT-direction cross-check: if the grammar accepts it, Python re must also --
    # unless skip_re_check is set (documented grammar over-admissions; see FINDING: rationales).
    if expected is ACCEPT and pattern != "" and not skip_re_check:
        try:
            re.compile(pattern)
        except re.error as exc:
            pytest.fail(
                f"ACCEPT mis-spec: grammar accepted {pattern!r} but Python re.compile rejects it: {exc}\n"
                f"Rationale: {rationale}"
            )
