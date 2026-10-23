# Add smaller registered panels and explicit MOSS sampling controls

Spoke: S01
Outcome: Add immutable small-panel MOSS sessions and step controls
Depends-on: none
Decisions: D1, D2, D3, D4, D5, D6
Constraints: C1, C2, C3, C4
Skills: python:python-core, web:typescript-core
Read-set: CODE.md, docs/plans/whole-house-moss/INDEX.md
Write-set: server/paint_contracts.py, server/paint_sessions.py, server/paint_routes.py, server/jobs.py, steps/_paint_set.py, steps/paint_generate.py, ui/src/MultiViewPaint.tsx, ui/src/multi-view-api.ts, tools/stage_multi_view_trial.py
State: done

## Context

The owner requested a separate whole-house MOSS trial after the completed twelve-candidate foundation comparison. Smaller panels are authorized for this new work. Previous sessions and source outputs stay immutable. Expected turns18; preserve standing budgets and prior usage history.

## Evidence

- server/paint_contracts.py:80 joint_group currently hardcodes512-square panels.
- steps/_paint_set.py capture and selection already accept a panel-size argument internally, but capture fixes it to512 for complete sheets.
- server/paint_sessions.py owns capture reuse, layout snapshots and stale-state rejection.
- steps/paint_generate.py currently fixes native differential sampling to eight steps and describes sheet columns using512.
- ui/src/MultiViewPaint.tsx renders registered rectangles but assumes512 when laying out the sheet.
- Earlier MOSS candidates used13.416GiB peak allocation and43.02-47.25s sampling at2560-square/eight steps. Loading was125.5-178.24s where recorded. These measurements do not support a universal1.4-second runtime.

## Steps

Add a validated immutable panel size for new whole-sheet MOSS sessions:192,256,384 or512. Historical pairs retain704 and existing complete sessions default512. Reject incompatible capture reuse or unsupported model/strategy combinations. Carry size through capture, selection, layout, job snapshots and the UI. Derive displayed sheet dimensions from recorded rectangles.

Add an explicit MOSS-only four/six/eight-step field with legacy default8. Persist it in recipes and runtime metrics. Keep other model samplers unchanged. Admit smaller MOSS sheets through the existing18GiB model requirement, preserving the28GiB gate for historical512 qualification. No engine or checkpoint changes.

## Files to touch

- server/paint_contracts.py
- server/paint_sessions.py
- server/paint_routes.py
- server/jobs.py
- steps/_paint_set.py
- steps/paint_generate.py
- ui/src/MultiViewPaint.tsx
- ui/src/multi-view-api.ts
- tools/stage_multi_view_trial.py

## Verification

1. Run scoped Ruff on changed Python, the offline trial UI build and plan validation after relevant changes. Expected: all commands pass. Use normal capture/generation operations in S02 to establish actual registration, coverage, preservation and timing. No code tests or model hashes. Stage only named source files; never rerun provisioning.

## Risks

Smaller views may lose tiny surfaces and texture detail. Report unreachable texels and refuse excess-camera layouts. Recipe defaults must preserve old outputs. Four steps above the model's intended canvas size may wash out detail; show guidance and record the actual sheet and settings. Upscaling cannot establish corrected mortar alignment.

## RESULT

Implemented immutable192/256/384/512 panel sizes and four/six/eight MOSS steps. Other adapters retain their existing settings. Smaller MOSS sessions use the existing18GiB admission limit; historical512 sessions retain their gate. Complete small-panel layouts support all26 cameras with explicit rectangles; no camera is silently removed.

Scoped Ruff and the offline trial UI build passed. Plan validation passed with advisory-only formatting findings. Named files were staged only into8380 and that idle lane restarted. Primary8370 was not rebuilt or restarted.

Runtime capture236 and diagnostic237 demonstrate all26 cameras at192 pixels, a1152x960 sheet,523762 selected texels and514986 reachable texels. The8776 unreachable selected texels remain protected. UI session1c223e7539774a62 displays the immutable size, four-step recipe, shared mask and exact layout. Generation jobc34b5c097bdc was submitted through its Generate complete view set button; art acceptance belongs to S02.
