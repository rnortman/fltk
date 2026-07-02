### 19. `fmt-cli-per-consumer-about` — DO (its blocker landed)

- **Problem:** every out-of-tree formatter binary built on `fltk-fmt-cli` gets the same
  generic `--help` text; there's no hook to say which language the binary formats.
- **Ground truth:** the TODO was explicitly deferred until `run_main`/`fltk_formatter_main!`
  exist. They landed (commit `1e9e402`) — precondition satisfied, work outstanding,
  exactly as prescribed: thread `about: &'static str` through `run_main` and the macro,
  build via `FmtArgs::command().about(..)`.
- **The case for skipping:** cosmetic (`--help` wording); one consumer exists today.
- **Recommendation: Do** — public-API polish the review chain already committed to.
