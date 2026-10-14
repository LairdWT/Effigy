import socket
import threading
import time

import pytest


@pytest.fixture
def live_server():
    """The app on a real uvicorn in a thread (TestClient can't stream SSE) → base URL. Joins the thread on
    teardown: the app's shutdown kills running jobs, so it must not fire later, inside another test."""
    import uvicorn

    from server.app import app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=20)
    assert not thread.is_alive(), "uvicorn did not shut down"


def glb_path():
    """A throwaway .glb on disk: library.import_file takes a path (M39) and moves it into the library."""
    import tempfile
    import uuid
    from pathlib import Path

    p = Path(tempfile.gettempdir()) / f"effigy_test_{uuid.uuid4().hex}.glb"
    p.write_bytes(b"glb")
    return p


@pytest.fixture(autouse=True)
def _testserver_is_local(monkeypatch):
    """M40: the API answers only to loopback hosts; TestClient's default Host is testserver."""
    from server import agent

    monkeypatch.setattr(agent, "LOCAL", agent.LOCAL | {"testserver"})
