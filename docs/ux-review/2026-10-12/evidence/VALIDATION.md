# Validation record

Date: 2026-10-12. Source baseline: `06be15b87798128a6ed1024c2f1f19d5c2aa8946`.

| Check | Command / method | Observed result | Scope |
|---|---|---|---|
| UI production build | `npm run build` in `ui/` | Exit 0; TypeScript check and Vite bundle completed; `built in 218ms` | Existing production source |
| Existing test suite | `npm test` in `ui/` | Exit 0; `42 passed (53.7s)` | Temporary library/settings, backend port 8123; existing test mocks isolate Blender and expensive steps |
| Review harness | `node docs/ux-review/2026-10-12/evidence/browser-review.mjs` | Exit 0; 34 captures, 8 probes, 0 probe errors, no page errors | Vite 8147; mocked API/files/EventSource; installed Playwright and synthetic fixtures |
| Visual inspection | Opened the generated screenshots using local image inspection | Library, new asset, generation, bake, checks, import, skin, animation editor, export, licences, compact workspace and compact editor inspected | Layout/usability evidence; no generated-model quality claim |
| Contrast | Computed rendered color luminance in Chromium | Main text 15.78:1; secondary text 7.79:1; textarea border/page 1.76:1; border/fill 1.36:1 | Selected tokens/control only |
| Review artifact integrity | `.venv\Scripts\python.exe docs\ux-review\2026-10-12\evidence\verify-review.py` | PASS: seven Markdown files, 15 findings, 14 workflows, 53 local links, 34 screenshots, eight probes without errors; tracked source unchanged | Final review documents and evidence |

The full harness output is [browser-review.log](browser-review.log); structured observations are [observations.json](observations.json); the repeatable harness is [browser-review.mjs](browser-review.mjs).

## Probe results

| Probe | Result |
|---|---|
| `unsaved_animation_close` | Save enabled, no confirmation, editor closed, reopened speed 1 instead of edited 0.5; no save POST |
| `history_keyboard_focus` | Tab reached Inspect/Wireframe/Frame behind drawer; Escape from preview focus left drawer open |
| `licences_layout` | Licence row collapsed to 0 px; heading covered by workspace body |
| `preparation_copy_with_active_job` | Active Checking and Preparation stopped partway shown together |
| `failed_save_retains_editor` | Refused save retained editor, speed 0.5 and enabled retry action |
| `library_filter_navigation` | One Dragon card before navigation; empty search and eight cards after returning |
| `missing_feature_actions` | Missing-files warnings shown; both concept and 3D generation actions remained enabled |
| `contrast_and_structure` | Color ratios above; no skip-to-main link found |

## Fixture calibration and limits

Early exploratory runs had an incomplete generator preset (missing `op: generate`) and an incorrectly named Frame locator. They were corrected and the final run replaced the observations, screenshots and log. The final results above have no harness errors.

Review fixtures deliberately reuse one lantern image for thumbnails/references and small meshes for viewing. No owner assets were edited, no real GPU inference or installation was run, and no live Blender session was used. First-run setup below the fold was source-reviewed and exercised by the existing test, rather than fully visually scrolled in this harness. The 640×360 editor screen approximates the CSS viewport available at 200% desktop zoom; actual browser zoom and NVDA remain follow-up acceptance checks.
