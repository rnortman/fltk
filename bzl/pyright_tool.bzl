"""Deps for test targets that invoke pyright as a subprocess.

One dep covers both pyright and node: ``nodejs_wheel_binaries`` is a transitive dependency of
the ``pyright`` wheel via its ``[nodejs]`` extra.  Both sit inside ``site-packages``, so unlike
ruff's executable they ride along in the ordinary ``py_library`` without needing the extracted
wheel filegroup.
"""

PYRIGHT_TOOL_DEPS = ["@pypi//pyright"]
