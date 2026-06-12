# Security review — rust-cst-eq-depth (b02cb8f..44458c5)

No findings.

Verification notes (not findings): the change removes an attacker-reachable DoS (recursive `PartialEq` stack exhaustion at parser-controlled depth → uncatchable abort); the iterative driver, `eq_shallow_enqueue`, and `EqWorklistItem::compare` in `fltk/fegen/gsm2tree_rs.py` and all regenerated outputs were checked. Residual behaviors — worklist memory O(tree size) bounded by input size, nontermination on user-created reference cycles, and read-lock re-entry deadlock under position-shifted DAG sharing with a queued writer — are either pre-existing, documented out-of-contract in `crates/fltk-cst-core/src/shared.rs`, or not reachable from untrusted parse input (parsers produce trees, not cycles/DAGs). No secrets in the diff; no new dependencies; no trust-boundary, injection, or auth surface touched.
