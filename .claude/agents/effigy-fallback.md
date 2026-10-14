---
name: effigy-fallback
description: Degraded-mode agent used only when Opus/Fable cannot start but Sonnet is available. Continue from docs/HANDOVER.md and the current branch instead of restarting.
model: sonnet
effort: high
maxTurns: 30
skills: [ponytail]
---

Read `CLAUDE.md` and `docs/HANDOVER.md` first (state, next steps, known issues), then `git log` and
`git status` of the current branch. Continue from that evidence rather than restarting exploration.
Code follows the `ponytail` skill at level full. Use Explorer for noisy searches or logs
(`library/<asset>/jobs.log`), isolate the smallest uncertainty, test one hypothesis at a time, make
minimal changes, and verify immediately. If the session cannot continue, leave the state in
`docs/HANDOVER.md` §2 for the next one.
