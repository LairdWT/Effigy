# Effigy UX review plan

## Intended result

A current, evidence-based map and review that a future implementation agent can use without reconstructing this conversation. Lead with improvements that reduce confusion, prevent lost work and simplify common tasks. Keep specialist 3D tools available through clear progressive disclosure.

## Sequence

1. Map navigation, screens, user goals, expected inputs and outputs, primary actions and optional branches.
2. Trace the implementation of each path, including busy, empty, error, success and reconnect states.
3. Render representative fixture screens at 1440×900 and 1280×720, plus compact layouts and a zoom-equivalent viewport.
4. Walk first-run setup, description/image creation, model import, preparation, character tools, checking/export, library/history and editor recovery. Use request mocks where expensive computation would otherwise be required.
5. Inspect hierarchy, panel density, spacing, line length, labels, target sizes, contrast, keyboard and focus behavior. Record observations separately from recommendations.
6. Write prioritized findings and a staged implementation backlog with observable acceptance checks.
7. Verify the documents, evidence and source-change scope; leave an explicit continuation pointer.

## Evidence standards

- Cite current source as `path:line` and note the baseline above; lines can move after implementation.
- Label runtime observations, source-confirmed behavior and design judgments distinctly.
- Reproduce material historical issues where practical; never copy old conclusions as newly verified.
- Use the existing Playwright installation and local test fixtures. Avoid production jobs, model installation, owner-library writes and external publishing.
- A complete review does not certify AI output quality, production inference, screen-reader compatibility or engine imports that were not exercised.

## Acceptance criteria

- Every main destination and major user goal appears in the workflow inventory.
- Findings explain the user impact, current evidence and concrete desired behavior.
- Visual claims refer to inspected rendered screens or measured CSS/DOM behavior.
- Recommendations retain useful specialist tools while simplifying common paths.
- Markdown records distinguish work completed from implementation still pending.

## Review references

- [Vercel Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) fetched on 2026-10-12; applied selectively to this local 3D app.
- [WAI-ARIA dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) for keyboard/focus evaluation.
- Existing [redesign proposal](../../archive/UI_REDESIGN_PROPOSAL.md) and the October 10 frontend audit (`docs/audit/2026-10-10/02-frontend.md`, untracked on purpose) as historical context only.
