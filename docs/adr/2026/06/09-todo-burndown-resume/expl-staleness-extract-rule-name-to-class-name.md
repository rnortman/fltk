# Staleness Check: extract-rule-name-to-class-name design

Verified against HEAD af6e6f3 (2026-06-09). Style: concise, precise, no padding.

## TODO slug liveness

`extract-rule-name-to-class-name` is live in both locations:

- `TODO.md:15` — entry present, unchanged from design's description.
- `fltk/fegen/gsm2tree_rs.py:18-22` — TODO comment block present at exactly those lines, unchanged.

## Named files: existence and shape

### `fltk/fegen/gsm2tree.py:46-47`

Present. `class_name_for_rule_node` is at lines 46-47, body unchanged:
```python
def class_name_for_rule_node(self, rule_name: str) -> str:
    return "".join(part.capitalize() for part in rule_name.lower().split("_"))
```

### `fltk/fegen/gsm2tree_rs.py:25-27`

Present. `_rust_variant_name` is at lines 25-27, body unchanged:
```python
def _rust_variant_name(label: str) -> str:
    """Label -> CamelCase Rust enum variant. 'no_ws' -> 'NoWs'."""
    return "".join(part.capitalize() for part in label.split("_"))
```
`_IDENTIFIER_RE` is at line 17. Import of `CstGenerator` from `gsm2tree` is at line 12. All line refs in design are exact.

### `fltk/unparse/gsm2unparser.py` — copy 2 and copy 3

File now has **1833 lines** (was 1894 at exploration time; shrunk by ~61 lines).

- Copy 2: `UnparserGenerator.class_name_for_rule_node` — design cited line 638-639. Now at **lines 634-635**. Body unchanged.
- Copy 3: inline list-comp — design cited line 1888. Now at **line 1827**. Expression unchanged: `["".join(part.capitalize() for part in rule_name.lower().split("_")) for rule_name in rule_names]`.

Line numbers for `gsm2unparser.py` have shifted (by ~54-61 lines) due to edits since exploration. The cited numbers in the design and exploration docs are stale for the unparser file. The expressions and their roles are intact.

### `fltk/fegen/naming.py`

Does **not** exist. The new module proposed by the design has not been created.

## Behavioral analysis: still valid?

All four copies exist with the same bodies as documented. The design's behavioral analysis (copies 1-3 include `.lower()`, copy 4 omits it; divergence is latent on lowercase-only grammar inputs) is still accurate.

## Impact of commit 4c8f0ad on this design

Commit 4c8f0ad reworked the Rust CST to hold native `Span` and children (no Python objects). That commit touched `fltk/fegen/gsm2tree_rs.py` (the Rust generator), but:

- `_rust_variant_name` at lines 25-27 is unchanged in body.
- The `TODO(extract-rule-name-to-class-name)` comment at lines 18-22 is unchanged.
- `class_name_for_rule_node` in `gsm2tree.py` and `gsm2unparser.py` are unchanged.

The commit has no bearing on this refactor. The design remains applicable as written, with one caveat: line numbers cited for `gsm2unparser.py` (638-639, 1888) are stale; current lines are 634-635 and 1827 respectively. All other file:line references in the design are accurate.

## Summary

| Claim | Status |
|---|---|
| TODO slug live in `TODO.md` | Confirmed (`TODO.md:15`) |
| TODO comment at `gsm2tree_rs.py:18-22` | Confirmed (exact lines) |
| Copy 1 at `gsm2tree.py:46-47` | Confirmed (exact lines, body unchanged) |
| Copy 4 at `gsm2tree_rs.py:25-27` | Confirmed (exact lines, body unchanged) |
| Copy 2 at `gsm2unparser.py:638-639` | Line-stale: now 634-635; body unchanged |
| Copy 3 at `gsm2unparser.py:1888` | Line-stale: now 1827; expression unchanged |
| `naming.py` does not yet exist | Confirmed absent |
| Design applicable as written | Yes — pure refactor, no structural blockers introduced by recent commits |
