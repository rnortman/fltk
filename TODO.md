# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `rule-preserve-blanks`

Rule-level `preserve_blanks` is parsed and stored but never consumed. `RuleConfig.preserve_blanks`
(`fltk/unparse/fmt_config.py`) and `FormatterConfig.get_preserve_blanks(rule_name)` exist, but both
unparser generators read the *global* `trivia_config.preserve_blanks` as a generation-time constant
rather than calling the rule-aware method, so a per-rule `preserve_blanks` directive has no effect.
Pre-existing feature gap, orthogonal to the blank-line-preservation bug fix. To close it, thread the
rule name to the newline-spacing emission and read `get_preserve_blanks(rule_name)`. Location:
`fltk/unparse/gsm2unparser.py` (both `# Get preserve_blanks from config` sites in
`_gen_trivia_processing`), `fltk/unparse/gsm2unparser_rs.py` (`_get_preserve_blanks`).

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

## `fmt-cli-per-consumer-version`

`fltk-fmt-cli`'s `FmtArgs` carries `#[command(version)]`, which clap expands to `CARGO_PKG_VERSION` where `FmtArgs` is defined — the scaffolding crate — so every consumer binary reports `fltk-fmt-cli`'s version, not its own. This is an observable defect today: `fltkfmt` is `0.1.0` (`crates/fltkfmt/Cargo.toml`; deliberately outside the root workspace with its own `[workspace]`), while `fltk-fmt-cli` is `0.2.0` (`crates/fltk-fmt-cli/Cargo.toml`), so `fltkfmt --version` prints `0.2.0` for a `0.1.0` binary. Fix by threading `version` (and possibly `name`) through `run_main` / `fltk_formatter_main!` the same way `about` is threaded (commit for `fmt-cli-per-consumer-about`), so `<consumer> --version` prints the consumer's own version. Do NOT add a second bare `&'static str` positional argument next to `about` on `run_main`: two adjacent indistinguishable string params can be swapped silently (a version string rendered as the `--help` description). Introduce an identity struct instead (e.g. `FormatterInfo::new(about).version(..)`, keeping `about` required) so this fix — and any later per-consumer knob — is a non-breaking addition rather than another signature break. Location: `crates/fltk-fmt-cli/src/lib.rs` (`#[command(version)]` on `FmtArgs`, and `run_main`).

## `lsp-cst-text-helpers`

`fltk/lsp/lsp_config.py`'s `_span_text` / `_identifier_text` and the inline literal-extraction
sequence in `_parse_anchor` duplicate helpers that already exist for `.fltkfmt`:
`fltk/unparse/fmt_config.py` (`_span_text`, `_extract_identifier_text`, `_extract_literal_text`)
and the more careful `fltk/unparse/pyrt.py:extract_span_text` (which guards against a
source-bearing span whose `text()` returns `None` — a guard the `fmt_config` and `lsp_config`
copies both lack). There is also a fourth single-backend copy at `fltk/fegen/fltk2gsm.py`
(`Cst2Gsm._span_text`). Consolidate into one canonical, `SpanProtocol`-typed helper (dropping
the `hasattr` probe and `type: ignore`s now that `SpanProtocol` includes `text()`), keeping the
pyrt source-bearing guard, and migrate all copies to it. Deferred because it touches out-of-round
modules (`fmt_config`, `unparse.pyrt`). Location: `fltk/lsp/lsp_config.py` (`_span_text`,
`_identifier_text`, `_parse_anchor`).

## `lsp-test-parse-helper`

`fltk/lsp/test_lsp_config.py` (`_load`) and `fltk/lsp/test_lsp_validation.py` (`_parse`) each
hand-roll the same `TerminalSource` → `Parser` → `apply__parse_lsp_spec` → full-consumption
check, diverging only on failure reporting (`_load` renders a caret diagnostic; `_parse`
bare-asserts). The design's `plumbing.parse_lsp_config` wrapper (not yet built) is the intended
home for this sequence; fold both helpers onto it once it lands, rather than building a throwaway
interim shared helper. Location: `fltk/lsp/test_lsp_config.py`, `fltk/lsp/test_lsp_validation.py`.

## `formatter-group-idempotency`

The formatter is not idempotent on grouped alternations at narrow widths: `fltk/fegen/test_data/rust_parser_fixture.fltkg` formatted at width 40 / indent 4 changes between pass 1 and pass 2 (a grouped alternation `( inner:rec_via_sub . "+" | inner:atom ) .` re-breaks into a multi-line `(` … `)` block on the second pass), converging only at pass 2. Single-pass cross-backend parity holds, so this is a shared formatter-layout bug present in both the Python and Rust backends, not a backend divergence. Fixing it is a formatter behavior change to both backends and was out of scope for the pure test addition that discovered it (`fltkfmt` integration tests). The idempotency integration test (`crates/fltkfmt/tests/cli.rs`, `format_format_is_format`) carves this one case out explicitly, pinning current behavior (`out2 != out1`, `out3 == out2`); when the formatter is fixed that carve-out's `assert_ne!` trips, forcing its removal alongside this entry. Location: `crates/fltkfmt/tests/cli.rs` (the `TODO(formatter-group-idempotency)` carve-out in `format_format_is_format`); the layout logic lives in the shared unparser/renderer (`fltk/unparse/` and the generated Rust unparser).

## `resolver-spec-file-recognition`

`fltk/lsp/resolver.py`'s `_looks_like_path` treats a `--resolver` spec head as a file whenever
`pathlib.Path(head).is_file()` — a cwd-relative check — even for a head that reads as a plain
module (no `.py`, no separator). So whether `--resolver mylang.resolvers:create_resolver` imports
the installed module `mylang.resolvers` or `exec`s a file literally named `mylang.resolvers`
depends on the server's cwd contents. Editors commonly spawn LSP servers with cwd = workspace
root, so a hostile project that plants a file matching a known resolver module name could get
arbitrary Python exec'd at startup for a user who configured a bare-module resolver spec. No
shipped config is affected (the gear demo and README use explicit `.py` paths). The fix — drop the
bare `is_file()` recognition, keeping only the unambiguous `.py`/separator signals — contradicts
the frozen step5 design §4.3 ("a path is recognized by an existing file"), so it requires a design
delta before landing; do it there, not by editing the frozen doc. Location: `fltk/lsp/resolver.py`
(`_looks_like_path`).

## `rename-guard-incomplete-scan`

`ProjectNavigator.rename_hazard` (`fltk/lsp/project.py`) decides whether a same-file rename is safe
by scanning the workspace for cross-file references. When that scan is incomplete -- a directory
`os.walk` error (surfaced only as an advisory `window/logMessage` warning), or a neighbor file that
is unreadable/unparseable and therefore dropped by `host.document()` -- the guard still returns
`Hazard.NONE` and permits the rename, so a cross-file reference hiding in the skipped file goes
undetected and the rename can silently break another file. This is the one fail-closed path (frozen
step5 design §4.6) meeting the read path's deliberate silent-degradation policy (§5:
transiently-broken neighbors are the normal state of live editing); the design did not resolve the
tension. Refusing on any imperfect scan would make rename nearly unusable during editing; permitting
weakens the guard. Reconciling requires a design delta (e.g. refuse only on walk/IO errors while
tolerating unparseable neighbors, or track scan completeness explicitly), not a respond-mode patch.
Location: `fltk/lsp/project.py` (`ProjectNavigator.rename_hazard`).

## `lsp-analysis-watchdog`

`fltk/lsp/server.py`'s analysis runs on a single-worker `ThreadPoolExecutor`, and Python worker
threads cannot be preempted. The engine already catches `RecursionError` and reports it as a normal
parse-failure diagnostic, but a truly non-terminating parse — catastrophic regex backtracking or an
unbounded grammar recursion that never hits the interpreter's recursion limit — starves every later
analysis for that server process: the protocol loop stays responsive (it is never blocked on the
worker) but that document, and every document analyzed after it, stops updating. Honoring the
engine's wall-clock promise fully needs either process isolation (run each analysis in a killable
subprocess) or a parser-level step/time budget threaded down into the generated parser — real design
work that would dominate this round. Deferred with the stale-token policy covering the degraded mode
meanwhile. Location: `fltk/lsp/server.py` (`FltkLanguageServer._analyze_blocking`).

## `lsp-classify-hotpath`

`fltk/lsp/classify.py`'s `classify` / `default_tokens` are the per-document hot path the M2
server will sit on. The once-per-grammar table build is now hoisted: `AnalysisEngine` builds a
`_GrammarTables` once in `__init__` and threads it into `classify` via the optional `tables`
parameter, so `highlight` no longer re-walks the grammar and recompiles every terminal regex per
call. Two internal inefficiencies remain, both confined to `classify.py` and neither forcing a
change to the engine seam's signature: (1) `_winner_segments` rescans all intervals per boundary
pair (O(n^2)); a sweep line maintaining the active set reaches the intended O(n log n); (2)
`classify` walks the analysis tree twice (`_explicit_intervals` then `_default_intervals`) — fold
default emission into the explicit walk. Both are the design-stage sweep-line/walk-fusion rewrite
of the interval-resolution core, best batched (shared walk/segment logic). Address before the M2
server ships (it drives `classify` per keystroke), or when profiling on a real grammar shows
`classify` latency dominates. Location: `fltk/lsp/classify.py` (`_winner_segments`, the second
`_default_intervals` loop in `classify`).

## `lsp-rule-surface-index`

`fltk/lsp/lsp_config.py`'s `_index_rule` (`RuleIndex`: labels / literals / invoked rules) and
`fltk/lsp/classify.py`'s `_build_terminal_table` (`_TerminalTable`: literals / regexes,
label-keyed) are two parallel per-rule walks over `rule.alternatives` × `gsm.for_each_item`, each
collecting an overlapping slice of a rule's item surface (literals appear in both). The definition
of "what a rule's items expose to anchors/classification" thus lives in two mirrored walkers in
two modules, and any drift shows up as validation accepting an anchor the classifier can't match.
Unify into one per-rule surface index (labels, literals, regexes, invoked rules; label-keyed views
derived from it) consumed by validation, resolution, and the classifier tables. Deferred rather
than done in respond-mode because it restructures private surfaces across two modules.
Location: `fltk/lsp/lsp_config.py` (`_index_rule`), `fltk/lsp/classify.py`
(`_build_terminal_table`).

The INLINE half of this is already handled and is no longer a reason to do the unification: `!`
dispositions are expanded into sub-expressions at the text→GSM parse boundary, so both walkers
receive a grammar in which an inlined rule's terminals already live in the parent rule's items.
Neither walker needs its own splice, and neither is forced to change by INLINE support. What
remains is the duplication itself.

## `rust-codegen-self-keyword`

The Rust CST backend emits uncompilable Rust for any grammar label or rule name whose
UpperCamelCase form is `Self`. `_rust_variant_name` (`fltk/fegen/gsm2tree_rs.py`) and the rule
class name both route through `naming.snake_to_upper_camel`, which has no keyword handling, and
`Self` is the only Rust keyword that survives camel-casing. Because `snake_to_upper_camel`
lowercases first and collapses underscores, the trigger set is `self`, `Self`, `SELF`, `self_`,
`_self`, `__self__` and friends — not just the literal `self`. A label named `self` emits
`enum {CN}Label { …, Self }` plus every `{CN}Label::Self` match arm; a rule named `self` emits
`pub struct Self`, `impl Self` and `NodeKind::Self`. rustc rejects both with "expected identifier,
found keyword `Self`" pointing into generated code, so a downstream consumer sees a build failure
in a file they did not write rather than a grammar-level error. The Python backend accepts these
names (`Label.SELF`, class `Self`) and parses normally, so this is a Rust-backend-only divergence;
no in-tree grammar uses such a name, which is why nothing catches it today.

`cst_ergonomics.RUST_UNRAWABLE_KEYWORDS` already contains `self` and correctly skips the ergonomic
bare accessor for such a label, so only the variant/class identifiers lack a guard. Two fix shapes:
reject at validation time next to the existing `_RESERVED_LABELS` / `_RESERVED_CLASS_NAMES` checks
in `RustCstGenerator.__init__` (both live in the Rust generator, so a Python-only consumer with a
`self` label is unaffected), or mangle the emitted Rust identifier while leaving the Python-visible
name (`SELF`) unchanged. Mangling would normally be a breaking rename of a generated public symbol,
but no consumer can depend on the current spelling because it does not compile. Whichever is
chosen, cover both the label path and the rule-name path, and add a fixture case — the Rust fixture
grammar has keyword labels (`type`, `match`) but nothing that camels to `Self`. Location:
`fltk/fegen/gsm2tree_rs.py` (`_rust_variant_name`, and the class-name collision check in
`RustCstGenerator.__init__`).

## `ast-terminal-repeat-synthesis`

`to_cst` on a terminal-only AST node rebuilds the CST by matching the node's `text` against one
regex per alternative, with a named capture group per included item
(`fltk/fegen/ast_model.py`, `_terminal_plan`). That construction cannot express an item whose
quantifier admits more than one occurrence — a single group would capture the whole run rather
than each occurrence — so `_terminal_plan` marks such an alternative unsynthesisable
(`pattern=None`), and `astrt.terminal_to_cst` raises `AstError` for it. The parse direction is
unaffected: `from_cst` reads the node's own span, so a rule like `word := c:/[a-z]/+ ;` converts
fine and only fails on the way back out. Closing this means splitting the text per occurrence
(walk the alternative's items left to right, matching each pattern at the current offset with
backtracking) and mirroring the algorithm in the Rust emitter so both backends synthesise the same
children. Location: `fltk/fegen/ast_model.py` (`_terminal_plan`'s `bounds != (1, 1)` return),
`fltk/fegen/pyrt/astrt.py` (`terminal_to_cst`).

## `ast-dispatch-order`

`alternatives_are_disjoint` (`fltk/fegen/grammar_shape.py`) decides whether two alternatives of a
rule can be told apart in the CST from their labeled children's occurrence counts and kinds alone.
It cannot use child *order*, so `x := a:num , b:name | b:name , a:num ;` reads as non-disjoint even
though the child order distinguishes the two, and the rule classifies as a merged product where a
sum would be sound. Closing this means an order-sensitive signature (the sequence of labeled item
positions per alternative, matched against the children in source order) in both the classifier and
the generated dispatch, on both backends. It must ship opt-in or with a major version: rules that
default to a merged product today would silently become sums, which is a breaking change to
generated public API for every downstream consumer of such a grammar. Location:
`fltk/fegen/grammar_shape.py` (`alternatives_are_disjoint`, and `alternatives_are_sum` /
`AltSignature` with it), `fltk/fegen/pyrt/astrt.py` (`AltSignature.accepts`).

## `ast-transparent-container-payload`

`transparent;` on a single-field product erases the rule to the type of its one field, but only
when that field occurs exactly once: an optional or repeated field is a generation error
(`_ModelBuilder.erased_product_payload`). Design §5.4 states the payload as "the field's type"
without restricting arity, so `list := "[" , (value , ("," , value)* , ","?)? , "]" ;` marked
`transparent;` should erase to `Vec<Value>` / `list[Value]` rather than being refused. Closing this
means composing two container levels: `FieldType` carries one `Container`, so a use site of an
erased collection payload needs `list[list[T]]` annotations, and `astrt.cursor` — which tells a
single value from a collection by `isinstance(value, list)` — would take a list-valued single field
for several values, so the emitter must construct the cursor explicitly at such positions.  Both
halves have to land in the Rust emitter the same way, or the two ASTs stop being shape-equivalent.
Location: `fltk/fegen/ast_model.py` (`_ModelBuilder.erased_product_payload`'s arity check),
`fltk/fegen/gsm2ast.py` (`field_annotation`, `cursor_expression`).

## `rust-cst-memberless-nodes`

The Rust CST generator refuses any rule whose model has no members (`gsm2tree_rs.py`,
`_rule_info`: "Model class ... would have no members"), while the Python CST generator accepts one.
Two AST-modelable shapes are therefore unreachable on the Rust backend: a marker product spelled
with `.` separators (`marker := $"!" . $"?" ;` — a rule whose included items are all unlabeled
literals, which the AST models as a span-only node) and an unlabeled-unincluded terminal rule. This
is pre-existing CST-generator behavior, not AST-layer debt, and the workaround is to `$`-include a
terminal so the node has one member. Closing it means teaching the Rust CST generator to emit a
memberless node — the node struct, its child and label enums (which have no variants), and the
parser plumbing that appends nothing — which is its own bounded design. Until it is closed, the
Python/Rust AST parity suite must carve these two shapes out as a known divergence rather than
reporting them as a backend bug. Location: `fltk/fegen/gsm2tree_rs.py` (the `if not model.types:`
guard in `_rule_info`).

## `ast-deep-clone-debug`

Generated Rust fold types derive `Clone` and `Debug` (`gsm2ast_rs.py`, `_NODE_DERIVES`), and both
derives recurse once per chain link, so cloning or `{:?}`-formatting a fold chain of some tens of
thousands of operands overflows the stack — the same hazard the emitted iterative `Drop` closes for
teardown and the emitted `eq_walk` closes for comparison. Unlike those two, `Clone` and `Debug` are
explicit consumer calls: they are avoidable, no design law rests on them, and a consumer who needs
neither pays nothing. So v1 documents the limit rather than emitting worklist implementations.
Closing it means emitting a written-out `Clone` (build the new chain bottom-up from a worklist over
the old one) and `Debug` (render iteratively, or bound the depth) for the types the recursion
analysis marks `deep`, in place of the derives. Do it when a consumer actually hits it — the
`PartialEq` walk is the shape to copy. Location: `fltk/fegen/gsm2ast_rs.py` (`_NODE_DERIVES`).


## `ast-select-literal-content`

Kind-aware `to_cst` alternative selection tests a value's *kind*, and a labeled literal's kind is
the same TEXT a regex position contributes (`element_types` maps a literal to SPAN, which
`field_type` coerces to TEXT wherever the label carries anything else). So for a rule whose
alternatives split a label between a literal and something else — `x := v:"lit" | v:item ;` under a
`rule x { product; }` sidecar — the literal alternative's selection guard admits *any* string, and
the literal position then renders the grammar's own text: a hand-built `X(v="xyz")` unparses to
`lit` on both backends, silently replacing the value. Pre-existing (name-only first-fit chose the
same alternative and swapped the same way); the kind test narrowed it to strings but not to the
literal's own string. Closing it means a content test at selection time — `Guard(GuardKind.LITERAL)`
where the accepted TEXT of a label is contributed by literal positions alone, which Python already
spells as `astrt.LiteralText` — *and* the matching content test on the Rust side, whose selection
conjunct is a `matches!` over field enum variants and carries no content today. That second half is
the design work: `AcceptedKind.guard` is currently the untagged backend's test only, so making
selection content-aware changes what the tagged backend reads, and it has to be decided against the
multi-spelling doctrine (`rival_signature` deliberately does not record which literal a value came
from, so alternatives differing only in literal spelling stay first-fit). Location:
`fltk/fegen/ast_model.py` (`_kind_guard`), `fltk/fegen/gsm2ast_rs.py` (`kind_condition`).

## `cst-mutator-append-parity`

The Python backend's `append`, `extend`, `extend_children`, `append_<label>` and
`extend_<label>` accept a child (and, for the first three, a label) without any isinstance
check; only `insert` and `replace_at` call `_check_child_type_for_mutators` /
`_check_label_type_for_mutators`. The Rust backend type-checks its `append` and per-label
mutators (`extract_from_pyobject`, `PyTypeError`), so the two backends reject different inputs
and `tests/test_cst_mutators_parity.py` cannot cover the difference. Until this round the
concrete annotations made the divergence unreachable from type-checked code; now that mutator
inputs are the protocol node types (so either backend's values type-check), a foreign-backend
child passed to the Python `append` is stored silently and surfaces far away — in the unparser,
in `astrt.bucket_children`, or in a `child()` tuple unpack. Closing it means either validating
in the un-strict mutators (a deliberate behaviour change on the parser's hot construction path,
where these methods are grandfathered as un-strict on purpose, and one that the frozen delta's
"runtime behaviour is unchanged" clause rules out for this work) or ruling the divergence
intended and pinning it in the parity suite. The inverse direction of the same asymmetry is open
too: the protocol module's own label sentinels (`cstp.<Class>Label.<X>`) are the only label objects
a purely protocol-typed consumer holds, they type-check into every mutator, and `insert`/
`replace_at` reject them on *both* backends while `append`/`extend` store them (leaving a children
entry whose label has no `.name` and is not the concrete enum). Both generated namespaces and the
grammar reference now document the same-backend-label contract; closing it means either resolving a
canonical-name-equal sentinel to the class's own label member before storing, or ruling the
rejection intended and pinning it. Either way it is a cross-backend behaviour decision
plus a hot-path cost judgement, not a mechanical fix. Location: `fltk/fegen/gsm2tree.py`
(`py_class_for_model`'s `append`/`extend`/`extend_children` and `concrete_body_for`),
`fltk/fegen/gsm2tree_rs.py` (`_generic_append`), `tests/test_cst_mutators_parity.py`.
