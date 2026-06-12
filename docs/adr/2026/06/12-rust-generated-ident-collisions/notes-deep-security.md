No findings.

(Reviewed d2abc80..4f66083. Change is build-time grammar validation in a code generator; input is developer-authored grammar, same trust level as source. Error messages embed rule names via `!r` repr, which escapes non-printable/format chars incl. bidi controls — no injection/spoofing vector. Module-level `assert` invariant check is skipped under `python -O`; consequence is a missed diagnostic (Rust E0428 at compile), not a security impact — noted, not a finding.)
