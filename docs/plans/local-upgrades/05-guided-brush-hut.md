# Paint the edited hut with guided brush strokes

Spoke: S05
Outcome: Produce and review an explicit brush-painted hut candidate in Effigy.
Depends-on: S04
Decisions: D12, D13, D14
Constraints: C1, C2, C3, C5
Skills: art:texture-painting-core, python:python-core, powershell:powershell-core, aep:aep-core
Read-set: INDEX.md, 04-owner-hut-iteration.md#result, CODE.md, steps/_views.py, N:/generated/Effigy/legaia_rim_elm_hut_effigy_comparison/096_refine/, N:/generated/Effigy/legaia_rim_elm_hut_effigy_comparison/099_export/authoring/hut-owner-texture-trial.blend, D:/AI/Blender/Skills/blender-projection-painting/references/paint-stroke-replay.md
Write-set: docs/plans/local-upgrades/, scratch/legaia/, N:/generated/Effigy/
State: done

## Context

Expected 45 turns, 256-turn breaker, 2250000-token ceiling. This is a local appearance-only candidate on the owner-edited hut, not a canonical Legaia scene edit or production promotion. Vahn stays held. No model generation is required.

Art profile for this isolated Effigy pass: preserve the current 096_refine atlas and geometry exactly. One 1024 square albedo, unique UVs, existing 16-pixel requested packing gutters, no mirroring or repacking. Measured reference density is 432.322 texels per Effigy asset unit, with no permitted density change. This binds to the current asset's scale; no physical building-metre conversion is asserted. The generic static-environment 512 px/m profile is recorded as a separate scene convention, not silently imposed on this normalized asset.

Source/guide: 096_refine's current painted appearance, rendered from four matching oblique views. Palette comes from this guide, with global material medians. Preserve windows, vent openings, silhouette and the owner's geometry. Roof and masonry recipes are a provisional hut-specific painting round; the terrain recipe is not applied indiscriminately.

Review goal: art-direction fidelity to visible brushwork, coherent material identity and the owner's inn reference. Apply description -> analysis -> qualified interpretation -> criteria -> strengths/improvements inline. The art-review skill's formal hash-bound multi-agent package conflicts with standing no-hash/no-subagent/no-extra-pack rules; do not generate it or claim formal protocol completion. Use the pinned art-review-source-bundle-v2 criteria without new web research.

## Evidence

- steps/_views.py:117 supplies local unlit guide renders with triangle visibility. The installed Blender painting reference supplies the native image_paint replay and linear colour/premultiplied canvas contract.
- S04 measured 409 triangles, zero collapsed new UV triangles and zero sampled UV overlaps. The 096 texture trial and its authoring blend are immutable inputs here.
- Observed guide: round hut, domed brown roof, pale narrow-course walls, buff masonry/chimney, gray-green foundation, dark framed windows and timber steps. Surface colour is coherent but long roof streaks and repeated even masonry dominate over individual brushwork.

### Painting rounds - 2026-10-20

- Native Blender image_paint replay completed for both candidates: 67069 strokes and 2339937 pressure-tapered dabs per round, using SolidFlat and StreakChalk tips. Four oblique guides supply visibility and colour; per-material float canvases prevent material spill. No diffusion model ran.
- Round 01: 101_import_model (job 189a6785b9f1), 102_sprites (0aaef1c4b1dc). Actual eight-direction renders retain the original palette, with softened roof streaks and rougher masonry. Brush marks remain too restrained at normal viewing size.
- Round 02: 104_import_model (28cce071395b), 105_sprites (2a2d0501257c). Only pigment contrast around global material medians changed to 1.6; stroke placement, sizes, pressure, seed and guide stayed fixed. Eight-direction renders and both comparison sheets were inspected. Broken pigment reads more clearly on straw and masonry; openings and pale wall courses remain readable. This is the assistant's preferred review candidate, not owner approval.
- Round 02 changed 311139 surface texels and 43146 gutter texels; zero changes outside permissions and zero alpha changes. Of painted texels, 170210 exceed 0.95 coverage. Protected feature mask covers 130835 texels; 28825 permitted but unseen texels remain unchanged. The output retains underlying guide colour in partially painted areas.
- Residual visual limits: regular mortar courses and long underlying straw strands remain. No obvious new camera-tone boundary was seen in the inspected views; this does not prove every texel defect absent or establish the owner's inn-quality target as met.
- Export 106_export (e3f2e7ddd5bc) reopened as rim_elm_hut_guided_brush_export_reop/002_import_model (402a17a1d02e), with one material, one texture and no missing textures. Source 096, candidate 104, export and reopened GLBs all have 409 triangles, the same geometry/UV assignments and a 1024-square atlas.
- Delivery: N:/generated/Effigy/legaia_rim_elm_hut_effigy_comparison/106_export/authoring/ contains hut-brush-02.blend, painted-01.png (16-bit), style-comparison.png and detail-comparison.png. Headless reopening confirmed all images packed and all five authoring UV layers retained. Higher-resolution images in hidden historical reference objects remain packed for editability; the visible delivered mesh uses one 1024 atlas.
- Changed-file Ruff passed. Agent-started paint and inspection processes exited; existing Blender windows and services remain untouched. Changes remain uncommitted.

## Steps

1. Extract material permissions from the retained authoring references; match them to the current mesh without changing geometry or UVs.
2. Render guides and derive front-visible texel ownership for four oblique cameras.
3. Plan separate seeded broad, medium and accent strokes from guide colours. Preserve mortar/layout and protected features; use distribution fields for placement, not cell-shaped paint.
4. Replay planned dabs with Blender brushes on float camera canvases in a private offline GUI process. Retain per-view caches for safe resume.
5. Composite stroke-over-stroke through the existing permission-checked patch writer, preserve alpha and refill permitted gutters. Keep a 16-bit authoring texture at 1024.
6. Import the candidate into Effigy, render actual textured mesh views, compare against 096, and record the inline visual judgment separately from owner approval.
7. Export/reopen the reviewable candidate and retain an editable blend.

## Files to touch

- docs/plans/local-upgrades/
- scratch/legaia/
- N:/generated/Effigy/

## Verification

1. Native stroke replay and patch writer. Expected: real planned brush operations, no changes outside permission/gutters, unchanged alpha.
2. Mesh/UV/dimensions and export reopen. Expected: 409 triangles, same UV assignments and 1024 albedo, no missing textures.
3. Actual mesh renders and comparison sheet. Expected: inspectable brushwork, retained material identities and no introduced view seams; findings are provisional.
4. Changed-file Ruff and plan check. Expected: pass without code tests, model hashes or shared installation changes.

## Risks

Brushwork can obscure narrow mortar, turn straw into wood, or produce uniform dashes. Camera overlap can create tone boundaries. Preserve feature masks and global palettes; reject a visually worse round without promoting it.

## RESULT

Produced native brush-painted variants 101 and 104; preferred 104 is starred "Brush 02 - stronger pigment (review)". Each round replayed 67069 strokes / 2339937 dabs. Reviewed eight-direction renders and before/after sheets. Round 02 changes only pigment contrast; permission checks found zero outside-mask or alpha changes. Source, candidate, export and reopen retain 409 triangles, identical geometry/UVs and one 1024 texture. Export 106 reopened without missing textures; editable packed blend and comparison images are in 106_export/authoring/. Brushwork is clearer, but regular mortar and underlying roof strands remain. Owner visual approval is pending; no formal multi-agent/hash art-review package was run. Vahn stays held. Ruff passed.
