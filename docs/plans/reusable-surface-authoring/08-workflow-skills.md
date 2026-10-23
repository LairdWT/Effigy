# Package the qualified workflow as Effigy skills and consumer recipes

Spoke: S08
Outcome: Package qualified workflow skills
Depends-on: S07
Decisions: D1, D2, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: aep:aep-core, planning:planning-core
Read-set: docs/plans/reusable-surface-authoring/INDEX.md, docs/plans/reusable-surface-authoring/07-cross-asset-qualification.md#result, docs/plans/reusable-surface-authoring/07-cross-asset-qualification.md#result, docs/IMPLEMENTATION.md
Write-set: .codex/skills/effigy-surface-authoring, docs/SURFACE-AUTHORING.md, docs/plans/reusable-surface-authoring
State: active

## Context

Load skill-creator when executing this unit. The user requested eventual skills; package them after capability qualification so they describe the real process and known limitations. This unit owns an Effigy-local skill, not a rewrite of shared Blender, 3DGen or Legaia skills.

Expected turns: 10. Preserve standing budgets and prior results. Source changes remain uncommitted. Ordinary app outputs are runtime artifacts under C4, not extra evidence packs.

## Evidence

- server/paint_sessions.py:45 and :368 provide the session/action ownership boundary the skill must consume.
- server/app.py:294 provides Blender integration; ui/src/SurfacePaint.tsx:62 is an existing user entry point.
- docs/adr/8a04ffd6-isolate-the-local-blender-editing-session.md:18 requires an isolated configured Blender bridge.

## Steps

1. Create a small effigy-surface-authoring router with preparation, sampling, authoring, review and recovery references. Each gives exact UI/API entry points, required profile fields, applicability and observable completion. Avoid one monolithic transcript of the hut experiments.

2. Delegate generic Blender/projection doctrine to the installed blender-core and 3dgen-core routes. Reference texture-painting-core for actual guided brush work and art-3d-realtime-core for the selected art profile. Keep model-aware prompts behind capability-aware recipes.

3. Keep N:/Blender's generic algorithms and projected skills read-only. Keep Legaia retail bindings, material registry, prompts and owner acceptance in the Legaia consumer. Document the Effigy consumer binding and a generic example without inserting project paths or hut semantics into the provider.

4. Describe reusable modes, approved-source roles, UV/provider limitations, sampling admission, model selection, bounded repair budgets and explicit acceptance. Document the rejected 312 lesson as a linked regression case, not a default style or a secret fallback.

5. Document failure recovery: incomplete model jobs, saved versus unsaved Blender changes, stale geometry/masks, NAS publication and unsupported methods. Never advise resetting a protected source or clearing another application's queue.

6. Add a worked three-stage quickstart: open a supported asset/profile, author one bounded edit, review and publish a reference. State that workflows requiring rigged or multi-material editing remain unsupported until separately qualified.

7. Inspect and validate only the new skill package with the installed supported skill tooling. Do not hand-edit generated shared projections or register cloud tools. Leave future shared-library promotion as a separately scoped change.

## Files to touch

- .codex/skills/effigy-surface-authoring
- docs/SURFACE-AUTHORING.md
- docs/plans/reusable-surface-authoring

## Verification

1. Read the local skill from a fresh bounded context and compare every claimed command/capability against S07's exercised results. Unsupported features must remain labelled, not placed on the happy path.
   Expected: Every advertised operation has matching qualification evidence or an explicit unsupported label.

2. Validate frontmatter, links and package structure using the installed skill-creator-selected validator; no model hashes, broad project verification or external publication.
   Expected: New skill structure and links validate without shared projection edits.

3. Run `agent-code-skills plan check docs/plans/reusable-surface-authoring`. RESULT records the actual local skill path and remaining limitations.
   Expected: The plan checker passes and RESULT names the real skill location.

## Risks

Premature skill packaging can fossilize experiments. Link to the capability owner and versioned profile instead of duplicating model constants or workstation paths. A valid skill file does not prove the workflow can be followed; S09 owns that observation.

## RESULT

Created .codex/skills/effigy-surface-authoring/SKILL.md and docs/SURFACE-AUTHORING.md with source, preparation, sampling, method, review and recovery routes. Qualified API behavior and unsupported capabilities are distinguished; shared Blender/3DGen/Legaia skills remain unchanged. Skill-creator quick_validate passes and local skill links resolve. No new scripts, cloud registration or model paths were introduced. S07's technical results support these instructions; fresh operator/UI verification remains S09, so this package is not a claim of a production-qualified automatic artist.
