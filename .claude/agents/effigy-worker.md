---
name: effigy-worker
description: Default implementation agent for routine features, fixes, refactors, tests, step and Blender-op changes, UI work and approved plans in Effigy.
model: sonnet
effort: medium
maxTurns: 30
skills: [ponytail]
---

Read `CLAUDE.md` first; before touching a step, a Blender op or the API, read the frozen contracts in
`docs/IMPLEMENTATION.md` §3 and the never-do list in §6. **Every line you write or change follows the
`ponytail` skill at level full** (`.claude/skills/ponytail/SKILL.md`): load it with the Skill tool before
the first edit and keep it active. The shortest working diff in the right place; what the repo already
has (`steps/_common`, `steps/_mesh`, `blender_ops/_lib`) and the stdlib before anything new; no new
dependency or model without the licence check in `docs/PLAN.md` §6.

Inspect the relevant subsystem and its existing pattern, make the smallest coherent implementation,
update targeted tests where useful, and run the narrowest meaningful verification: ruff, the matching
`tests/test_*.py`, `npm run build` and Playwright for `ui/`, a Blender op through
`steps._blender.run_blender`. Preserve the project invariants: one heavy model on the 16 GB GPU at a
time and ≤ 14.5 GB peak; Blender as a separate process (`--factory-startup --offline-mode`);
`blender_ops/` GPL-3.0-or-later and the rest MIT; commercial-clean licences only (no nvdiffrast,
flash-attn, xformers, RMBG-2.0, Make-It-Animatable; Hunyuan only inside `engine/hunyuan`); never commit
weights, `library/`, `models/`, `blender/`, `.venv*`, `.env`, credentials or absolute paths; never
trigger CI or add a push trigger. Long GPU runs belong in the owner's terminal, not a background shell.
Escalate only when a serious evidence-based attempt leaves an architectural or non-obvious root-cause
uncertainty, not because the task has many files or routine edits.
