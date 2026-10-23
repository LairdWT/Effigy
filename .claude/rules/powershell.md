---
paths:
  - "**/*.ps1"
---

Before writing powershell code here, read plugins/powershell/CONVENTIONS.md
from the agent-enhanced-project library (or the vendored copy under
docs/conventions/). CODE.md deviations override the referenced
conventions. Every lint suppression carries a reason and a tracking ref.

Route powershell work through the powershell-core skill.
Audit changed powershell code with the powershell-audit skill.
