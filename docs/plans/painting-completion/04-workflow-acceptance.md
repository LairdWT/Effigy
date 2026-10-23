# Complete the remaining workflow acceptance

Spoke: S04
Outcome: Close browser lifecycle and remaining runtime acceptance
Depends-on: S03
Decisions: D1, D5
Constraints: C1, C2, C3, C4
Skills: planning:planning-core, python:python-core, web:typescript-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/03-hut-repair.md#result, docs/plans/multi-view-paint/11-runtime-comparison.md#result
Write-set: docs/plans, scratch/lanes/fibo2, ui/src/LocalRuntimeStatus.tsx, ui/src/events.ts, ui/src/MultiViewPaint.tsx, ui/src/PaintSelection.tsx, tools/stage_multi_view_trial.py
State: done

## Context

Historical UI blockers must be reconciled with current browser access, while external browser-host traffic remains unattributed. Expected turns12; do not rerun unchanged model comparisons.

## Evidence

docs/plans/multi-view-paint/11-runtime-comparison.md:1 records completed lifecycle/failure exercises and the browser-specific offline gap. docs/plans/surface-paint-ux/INDEX.md:1 still lists an old unavailable-browser check.

Added a page-owned resource observer in ui/src/LocalRuntimeStatus.tsx:1. It shows actual resource origins, per-page CSP events and the connected EventSource origin alongside the existing server policy counter. It does not inspect unrelated desktop traffic or claim OS containment. During the FIBO repair, the UI reported58 resource requests, only http://127.0.0.1:8380, zero external resources, zero blocked page requests and zero server CSP violations.

After the local describe operation, this observer had258 resource entries with the same sole origin and zero external or blocked requests. Describe job92c61c18aae6 produced258_describe in84.33s using the selected Q3.5 GGUF (9527501312 bytes) and projector (624229376 bytes), llama.cpp-b10632-cuda13.3, observed CUDA0 process. It returned an editable description of the hut; Append, Replace selected text and Discard remain explicit actions. No appearance was automatically replaced. Clear mask disabled Generate with an explanation; Undo restored the saved suggested-mask preset plus user erasure/addition and re-enabled it.

After confirming no trial worker or session action was active,8380 restarted and reopened265. The new trial backend is PID65892; primary8370 remains PID49908. Existing captures, reviewed bakes, model settings and prompt scope survived. The next foundation edit7538292331cc resumed from immutable side capture266 after that restart, using full-frame context and the accumulated265 mesh as its source.

Follow-up UI inspection found that a fully erased seam preset retained its erase strokes when a new triangle was selected. The new face-add path clears those stale strokes only when starting from an actually empty mask; Undo retains the prior selection. Face-remove never turns an empty mask into painted faces. Removing a triangle boundary preserves an existing seam preset. A completed heal capture also no longer navigates away from a route the user selected while that job ran.

The corrected UI was exercised on capture251: erase the suggested mask completely, select visible triangle124, and verify Generate becomes enabled with a one-face boundary. Two Undo operations restored the original rectangle and the draft was saved. Final source268 was reopened; owned model/description workers were absent, trial8380 was PID65892 and primary8370 remained PID49908. Branch codex/local-gpu remains uncommitted.

The exact previously authorized cleanup was rechecked:38 named Trash groups,96 version directories plus one nested views/meta.json,1209649031 bytes, no Blender files or links. The deletion command was rejected before execution by automatic approval review with only "blocked by policy". No files were removed. Do not try another deletion mechanism to bypass this refusal.

## Steps

Exercise the new UI capture, mask edits, generation, projection, reopening and appearance persistence. Confirm camera continuity, saved selection and protection across idle restart. Inspect available browser-specific network observability; use only supported tools and document any actual capability gap. Reconcile old statuses from current proof. Verify primary8370 remains unchanged and agent-owned model workers are released. Review exact historical cleanup targets before deciding whether anything remains to execute under existing authorization.

## Files to touch

- docs/plans
- scratch/lanes/fibo2
- ui/src/LocalRuntimeStatus.tsx
- ui/src/events.ts
- ui/src/MultiViewPaint.tsx
- ui/src/PaintSelection.tsx
- tools/stage_multi_view_trial.py

## Verification

1. UI operations and job metadata. Expected: normal lifecycle succeeds without hidden copies or partially published outputs.
2. Runtime boundary observations. Expected: local backend/workers; browser claims limited to attributable evidence.
3. Plan validation. Expected: all completed requirements map to actual results; no technical or owner acceptance blocker is erased.

## Risks

Browser inspection may not expose per-tab network data. Owner art acceptance cannot be fabricated. Missing observability remains incomplete even when static controls forbid external operations.

## RESULT

Current trial UI passed capture, editable seam suggestions, add/erase, empty-mask disabling, generation, projection, eight-angle review and reopen. Idle restart retained265, captures and repair settings; primary8370 stayed PID49908. Q3.5-9B description258 used the selected9.53GB GGUF plus624MB projector and remained an editable proposal. Page-owned observation during actual jobs recorded258 localhost resource entries, zero external/blocked requests and zero CSP violations, with a connected localhost progress stream. This closes the prior page-attribution gap for observed operations, not OS containment. Scoped source checks, trial builds and plan checks passed. Art qualification remains S03. Exact authorized cleanup is externally blocked and retained under S05; no deletion occurred.
