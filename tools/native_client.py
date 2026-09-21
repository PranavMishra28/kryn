"""Small lifecycle/HTTP adapter for native OpenCode; not an agent loop."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path.home() / "Library/Application Support/LocalAI"
PROJECT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "opencode/2.0.10/package/bin/opencode"
MODEL_ID = "Qwen3.5-9B-6bit"
SHELL_SHIM = Path(__file__).absolute().with_name("native-shell")
SHELL_SHIM_BYTES = b'#!/bin/sh\nexec "${LOCALAI_SHELL_PYTHON:?missing owned interpreter}" -B "${LOCALAI_SHELL_HELPER:?missing owned helper}" --guarded-shell "$@"\n'


# Direct write containment only; reads, network and outside-service delegation remain outside its scope.
WRITE_PROFILE = """;; Direct filesystem-write containment for ordinary shell descendants only.
;; Parameters must be canonical, existing, operator-owned directories.
;; No HOME, whole LocalAI root, whole /private/tmp or XDG config allowance.
;; Reads, networking and IPC are not contained by this profile.
(version 1)
(allow default)
(deny file-write*)
(allow file-write*
    (subpath (param "PROJECT"))
    (subpath (param "XDG_DATA"))
    (subpath (param "XDG_CACHE"))
    (subpath (param "XDG_STATE"))
    (subpath (param "PRIVATE_TMP"))
    (subpath (param "BROWSER_OUTPUT"))
    (subpath (param "LOG_DIR")))
;; Character-device output only; no device creation/deletion allowance.
(allow file-write-data
    (literal "/dev/null")
    (literal "/dev/tty")
    (literal "/dev/ptmx")
    (regex #"^/dev/ttys[0-9]+$"))
"""


def background_boundary(workspace, private, dependencies, inference_port, native_port=0):
    """Whole-process boundary for disposable learning, never ordinary user work.

    The trusted worker/grader stays outside this sandbox. No personal XDG state,
    evaluator files, credentials or non-loopback service is readable/reachable.
    Only the inference-only worker proxy is reachable, never runtime admin APIs.
    """
    sandbox = Path("/usr/bin/sandbox-exec")
    if sys.platform != "darwin" or not sandbox.is_file() or sandbox.stat().st_uid != 0 or sandbox.stat().st_mode & 0o022:
        raise RuntimeError("Background evaluation requires the owned macOS sandbox boundary")
    workspace, private = (_owned_directory(Path(p)) for p in (workspace, private))
    if workspace in {Path("/"), Path.home(), ROOT, PROJECT} or _within(ROOT, workspace):
        raise RuntimeError("Background workspace is too broad")
    if private in {Path("/"), Path.home(), ROOT, PROJECT} or _within(ROOT, private):
        raise RuntimeError("Background private root is too broad")
    if workspace == private or _within(workspace, private) or _within(private, workspace):
        raise RuntimeError("Background workspace/private roots must be separate")
    ports = ([inference_port] if inference_port is not None else []) + ([native_port] if native_port else [])
    if any(type(p) is not int or not 1024 <= p <= 65535 for p in ports):
        raise RuntimeError("Background boundary requires explicit unprivileged ports")
    reads = [workspace, private, Path("/System"), Path("/usr/lib"), Path("/usr/share"),
             Path("/usr/bin"), Path("/bin"), Path("/sbin"), Path("/Library/Apple"),
             Path("/private/var/db/timezone")]
    for given in dependencies:
        path = Path(given)
        if not path.is_absolute() or path != path.resolve() or not path.exists():
            raise RuntimeError("Background dependencies must be canonical existing paths")
        info = path.stat()
        if info.st_uid not in {0, os.geteuid()} or info.st_mode & 0o022:
            raise RuntimeError("Background dependency is writable by another user")
        if path in {Path("/"), Path.home(), ROOT, PROJECT, Path("/Users"), Path("/private")}:
            raise RuntimeError("Background dependency allowance is too broad")
        reads.append(path)
    quote = lambda path: json.dumps(str(path))
    allowed = "\n".join(f'    ({"subpath" if p.is_dir() else "literal"} {quote(p)})' for p in reads)
    # Bun resolves cwd through parent directories. Literal directory reads permit
    # this traversal without granting any parent subtree's file contents.
    ancestors = "\n".join(f'    (literal {quote(p)})' for p in sorted(set(workspace.parents) | set(private.parents)))
    # Seatbelt's address grammar accepts localhost/*, not numeric hosts.
    # All actual listeners/requests are bound to explicit IPv4 loopback addresses.
    network = "\n".join(f'(allow network-outbound (remote ip "localhost:{p}"))' for p in ports)
    inbound = f'(allow network-inbound (local ip "localhost:{native_port}"))' if native_port else ''
    profile = f'''(version 1)
(allow default)
(deny file-read-data)
(deny file-write*)
(deny network*)
(deny mach-lookup)
(deny appleevent-send)
(deny process-info*)
(allow process-info* (target self))
(allow file-read-data
{allowed}
{ancestors}
    (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))
(allow file-write* (subpath {quote(workspace)}) (subpath {quote(private)}))
(deny file-read-data file-write* (subpath {quote(workspace / '.opencode')})
    (literal {quote(workspace / 'opencode.json')}) (literal {quote(workspace / 'opencode.jsonc')}))
;; Even an interpreter allowance must never expose installed evaluation answers.
(deny file-read-data file-write* (subpath {quote(PROJECT / 'tools')}) (subpath {quote(PROJECT / 'evals')}))
(allow file-write-data (literal "/dev/null") (literal "/dev/tty"))
{inbound}
{network}
'''
    return ["/usr/bin/sandbox-exec", "-p", profile]

def _owned_directory(path, *, create=False):
    path = Path(path)
    if not path.is_absolute() or path != path.resolve() or any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError("Write boundary requires a canonical directory without symlinks: " + str(path))
    existing = next(p for p in (path, *path.parents) if p.exists())
    info = existing.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise RuntimeError("Write boundary requires an owned, non-shared directory: " + str(existing))
    if create:
        missing = []
        cursor = path
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        for directory in reversed(missing):
            directory.mkdir(mode=0o700)
    if not path.is_dir():
        raise RuntimeError("Write boundary directory is missing: " + str(path))
    return path


def _path_key(path):
    # Conservatively refuse case/Unicode aliases even on a case-sensitive volume.
    return tuple(unicodedata.normalize("NFD", part).casefold() for part in Path(path).parts)


def _within(path, directory):
    parent = _path_key(directory)
    return _path_key(path)[:len(parent)] == parent


def _validate_work_locations(directory, log_dir):
    # Run before allocating project scratch; these checks never create directories.
    root = _owned_directory(ROOT)
    home = Path.home().resolve()
    protected = [home / ".omlx", home / ".opencode", home / "Applications/oMLX.app",
                 BINARY.resolve(), Path(sys.executable).resolve(),
                 Path(__file__).resolve(), SHELL_SHIM.resolve()]
    broad = {Path("/"), Path("/Users"), Path("/private"), Path("/private/tmp"),
             Path("/private/var"), Path("/private/var/folders"), Path(tempfile.gettempdir()).resolve(), home,
             *(home / name for name in ("Library", "Documents", "Desktop", "Downloads", "Pictures", "Music", "Movies", "Public", ".Trash"))}
    for path in (Path(directory), Path(log_dir)):
        if (_path_key(path) in {_path_key(p) for p in broad} or _within(root, path) or
                (_within(path, root) and not _within(path, root / "runs")) or
                any(_within(path, p) or _within(p, path) for p in protected)):
            raise RuntimeError("Write boundary would expose a protected or broad directory: " + str(path))
    _owned_directory(directory)
    return root


def _sandbox_prefix(directory, temporary, log_dir, env):
    # Paths come from this owner, never from model input or an opt-out environment variable.
    root = _validate_work_locations(directory, log_dir)
    roots = {"PROJECT": Path(directory), "XDG_DATA": root / "xdg/data",
             "XDG_CACHE": root / "xdg/cache", "XDG_STATE": root / "xdg/state",
             "PRIVATE_TMP": Path(temporary), "BROWSER_OUTPUT": root / "browser-output",
             "LOG_DIR": Path(log_dir)}
    for path in roots.values():
        if any(_within(p, path) for p in (Path(__file__).resolve(), SHELL_SHIM.resolve(),
                                                  Path(sys.executable).resolve(), BINARY.resolve())):
            raise RuntimeError("Shell boundary would make its own implementation writable: " + str(path))
    task_tmp = _owned_directory(env.get("LOCALAI_TASK_TMP", ""))
    if (task_tmp.parent != roots["PROJECT"] or not task_tmp.name.startswith(".localai-tmp-")
            or task_tmp.stat().st_mode & 0o777 != 0o700
            or _within(task_tmp, roots["PRIVATE_TMP"]) or _within(roots["PRIVATE_TMP"], task_tmp)):
        raise RuntimeError("Task temporary directory must be a private, separate child of the project")
    expected = {"XDG_CONFIG_HOME": root / "xdg/config", "XDG_DATA_HOME": roots["XDG_DATA"],
                "XDG_CACHE_HOME": roots["XDG_CACHE"], "XDG_STATE_HOME": roots["XDG_STATE"],
                "PWTEST_SERVER_REGISTRY": roots["PRIVATE_TMP"] / "pw-registry",
                "TMPPREFIX": task_tmp / "zsh",
                **{key: task_tmp for key in ("TMPDIR", "TMP", "TEMP")},
                **{key: roots["PRIVATE_TMP"] for key in ("MAC_CHROMIUM_TMPDIR", "BREAKPAD_DUMP_LOCATION")}}
    if any(env.get(key) != str(value) for key, value in expected.items()):
        raise RuntimeError("Write boundary refuses redirected native state or temporary directories")
    private = _owned_directory(roots["PRIVATE_TMP"])
    if private.stat().st_mode & 0o777 != 0o700:
        raise RuntimeError("Native temporary directory must remain private")
    # Check all destinations before creating any missing owned state/log directories.
    for path in roots.values():
        existing = path
        while not existing.exists():
            existing = existing.parent
        _owned_directory(existing)
        if path != path.resolve():
            raise RuntimeError("Write boundary refuses a redirected directory: " + str(path))
    for name, path in roots.items():
        _owned_directory(path, create=name not in {"PROJECT", "PRIVATE_TMP"})
    sandbox = Path("/usr/bin/sandbox-exec")
    info = sandbox.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or not os.access(sandbox, os.X_OK):
        raise RuntimeError("Required macOS sandbox-exec is unavailable or changed")
    prefix = [str(sandbox), "-p", WRITE_PROFILE]
    for name, path in roots.items():
        prefix += ["-D", name + "=" + str(path)]
    return prefix, {"profile_sha256": hashlib.sha256(WRITE_PROFILE.encode()).hexdigest(),
                    "task_temporary": str(task_tmp),
                    "roots": {name: str(path) for name, path in roots.items()}}


def _open_owned_log(path):
    # No inherited writable descriptor may point at a symlink or shared hardlink.
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            raise RuntimeError("Preserving an unowned or linked native log: " + str(path))
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            raise RuntimeError("Preserving an unowned or linked native log: " + str(path))
        os.fchmod(fd, 0o600)
        return os.fdopen(fd, "ab")
    except BaseException:
        os.close(fd)
        raise


def _shell_identity():
    helper = Path(__file__).absolute()
    python = Path(sys.executable).resolve()
    for path in (helper, SHELL_SHIM, python):
        if path != path.resolve() or any(p.is_symlink() for p in (path, *path.parents)):
            raise RuntimeError("Shell boundary refuses a redirected executable: " + str(path))
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in {0, os.geteuid()}
                or info.st_nlink != 1 or info.st_mode & 0o022):
            raise RuntimeError("Shell boundary requires an owned, non-shared executable: " + str(path))
    if SHELL_SHIM.read_bytes() != SHELL_SHIM_BYTES or not os.access(SHELL_SHIM, os.X_OK):
        raise RuntimeError("Shell boundary shim is missing, changed or not executable")
    return helper, python, hashlib.sha256(helper.read_bytes()).hexdigest()


def guarded_shell(args):
    # Native ShellSelect passes exactly these two arguments; never parse/eval the command here.
    if len(args) != 2 or args[0] != "-c":
        raise RuntimeError("Guarded shell supports only the native '-c command' contract")
    helper, python, digest = _shell_identity()
    env = dict(os.environ)
    expected = {"LOCALAI_SHELL_HELPER": str(helper), "LOCALAI_SHELL_PYTHON": str(python),
                "LOCALAI_SHELL_HELPER_SHA256": digest}
    if any(env.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Guarded shell executable identity differs from its native owner")
    # These are fixed at NativeServer entry, never derived from the command's cwd/PWD.
    project = env.get("LOCALAI_SHELL_PROJECT", "")
    temporary = env.get("LOCALAI_SHELL_TEMP", "")
    log_dir = env.get("LOCALAI_SHELL_LOG_DIR", "")
    if not all((project, temporary, log_dir)):
        raise RuntimeError("Guarded shell is missing its owned boundary roots")
    prefix, _ = _sandbox_prefix(project, temporary, log_dir, env)
    command = prefix + ["/bin/zsh", "-c", args[1]]
    os.execve(command[0], command, env)


def owned_config():
    path = ROOT / "xdg/config/opencode/opencode.json"
    return json.loads(path.read_text())


def environment(config=None):
    # Give the owned processes normal shell/terminal prerequisites without
    # forwarding ambient cloud credentials or unrelated application settings.
    allowed = {"HOME", "USER", "LOGNAME", "PATH", "SHELL", "LANG", "LANGUAGE",
               "TMPDIR", "TMP", "TEMP", "TERM", "TERM_PROGRAM", "TERM_PROGRAM_VERSION",
               "COLORTERM", "NO_COLOR", "FORCE_COLOR", "TZ", "__CF_USER_TEXT_ENCODING",
               "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS"}
    env = {key: value for key, value in os.environ.items()
           if key in allowed or key.startswith("LC_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key, name in (("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                      ("XDG_CACHE_HOME", "cache"), ("XDG_STATE_HOME", "state")):
        env[key] = str(ROOT / "xdg" / name)
    # npm otherwise writes ~/.npm, outside the ordinary shell write boundary.
    env["NPM_CONFIG_CACHE"] = str(ROOT / "xdg/cache/npm")
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost,::1"
    env["OPENCODE_CLI_CONFIG_CONTENT"] = '{"session":{"permissions":"prompt"}}'
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config if config is not None else owned_config())
    return env


class NativeServer:
    def __init__(self, directory, config=None, log=None, *, background=None):
        self.directory = Path(directory).absolute()
        self.env = environment(config)
        self.background = background
        effective = json.loads(self.env["OPENCODE_CONFIG_CONTENT"])
        if effective.get("shell") not in (None, str(SHELL_SHIM)):
            raise RuntimeError("Owned shell setting conflicts with the required boundary shim")
        effective["shell"] = str(SHELL_SHIM)
        plugins = effective.get("plugins", [])
        if not isinstance(plugins, list):
            raise RuntimeError("Owned plugins must be an ordered list")
        effective["plugins"] = [p for p in plugins if p not in ("opencode.config.shell", "-opencode.config.shell")]
        effective["plugins"].append("opencode.config.shell")
        self.env["OPENCODE_CONFIG_CONTENT"] = json.dumps(effective)
        # OpenCode resolves the invocation directory from PWD; Popen(cwd=...) alone
        # leaves a parent's inherited PWD pointing at the wrong repository.
        self.env["PWD"] = str(self.directory)
        self.env.pop("OLDPWD", None)
        self.env["OPENCODE_PASSWORD"] = secrets.token_urlsafe(32)
        auth = base64.b64encode(("opencode:" + self.env["OPENCODE_PASSWORD"]).encode()).decode()
        self.headers = {"Authorization": "Basic " + auth,
                        "x-opencode-directory": urllib.parse.quote(str(self.directory), safe="")}
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.log_path = Path(log or ROOT / "runs/native-server.log").absolute()
        self.process = None
        self.log_file = None
        self.temporary = None
        self.task_temporary = None
        self.forced_shutdown = False
        self.termination_requested = False

    def _enter_background(self):
        options = self.background
        if set(options) - {"dependencies", "inference_port", "cancel"} or not {"dependencies", "inference_port"}.issubset(options):
            raise RuntimeError("Unexpected background isolation options")
        self.temporary = tempfile.TemporaryDirectory(prefix="kryn-isolated-", dir="/private/tmp", delete=False)
        private = Path(self.temporary.name)
        effective = json.loads(self.env["OPENCODE_CONFIG_CONTENT"])
        # The whole server and descendants are sandboxed; do not route a nested
        # shell shim back to the foreground user's private XDG directories.
        effective["shell"] = "/bin/zsh"
        self.env["OPENCODE_CONFIG_CONTENT"] = json.dumps(effective)
        self.env["HOME"] = str(private)
        # Pinned OpenCode 2.0.10 uses os.homedir(), which ignores HOME in Bun.
        # Its explicit home hook keeps discovery inside the disposable boundary.
        self.env["OPENCODE_TEST_HOME"] = str(private)
        self.env["OPENCODE_CONFIG_PROJECT_DISABLE"] = "true"
        self.env["PATH"] = str(Path(sys.executable).parent) + ":/usr/bin:/bin"
        for key in ("TMPDIR", "TMP", "TEMP", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
            dest = private / key.lower()
            dest.mkdir(mode=0o700)
            self.env[key] = str(dest)
        self.env["NPM_CONFIG_CACHE"] = str(private / "xdg_cache_home/npm")
        self.env["TMPPREFIX"] = str(private / "zsh")
        dependencies = list(options["dependencies"])
        # /usr/bin/git is Apple's xcrun shim; its public implementation lives here.
        git_toolchain = Path("/Library/Developer/CommandLineTools")
        if git_toolchain.is_dir(): dependencies.append(git_toolchain.resolve())
        prefix = background_boundary(self.directory, private, dependencies,
                                     options["inference_port"], self.port)
        self.background_prefix = prefix
        self.log_file = _open_owned_log(self.log_path)
        self.process = subprocess.Popen(prefix + [str(BINARY), "serve", "--hostname", "127.0.0.1",
                                                  "--port", str(self.port)], cwd=self.directory,
                                        env=self.env, stdout=self.log_file, stderr=self.log_file)
        for _ in range(100):
            if options.get("cancel", lambda: False)():
                raise RuntimeError("Background native startup yielded to foreground")
            if self.process.poll() is not None:
                raise RuntimeError("Isolated native server exited before readiness")
            try:
                self.request("GET", "/api/info", timeout=1)
                return self
            except (OSError, urllib.error.URLError):
                time.sleep(.2)
        raise RuntimeError("Isolated native server readiness timed out")

    def request(self, method, endpoint, body=None, timeout=30):
        if not endpoint.startswith("/api/"):
            raise ValueError("Only native local API paths are allowed")
        headers = dict(self.headers)
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.url + endpoint, data=data, headers=headers, method=method)
        # Never send even loopback traffic through a user's proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as response:
            payload = response.read()
        return json.loads(payload) if payload else None

    def _verify_guarded_shell(self):
        # An operator startup canary, not a session or model tool call.
        deadline = time.monotonic() + 15
        while True:
            response = self.request("GET", "/api/plugin", timeout=5)
            if response.get("location", {}).get("directory") != str(self.directory):
                raise RuntimeError("Shell plugin inventory belongs to a different project")
            selected = [p for p in response.get("data", []) if p.get("id") == "opencode.config.shell"]
            if (len(selected) == 1 and selected[0].get("source", {}).get("type") == "builtin"
                    and selected[0].get("state", {}).get("status") == "active"):
                break
            if len(selected) > 1 or time.monotonic() >= deadline or any(
                    p.get("state", {}).get("status") in {"failed", "error", "disabled"} for p in selected):
                raise RuntimeError("Required native shell configuration plugin did not become active")
            time.sleep(0.1)
        marker = secrets.token_hex(12)
        expected_output = marker + "\n"
        command = "/bin/cat <<'LOCALAI_HEREDOC'\n" + expected_output + "LOCALAI_HEREDOC\n"
        owned_id = None
        try:
            response = self.request("POST", "/api/shell", {"command": command, "cwd": str(self.directory),
                                    "timeout": 10000, "metadata": {"localai_shell_admission": marker}}, timeout=15)
            info = response.get("data", {})
            candidate = info.get("id")
            if (not isinstance(candidate, str) or not candidate.startswith("sh_")
                    or info.get("metadata", {}).get("localai_shell_admission") != marker
                    or info.get("command") != command or info.get("cwd") != str(self.directory)):
                raise RuntimeError("Native shell canary ownership was not proved")
            owned_id = candidate
            endpoint = "/api/shell/" + urllib.parse.quote(owned_id, safe="")
            deadline = time.monotonic() + 12
            while True:
                if (info.get("id") != owned_id or info.get("shell") != str(SHELL_SHIM)
                        or info.get("metadata", {}).get("localai_shell_admission") != marker
                        or info.get("command") != command or info.get("cwd") != str(self.directory)):
                    raise RuntimeError("Native resolved shell does not match the owned boundary shim")
                if info.get("status") != "running":
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("Native shell startup canary did not settle")
                time.sleep(0.1)
                info = self.request("GET", endpoint, timeout=5).get("data", {})
            completed = info.get("time", {}).get("completed")
            if (info.get("status") != "exited" or info.get("exit") != 0
                    or isinstance(info.get("exit"), bool)
                    or not isinstance(completed, (int, float)) or isinstance(completed, bool)
                    or not 0 < completed < float("inf")):
                raise RuntimeError("Native guarded shell startup canary failed")
            # Native exit metadata can precede the output writer's final flush.
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError("Native guarded shell heredoc output did not settle")
                output = self.request("GET", endpoint + "/output?cursor=0&limit=1024",
                                      timeout=min(5, remaining)).get("data", {})
                content = output.get("output")
                cursor, size = output.get("cursor"), output.get("size")
                if (not isinstance(content, str) or not expected_output.startswith(content)
                        or output.get("truncated") is not False
                        or type(cursor) is not int or type(size) is not int
                        or cursor != len(content.encode()) or not 0 <= cursor <= size <= len(expected_output.encode())):
                    raise RuntimeError("Native guarded shell heredoc output did not match")
                if content == expected_output and cursor == size:
                    break
                time.sleep(0.1)
            self.log_file.write((json.dumps({"shell_admission": {"scope": "operator startup heredoc; no inference",
                                 "id": owned_id, "shell": info["shell"], "status": info["status"],
                                 "exit": info["exit"], "completed": completed,
                                 "heredoc_output_verified": True}}) + "\n").encode())
            self.log_file.flush()
        finally:
            original = sys.exception()
            if owned_id is not None:
                try:
                    self.request("DELETE", "/api/shell/" + urllib.parse.quote(owned_id, safe=""), timeout=5)
                except BaseException as cleanup_error:
                    if original is None:
                        raise
                    original.add_note("Startup shell cleanup: " + type(cleanup_error).__name__ + ": " + str(cleanup_error))

    def __enter__(self):
        if self.temporary is not None or self.task_temporary is not None:
            raise RuntimeError("Native server still owns its temporary directory")
        try:
            if self.background is not None:
                return self._enter_background()
            helper, python, digest = _shell_identity()
            _validate_work_locations(self.directory, self.log_path.parent)
            # delete=False prevents garbage collection from deleting beneath an
            # owned server whose shutdown could not be proved. Python 3.13+ is required.
            self.temporary = tempfile.TemporaryDirectory(prefix="localai-", dir="/private/tmp", delete=False)
            self.task_temporary = tempfile.TemporaryDirectory(prefix=".localai-tmp-", dir=self.directory, delete=False)
            # Only this newly allocated directory is ignored; never edit the project's ignore files.
            with (Path(self.task_temporary.name) / ".gitignore").open("x") as ignored:
                ignored.write("*\n")
            self.env.update({key: self.task_temporary.name for key in ("TMPDIR", "TMP", "TEMP", "LOCALAI_TASK_TMP")})
            # Chromium on macOS has separate supported temp and crash-dump overrides.
            self.env.update({key: self.temporary.name for key in ("MAC_CHROMIUM_TMPDIR", "BREAKPAD_DUMP_LOCATION")})
            # zsh heredocs use TMPPREFIX, independently of TMPDIR.
            self.env["TMPPREFIX"] = str(Path(self.task_temporary.name) / "zsh")
            # Pinned upstream test hook; revalidate this path-only override on upgrade.
            self.env["PWTEST_SERVER_REGISTRY"] = str(Path(self.temporary.name) / "pw-registry")
            effective = json.loads(self.env["OPENCODE_CONFIG_CONTENT"])
            browser = effective.get("mcp", {}).get("servers", {}).get("browser")
            if browser is not None:
                if (not isinstance(browser, dict) or browser.get("type") != "local"
                        or not isinstance(browser.get("environment", {}), dict)
                        or any(not isinstance(k, str) or not isinstance(v, str)
                               for k, v in browser.get("environment", {}).items())):
                    raise RuntimeError("Owned browser must have a local MCP environment")
                browser["environment"] = {**browser.get("environment", {}),
                    **{key: self.temporary.name for key in ("TMPDIR", "TMP", "TEMP", "MAC_CHROMIUM_TMPDIR", "BREAKPAD_DUMP_LOCATION")},
                    "TMPPREFIX": str(Path(self.temporary.name) / "zsh"),
                    "PWTEST_SERVER_REGISTRY": self.env["PWTEST_SERVER_REGISTRY"]}
                self.env["OPENCODE_CONFIG_CONTENT"] = json.dumps(effective)
            self.env.update({"LOCALAI_SHELL_PROJECT": str(self.directory),
                             "LOCALAI_SHELL_TEMP": self.temporary.name,
                             "LOCALAI_SHELL_LOG_DIR": str(self.log_path.parent),
                             "LOCALAI_SHELL_HELPER": str(helper),
                             "LOCALAI_SHELL_PYTHON": str(python),
                             "LOCALAI_SHELL_HELPER_SHA256": digest})
            _, boundary = _sandbox_prefix(self.directory, self.temporary.name, self.log_path.parent, self.env)
            boundary.update(scope="ordinary native shell descendants only",
                            shim=str(SHELL_SHIM), shim_sha256=hashlib.sha256(SHELL_SHIM_BYTES).hexdigest(),
                            helper_sha256=digest, native_config_shell=str(SHELL_SHIM),
                            required_builtin="opencode.config.shell")
            self.log_file = _open_owned_log(self.log_path)
            self.log_file.write((json.dumps({"write_boundary": boundary}) + "\n").encode())
            self.log_file.flush()
            self.process = subprocess.Popen([str(BINARY), "serve", "--hostname", "127.0.0.1",
                                             "--port", str(self.port)], cwd=self.directory,
                                            env=self.env, stdout=self.log_file, stderr=self.log_file)
            for _ in range(100):
                if self.process.poll() is not None:
                    raise RuntimeError(f"Native server exited; inspect {self.log_path}")
                try:
                    self.request("GET", "/api/info", timeout=1)
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.2)
            else:
                raise RuntimeError("Native OpenCode server did not become ready")
            self._verify_guarded_shell()
            return self
        except BaseException as error:
            try:
                self.close()
            except BaseException as cleanup_error:
                error.add_note("Native cleanup: " + type(cleanup_error).__name__ + ": " + str(cleanup_error))
            raise

    def inventory(self):
        for _ in range(80):
            providers = self.request("GET", "/api/provider")
            models = self.request("GET", "/api/model")
            if providers.get("data") and models.get("data"):
                return providers, models
            time.sleep(0.25)
        raise RuntimeError("No configured model/provider appeared after bounded initialization")

    def close(self):
        entry_error = sys.exception()
        stopped = self.process is None
        try:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.terminate()
                    self.termination_requested = True
                    try:
                        self.process.wait(timeout=2 if self.background is not None else 10)
                    except subprocess.TimeoutExpired:
                        self.forced_shutdown = True
                        self.process.kill()
                        self.process.wait(timeout=2 if self.background is not None else 5)
                # Effect's scoped SIGTERM teardown exits 130 on interruption.
                # Accept it only after our terminate request; forced/unknown exits retain.
                code = self.process.poll()
                stopped = not self.forced_shutdown and (code == 0 or
                          (code == 130 and self.termination_requested))
        finally:
            try:
                if self.log_file is not None:
                    self.log_file.close()
            finally:
                owned = [(name, getattr(self, name)) for name in ("task_temporary", "temporary")
                         if getattr(self, name) is not None]
                if stopped:
                    original = sys.exception()
                    cleanup_error = None
                    for name, temporary in owned:
                        try:
                            temporary.cleanup()
                            setattr(self, name, None)
                        except BaseException as error:
                            if cleanup_error is None:
                                cleanup_error = error
                            else:
                                cleanup_error.add_note("Additional temporary cleanup: " + str(error))
                    if cleanup_error is not None:
                        if original is not entry_error:
                            original.add_note("Temporary cleanup: " + str(cleanup_error))
                        else:
                            raise cleanup_error
                elif owned:
                    retained = ", ".join(temporary.name for _, temporary in owned)
                    print("Retained native temporary directories (shutdown unproved): " + retained, file=sys.stderr)
                    # Do not replace a new wait/kill exception already unwinding.
                    if sys.exception() is entry_error:
                        raise RuntimeError("Native server shutdown unproved; retained " + retained)

    def __exit__(self, error_type, error, traceback):
        try:
            self.close()
        except BaseException as cleanup_error:
            if error is None:
                raise
            error.add_note("Native cleanup: " + type(cleanup_error).__name__ + ": " + str(cleanup_error))


if __name__ == "__main__":
    try:
        if sys.argv[1:2] != ["--guarded-shell"]:
            raise RuntimeError("This helper only exposes the guarded native shell entrypoint")
        guarded_shell(sys.argv[2:])
    except (OSError, ValueError, RuntimeError) as error:
        sys.exit("STOP: " + str(error))
