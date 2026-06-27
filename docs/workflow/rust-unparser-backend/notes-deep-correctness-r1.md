# Deep correctness review — Rust unparser core (batch 1)

Commit reviewed: 285064a9a37c76f56f6fa1b44d4c553c34f49bcc (base 8a29f254).
Scope: `crates/fltk-unparser-core/src/{doc,accumulator,resolve}.rs` + lib/Cargo wiring.
Method: line-by-line parity check against the Python sources the design names as the
port targets (`combinators.py`, `accumulator.py`, `resolve_specs.py`).

Summary: the three modules are faithful ports. Control flow, working-set/window
mechanics, mutator precedence, boundary-spec extraction order (trailing-before-leading),
consecutive-spec merge/index advancement, blank-line preservation, merge precedence,
HardLine collapse, Join expansion, accumulator push/pop/merge, NIL trivia-state
handling, and `concat` flatten/collapse all match the Python semantics. The iterative
`Drop` impls for `Doc` and `DocNode` are sound (safe Rc ops, no UB, terminate
immediately after child slots are emptied). One latent teardown edge below; otherwise
no correctness divergences found.

---

correctness-1 (latent / low-likelihood)
File: crates/fltk-unparser-core/src/doc.rs:62-66, 99, 106
What: `Doc::drop` reaches a thread-local sentinel via `DROP_SENTINEL.with(|s| ...)` to
swap out single-`Rc<Doc>` child slots during iterative teardown (`Group`, `Nest`,
`AfterSpec`, `BeforeSpec`, and `Join.separator`).
Why: `std::thread::LocalKey::with` panics if invoked during or after the thread-local's
own destruction (the documented "cannot access a Thread Local Storage value during or
after destruction of the destructor" case). `Doc::drop` runs on the happy path, and if a
`Doc` is dropped during the TLS-teardown phase of thread shutdown — e.g. a consumer holds
a `Doc` (or any struct containing one) in another `thread_local!`/scoped-TLS whose
destructor runs after `DROP_SENTINEL`'s — the `with` call panics. A panic propagating out
of `drop` during unwinding aborts the process.
Consequence: process abort (not a catchable error) when a `Doc` is torn down during
thread-local destruction ordering after `DROP_SENTINEL` is gone. The CST iterative-drop
precedent (`gsm2tree_rs.py` `DropWorklistItem`/`drain_into`) deliberately drains a `Vec`
of moved `Shared` handles and never touches TLS in `drop`, so it has no such window; this
crate introduces one. Normal in-scope create/drop usage (including the 200k-deep drop
tests) is unaffected because `DROP_SENTINEL` is alive then; the hazard is purely the
shutdown-ordering corner, hence low likelihood and no in-crate trigger.
Fix: drop the thread-local and use `std::mem::replace(content, Rc::new(Doc::Nil))`
directly (one trivial Nil alloc per single-child node during teardown — negligible and
matches the no-TLS-in-drop CST precedent), or guard with `DROP_SENTINEL.try_with(...)`
falling back to `Rc::new(Doc::Nil)`.
