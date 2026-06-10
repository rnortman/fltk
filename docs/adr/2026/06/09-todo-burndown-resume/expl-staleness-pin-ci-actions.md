# Staleness check: pin-ci-actions design

Concise. Precise. Token-dense. No fluff. Audience: smart LLM/human.

Reference: `docs/adr/2026/06/06-pin-ci-actions/design.md` (HEAD af6e6f3).
Intervening commit of note: `4c8f0ad` ("Rust CST holds native Span and children — no Python objects").

---

## `.github/workflows/ci.yml` — current state vs. design claims

Design claims (design.md root-cause section):

| Design claim | Actual at HEAD |
|---|---|
| `actions/checkout@v4` at `ci.yml:13` | CONFIRMED — `ci.yml:13`: `- uses: actions/checkout@v4` |
| `astral-sh/setup-uv@v6` at `ci.yml:17` | CONFIRMED — `ci.yml:17`: `uses: astral-sh/setup-uv@v6` |
| `dtolnay/rust-toolchain@stable` at `ci.yml:24` | CONFIRMED — `ci.yml:24`: `uses: dtolnay/rust-toolchain@stable` |
| TODO comments at `ci.yml:12,15,22` | CONFIRMED — all three `# TODO(pin-ci-actions):` comments present at exactly those lines |
| No SHA-pinned form anywhere in file | CONFIRMED — no `@[0-9a-f]{40}` anywhere in `ci.yml` |
| No `.github/dependabot.yml` exists | CONFIRMED — `.github/` contains only `workflows/`; `dependabot.yml` absent |

The `ci.yml` file is 31 lines total (unchanged from when the design was written). Commits `4c8f0ad` and `d40d8bc` touched `Makefile` targets (`make build-native build-test-user-ext build-fegen-rust-cst` at `ci.yml:27`, `make check` at `ci.yml:30`) but did NOT alter the three `uses:` lines or the TODO comments. Line numbers in the design remain accurate.

Design note: `design.md:15` states `TODO.md:15` holds the matching entry. Actual: `TODO.md:11` is the `## \`pin-ci-actions\`` header (the entry starts at line 11, not 15). This is a minor off-by-4 in the design's cross-reference to `TODO.md`; the entry itself is unchanged and present.

Design note: `design.md:56` says to remove `TODO.md:15-17`. Current `TODO.md` has the `pin-ci-actions` section at lines 11–13 (header + one-sentence body + blank line following). The line numbers in the removal instruction are stale, but the section content and slug are correct.

---

## TODO slug liveness

`TODO(pin-ci-actions)` is live at:
- `.github/workflows/ci.yml:12` — `# TODO(pin-ci-actions): Pin to immutable commit SHA.`
- `.github/workflows/ci.yml:15` — `# TODO(pin-ci-actions): Pin to immutable commit SHA.`
- `.github/workflows/ci.yml:22` — `# TODO(pin-ci-actions): Pin all action refs to immutable commit SHAs.`

`TODO.md` entry present at lines 11–13. Slug is live in both locations.

---

## Impact of commit 4c8f0ad on this design

`4c8f0ad` ("Rust CST holds native Span and children — no Python objects") is a Rust CST backend change. It touches `src/`, `crates/`, `fltk/fegen/gsm2tree_rs.py`, and related tests. It has zero interaction with `.github/workflows/ci.yml` or `.github/dependabot.yml`. The `pin-ci-actions` design is entirely about CI workflow configuration; it is orthogonal to Rust CST internals.

---

## Summary verdict

The design is **fully applicable as written** with two minor inaccuracies in cross-references to `TODO.md` line numbers (design cites lines 15 and 15–17; actual lines are 11 and 11–13). These do not affect the implementation steps — the slug and section content are unambiguous. All cited `ci.yml` line numbers, action refs, TODO comment text, and the absence of `dependabot.yml` remain accurate at HEAD af6e6f3.
