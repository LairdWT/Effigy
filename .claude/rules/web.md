---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.css"
---

Before writing web code here, read plugins/web/CONVENTIONS.md
from the agent-enhanced-project library (or the vendored copy under
docs/conventions/). CODE.md deviations override the referenced
conventions. Every lint suppression carries a reason and a tracking ref.

Route web work through the typescript-core skill.
Audit changed web code with the typescript-audit skill.
