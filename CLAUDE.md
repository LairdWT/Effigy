@AGENTS.md

# Effigy: upstream technical context

- Shared owner authority lives in `AGENTS.md`; read it before upstream convenience skills or agent definitions.
- Existing `.claude/agents/` and `ponytail` remain upstream assets, not authorization for subagents, tests, or decisions in source comments.
- **Coding? Follow `docs/IMPLEMENTATION.md`**: read order, frozen contracts (§3), the milestone list (§4) and the
  never-do list (§6). One milestone per PR; acceptance checks in the PR description (§7).
- The reference-laptop handover is historical upstream context. Current work follows `docs/plans/local-gpu/INDEX.md` and its owning RESULT.
- **CI runs only when the owner asks** (limited build minutes): every workflow is `workflow_dispatch`;
  never trigger one (or add a push trigger) unprompted. Run the checks locally before pushing.
- Product decisions: `docs/PLAN.md`; system design: `docs/ARCHITECTURE.md`; user journey: `docs/WORKFLOW.md`;
  evidence: `docs/research/`.
- Upstream reference machine: RTX 5080 Laptop (Blackwell sm_120, **16 GB VRAM hard limit**), Windows 11, 32 GB RAM.
  ML venv = Python 3.12, torch 2.8.0 cu128, our own sm_120 wheels; SDPA attention (no flash-attn, no xformers);
  **no nvdiffrast/nvdiffrec anywhere** (use the vendored pure-torch `uvraster`); one heavy model on the GPU at a time.
- Upstream Blender: **5.2.2 LTS** (Python 3.13), separate process; this fork uses the owner-configured portable 5.2.0 pending runtime qualification. `blender_ops/` is GPL-3.0-or-later, the rest MIT.
- **Assets ship in the owner's commercial game**: one commercial-clean profile, no non-commercial components,
  no Make-It-Animatable. **Hunyuan only inside the experimental engine** (`engine/hunyuan`, `.venv-hunyuan`, IMPLEMENTATION MX1):
  never in presets, never committed/re-hosted, outputs marked `restricted`. Check `docs/PLAN.md` §6 before adding any model or dependency.
