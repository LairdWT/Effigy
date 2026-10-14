# Effigy: notes for Claude

- **All coding in this repo uses the `ponytail` skill (level: full)**: `.claude/skills/ponytail/SKILL.md`.
  This applies to writing, refactoring, reviewing and designing code, and to choosing dependencies.
- **Subagents** (`.claude/agents/`, brought over from the owner's demolition_man project): route by evidence and
  unresolved uncertainty, one focused subagent at a time. `effigy-explorer` for read-only research, tracing and logs;
  `effigy-worker` for normal implementation and verification; `effigy-expert` for architecture, hard root causes, contract
  and GPU/process design; `effigy-escalation` only after Expert cannot resolve it; `effigy-fallback` when Opus/Fable
  cannot start. Read-only review specialists beside that ladder, one at a time, before a commit: `step-reviewer`,
  `silent-failure-hunter`, `comment-analyzer`. **Every agent that writes or reviews code uses the `ponytail`
  skill (level: full)**: the agent files say so and preload it.
- **Coding? Follow `docs/IMPLEMENTATION.md`**: read order, frozen contracts (§3), the milestone list (§4) and the
  never-do list (§6). One milestone per PR; acceptance checks in the PR description (§7).
- **Session on the reference laptop? Start with `docs/HANDOVER.md`**: state, what is next, decisions (the history before
  2026-10-13 and the finished bring-up plan: `docs/archive/handover-history.md`).
- **CI runs only when the owner asks** (limited build minutes): every workflow is `workflow_dispatch`;
  never trigger one (or add a push trigger) unprompted. Run the checks locally before pushing.
- Product decisions: `docs/PLAN.md`; system design: `docs/ARCHITECTURE.md`; user journey: `docs/WORKFLOW.md`;
  evidence: `docs/research/`.
- Reference machine: RTX 5080 Laptop (Blackwell sm_120, **16 GB VRAM hard limit**), Windows 11, 32 GB RAM.
  ML venv = Python 3.12, torch 2.8.0 cu128, our own sm_120 wheels; SDPA attention (no flash-attn, no xformers);
  **no nvdiffrast/nvdiffrec anywhere** (use the vendored pure-torch `uvraster`); one heavy model on the GPU at a time.
- Blender: pinned **5.2.2 LTS** (Python 3.13), always a separate process; `blender_ops/` is GPL-3.0-or-later, the rest MIT.
- **Assets ship in the owner's commercial game**: one commercial-clean profile, no non-commercial components,
  no Make-It-Animatable. **Hunyuan only inside the experimental engine** (`engine/hunyuan`, `.venv-hunyuan`, IMPLEMENTATION MX1):
  never in presets, never committed/re-hosted, outputs marked `restricted`. Check `docs/PLAN.md` §6 before adding any model or dependency.
