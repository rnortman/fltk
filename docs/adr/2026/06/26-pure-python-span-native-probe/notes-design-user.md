# User notes on design (verbatim)

The designer decided that the existing "python parser using rust CST" is to be preserved, but it is not. That was an intermediate step during development of the rust backend. There is no use case for a python parser producing rust CST. We should rip that out. You have only two choices: Python parsers that produce Python CST, or Rust parsers that produce Rust CST. Remove the hybrid option, and remove any unit tests that enforce the presence of that option.
