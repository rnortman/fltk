# User correction (round 1)

How did my requirement get scoped *down* to "with respect to span". This is with respect to *FUCKING ANYTHING*.

# User correction (round 2)

The phrase "hand-written and generated" (line 26) is wrong. All Rust CST node structs holding a Python Span are GENERATED artifacts — emitted by RustCstGenerator (fltk/fegen/gsm2tree_rs.py) and checked into the repo. There are zero hand-written CST structs with span fields anywhere, including tests. Generated-into-repo files: src/cst_generated.rs, src/cst_fegen.rs, tests/rust_cst_fixture/src/cst.rs, tests/rust_cst_fegen/src/cst.rs. The fix belongs in the generator and regenerates these files; correct the doc to reflect that the structs are entirely generated.
