"""Start the offline app on loopback port 8370, the browser
opening there once it listens. EFFIGY_NO_BROWSER keeps the browser closed."""

import os
import sys
import threading
import webbrowser

import uvicorn

from server import machine, runtime_policy, settings


def main() -> None:
    runtime_policy.activate()
    port = settings.port()
    if not machine.port_free(port):
        sys.exit(
            f"Effigy cannot start: loopback port {port} is occupied. Close the other Effigy instance "
            "or resolve the port conflict before retrying run.bat."
        )
    url = f"http://127.0.0.1:{port}"
    if not os.environ.get("EFFIGY_NO_BROWSER"):
        t = threading.Timer(2, webbrowser.open, [url])
        t.daemon = True
        t.start()
    uvicorn.run("server.app:app", host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
