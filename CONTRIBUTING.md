# Contributing to Effigy

Effigy is a small project with firm rules. Reading them first saves a review round.

## Before you start

- Read `CLAUDE.md` (the rules on one page), then `docs/IMPLEMENTATION.md` §0 (how work is done here), §3 (the
  frozen contracts between the steps) and §6 (what is never done). Product decisions are in `docs/PLAN.md`.
- **Licences are part of the product.** Assets made with Effigy ship in commercial games (`docs/PLAN.md` §6): no
  non-commercial component, no Hunyuan outside the experimental engine, and every new model or package gets a
  row in `licenses.yaml` with `tests/test_licenses.py` passing. A dependency that fails that check is not a
  dependency we can take, however good it is.
- Open an issue first for anything beyond a fix, so the scope is agreed before the work.
- Code is written the lazy way (`.claude/skills/ponytail/SKILL.md`): the smallest change that works, the
  standard library and the installed dependencies before a new one, no abstraction for a single use, and a
  `# ponytail:` comment where a corner is cut on purpose, naming its ceiling.

## The flow

1. Fork, branch from `main`, one milestone or one fix per branch.
2. Leave the §3 contracts alone. A contract change is its own pull request that updates the docs, the code and
   every caller together.
3. Run the checks locally before you push. CI runs only when the maintainer asks and never on a pull request:

   ```sh
   uv sync --frozen
   uv run pytest -q && uv run ruff check . && uv run ruff format --check .
   cd ui && npm ci && npm run build && npx playwright test   # when ui/ changed
   ```

   The ML steps' suite needs `.venv-ml` (`UV_PROJECT_ENVIRONMENT=.venv-ml uv sync --frozen --group ml`); tests
   that need a GPU, Blender or a model skip without them and say so.
4. Open the pull request. Its template appears by itself: fill every line, and tick **Allow edits by
   maintainers** so fixes can land on your branch.
5. An acceptance check you could not run is marked "needs GPU, not run" in the description, never claimed.
   Numbers in the docs are measured ones, never rounded estimates.

## Licences of the code

MIT, except `blender_ops/` (GPL-3.0-or-later): everything that imports `bpy` lives there and runs in Blender's
own process. Nothing in `server/`, `steps/`, `ui/` or `mcp/` imports from it or from any GPL package.

Never commit model weights, `library/`, `models/`, a virtual environment, a licence key, `.env` or anything
under `scratch/`.
