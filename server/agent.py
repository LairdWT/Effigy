"""Connect an agent (M40): the text each MCP client needs, a test that starts the bridge, and the guard that
keeps web pages out of the API (a page may reach 127.0.0.1 from the user's browser; Host and Origin say who asked)."""

import json
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
LOCAL = {"127.0.0.1", "localhost", "::1"}  # tests add "testserver"


class LocalOnly:
    """ASGI guard (pure ASGI: SSE streams through untouched). DNS rebinding changes the Host, a web page
    sends an Origin; the app's own UI and the MCP bridge send neither a foreign Host nor a foreign Origin."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            h = {k.decode(): v.decode("latin-1") for k, v in scope["headers"]}
            origin = h.get("origin")
            bad = None
            if urlsplit("//" + h.get("host", "")).hostname not in LOCAL:
                bad = 400, "bad_host", "this API answers to 127.0.0.1 and localhost only"
            elif origin is not None and (
                urlsplit(origin).scheme != "http" or urlsplit(origin).hostname not in LOCAL
            ):
                bad = 403, "bad_origin", "this API does not answer web pages from other origins"
            if bad:
                r = JSONResponse({"error": {"code": bad[1], "message": bad[2]}}, status_code=bad[0])
                return await r(scope, receive, send)
        await self.app(scope, receive, send)


def uv() -> str | None:
    bundled = ROOT / "uv.exe"  # the portable zip's own
    return shutil.which("uv") or (str(bundled) if bundled.is_file() else None)


def command() -> tuple[str, list[str]]:
    server = str(ROOT / "mcp" / "effigy_server.py")
    return uv() or "uv", ["run", "--frozen", "--project", str(ROOT), "python", server]


def setup() -> dict:
    exe, args = command()
    entry = {"command": exe, "args": args}
    js = lambda key, extra=None: json.dumps({key: {"effigy": {**(extra or {}), **entry}}}, indent=2)
    q = lambda v: json.dumps(v, ensure_ascii=False)
    toml = f"[mcp_servers.effigy]\ncommand = {q(exe)}\nargs = {q(args)}\ntool_timeout_sec = 120\n"
    clients = [
        ("claude-code", "Claude Code", "Run this in a terminal.",
         # a path quoted: its backslashes survive Git Bash as well as PowerShell and cmd
         "claude mcp add -s user effigy -- " + " ".join(f'"{a}"' if ("\\" in a or " " in a) else a for a in [exe, *args])),
        ("claude-desktop", "Claude Desktop", r"Merge into %APPDATA%\Claude\claude_desktop_config.json, then restart Claude.",
         js("mcpServers")),
        ("codex", "Codex", "Add to ~/.codex/config.toml.", toml),
        ("cursor", "Cursor", "Merge into ~/.cursor/mcp.json.", js("mcpServers")),
        ("vscode", "VS Code", "Merge into .vscode/mcp.json in your project.", js("servers", {"type": "stdio"})),
        ("gemini", "Gemini CLI", "Merge into ~/.gemini/settings.json.", js("mcpServers")),
    ]  # fmt: skip
    return {
        "root": str(ROOT),
        "python": args,
        "server": args[-1],
        "uv": uv(),
        "clients": [{"id": i, "name": n, "how": h, "text": t} for i, n, h, t in clients],
    }


async def _tools(exe: str, args: list[str], log) -> list[str]:
    params = StdioServerParameters(command=exe, args=args, cwd=ROOT)
    async with stdio_client(params, errlog=log) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        return [t.name for t in (await s.list_tools()).tools]


def test() -> dict:
    exe, args = command()
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as log:

        def tail() -> str:
            log.flush()
            log.seek(0)
            return log.read()[-800:]

        async def run():
            with anyio.fail_after(30):
                return await _tools(exe, args, log)

        try:
            return {"ok": True, "tools": anyio.run(run)}
        except BaseException as e:  # a crash or a timeout in the bridge: show why
            if isinstance(e, KeyboardInterrupt):
                raise
            err = "no tools in 30 s" if isinstance(e, TimeoutError) else f"{type(e).__name__}: {e}"
            return {"ok": False, "error": (err + "\n" + tail()).strip()}
