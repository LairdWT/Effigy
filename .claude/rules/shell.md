---
paths:
  - "**/*.sh"
---

Before writing shell code here, read plugins/shell/CONVENTIONS.md
from the agent-enhanced-project library (or the vendored copy under
docs/conventions/). CODE.md deviations override the referenced
conventions. Every lint suppression carries a reason and a tracking ref.

Route shell work through the shell-core skill.
Audit changed shell code with the shell-audit skill.
