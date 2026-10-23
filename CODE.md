# CODE.md - Effigy

Binding for all committed code. Rationale lives in docs/adr/ (see
INDEX.md); do not relitigate here.

## Conventions by reference

Library: agent-enhanced-project
(install: git clone https://github.com/LairdWT/agent-enhanced-project)

- python @ plugins/python/CONVENTIONS.md (v0.25.0)
- web @ plugins/web/CONVENTIONS.md (v0.42.0)
- powershell @ plugins/powershell/CONVENTIONS.md (v0.12.0)
- shell @ plugins/shell/CONVENTIONS.md (v0.7.0)
- git @ plugins/git/CONVENTIONS.md (v0.12.0)

## Project deviations and additions

- Preserve frozen upstream dependency groups and wheel ABIs; other projects' pins do not apply - adr:preserve-isolated-upstream-runtime-environments.
- Runtime is offline; downloads belong to explicit provisioning - adr:separate-online-provisioning-from-offline-runtime.
- Borrowed model paths are read-only, including generated configuration - adr:borrow-shared-models-read-only.
- Optional reference models use the configured native interpreter in isolated Effigy workers - adr:reuse-the-configured-native-engine-for-reference-workflows.
- Reuse configured portable Blender 5.2.0 pending qualification - adr:reuse-configured-portable-blender.
- Use upstream Ruff, the UI build, structural checks, and authorized runtime samples. Broader AEP standards findings remain advisory for this baseline - adr:preserve-upstream-checks-for-baseline-adaptation.

## Toolchain configs are law

- `pyproject.toml` and `uv.lock`: Python range, isolated groups, versions, CUDA index, wheels, and Ruff rules.
- `ui/package.json`, `ui/package-lock.json`, `ui/tsconfig.json`, and `ui/vite.config.ts`: UI dependencies and build behavior.
- `.aep/standards.json`: advisory migration analysis. Existing whole-file findings and missing providers are recorded, not reported as passing.
- `.claude/aep-lint.json`: non-downloading feedback; missing tools fail visibly.

## Verification

### Routine

- `.venv/Scripts/ruff.exe check .`

Routine is fast feedback. Pre-commit also runs the offline UI build. Each task needs proof
scoped to the behavior changed, declared in its plan or WorkUnit.

### Complete

- `agent-code-skills adr check --target .`
- `agent-code-skills plan check docs/plans/local-gpu`
- `.venv/Scripts/ruff.exe check .`
- `npm --offline --prefix ui run build`

Run Complete only at an explicitly authorized milestone with installed project
tools. Checks never install tools or execute code tests. AEP standards inspection
remains available for a separately authorized migration; do not suppress its
findings or borrow another application's environment. Existing upstream CI remains manual-only and must not
be triggered without owner instruction.

## Task proof

WU01 uses ADR, plan, standards-configuration, hook, and Git inspection only.
Scaffolding does not install or qualify runtime dependencies or native analyzers.
WU05 uses the normal application and its sample matrix. Static checks do not
prove offline operation, GPU execution, output quality, or Blender compatibility.
