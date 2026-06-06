# User directive — ship-gate (verbatim)

> Why do we have this _cst_const mess still? The point is to MAKE USER CODE LOOK CLEAN. This does not look clean so we are not done.

Context (diff the user was reacting to, fltk2gsm.py):

```
-        if items.children and items.children[0][0] in (
-            cst.Items.Label.NO_WS,
-            cst.Items.Label.WS_ALLOWED,
-            cst.Items.Label.WS_REQUIRED,
+        if labeled_children and labeled_children[0][0] in (
+            _cst_const.Items.Label.NO_WS,
+            _cst_const.Items.Label.WS_ALLOWED,
+            _cst_const.Items.Label.WS_REQUIRED,
         ):
```

Requirement: the runtime label-compare sites in fltk2gsm.py must read as clean `cst.Items.Label.NO_WS` (no `_cst_const` alias). This is the in-tree proof of clean downstream user code (AC10). Root-cause + a clean approach are in cst-const-investigation.md.
