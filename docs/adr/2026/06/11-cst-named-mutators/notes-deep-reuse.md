No reuse findings for generated CST modules, test fixtures, or Rust crates.

Two findings in the generator source (gsm2tree_rs.py and gsm2tree.py).

---

reuse-1

File: `fltk/fegen/gsm2tree_rs.py:1290-1311` and `1358-1378`

What is duplicated: The "resolve index to Option<usize>" block is copy-pasted verbatim between `_generic_remove_at` and `_generic_replace_at`:

```
let (resolved, n) = {
    let guard = self.inner.read();
    let n = guard.children.len();
    let resolved: Option<usize> = if let Ok(i) = raw_idx.extract::<i64>() {
        if i < 0 { ... } else if (i as usize) < n { ... } else { None }
    } else { None };
    (resolved, n)
};
let idx = match resolved {
    Some(i) => i,
    None => { let orig = raw_idx.str()...;
               return Err(PyIndexError::new_err(format!(...))) }
};
```

Existing function/utility: None exists; the fix is a new private generator method, e.g. `_emit_resolve_index_stmts(self, class_name: str, method_name: str) -> list[str]`, called from both `_generic_remove_at` and `_generic_replace_at`.

Consequence: Any future change to index normalization semantics, error message format, or beyond-i64 handling must be applied identically in two places. The blocks differ only in `method_name` in the format string, so a copy-paste error silently produces a mismatched error message (e.g. `remove_at` saying `replace_at`). The existing parity tests would catch a message mismatch at test time, but the source redundancy remains a maintenance burden.

---

reuse-2

File: `fltk/fegen/gsm2tree.py:_emit_py_mutators`, specifically the `remove_at` body fragment (lines ~537-542) and the `replace_at` body fragment (lines ~558-565).

What is duplicated: Both methods emit identical index-normalization + bounds-check + `IndexError`-raise logic in Python:

```python
idx = operator.index(index)
n = len(self.children)
norm = idx + n if idx < 0 else idx
if norm < 0 or norm >= n:
    msg = f"{class_name}.{method}.remove_at: index {index} out of range ({n} children)"
    raise IndexError(msg)
```

(The only difference is `method_name` in the f-string.)

Existing function/utility: None; the fix is a helper string constant or a private method `_bounds_check_stmts(class_name: str, method_name: str) -> str` whose output is fed into `ast.parse(...).body`, called from both `remove_at` and `replace_at` emission paths.

Consequence: Same as reuse-1 on the Python side: a future message-format change or normalization adjustment must be applied in two places. The existing cross-backend parity tests will catch a live divergence, but source-level redundancy increases the cost of every future touch to this logic.
