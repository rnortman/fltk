## Quality findings — rust-cst-eq-depth (b02cb8f..44458c5)

Commit reviewed: 44458c5

---

### quality-1 Split impl blocks: `into_drop_item` and `eq_shallow_enqueue` each get a separate `impl FooChild {}` block

**File:line** — `fltk/fegen/gsm2tree_rs.py:606-617` (into_drop_item block) and `626-650` (eq_shallow_enqueue block). Visible in every generated file, e.g. `tests/rust_parser_fixture/src/cst.rs:226-232` vs `234-243`.

**Issue** — `into_drop_item` and `eq_shallow_enqueue` are private helpers on the same type, emitted under identical guards (`needs_drop_item`), in adjacent generator code. Each is wrapped in its own `impl {enum_name} { … }`. Rust allows merging them; the generator emits two separate blocks because eq_shallow_enqueue was added by appending its own wrapper after the existing into_drop_item block rather than extending it.

**Consequence** — Every future private method added to ChildEnum under the same condition will follow this pattern of appending a third, fourth… split block. Readers must scan multiple non-contiguous impl blocks to understand the type's private API. The pattern propagates: the equivalent problem has already happened (the `#[cfg(feature = "python")]` impl is a third block, but that one is legitimately gated and cannot merge).

**Fix** — In `_child_enum_block`, open a single `impl {enum_name} {` block when `needs_drop_item` is true, emit both `into_drop_item` and `eq_shallow_enqueue` inside it, then close. Remove the intermediate `}` / `lines.append("")` / `lines.append(f"impl {enum_name} {{")` between them (generator lines 616-628).

---

### quality-2 Misleading generated comment: "Guards are held only for the duration of one arm and dropped before any push"

**File:line** — `fltk/fegen/gsm2tree_rs.py:2091` (generated into every cst.rs, e.g. `tests/rust_cst_fixture/src/cst.rs:6892`).

**Issue** — The comment appears immediately above the `match self` in `EqWorklistItem::compare`. Inside each arm, `ga` and `gb` (the `RwLockReadGuard`s) are held alive for the full duration of the `for` loop, and `eq_shallow_enqueue` pushes to the worklist (`Arc::clone` + `Vec::push`) *while* those guards are still live. The comment says the opposite: "dropped before any push." The comment is trying to convey that no *lock acquisition* happens during a push, which is correct (Arc::clone acquires no lock), but it says "dropped" where it means "not re-acquired."

**Consequence** — A future maintainer auditing the locking story (e.g. to evaluate the DAG-deadlock caveat in `shared.rs`) will read this as meaning the guards are released before child enqueues, conclude that the lock window is narrow, and not see the actual window (guards live across the entire child iteration). The incorrect framing will propagate to any copy of this comment pattern.

**Fix** — Replace the comment (generator line 2091) with: `// Guards are held across the child iteration; pushes to the worklist are Arc::clone + Vec::push (no lock acquisition).`

---

No other findings.
