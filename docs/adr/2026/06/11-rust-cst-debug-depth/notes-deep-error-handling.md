Style: concise, precise, complete, unambiguous. No padding, no preamble. Audience: smart human/LLM.

Commit reviewed: 2f9b05e  Base: 8c10cea

No findings.

---

Audit trace (for traceability):

**Debug path**: `impl fmt::Debug for <Node>` reads `self.span` and `self.children.len()` directly on the data struct with no lock — both fields are owned by `&self`, so no lock contention, no recursion. Formatting a `Shared<T>` (via `Shared<T>::Debug`) acquires exactly one read lock and delegates to the node's manual `Debug`, which does not re-enter `Shared`. Chain depth is O(1) regardless of tree depth. Correct.

**Drop path — primary invariant**: `drain_into` acquires a write lock only when `strong_count() == 1`. At that point, this thread holds the sole `Shared<T>` handle; `Shared` exposes no `Arc::downgrade`, so no `Weak` handles exist. Therefore the `RwLock` cannot be read- or write-locked by any other party, making the write uncontended and non-deadlocking. The `mem::take` completes in the same statement expression; the `RwLockWriteGuard` temporary drops at the semicolon, before `worklist.extend` runs. No lock is held during worklist processing. Correct.

**Drop path — concurrent dropper**: if `strong_count > 1` is observed but drops to 1 between the check and the decrement, the remaining `Arc` drop fires `impl Drop` on the inner node, which is itself iterative. Nesting depth equals the number of racing concurrent droppers, not tree depth. Correct.

**Python handle interaction**: `PyItems`, `PyIdentifier`, etc. each hold `inner: Shared<T>` (a strong Arc reference). While any Python handle is alive, `strong_count >= 2`, so `drain_into` does not steal those nodes. They are freed when the Python GC releases the handle, which runs the Python-handle's `Drop` (Arc decrement), not the node `Drop` directly — the node `Drop` fires only when the last Arc drops. Correct.

**Span-only nodes in child_union**: nodes like `Identifier` (in `cst_generated.rs`) appear in the `child_union` and have a `DropWorklistItem` variant, but their `into_drop_item` returns `None` for all variants because they have only `Span` children. `drain_into` steals their `children` Vec, but nothing is added to the worklist. The node then drops childless (empty Vec after take) and hits the early-return. No uncovered exit path. Correct.

**Never-child root classes** (e.g., `Grammar` in `cst_fegen.rs` — no variant in `DropWorklistItem` since it never appears as a child): their own `impl Drop` seeds the worklist directly from `self.children.drain(..)`. Their `DropWorklistItem` variant would be unconstructable and would trip `dead_code` under `-D warnings`. Design correctly excludes them. Correct.

**Empty child_union (flat grammar)**: `_drop_block` returns `""`, no `DropWorklistItem` enum is emitted, no `impl Drop` or `into_drop_item` methods are emitted for any node. No dead references. Correct.

**Poison handling**: `shared.write()` calls `self.0.write().unwrap_or_else(|e| e.into_inner())`, ignoring poison. `mem::take` and `Vec` ops do not panic. The drop path introduces no new panicking operations. Correct.

**`strong_count` soundness**: `Arc::strong_count` returns a snapshot; it is not a synchronized "check then act" — but the sole-ownership invariant is: if this thread holds the only `Shared<T>` (count == 1), no other thread can acquire a new one (cloning requires an existing handle). So the count cannot increase from 1 after we observe it while holding the handle. The count can decrease from 2+ to 1 between our read and decrement, but that case is handled by the concurrent-dropper argument above. Correct.

**`PartialEq` deep recursion** (noted in design as out-of-scope, pre-existing): not introduced by this diff; correctly deferred.
