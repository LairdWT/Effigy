"""Start the app (run.bat, run.sh): on its port (EFFIGY_PORT, else Setup's choice, else 8000), the browser
opening there once it listens. EFFIGY_NO_BROWSER keeps the browser closed."""

import os
import sys
import threading
import webbrowser

import uvicorn

from server import machine, settings


def main() -> None:
    port = settings.port()
    if not machine.port_free(port):
        sys.exit(
            f"Port {port} is in use by another program (Unreal's MCP plugin uses 8000). Start Effigy once on "
            "another port (set EFFIGY_PORT=8001, then run.bat), then choose one for good in Setup, App address."
        )
    url = f"http://127.0.0.1:{port}"
    if not os.environ.get("EFFIGY_NO_BROWSER"):
        t = threading.Timer(2, webbrowser.open, [url])
        t.daemon = True
        t.start()
    uvicorn.run("server.app:app", host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
