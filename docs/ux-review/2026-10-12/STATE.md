# Effigy UX review — state and continuation

Started: 2026-10-12 (Europe/Berlin). Baseline: `06be15b87798128a6ed1024c2f1f19d5c2aa8946`.

User request: map the app's workflows and interface elements, then examine workflows, buttons, layout, spacing and descriptions for a clean, straightforward experience. Preserve progress in Markdown.

Scope: review and a concrete improvement backlog. Production source and owner assets remain untouched during the review. Browser evidence uses isolated fixtures; no GPU generation, downloads or live Blender edits are needed to review the interface. Existing untracked `docs/audit/` belongs to previous work and must be preserved.

## Review ledger

| Work | Status | Evidence / next action |
|---|---|---|
| Identify stack, instructions and historical reviews | Complete | React/TypeScript/plain CSS/three.js; no applicable AGENTS.md found. Previous October 4 proposal and October 10 audit are historical leads, not current conclusions. |
| Map destinations and user workflows | Complete | [WORKFLOWS.md](WORKFLOWS.md): seven destinations/shared surfaces, workspace control inventory and 14 goal paths. |
| Inventory controls and interaction states | Complete | Source traced creation, import, workflow actions, history/compare, setup/welcome, rig/animation and recovery. |
| Render representative screens | Complete | 34 fixture captures at 1440×900, 1280×720, 390×844 and 640×360; [observations](evidence/observations.json). |
| Walk workflows and evaluate clarity | Complete | Eight focused runtime probes; existing real isolated-backend suite passed 42 tests. Expensive inference and live Blender were not part of review. |
| Inspect layout, spacing, copy and accessibility | Complete | Inspected rendered evidence, measured panel/toolbar layout and selected contrast, tabbed History and traced specialist keyboard gaps. Formal screen-reader/zoom checks remain implementation acceptance work. |
| Prioritize recommendations | Complete | [FINDINGS.md](FINDINGS.md): 15 findings, with reproduced behavior separated from source evidence and design recommendations. |
| Verify review artifacts and handoff | Complete | [Validator](evidence/verify-review.py) checks documents, links, workflow/finding counts, screenshots, probe errors and unchanged tracked source; output recorded in final verification. |

## Working files

- [PLAN.md](PLAN.md): scope, method and acceptance criteria.
- [WORKFLOWS.md](WORKFLOWS.md): current screens, controls and end-to-end paths.
- [FINDINGS.md](FINDINGS.md): prioritized findings with source and runtime evidence.
- [IMPROVEMENTS.md](IMPROVEMENTS.md): pending implementation order and acceptance checks.
- [Validation](evidence/VALIDATION.md): build, test, probe and visual evidence.
- `evidence/`: repeatable browser script, observations, log and 34 screenshots.

## Resume procedure

The requested review is complete. Read this file, FINDINGS.md and IMPROVEMENTS.md. All four passes are built and merged (the log below); what remains are the review's own follow-ups: a real 200 % browser zoom and NVDA. Recheck current callers before editing. Never treat fixture screenshots as successful AI generation or old test logs as current verification.

## Implementation log

- **Pass 1 built 2026-10-12** on branch `ux-pass1` (UX-01, UX-02, UX-03, UX-04, UX-08; the checkboxes in
  [IMPROVEMENTS.md](IMPROVEMENTS.md) say how). Decision for UX-08: History and Licences are one *docked, non-modal*
  panel (`role="region"`) in its own grid column, never an overlay; the batch panel stays an inline region. Three
  browser regressions at the end of `ui/tests/smoke.spec.ts` (the dirty guard through Close, a link and History; the
  Licences column and the History focus/Escape walk; the panel's sideways overflow at 1280/1024/900 px and the editor
  at 1280×720 and 640×360). Not done here: a real 200 % browser zoom and NVDA (the review's own follow-ups). Merged
  2026-10-12 (`32f24f2`).
- **Pass 1 reviewed 2026-10-12** (`ux-pass1-fixes`): two follow-ups fixed with browser regressions: the timeline's
  canvases were stretched by the editor's canvas minimum (ruler drawn 24 px, shown 180); a job result during an
  unsaved edit asked out of nowhere and was dropped when the edits were kept (now a View result notice). History at
  900 px leaves the view 272 px: kept, since a narrower panel cut its labels to one letter.
- **Pass 2 merged 2026-10-12** (`cb9fc97`, reviewed on the laptop: the readiness test's model mock came after the app had
  read the real list; three of its four failures there were the work machine's environment). **Pass 3 built 2026-10-12**
  (`ux-pass3`; UX-10, UX-11, UX-12; the checkboxes in IMPROVEMENTS.md say how). Browser tests at the end of `smoke.spec.ts`
  (the package to a folder, the batch preview, the library's view through navigation, Setup's card links and login).
- **Pass 3 merged 2026-10-12** (`398c8b5`). **Pass 4 built 2026-10-12** (`ux-pass4`; UX-13, UX-14 and the rest of
  UX-15; the checkboxes in IMPROVEMENTS.md say how). Browser tests at the end of `smoke.spec.ts` (the skip link, the h1,
  the field outline's contrast measured, an announced file error, a disabled task's reason; the key list with a value
  edit and a frame move saved; Select assets and Recently deleted, a real delete and restore against the test server);
  `tests/test_library.py` and `tests/test_api.py` cover the trash and every refusal. Not done: NVDA and a real 200 % zoom.
- **Pass 2 design** (2026-10-12, branch `ux-pass2`): [PASS2-NAVIGATION.md](PASS2-NAVIGATION.md): five tasks instead of
  fourteen stages, a Tools menu, the preparation states, readiness-aware primaries, the panel order per checkpoint,
  and the 2D track's row; proposed as two PRs. The owner decided the same day (its §7): the names, the menu, the renames,
  one PR, the 2D row.
- **Pass 2 built 2026-10-12** on branch `ux-pass2` (UX-05, UX-06, UX-07, UX-09, UX-15; one PR, the owner's decisions in
  PASS2-NAVIGATION.md §7; the checkboxes in [IMPROVEMENTS.md](IMPROVEMENTS.md) say how, the deviations from the design in
  PASS2-NAVIGATION.md §8). Checks: `ui/tests/workflow.spec.ts` (the task and preparation-state rules on fixture lineages)
  and four browser tests in `smoke.spec.ts` (the row at 1280 px, the preparation states and the Imported chip, the
  acceptance walk at 1280×720, readiness). Not done here: a real 200 % zoom and NVDA (the review's own follow-ups), the
  2D panels (they come with M50–M58 into the same row model).

## Latest checkpoint

*(The review's own closing note, written before any implementation; the log above is current.)*

Completed the source and rendered UX review. Existing visual foundation and several October 10 recovery fixes are present. Highest-value next changes: protect dirty editor exits; constrain motion and timeline controls; allocate Licences space; lead the action panel with check/export/clip selection; then simplify stage navigation and delivery.

Build exit 0; Playwright **42 passed (53.7s)**; final harness **34 captures / 8 probes / zero probe errors / zero page errors**. No tracked source changes, owner-library changes, GPU jobs, downloads, publishing or commits were made. Review browser/server instances closed in `finally`; the test runner shut down its isolated backend. Existing `docs/audit/` was preserved.

Initial harness calibration issues were corrected before final evidence. Below-fold setup and advanced 3D functionality have source/existing-test coverage; this review does not claim full visual inspection of every possible asset/editor state. Real inference quality, actual browser zoom, screen readers and live Blender remain explicit follow-up checks, not unfinished review tasks.
