No findings from either notes-shipgate-scope.md or notes-shipgate-slop.md.

User directive (notes-shipgate-user.md) requires Protocol class names match concrete CST class names exactly (bare names, no `Node` suffix). Current implementation already satisfies this: fltk_cst_protocol.py uses `Grammar`, `Rule`, `Alternatives`, `Items`, `Item`, `Term`, `Disposition`, `Quantifier`, `Identifier`, `RawString`, `Literal`, `Trivia`, `LineComment`, `BlockComment` — no `Node` suffix anywhere. fltk2gsm.py imports as `cst` and uses `cst.Grammar`, `cst.Rule`, etc. (same bare names). No changes required.

No commits made; HEAD is d2e7757. make check: exit 0.
