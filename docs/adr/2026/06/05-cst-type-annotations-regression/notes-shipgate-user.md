# User notes — ship gate (verbatim chat directives)

1. FLTK generated CST and parsers are used for more than just fltk self-hosting. FLTK is a *library and framework* used by *other applications* to generate parsers. There are *existing applications*, so if we force all of them to update every single type annotation to add Node that is a big and completely unnecessary change. The entire point of this whole project is to create a Rust backend as a near-drop-in replacement. Yes they probably have to change some import statements, but they don't have to touch every function parameter annotation. [Principle captured in CLAUDE.md.]

2. When would the protocol and the concrete classes ever be generated in the same namespace? That means, in Python, literally in the same .py file. Are we generating them in the same .py file? Are we even making that possible?

Resolution (confirmed by protocol-namespace-investigation.md): Protocol and concrete classes are NEVER emitted in the same .py file (separate modules, referenced by module alias). The "same-namespace disambiguation" justification for the `Node` suffix is false. DIRECTIVE: drop the `Node` suffix so Protocol class names exactly match the concrete CST class names; downstream code keeps `cst.Rule` annotations unchanged (only import lines may change).
