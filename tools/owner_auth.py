"""GitHub owner authorization; credentials stay in gh's OS credential store.

The private cache contains identity and expiry, never an access token. This is
an offline owner-session policy, not protection against a user modifying code.
"""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time

OWNER_ID = 90290458
OWNER_LOGIN = "PranavMishra28"
TTL_SECONDS = 7 * 86400
TOKEN_ENV = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")


class AuthorizationError(RuntimeError):
    pass


def cache_path():
    return Path.home() / "Library/Application Support/LocalAI/state/owner.json"


def _safe_parent(path, create=False):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise AuthorizationError("Linked owner-session storage is refused")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.exists():
        info = path.parent.stat()
        if info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise AuthorizationError("Owner-session storage must be private and owned")
    return path


def logout(path=None):
    path = _safe_parent(path or cache_path())
    if path.exists():
        _read(path, decode=False)
        path.unlink()


def _read(path, decode=True):
    path = _safe_parent(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_nlink != 1 or info.st_mode & 0o077 or info.st_size > 4096):
            raise AuthorizationError("Owner-session cache has unsafe permissions or size")
        if not decode:
            return None
        value = json.load(stream)
        if not isinstance(value, dict):
            raise AuthorizationError("Owner-session cache has an invalid format. Run kryn login.")
        return value


def authorize(path=None, now=None):
    """Cheap offline check. Expiry/no cache requires explicit login, never fallback."""
    now = time.time() if now is None else now
    try:
        value = _read(path or cache_path())
    except (OSError, ValueError) as error:
        raise AuthorizationError("No valid owner session. Run kryn login.") from error
    if (value.get("schema") != 1 or type(value.get("owner_id")) is not int
            or value["owner_id"] != OWNER_ID or value.get("credential_source") != "keyring"
            or type(value.get("verified_at")) not in (int, float)
            or type(value.get("expires_at")) not in (int, float)
            or not value["verified_at"] <= now < value["expires_at"]
            or value["expires_at"] - value["verified_at"] != TTL_SECONDS):
        raise AuthorizationError("Owner session is invalid or expired. Run kryn login.")
    return value


def _gh(command, runner):
    binary = shutil.which("gh")
    if not binary:
        raise AuthorizationError("GitHub CLI is required for login and private downloads")
    result = runner([binary, *command], capture_output=True, text=True, timeout=30)
    if result.returncode:
        # Never relay credential-related subprocess output to logs or model context.
        raise AuthorizationError("GitHub identity verification failed; check network and gh authentication")
    try:
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError("Expected identity object")
        return value
    except (ValueError, TypeError) as error:
        raise AuthorizationError("Unexpected GitHub identity response") from error


def login(path=None, now=None, runner=subprocess.run):
    """Refresh online through gh. A failed refresh invalidates KRYN's old session."""
    path = _safe_parent(path or cache_path(), create=True)
    if path.exists():
        logout(path)
    if any(os.environ.get(key) for key in TOKEN_ENV):
        raise AuthorizationError("Use gh's OS credential store; token environment overrides are refused")
    hosts = Path(os.environ.get("GH_CONFIG_DIR", str(Path.home() / ".config/gh"))) / "hosts.yml"
    if hosts.is_file() and re.search(r"^\s*oauth_token:\s*\S+", hosts.read_text(), re.M):
        raise AuthorizationError("Plaintext gh token storage is refused. Reauthenticate with the OS credential store")
    status = _gh(["auth", "status", "--active", "--hostname", "github.com", "--json", "hosts"], runner)
    accounts = status.get("hosts", {}).get("github.com", [])
    if (len(accounts) != 1 or accounts[0].get("active") is not True
            or accounts[0].get("state") != "success" or accounts[0].get("tokenSource") != "keyring"):
        raise AuthorizationError("Secure GitHub login required: gh auth login --hostname github.com --web")
    user = _gh(["api", "--hostname", "github.com", "user"], runner)
    if type(user.get("id")) is not int or user["id"] != OWNER_ID or user.get("type") != "User":
        raise AuthorizationError("This KRYN release authorizes only the verified repository owner")
    now = time.time() if now is None else now
    value = {"schema": 1, "owner_id": OWNER_ID, "login": user.get("login"),
             "verified_at": now, "expires_at": now + TTL_SECONDS, "credential_source": "keyring"}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return value
