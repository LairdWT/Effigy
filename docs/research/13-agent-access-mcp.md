# 13 · Agent access over MCP (and dropping Ask Claude)

Owner, 2026-10-09: "i want to make the app available to claude or other agents via mcp. this also means, we then can
drop the 'ask claude' section in the ui completely". Research by three agents in parallel (this repo; the protocol,
SDK and clients; comparable creative-app servers), sources read on 2026-10-09 unless dated. Decisions: the end of
this note; the build plan: IMPLEMENTATION.md M40.

## 1. What we have

- `mcp/lt2_server.py` (M9): a stdio server on the official SDK (`mcp` 2.3.0, `MCPServer`), 7 tools frozen in §3.7:
  `list_assets`, `get_version`, `run_step`, `validate`, `export`, `pull_from_blender`, `open_in_blender`. It calls
  the app's HTTP API (`LT2_API`, default `http://127.0.0.1:8000`) with urllib; `run_step` posts the job and polls
  every second **until it ends**: no progress, no cancel, no bound (a 15-minute bake outlives most clients' tool
  timeouts). No images (an agent cannot see a result), no way to bring a file in, no step or parameter discovery
  (`GET /api/steps` lists names and presets only). Two tests (`tests/test_lt2_mcp.py`): the tool list, and a live
  uvicorn round trip with the `_echo` step.
- It did not connect in our own Claude Code sessions: `.mcp.json` runs `uv run --project ${LT2_ROOT} …` and
  `LT2_ROOT` is set nowhere (only HANDOVER mentions it; `claude_runner` sets it for its own child). Relative paths
  fix it for this repo; any other client needs the install's absolute path, which the app can print.
- Ask Claude (M9 path B): `server/claude_runner.py` runs `claude -p` with our MCP servers, four routes
  (`/api/claude/presets`, `/api/assets/{id}/claude/run`, `/api/jobs/{id}/accept|revert`), `prompts/presets.yaml`,
  `prompts/blender_agent.md`, a UI panel in the Blender section, Keep/Revert on job rows, the `claude_event` SSE
  event, `blender_client.revert()`, tests and docs. Nothing else depends on it (Edit in Blender's pull is its own
  route). Old versions on disk keep `provenance: "claude_run"`: the label stays for them.
- The backend has **no Host or Origin check** (`server/app.py`), yet serves DELETE routes and the HF login. A web
  page can reach `127.0.0.1:8000` (DNS rebinding, simple cross-origin POSTs): worth closing whatever MCP does.

## 2. MCP in October 2026

- **Spec**: 2025-03-26 (Streamable HTTP, annotations), 2025-06-18 (structured output, elicitation, resource links,
  titles), 2025-11-25 (icons, tasks experimental, Origin 403, validation errors as tool errors) and **2026-07-28**
  (current): stateless (no `initialize`, `server/discover`), multi-round-trip requests replace server→client
  requests, **tasks moved to an optional extension** that no client lists as supported, Roots/Sampling/Logging
  deprecated. https://modelcontextprotocol.io/specification/2026-07-28/changelog
- **Python SDK** `mcp` 2.3.0 (2026-10-02, MIT): `MCPServer`, dual-era (serves 2026-07-28 and older handshake
  clients from one server), `ToolError` → an `isError` result the model can correct, `ctx.report_progress`,
  `Image(...)` → real image content, cancellation of a sync tool only at `anyio.from_thread.check_cancelled()`,
  tasks **not** implemented, MCP Apps built in. https://pypi.org/project/mcp/ ·
  https://py.sdk.modelcontextprotocol.io/whats-new/ · standalone `fastmcp` 4.1 is Apache-2.0 and adds tasks via
  Docket: not needed.
- **Clients** (stdio everywhere; the only way Claude Desktop reaches a local server):

  | Client | Configure | Limits that matter here |
  |---|---|---|
  | Claude Code | `claude mcp add -s user lt2 -- …`, or `.mcp.json` (`${VAR:-default}`) | tool search on; descriptions and instructions cut at 2,048 chars; a call over 2 min goes to the background; idle 30 min (stdio), 5 min (HTTP); 25k-token results; images shown, the original saved to a file |
  | Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json`, or a `.mcpb` bundle | connectors: 240 s a call (unverified for local stdio) |
  | Codex CLI | `~/.codex/config.toml` `[mcp_servers.lt2]` / `codex mcp add` | **`tool_timeout_sec` 60 by default**, instructions: first 512 chars |
  | Cursor | `~/.cursor/mcp.json`, install deeplink | asks before each tool by default |
  | VS Code | `.vscode/mcp.json` / `code --add-mcp` | 128 tools a request |
  | Gemini CLI | `~/.gemini/settings.json` / `gemini mcp add` | 600 s timeout |

  https://code.claude.com/docs/en/mcp · https://learn.chatgpt.com/docs/extend/mcp?surface=cli ·
  https://cursor.com/docs/mcp.md · https://code.visualstudio.com/docs/copilot/reference/mcp-configuration ·
  https://geminicli.com/docs/tools/mcp-server/
- **Images**: Claude counts ⌈w/28⌉·⌈h/28⌉ tokens (768² ≈ 784, 1024² ≈ 1,369), images stay in context; a 2×2
  contact sheet at 768 px costs half of four 512 px pictures. Base64 inside text is **not** an image to the model
  (the likely reason Claude could not see Blender MCP Pro's screenshots in M9).
  https://platform.claude.com/docs/en/build-with-claude/vision

## 3. How others do it

| Server | Tools | Long jobs | Visuals |
|---|---|---|---|
| Epic Unreal MCP (UE 5.8, embedded HTTP `:8000/mcp`) | 3 meta-tools over 30+ toolsets, skills | progress, async results | async image results |
| MCP for Blender (ahujasid) | ~9 coarse + `execute_blender_code` | `generate_3d` waits ≤ 45 s, then a job handle; a repeat resumes | `look`: viewport/angles/frames, `max_size` 768, one image |
| Comfy-Org comfy-mcp | 40 workflow tools | `wait` with timeout → `timed_out` + id; progress | `fetch_outputs` inline or paths |
| CoplayDev unity-mcp | ~50 `manage_*` + batch | `job_id` + long-poll `wait_timeout=60` | 6-angle contact sheet, `max_resolution` 256–512 |
| Meshy (official) | 24: generate/remesh/rig/animate/status | task id + status | saves files, paths |
| Rodin | 2 | download polls | `preview.webp` as an image + path |

Patterns that work: few coarse tools built around the workflow (Anthropic: "fewer, consolidated tools"; FastMCP:
generating from an API is "not for mirroring your API to LLM clients"); **wait a bounded time, else hand back a job
id**; a repeated request resumes the running job instead of paying twice; one combined preview image with a small
size and the file path; files as local paths, never base64; destructive tools marked and few; the pipeline
described in server instructions plus a skill file (Agent Skills, served over MCP by SEP-2640, final 2026-09-13,
no client yet). Unity deprecated its in-editor MCP for a CLI + skills; Epic and Meshy ship skills beside their
servers. Pitfalls: too many tools, base64 as text, unbounded waits, unauthenticated localhost sockets
(CVE-2026-66004, a path traversal in blender-mcp), Windows `uvx`/`npx` not on a GUI client's PATH.
https://www.anthropic.com/engineering/writing-tools-for-agents · https://github.com/ahujasid/blender-mcp ·
https://github.com/Comfy-Org/comfy-mcp · https://github.com/CoplayDev/unity-mcp ·
https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor ·
https://modelcontextprotocol.io/seps/2640-skills-extension

## 4. Security

- stdio: the client and the server are one trust domain (the user's account); folder allow-lists are guard rails,
  not a boundary. Tool results that carry file contents are untrusted input to the model.
  https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/local-server-security
- A local HTTP endpoint needs Host/Origin validation and a token ("binding to 127.0.0.1 is not an authentication
  boundary"); the SDK's mounted app checks Host and Origin by default. Not needed while we stay on stdio, but the
  **app's own API** needs the same Host and Origin checks today.

## 5. Decisions for Effigy

1. **Keep the stdio bridge** (`mcp/lt2_server.py` → the app's HTTP API). Every client launches it, Claude Desktop
   only reaches local servers this way, an app restart does not kill the client's session, and it adds no network
   surface. A `/mcp` endpoint inside FastAPI: later, only if several clients must share live state.
2. **A small coarse tool set** (about 14) around the workflow, with discovery (`describe_steps` from the steps'
   own docstrings), a preview tool returning one real image, file import from a local path, export to a folder,
   bounded waits (≤ 45 s, under Codex's 60 s) with progress and a job id to poll, cancel, and identical requests
   resuming the running job. No tasks extension (no client supports it), no deletes (the library stays
   append-only for agents; the owner deletes in the app).
3. **Describe the pipeline twice**: server instructions under 512 characters for the essentials (Codex reads only
   that much), the full guide as `mcp/SKILL.md`, served as a resource and readable through a tool.
4. **Setup gains "Connect an agent"**: the ready-to-paste command or config for Claude Code, Claude Desktop, Codex,
   Cursor/VS Code and Gemini with this install's absolute path filled in, and a check that the server starts. The
   repo's `.mcp.json` uses relative paths (no `LT2_ROOT`).
5. **Drop Ask Claude** completely (runner, routes, prompts, panel, Keep/Revert, events, tests, docs), keep the
   "Claude edit" label for old versions.
6. **Close the API**: Host must be `127.0.0.1`/`localhost` (any port), and a request carrying an `Origin` must come
   from the app itself (or the Vite dev server); otherwise 403.
