### 7. `gsm-for-each-item-public` — DO (the rename, not the helper)

- **Problem:** `regex_corpus.py` calls `gsm._for_each_item` — a private-by-convention name
  across module boundaries that no type checker will guard.
- **What the work looks like:** rename to public `for_each_item` (docstring already
  present); update the one cross-module call site + two in-module call sites. Skip the
  TODO's alternative `iter_regexes(grammar)` helper — it moves regex-specific filtering
  into `gsm.py`, which has none today, for no additional caller.
- **The case for skipping:** it's cosmetic-adjacent; the call works fine.
- **Recommendation: Do** — trivial, gives the walk a stable public contract.
