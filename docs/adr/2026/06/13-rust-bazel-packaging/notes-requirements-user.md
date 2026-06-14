# User correction (verbatim)

OK, there was a misunderstanding in what I said: The requirements interpreted "submodule" as "git submodule" but that's not what I said. I said "bazel submodule", which is correct. fltk itself becomes available within bazel build files as `@fltk//...`, which is a bazel submodule. See if the exploration and/or requirements need to be updated to correct this.

# User notes round 2 (verbatim)

1. the requirements set up a strawman of the alternatives by complaining about the fact that each alternative requires bazel in clockwork to be able to build rust code. I have to say, this is a giant "Duh". Of course bazel needs to be able to build rust code. That is true of all possible paths and therefore should not be mentioned as a differentiator between alternatives. We must assume not only that Clockwork's bazel config must be able to build rust code, but that a big part of why clockwork would want to use the fltk rust backend is *because clockwork wants to start writing native Rust code of its own*, in addition to using the pyo3 bindings.

2. The other substantive note is another DUH OF COURSE: That this all only works if clockwork.fltkg's regexes work with the rust regex crate. Of course. We do not need to complain loudly about this. This is incidental to the purpose of hte project, which is focused on how we package and integrate into a bazel project. If clockwork.fltkg needs to be updated, we'll either do that *or* we'll fix fltk to support the advanced regexes that clockwork needs. That is beyond the scope of solving the packaging and build problem.

3. Lastly, the requirements are demanding a decision on a packaging path (compile from scratch in bazel vs pip wheel) and THAT IS NOT WHAT "REQUIREMENTS" MEANS in the context of this project. That is DESIGN. The requirements say "this is what needs to work" and the designer says "OK, let's try (pip wheels|build-in-bazel)". The requirements don't make that decision and don't need to force it to be answered before we go to the designer.

# User notes round 3 (verbatim)

1. There's a question about whether fltk crates are published on crates.io. The answer is: not yet, but if the designer decides that this is the most expedient/cleanest path, then we will publish on crates.io.

2. The other question about the equivalence test is... WE ARE NOT FUCKING TESTING THAT FLTK IS CORRECT WE ARE TESTING THAT WE CAN PACKAGE THIS FOR CONSUMPTION IN ANOTHER FUCKING PROJECT SO ALL I REALLY CARE IS THAT IT PRODUCES SOMETHING... ANYTHING. QUIT BEING SO FUCKING PEDANTIC.
