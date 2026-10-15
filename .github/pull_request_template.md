<!-- One milestone or one fix per pull request (docs/IMPLEMENTATION.md §0 and §7). Fill every line; delete nothing. -->
Milestone: M<n> <title> (or: fix <what>)
Scope: <files>
Skipped (ponytail): <what> → add when <trigger>
Acceptance:
  - [ ] <check 1> — output: …
  - [ ] <check 2> — needs GPU, not run / run on laptop: …
Measurements: peak VRAM …, time …, commit …
Docs updated: IMPLEMENTATION.md §… / PLAN.md §… / none
Checks run locally: `uv run pytest -q`, `ruff check .`, `ruff format --check .`<!-- , `npm run build`, Playwright when ui/ changed -->
