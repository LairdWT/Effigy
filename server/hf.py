"""The Hugging Face login, from the app (IMPLEMENTATION.md M35c; owner decision 2026-10-08).

The token the user pastes goes straight into huggingface_hub's own token store (where `hf auth login` puts
it, in the user's profile), through .venv-ml's huggingface_hub on stdin: never a command line, the library,
a log, a job's params or the browser's storage. The page only learns whether a login exists, as whom, and
whether the gated models' licences are accepted.
"""

import json
import re
import subprocess

from server import jobs
from server.library import ApiError

# the gated repos (tools/download_models.py) and the model groups that need them
GATED = {
    "facebook/dinov3-vitl16-pretrain-lvd1689m": ["fast", "faithful"],
    "meta-llama/Meta-Llama-3-8B-Instruct": ["kimodo"],
}
TOKEN = re.compile(r"^hf_[A-Za-z0-9]{20,100}$")

_STATUS = """
import json, sys
from huggingface_hub import HfApi, get_token
from huggingface_hub.errors import GatedRepoError
api, out = HfApi(), {"token": get_token() is not None, "user": None, "access": {}}
if out["token"]:
    try:
        out["user"] = api.whoami()["name"]
    except Exception as e:  # offline, or the token was revoked
        out["error"] = type(e).__name__
    for repo in sys.argv[1:]:
        try:
            api.auth_check(repo)
            out["access"][repo] = True
        except GatedRepoError:
            out["access"][repo] = False
        except Exception:
            out["access"][repo] = None
print(json.dumps(out))
"""
_LOGIN = """
import json, sys
from huggingface_hub import login, whoami
token = sys.stdin.read().strip()
offline = ("Connect", "Timeout", "Proxy", "Offline")
try:  # ponytail: login() asks Hugging Face again; one round trip more, and no private API
    name = whoami(token=token)["name"]
except Exception as e:
    kind = type(e).__name__
    print(json.dumps({"error": "network" if any(w in kind for w in offline) else "invalid"}))
    sys.exit(0)
try:
    login(token=token, add_to_git_credential=False)
except Exception as e:
    print(json.dumps({"error": "store", "kind": type(e).__name__}))
    sys.exit(0)
print(json.dumps({"user": name}))
"""
_LOGOUT = "from huggingface_hub import logout\nlogout()\n"


def _run(script: str, *args: str, stdin: str = "") -> dict | None:
    """One of the scripts above in .venv-ml; its last output line as JSON (None for none)."""
    try:
        r = subprocess.run(
            [jobs._python("hf"), "-c", script, *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            env=jobs._env(),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as e:
        raise ApiError(503, "unavailable", f"could not ask Hugging Face: {type(e).__name__}") from e
    lines = r.stdout.strip().splitlines()
    try:
        return json.loads(lines[-1]) if lines else None
    except ValueError:
        return None


def status() -> dict:
    """{"token": bool, "user": name or None, "access": {repo: True | False | None (unknown)}, "gated": GATED}.
    Without `.venv-ml` (a dev checkout, CI; run.bat makes it on a real install) the answer is the unknown one,
    not a 503: the pages treat it as "log in first", and an <img>-free poll should not log browser errors."""
    import os
    from pathlib import Path

    home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    token_file = Path(os.environ.get("HF_TOKEN_PATH", home / "token"))
    present = bool(os.environ.get("HF_TOKEN")) or token_file.is_file()
    return {"token": present, "user": None, "access": {}, "gated": GATED, "offline": True}


def login(token: str) -> dict:
    token = token.strip()
    if not TOKEN.match(token):
        raise ApiError(
            400,
            "bad_token",
            "a Hugging Face token starts with hf_: copy it whole from huggingface.co/settings/tokens",
        )
    out = _run(_LOGIN, stdin=token) or {"error": "invalid"}
    if out.get("error") == "store":
        raise ApiError(
            500,
            "store",
            f"Hugging Face's login could not be saved on this computer ({out.get('kind')})",
        )
    if out.get("error") == "network":
        raise ApiError(
            503, "offline", "could not reach huggingface.co: check the internet connection"
        )
    if "user" not in out:
        raise ApiError(
            400,
            "bad_token",
            "Hugging Face did not accept this token: create a Read token and copy it whole",
        )
    return {"user": out["user"]}


def logout() -> dict:
    _run(_LOGOUT)
    return {"ok": True}
