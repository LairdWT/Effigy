"""settings.json: two writes at once both land (audit 2026-10-10, BE-004)."""

import threading
import time

from server import settings


def test_two_writes_at_once_both_persist(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "FILE", tmp_path / "settings.json")
    monkeypatch.setattr(settings, "_cache", None)
    real = settings.read

    def slow():
        d = real()
        time.sleep(0.02)
        return d

    monkeypatch.setattr(settings, "read", slow)
    threads = [
        threading.Thread(target=settings.write, kwargs={"welcomed": True}),
        threading.Thread(target=settings.write, kwargs={"models": "D:/models"}),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    monkeypatch.setattr(settings, "_cache", None)
    assert real() == {"welcomed": True, "models": "D:/models"}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["settings.json"]


def test_the_port_env_then_setup_then_8000(tmp_path, monkeypatch):
    """The app's port: EFFIGY_PORT wins, else the one chosen in Setup, else 8000; and who chose it."""
    monkeypatch.setattr(settings, "FILE", tmp_path / "settings.json")
    monkeypatch.setattr(settings, "_cache", None)
    monkeypatch.delenv("EFFIGY_PORT", raising=False)
    assert (settings.port(), settings.port_source()) == (8000, "default")
    settings.write(port=8001)
    assert (settings.port(), settings.port_source()) == (8001, "settings")
    monkeypatch.setenv("EFFIGY_PORT", "8002")
    assert (settings.port(), settings.port_source()) == (8002, "env")
