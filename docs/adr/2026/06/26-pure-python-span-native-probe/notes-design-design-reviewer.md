# Design review notes — pure-Python span native probe

Scope: verified design.md claims against source at base `49e9701`. Most citations check out
and are accurate (often more accurate than the explorations — e.g. design §2.6 correctly lists
all 10 committed parsers incl. `fltk_trivia_parser.py`, which the exploration omitted). The
hybrid-path interpretation is sound and `plumbing.generate_parser` is confirmed as the single,
complete chokepoint for the native-span flag (all in-tree Python-parser+Rust-CST construction
goes through it: `tests/test_phase4_rust_fixture.py:54`, `tests/test_clean_protocol_consumer_api.py:163`,
`fltk/plumbing.py:165`; the real all-Rust `fegen_rust_cst.parser.Parser` path is untouched and
already correct). `make gencode` regenerates every committed parser (`Makefile:242-261`).
`pygen` provides `module`/`if_`/`import_`/`stmt`/`expr` (`fltk/pygen.py:19,27,49,82`). Parity
helpers compare spans by `.start`/`.end`, not `==` (`tests/parser_parity.py:15-18,39-42`), so
edge case 4 holds. `extract_span` rejecting non-native spans confirmed
(`crates/fltk-cst-core/src/cross_cdylib.rs` `extract_span`, raises
`TypeError("expected fltk._native.Span, ...")`), and Rust CST `new`/`set_span` route through it
(`crates/fegen-rust/src/cst.rs:569-599`). Native `SourceText.__init__(text, filename=None)`
accepts keyword construction (`fltk/_native/__init__.pyi:39`). `test_gsm2tree_rs.py:1153` and
`:1222` pin the gsm2tree_rs span import and union annotation that §2.5 preserves.

## design-1

Section: §2.2, second bullet — "`_source_text` initializer (`:105-137`): emit the
`SourceText(text=..., filename=...)` call against the selected construction module ... instead
of the registry's `SourceText` import name." In tension with §2.1/§2.5 ("The type registry
entries for `Span`/`SourceText` ... are left registered to `("fltk","fegen","pyrt","span")`").

What's wrong: the design treats the two construction sites symmetrically as "change the module
string," and §2.2's first bullet is explicitly correct that `_make_span_expr` "already
constructs an `iir.VarByName` from a dotted string ... only the string changes"
(`gsm2parser.py:270-281` builds a `VarByName` from a string and calls `with_source` on it — a
string swap suffices). But the `_source_text` site is NOT structurally the same: it is built as
`iir.Construct.make(self.SourceTextType, text=..., filename=...)` (`gsm2parser.py:113-123`), and
the IIR compiler resolves a `Construct`'s class name through the type registry
(`compiler.py:312-315` → `iir_type_to_py_constructor` → `reg.TypeInfo.import_name(concrete=True)`,
`reg.py:26-29`). Because §2.5 freezes that registry entry to the `span` module, there is no
string to swap: a `Construct(SourceTextType)` will always compile to
`fltk.fegen.pyrt.span.SourceText(...)`. Retargeting it requires replacing the `Construct` node
with a registry-independent call expression (e.g.
`iir.MethodAccess("SourceText", iir.VarByName(name="fltk.fegen.pyrt.terminalsrc")).call(text=..., filename=...)`,
parallel to `_make_span_expr`) — a structural change the design never describes.

Why: source-backed above. The design's own §2.2 wording ("instead of the registry's `SourceText`
import name") shows the author knew the Construct resolves via the registry, but §2.2 gives no
mechanism for bypassing it and §2.5 simultaneously forbids changing the registry.

Consequence: a one-shot implementer following §2.2+§2.5 literally has no described way to retarget
the SourceText construction. The tempting shortcut — re-register `SourceTextType` (or, by the
design's symmetric treatment, also `Span`) to `terminalsrc`/`_native` — directly violates the
§2.5 frozen-registry invariant; if generalized to the `Span` entry it churns the public CST
**child** span annotations (which render `fltk.fegen.pyrt.span.Span` via that same registry, per
§1.4), i.e. exactly the public-API annotation churn CLAUDE.md forbids and the design set out to
avoid. Best case the implementer stalls reconciling the contradiction. The Span site is unaffected
by this (its string swap is genuinely correct); the gap is specific to the SourceText `Construct`.

Suggested fix: in §2.2, state that the `_source_text` init must be rebuilt from the
`iir.Construct.make(SourceTextType, ...)` into a module-qualified call expression keyed off the
selected construction-module string (mirroring `_make_span_expr`), leaving the type registry
entry untouched — so the Construct no longer drives the emitted class name.

## design-2

Section: §2.4, first bullet — "ensure `fltk._native` is resolvable by the exec'd parser (add it
to `parser_globals`, `:264-273`, alongside the existing `terminalsrc`)"; echoed in edge case 6
("`fltk._native` added to `parser_globals` on the native path").

What's wrong: on the native path the construction names emitted are `fltk._native.Span` /
`fltk._native.SourceText` (dotted access off the `fltk` package, which is already
`parser_globals["fltk"] = fltk`, `plumbing.py:271`). `fltk._native` resolves as
`getattr(fltk, "_native")`, which exists only if the `_native` submodule has actually been
imported in-process (binding it as an attribute on the `fltk` package object). Adding a dict
*key* `"fltk._native"` to `parser_globals` does not create that attribute and would not be
consulted for the dotted reference.

Why: `fltk._native` is a compiled submodule with no `__init__.py` (`fltk/_native/__init__.pyi:1-7`);
attribute resolution off `fltk` requires an explicit import to have run.

Consequence: if the implementer literally "adds it to parser_globals" rather than executing
`import fltk._native`, the native/hybrid-path parser raises `AttributeError: module 'fltk' has no
attribute '_native'` at the first construction site in any process where `_native` was not
already imported by some other path. Low severity because loading the Rust CST module may import
`_native` as a side effect, but the design should not rely on that incidental ordering.

Suggested fix: specify `import fltk._native` on the native path (after which the existing
`parser_globals["fltk"]` suffices), rather than "add it to parser_globals."
