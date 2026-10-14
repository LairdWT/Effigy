# Research 10: Claude (owner's subscription) + MCP → working on assets in Blender

> Status: research notes, 2026-10-03. Facts verified against the official Claude Code docs
> (code.claude.com/docs/en/headless, …/agent-sdk/quickstart). Owner requirement: *"the tool may
> rely on my Claude subscription and MCP connection to work with the asset in Blender
> automatically."*

## 1. Verified facts

| Topic | Fact (source) |
|---|---|
| Non-interactive runs | `claude -p "<prompt>"` runs Claude Code headless. It exits 0 on success, non-zero on failure, and **143 on SIGTERM**. Send **SIGINT** to end a turn cleanly (headless docs) |
| Auth in `-p` | Without `--bare`, `-p` uses the **same login as interactive Claude Code**, including a subscription login. **`--bare` never reads OAuth/keychain credentials** and needs `ANTHROPIC_API_KEY` (headless docs) |
| Streaming | `--output-format stream-json --verbose [--include-partial-messages]` emits NDJSON events: `system/init` (model, tools, `mcp_servers` with status, `mcp_server_errors`), `assistant`/`user` messages with `tool_use`/`tool_result`, `stream_event` deltas, `system/api_retry`, `permission_denied`, and a final `result` (text, `session_id`, `total_cost_usd` estimate, `permission_denials`) |
| MCP | `--mcp-config <file-or-json>`. With `-p`, Claude Code waits for pending servers up to `MCP_TIMEOUT` (30 s default) before the first turn. Invalid entries are skipped and reported in `mcp_server_errors` |
| Tool lockdown | `--allowedTools "mcp__blender-mcp-pro__*,mcp__lt2__*"` + **`--permission-mode dontAsk`** → anything not allowed is **denied** instead of prompting. **`--permission-prompts none`** (v2.1.259+) tells Claude not to retry denied calls |
| Other flags | `--append-system-prompt[-file]`, `--json-schema` (structured result), `--resume <session_id>` / `--continue`, `--max-turns` |
| Repo content | Without `--bare`, `-p` **loads `.claude/settings.json` hooks and `.mcp.json` of the working directory without a trust prompt**. So we run it in a **dedicated, clean working directory** (the asset's folder), never in an untrusted repo |
| Limits | `-p` usage counts against the same plan limits as interactive use. `total_cost_usd` is a client-side estimate |
| MCP tool results | Images (PNG/JPEG/WebP) are supported as tool results (e.g. viewport screenshots). Output warning at 10k tokens, default cap 25k (`MAX_MCP_OUTPUT_TOKENS`) |
| **Policy** | *"Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. Please use the API key authentication methods described in this document instead."* (Agent SDK quickstart) |

## 2. What the policy means for us

| Path | Fit |
|---|---|
| **A. The user drives Claude** (Claude Desktop or interactive Claude Code) with our **MCP servers** configured via a shipped `.mcp.json` | **Clearly fine.** It's the user's own Claude product with MCP servers they chose. Best for open-ended work |
| **B. Our UI's "Ask Claude…" button spawns the user's own installed, logged-in `claude -p`** | Works technically: it's the user's own Claude Code install and login, run on their machine. **For the owner's personal use** this is them using Claude Code headless. **For an open-source tool distributed to others**, a button that runs agent features on people's claude.ai plans could be read as "offering claude.ai rate limits" in a third-party product. **Don't make subscription mode the default in distributed builds without Anthropic's approval**; ship it as an explicit opt-in that runs the user's own CLI, and document the policy |
| **C. API key** (`ANTHROPIC_API_KEY`, then `claude --bare -p …` or the Agent SDK) | **The documented, compliant path for third-party products.** Billed per token on the user's Console account |
| D. Embedding the Agent SDK with subscription OAuth | ✘ not allowed without approval |

**Decision:**
- Build **A** first. The MCP servers are needed anyway, and it works with zero extra code.
- Add **B** as the owner's personal convenience, behind a setting `claude.auth = "local-cli"`, with
  **C** (`claude.auth = "api-key"`) as the alternative.
- In public releases, B stays off by default and carries a note pointing to Anthropic's policy.

## 3. Design

### MCP servers (stdio, Python `mcp` SDK)

1. **blender-mcp-pro**: the owner's licensed **Blender MCP Pro** server (see research 08). Key via
   env `BLENDER_MCP_PRO_LICENSE`, never in the repo. 110+ tools, lazily enabled per category. Public
   builds without Pro fall back to the free `blender-mcp`.
2. **lt2**: a thin wrapper over our FastAPI:
   - `list_assets`, `get_version`
   - `pull_from_blender` (snapshot)
   - `run_step(name, params)` (e.g. `bake` onto the edited mesh)
   - `validate` (production checklist → JSON)
   - `export(profile)`

### "Ask Claude…" run (path B/C)

```
backend:
  1. pull_from_blender → version N            (snapshot for revert)
  2. spawn in library/<asset>/ (clean cwd):
     claude -p "<preset prompt with brief + budget + validate output>" \
       --mcp-config lt2-mcp.json \
       --allowedTools "mcp__blender-mcp-pro__*,mcp__lt2__*" \
       --permission-mode dontAsk --permission-prompts none \
       --append-system-prompt-file prompts/blender_agent.md \
       --output-format stream-json --verbose
       [--bare + ANTHROPIC_API_KEY when claude.auth = api-key]
  3. relay NDJSON lines → SSE "claude_event" → UI log (tool calls, screenshots, result)
  4. on result: run validate; UI shows Accept (pull → version N+1, transcript.jsonl attached)
     or Revert (reload version N into Blender)
  Cancel = SIGINT (clean turn end), then SIGTERM after a timeout.
```

`prompts/blender_agent.md` (system prompt addition):
- Enable only the needed Blender MCP Pro categories (`enable_tools`). Never enable `assets`.
- Work only through the provided tools.
- Check results with a viewport screenshot.
- Finish with `lt2.validate`.
- Never delete the user's objects outside the asset collection.
- Keep a short summary of what changed.

### Path A config (shipped)

`.mcp.json` at the repo root, so interactive Claude Code in this folder picks it up. Claude Desktop
needs the same two servers added to its own config (documented in the README, no automation).

## 4. Risks
- **Arbitrary Python in the user's Blender.** That's inherent to blender-mcp-style tools.
  Mitigations: snapshot first, Accept/Revert, the tool allowlist (no shell, no file edits outside
  MCP), localhost-only bridge with a session token.
- **Plan limits:** long agent runs consume the user's quota. Show the `total_cost_usd` estimate
  and turn count, and cap `--max-turns`.
- **CLI version drift:** newer flags (`--permission-prompts`, `mcp_server_errors`) need recent
  Claude Code. Check `claude --version` at startup and degrade gracefully.
- **Policy** (see §2): the default for public builds is A + C. B is the owner's opt-in.

## Sources
code.claude.com/docs/en/headless · code.claude.com/docs/en/agent-sdk/quickstart · code.claude.com/docs/en/cli-reference ·
code.claude.com/docs/en/mcp · code.claude.com/docs/en/authentication · code.claude.com/docs/en/permission-modes
