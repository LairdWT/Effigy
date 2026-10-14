# Third-party notices — `.claude/`

The agent definitions in `agents/` were brought over from the owner's `demolition_man` project on
2026-10-05 and adapted to this repository. Three of them descend from **ECC**
(https://github.com/affaan-m/ECC), at commit `bf70150` (2026-09-21), under the MIT License reproduced
below; the `effigy-*` ladder (explorer, worker, expert, escalation, fallback) is the owner's own work.

| File | From ECC | How |
|---|---|---|
| `agents/silent-failure-hunter.md` | `agents/silent-failure-hunter.md` | verbatim, plus an "In this repository" section |
| `agents/comment-analyzer.md` | `agents/comment-analyzer.md` | verbatim, plus an "In this repository" section; model `haiku` → `sonnet` |
| `agents/step-reviewer.md` | `agents/cpp-reviewer.md` (via demolition_man's `unreal-cpp-reviewer.md`) | adapted: structure, severity scale and approval criteria kept, checks rewritten for this repository |

Nothing else from ECC is used: no hooks, commands, scripts, install steps or MCP configuration. These
files are development tooling; nothing from them ships in the application or its assets.

---

MIT License

Copyright (c) 2026 Affaan Mustafa

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
