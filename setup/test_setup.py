"""Offline checks for installer boundaries. No packages, apps or models executed."""
import contextlib
import copy
import hashlib
import io
import json
import os
import plistlib
import shutil
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import setup
import deploy_client
sys.path.insert(0, str(setup.HERE.parent / "tools"))
import localai
import native_client


class SetupChecks(unittest.TestCase):
    def test_daily_start_waits_for_mcp_and_reports_degraded_tools(self):
        for state in ("connected", "failed", "pending", "missing"):
            with self.subTest(state=state):
                order = []
                server = MagicMock(url="http://127.0.0.1:12345", env={})
                owner = MagicMock()
                owner.__enter__.return_value = server
                error = io.StringIO()
                def readiness(*args):
                    order.append("readiness")
                    return {"browser": {"status": "connected"}, "search": {"status": state}}
                def launch(*args, **kwargs):
                    self.assertEqual(order, ["readiness"])
                    order.append("tui")
                    return 0
                with patch.object(sys, "argv", ["localai", str(self.root)]), \
                     patch.object(localai, "prerequisites", return_value={}), \
                     patch.object(localai, "ensure_runtime", return_value={"healthy": True, "active_requests": 0, "waiting_requests": 0}), \
                     patch.object(localai, "dependency_report", return_value={}), \
                     patch.object(localai, "await_runtime_idle"), \
                     patch.object(localai.improvement, "foreground", return_value=contextlib.nullcontext()), \
                     patch.object(localai.improvement, "record_outcome"), \
                     patch.object(localai.improvement, "active_skill_directory", return_value=None), \
                     patch.object(localai, "NativeServer", return_value=owner), \
                     patch.object(localai, "inventory"), \
                     patch.object(localai, "mcp_status", side_effect=readiness), \
                     patch.object(localai, "guarded_run", side_effect=launch), \
                     contextlib.redirect_stderr(error):
                    self.assertEqual(localai.main(), 0)
                self.assertEqual(order, ["readiness", "tui"])
                self.assertEqual("search" in error.getvalue(), state != "connected")
                owner.__exit__.assert_called_once()

    def test_profile_pin_paths_and_memory(self):
        profile = setup.load_profile()
        profile.update(repository="gcoli/Qwen3.8-27B-oQ5e-mtp", revision="a" * 40,
                       memory_gib=32, model_parent="challenger/models")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps(profile))
            selected = setup.load_profile(path)
            self.assertEqual(setup.model_id(selected), "Qwen3.8-27B-oQ5e-mtp")
            self.assertEqual(setup.runtime_settings(Path(directory), selected)["model"]["model_dirs"],
                             [str(Path(directory) / "challenger/models")])
            self.assertEqual(setup.runtime_settings(Path(directory), selected)["memory"]["memory_guard_custom_ceiling_gb"], 32)
            for changes in ({"revision": "main"}, {"revision": None}, {"repository": "owner/.."},
                            {"repository": 5}, {"model_parent": "a//b"},
                            {"model_parent": "../outside"}, {"memory_gib": True},
                            {"files": {"../model.safetensors": "0" * 64}},
                            {"files": {"model.safetensors": None}},
                            {"files": {"-model.safetensors": "0" * 64}}):
                path.write_text(json.dumps({**profile, **changes}))
                with self.assertRaises(RuntimeError):
                    setup.load_profile(path)

    def test_release_pins_are_literal_and_single(self):
        self.assertEqual(deploy_client.pin_constant(b'MODEL_ID = "old"\n', "MODEL_ID", "new"),
                         b"MODEL_ID = 'new'\n")
        for source in (b"OTHER = 1\n", b"MODEL_ID = 1\nMODEL_ID = 2\n"):
            with self.assertRaises(RuntimeError):
                deploy_client.pin_constant(source, "MODEL_ID", "new")

    def test_daily_release_uses_selected_pin_without_changing_source(self):
        profile = setup.load_profile()
        profile.update(repository="gcoli/Qwen3.8-27B-oQ5e-mtp", revision="a" * 40,
                       memory_gib=32, model_parent="challenger/models")
        install_root = self.root / "Library/Application Support/LocalAI"
        cfg = setup.render(install_root, self.root / "node", profile)
        setup.write_same(install_root / "xdg/config/opencode/opencode.json", setup.encode(cfg))
        setup.write_same(install_root / "install-profile.json", setup.encode(profile))
        marker = install_root / "challenger/models/Qwen3.8-27B-oQ5e-mtp/.localai-download.json"
        setup.write_same(marker, setup.encode({key: profile[key] for key in ("repository", "revision")}))
        source = setup.HERE.parent / "tools/native_client.py"
        before = source.read_bytes()
        server_settings = setup.model_settings(profile)
        server_settings["models"][setup.model_id(profile)]["max_context_window"] = 24576
        with patch.object(Path, "home", return_value=self.root), \
             patch.object(sys, "argv", ["deploy_client.py", "--apply"]), \
             patch.object(setup, "model_settings", return_value=server_settings), \
             contextlib.redirect_stdout(io.StringIO()):
            deploy_client.main()
            deploy_client.main()  # Identical owned release and launchers are reusable.
        self.assertEqual(source.read_bytes(), before)
        release = json.loads((install_root / "client/deployment.json").read_text())
        directory = Path(release["directory"])
        localai = (directory / "tools/localai.py").read_text()
        self.assertIn("REPOSITORY = 'gcoli/Qwen3.8-27B-oQ5e-mtp'", localai)
        self.assertIn("MODEL_PARENT = 'challenger/models'", localai)
        self.assertIn("MEMORY_GIB = 32", localai)
        self.assertIn("SERVER_CONTEXT = 24576", localai)  # Independent of the 16K client context.
        result = subprocess.run([sys.executable, "-B", directory / "tools/localai.py", "--self-check"],
                                env={**setup.os.environ, "HOME": str(self.root)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / ".local/bin/localai").read_text(), release["launcher"])
        shim = directory / "tools/native-shell"
        self.assertEqual(shim.read_bytes(), native_client.SHELL_SHIM_BYTES)
        self.assertTrue(os.access(shim, os.X_OK))
        self.assertEqual(release["files"]["tools/native-shell"], hashlib.sha256(shim.read_bytes()).hexdigest())
        # Byte-identical shared-writable shims must fail before dry-run or promotion.
        shim.chmod(0o777)
        targets = [p for p in directory.rglob("*") if p.is_file()] + [
            install_root / "client/deployment.json", install_root / "localai", self.root / ".local/bin/localai"]
        def snapshot():
            return {str(p): (p.read_bytes(), p.stat().st_mode, p.stat().st_ino, p.stat().st_mtime_ns) for p in targets}
        unsafe_before = snapshot()
        for flags in ([], ["--apply"]):
            with self.subTest(flags=flags), patch.object(Path, "home", return_value=self.root), \
                 patch.object(sys, "argv", ["deploy_client.py", *flags]), \
                 patch.object(setup, "model_settings", return_value=server_settings), \
                 self.assertRaisesRegex(RuntimeError, "unsafe existing release shim"):
                deploy_client.main()
            self.assertEqual(snapshot(), unsafe_before)  # Refuse; never repair permissions or promote.
        self.assertEqual(shim.stat().st_mode & 0o777, 0o777)

    def test_owned_profile_rejects_changed_defaults(self):
        config = localai.expected_config()
        localai.validate_owned_config(config)
        for section, name in (("agents", "plan"), ("commands", "review")):
            changed = copy.deepcopy(config)
            changed[section][name]["model"] = "local/qwen#low"
            with self.subTest(section=section), self.assertRaises(RuntimeError):
                localai.validate_owned_config(changed)

    def test_effective_profile_matches_native_shapes_and_rejects_drift(self):
        config = localai.expected_config()
        def reference(text):
            return {"providerID": "local", "model": "qwen", "variant": text.partition("#")[2]}
        # Actual v2 config documents normalize model strings to {providerID, model, variant}.
        document = copy.deepcopy(config)
        document["model"] = reference(document["model"])
        for section in ("agents", "commands"):
            for item in document[section].values():
                item["model"] = reference(item["model"])
        provider = copy.deepcopy(config["providers"]["local"])
        model = provider.pop("models")["qwen"]
        model.update(id="qwen", providerID="local", enabled=True, status="active", cost=[], time={"released": 0})
        agents = [{"id": name, "model": {"id": "qwen", "providerID": "local", "variant": reference(item["model"])["variant"]}}
                  for name, item in config["agents"].items()]
        inventory = {"providers": {"data": [{"id": "local", **provider}]}, "models": {"data": [model]},
                     "agents": {"data": agents}, "config": [{"type": "document", "info": {"compaction": {"buffer": 1}}},
                     {"type": "directory", "path": "/fixture"}, {"type": "document", "info": document}]}
        localai.validate_inventory(inventory)
        inventory["models"]["data"][0]["variants"].reverse()
        localai.validate_inventory(inventory)  # List order is not reasoning-profile drift.
        mutations = [
            (("models", "data", 0, "limit", "context"), 65536),
            (("models", "data", 0, "limit", "output"), 16384),
            (("models", "data", 0, "body", "max_tokens"), 16384),
            (("models", "data", 0, "body", "chat_template_kwargs", "reasoning_effort"), "low"),
            (("models", "data", 0, "variants", 0, "body", "temperature"), 0.99),
            (("models", "data", 0, "settings", "baseURL"), "https://example.invalid/v1"),
            (("agents", "data", 0, "model", "variant"), "low"),
            (("config", 2, "info", "compaction", "buffer"), 1),
            (("config", 2, "info", "default_agent"), "plan"),
            (("config", 2, "info", "model", "variant"), "low"),
            (("config", 2, "info", "commands", "review", "model", "variant"), "fast"),
        ]
        for keys, value in mutations:
            changed = copy.deepcopy(inventory)
            target = changed
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            with self.subTest(path=keys), self.assertRaises(RuntimeError):
                localai.validate_inventory(changed)
        expected = config["compaction"]
        for partial in ({"buffer": expected["buffer"]}, {"keep": {"tokens": expected["keep"]["tokens"]}},
                        {"auto": expected["auto"]}, {"keep": {}}):
            changed = copy.deepcopy(inventory)
            changed["config"].append({"type": "document", "info": {"compaction": partial}})
            with self.subTest(unchanged_partial=partial):
                localai.validate_inventory(changed)
        for partial in ({"buffer": expected["buffer"] + 1}, {"keep": {"tokens": expected["keep"]["tokens"] + 1}},
                        {"auto": not expected["auto"]}):
            changed = copy.deepcopy(inventory)
            changed["config"].append({"type": "document", "info": {"compaction": partial}})
            with self.subTest(changed_partial=partial), self.assertRaises(RuntimeError):
                localai.validate_inventory(changed)

    def test_runtime_profile_context_and_effective_memory_bound(self):
        # oMLX server.py /v1/models ModelInfo and /api/status public response shapes.
        results = {"health": {"status": "ok"}, "models": {"object": "list", "data": [
            {"id": localai.MODEL_ID, "owned_by": "omlx", "max_model_len": localai.SERVER_CONTEXT}]},
            "status": {"status": "ok", "model_memory_max": localai.MEMORY_GIB * 1024**3,
                       "active_requests": 0, "waiting_requests": 0}}
        localai.validate_runtime_metadata(results)
        results["status"]["model_memory_max"] -= 1024**3  # A lower native constraint is valid.
        localai.validate_runtime_metadata(results)
        for value in (0, None, True, -1, float("inf"), float("nan"), "32GB", (localai.MEMORY_GIB + 1) * 1024**3):
            changed = copy.deepcopy(results)
            changed["status"]["model_memory_max"] = value
            with self.subTest(ceiling=value), self.assertRaises(RuntimeError):
                localai.validate_runtime_metadata(changed)
        for value in (None, 65536, "32768", True):
            changed = copy.deepcopy(results)
            changed["models"]["data"][0]["max_model_len"] = value
            with self.subTest(context=value), self.assertRaises(RuntimeError):
                localai.validate_runtime_metadata(changed)
        changed = copy.deepcopy(results)
        changed["models"]["data"][0]["id"] = "other-model"
        with self.assertRaises(RuntimeError):
            localai.validate_runtime_metadata(changed)

    def test_model_download_only_missing_and_never_repairs_changed_files(self):
        profile = setup.load_profile()
        payloads = {"model.safetensors": b"fixture weights", ".gitattributes": b"fixture attributes"}
        profile["files"] = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}
        directory = self.root / "model"
        directory.mkdir()
        (directory / "model.safetensors").write_bytes(payloads["model.safetensors"])
        def fake_run(command, env):
            start = command.index(profile["repository"]) + 1
            filenames = command[start:command.index("--revision")]
            self.assertEqual(len(filenames), 1)  # Multi-file CLI requests take the defective snapshot path.
            self.assertEqual(command[command.index("--revision") + 1], profile["revision"])
            (directory / filenames[0]).write_bytes(payloads[filenames[0]])
        with patch.object(setup, "run", side_effect=fake_run) as run:
            setup.download_model(Path("/fixture/uv"), directory, profile, {})
            self.assertEqual(run.call_count, 1)
        with patch.object(setup, "run") as run:
            setup.download_model(Path("/fixture/uv"), directory, profile, {})
            run.assert_not_called()
        (directory / "model.safetensors").write_bytes(b"corrupt")
        with patch.object(setup, "run") as run, self.assertRaises(RuntimeError):
            setup.download_model(Path("/fixture/uv"), directory, profile, {})
        run.assert_not_called()
        self.assertEqual((directory / "model.safetensors").read_bytes(), b"corrupt")
        for name in payloads:
            (directory / name).unlink()  # Remove only this test's two tiny fixture files.
        with patch.object(setup, "run", side_effect=fake_run) as run:
            setup.download_model(Path("/fixture/uv"), directory, profile, {})
            self.assertEqual(run.call_count, len(payloads))
        self.assertEqual({name:(directory/name).read_bytes() for name in payloads}, payloads)

    def test_npm_preserves_existing_tree_before_any_write_or_command(self):
        changed = self.root / "browser/node_modules/example/index.js"
        changed.parent.mkdir(parents=True)
        changed.write_bytes(b"user edit")
        with patch.object(setup, "run") as run, patch.object(setup, "write_same") as write, \
             self.assertRaisesRegex(RuntimeError, "Preserving existing dependency tree"):
            setup.npm_install(self.root, self.root / "node", "browser", "@playwright/mcp@0.0.82", {})
        run.assert_not_called()
        write.assert_not_called()
        self.assertEqual(changed.read_bytes(), b"user edit")

    def app_transport(self, images=None, copy_failure=False, detach_failure=False):
        root = self.root / "LocalAI"
        (root / "downloads").mkdir(parents=True)
        (root / "downloads/oMLX-0.6.4-macos26-27.dmg").write_bytes(b"mock verified DMG")
        calls, mounts = [], []
        def lookup(command, **kwargs):
            calls.append(list(map(str, command)))
            if command[1] == "info":
                return plistlib.dumps({"images": images or []})
            mount = Path(command[command.index("-mountpoint") + 1])
            mounts.append(mount)
            contents = mount / "oMLX.app/Contents"
            contents.mkdir(parents=True)
            (contents / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "app.omlx", "CFBundleShortVersionString": "0.6.4"}))
            return plistlib.dumps({"system-entities": [{"dev-entry":"/dev/disk990"},
                {"dev-entry":"/dev/disk990s1", "mount-point":str(mount)}]})
        def run(command, env, timeout=None):
            calls.append(list(map(str, command)))
            if command[0] == "/usr/bin/ditto":
                if copy_failure: raise RuntimeError("mock copy failure")
                shutil.copytree(command[-2], command[-1])
            if command[:2] == ["/usr/bin/hdiutil", "detach"]:
                self.assertEqual(command[-1], "/dev/disk990")
                self.assertEqual(timeout, 30)
                if detach_failure: raise RuntimeError("mock detach failure")
                shutil.rmtree(mounts[0] / "oMLX.app")  # Mock unmount of our tiny test fixture.
        return root, calls, lookup, run

    def test_user_app_preserves_unowned_and_already_attached_image(self):
        destination = self.root / "Applications/oMLX.app"
        destination.mkdir(parents=True)
        with patch.object(Path, "home", return_value=self.root), \
             patch.object(setup.subprocess, "check_output", side_effect=AssertionError("native command forbidden")), \
             self.assertRaisesRegex(RuntimeError, "without this installer's receipt"):
            setup.install_app(self.root / "LocalAI", {})
        destination.rmdir()
        dmg = self.root / "LocalAI/downloads/oMLX-0.6.4-macos26-27.dmg"
        root, calls, lookup, run = self.app_transport(images=[{"image-path":str(dmg),
            "system-entities":[{"dev-entry":"/dev/disk7"}]}])
        with patch.object(Path, "home", return_value=self.root), \
             patch.object(setup.subprocess, "check_output", side_effect=lookup), \
             patch.object(setup, "run", side_effect=run), \
             self.assertRaisesRegex(RuntimeError, "already-attached"):
            setup.install_app(root, {})
        self.assertEqual([command[1] for command in calls], ["info"])

    def test_user_app_copy_failure_cleans_only_new_device_and_retains_errors(self):
        root, calls, lookup, run = self.app_transport(copy_failure=True, detach_failure=True)
        with patch.object(Path, "home", return_value=self.root), \
             patch.object(setup.subprocess, "check_output", side_effect=lookup), \
             patch.object(setup, "run", side_effect=run), \
             self.assertRaisesRegex(RuntimeError, "mock copy failure.*mock detach failure"):
            setup.install_app(root, {})
        self.assertEqual(calls[-1], ["/usr/bin/hdiutil", "detach", "/dev/disk990"])
        self.assertFalse((self.root / "Applications/oMLX.app").exists())
        self.assertFalse((root / "app-install.json").exists())

    def test_user_app_reused_device_is_not_detached(self):
        root, calls, lookup, run = self.app_transport(images=[{"image-path":str(self.root / "other.dmg"),
            "system-entities":[{"dev-entry":"/dev/disk990"}]}])
        with patch.object(Path, "home", return_value=self.root), \
             patch.object(setup.subprocess, "check_output", side_effect=lookup), \
             patch.object(setup, "run", side_effect=run), \
             self.assertRaisesRegex(RuntimeError, "Could not prove a new private"):
            setup.install_app(root, {})
        self.assertEqual([command[1] for command in calls], ["info", "attach"])

    def test_user_app_success_receipt_and_identical_rerun(self):
        root, calls, lookup, run = self.app_transport()
        with patch.object(Path, "home", return_value=self.root), \
             patch.object(setup.subprocess, "check_output", side_effect=lookup), \
             patch.object(setup, "run", side_effect=run):
            setup.install_app(root, {})
            setup.install_app(root, {})
        self.assertEqual(sum(command[1] == "attach" for command in calls), 1)
        self.assertEqual(sum(command[1] == "detach" for command in calls), 1)
        receipt = json.loads((root / "app-install.json").read_text())
        self.assertEqual(receipt["dmg_sha256"], setup.DMG_SHA)
        self.assertEqual(receipt["bundle_sha256"], setup.bundle_digest(self.root / "Applications/oMLX.app"))

    def test_native_private_temp_lifecycle(self):
        actual_temp = tempfile.TemporaryDirectory
        ambient = {key: setup.os.environ.get(key) for key in ("TMPDIR", "TMP", "TEMP", "TMPPREFIX", "MAC_CHROMIUM_TMPDIR", "BREAKPAD_DUMP_LOCATION", "PWTEST_SERVER_REGISTRY")}
        for failure in (None, "constructor", "log", "spawn", "readiness", "interrupt", "shutdown", "forced", "abnormal", "graceful130", "unrequested130", "signal"):
            with self.subTest(failure=failure), contextlib.ExitStack() as stack:
                paths = []
                def private_temp(**kwargs):
                    self.assertEqual(kwargs, {"prefix": ".localai-tmp-" if paths else "localai-",
                                              "dir": self.root if paths else "/private/tmp", "delete": False})
                    value = actual_temp(**{**kwargs, "dir": self.root})
                    paths.append(Path(value.name))
                    self.assertEqual(paths[-1].stat().st_mode & 0o777, 0o700)
                    return value
                factory = stack.enter_context(patch.object(native_client.tempfile, "TemporaryDirectory", side_effect=private_temp))
                socket = stack.enter_context(patch.object(native_client.socket, "socket"))
                socket.return_value.__enter__.return_value.getsockname.return_value = ("127.0.0.1", 12345)
                if failure == "constructor":
                    socket.side_effect = OSError("bind failed")
                    with self.assertRaises(OSError):
                        native_client.NativeServer(self.root, {}, self.root / "native.log")
                    factory.assert_not_called()
                    continue
                with patch.dict(native_client.os.environ, {"MAC_CHROMIUM_TMPDIR": "/unrelated/chrome-temp",
                                                            "TMPPREFIX": "/unrelated/zsh",
                                                            "BREAKPAD_DUMP_LOCATION": "/unrelated/crashpad",
                                                            "PWTEST_SERVER_REGISTRY": "/unrelated/registry"}):
                    server = native_client.NativeServer(self.root, {}, self.root / "native.log")
                self.assertNotIn("MAC_CHROMIUM_TMPDIR", server.env)
                self.assertNotIn("BREAKPAD_DUMP_LOCATION", server.env)
                self.assertNotIn("PWTEST_SERVER_REGISTRY", server.env)
                self.assertNotIn("TMPPREFIX", server.env)
                factory.assert_not_called()  # Constructor failure cannot leave owned scratch.
                process = MagicMock()
                process.poll.return_value = None
                def wait(timeout):
                    self.assertTrue(all(p.is_dir() for p in paths))  # Never clean before proven child exit.
                    if failure == "shutdown" or (failure == "forced" and timeout == 10):
                        raise subprocess.TimeoutExpired("owned native", timeout)
                    code = 130 if failure == "graceful130" else 0
                    process.poll.return_value = code
                    return code
                process.wait.side_effect = wait
                spawn = stack.enter_context(patch.object(native_client.subprocess, "Popen", return_value=process))
                request = stack.enter_context(patch.object(server, "request", return_value={}))
                stack.enter_context(patch.object(native_client.time, "sleep"))
                if failure == "log":
                    stack.enter_context(patch.object(native_client, "_open_owned_log", side_effect=OSError("log denied")))
                if failure == "spawn":
                    spawn.side_effect = OSError("spawn failed")
                if failure == "readiness":
                    request.side_effect = OSError("not ready")
                if failure == "interrupt":
                    request.side_effect = KeyboardInterrupt()
                if failure in ("abnormal", "unrequested130", "signal"):
                    process.poll.return_value = {"abnormal": 7, "unrequested130": 130, "signal": -15}[failure]
                if failure in ("log", "spawn", "readiness", "interrupt", "abnormal", "unrequested130", "signal"):
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises((OSError, RuntimeError, KeyboardInterrupt)):
                        server.__enter__()
                    if failure in ("abnormal", "unrequested130", "signal"):
                        self.assertFalse(server.termination_requested)
                        process.terminate.assert_not_called()
                        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(RuntimeError):
                            server.close()
                        self.assertTrue(all(p.exists() for p in paths))
                        for name in ("task_temporary", "temporary"):
                            getattr(server, name).cleanup()  # Test-only cleanup after fake process.
                            setattr(server, name, None)
                    if failure == "spawn":
                        self.assertEqual(spawn.call_count, 1)  # No unsandboxed retry.
                    self.assertTrue(all(not p.exists() for p in paths))
                    self.assertIsNone(server.temporary)
                    self.assertIsNone(server.task_temporary)
                    if server.log_file is not None:
                        self.assertTrue(server.log_file.closed)
                    continue
                server.__enter__()
                command = spawn.call_args.args[0]
                self.assertEqual(command[0], str(native_client.BINARY))
                self.assertNotIn("/usr/bin/sandbox-exec", command)
                self.assertEqual(command[-6:], [str(native_client.BINARY), "serve", "--hostname", "127.0.0.1", "--port", "12345"])
                metadata = json.loads(server.log_path.read_text().splitlines()[-1])["write_boundary"]
                self.assertEqual(metadata["roots"]["PRIVATE_TMP"], str(paths[0]))
                self.assertEqual(metadata["task_temporary"], str(paths[1]))
                self.assertEqual(metadata["scope"], "ordinary native shell descendants only")
                self.assertEqual(json.loads(server.env["OPENCODE_CONFIG_CONTENT"])["shell"], str(native_client.SHELL_SHIM))
                self.assertEqual(server.env["LOCALAI_SHELL_PROJECT"], str(self.root))
                self.assertEqual(server.env["LOCALAI_SHELL_TEMP"], str(paths[0]))
                self.assertEqual(server.env["LOCALAI_TASK_TMP"], str(paths[1]))
                self.assertNotIn(server.env["OPENCODE_PASSWORD"], server.log_path.read_text())
                self.assertEqual({server.env[k] for k in ("TMPDIR", "TMP", "TEMP")}, {str(paths[1])})
                self.assertEqual({server.env[k] for k in ("MAC_CHROMIUM_TMPDIR", "BREAKPAD_DUMP_LOCATION")}, {str(paths[0])})
                self.assertEqual(server.env["PWTEST_SERVER_REGISTRY"], str(paths[0] / "pw-registry"))
                self.assertEqual(server.env["TMPPREFIX"], str(paths[-1] / "zsh"))
                self.assertEqual((paths[1] / ".gitignore").read_bytes(), b"*\n")
                self.assertFalse((self.root / ".gitignore").exists())
                self.assertIs(spawn.call_args.kwargs["env"], server.env)
                self.assertEqual(server.env["PWD"], str(self.root))
                with self.assertRaises(RuntimeError):
                    server.__enter__()  # No overlapping ownership/restart.
                if failure in ("shutdown", "forced"):
                    with contextlib.redirect_stderr(io.StringIO()) as error:
                        if failure == "shutdown":
                            with self.assertRaises(subprocess.TimeoutExpired):
                                server.close()
                        else:
                            with self.assertRaises(RuntimeError):
                                server.close()
                    self.assertTrue(all(str(p) in error.getvalue() for p in paths))
                    self.assertTrue(all(p.exists() for p in paths))
                    self.assertTrue(server.log_file.closed)
                    # Neither GC nor a later close may erase a forced-exit tree.
                    server.temporary._finalizer()
                    server.task_temporary._finalizer()
                    process.poll.return_value = 0
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(RuntimeError):
                        server.close()
                    self.assertTrue(all(p.exists() for p in paths))
                    for name in ("task_temporary", "temporary"):
                        getattr(server, name).cleanup()  # Test-only cleanup after fake process.
                        setattr(server, name, None)
                server.close()
                if failure == "graceful130":
                    self.assertEqual(process.poll(), 130)
                    self.assertTrue(server.termination_requested)
                    self.assertFalse(server.forced_shutdown)
                server.close()  # Idempotent after a verified exit.
                self.assertTrue(all(not p.exists() for p in paths))
                self.assertIsNone(server.temporary)
                self.assertIsNone(server.task_temporary)
        self.assertEqual({key: setup.os.environ.get(key) for key in ambient}, ambient)

    def test_retained_close_cannot_mark_lifecycle_success(self):
        actual_temp = tempfile.TemporaryDirectory
        with patch.object(native_client.tempfile, "TemporaryDirectory",
                          side_effect=lambda **kw: actual_temp(**{**kw, "dir": self.root})), \
             patch.object(native_client.socket, "socket") as socket, \
             patch.object(native_client.subprocess, "Popen") as spawn, \
             patch.object(native_client.NativeServer, "request", return_value={}):
            socket.return_value.__enter__.return_value.getsockname.return_value = ("127.0.0.1", 12345)
            for failure in ("forced", "abnormal", "new_timeout"):
                with self.subTest(failure=failure):
                    process = MagicMock(); process.poll.return_value = None
                    late = subprocess.TimeoutExpired("second wait", 5)
                    def wait(timeout):
                        if timeout == 10:
                            raise subprocess.TimeoutExpired("first wait", 10)
                        if failure == "new_timeout":
                            raise late
                        process.poll.return_value = -9
                    process.wait.side_effect = wait; spawn.return_value = process
                    accepted = False; audit_like_success = False
                    server = native_client.NativeServer(self.root, {}, self.root / "native.log")
                    expected = subprocess.TimeoutExpired if failure == "new_timeout" else RuntimeError
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(expected) as caught:
                        with server:
                            audit_like_success = True  # A ready/closed-like success cannot waive teardown.
                            if failure == "abnormal":
                                process.poll.return_value = 7
                        accepted = True
                    self.assertTrue(audit_like_success); self.assertFalse(accepted)
                    self.assertIsNotNone(server.temporary)
                    self.assertIsNotNone(server.task_temporary)
                    self.assertTrue(Path(server.temporary.name).exists())
                    self.assertTrue(Path(server.task_temporary.name).exists())
                    if failure == "new_timeout":
                        self.assertIs(caught.exception, late)  # Do not mask the real shutdown error.
                    # A caller's unrelated handled exception must not suppress direct close failure.
                    try:
                        raise ValueError("already handled")
                    except ValueError:
                        process.poll.return_value = 7
                        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(RuntimeError):
                            server.close()
                    for name in ("task_temporary", "temporary"):
                        getattr(server, name).cleanup()  # Fake-process cleanup only.
                        setattr(server, name, None)

    def test_native_cleanup_preserves_original_body_and_enter_errors(self):
        class OverrideServer(native_client.NativeServer):
            def close(self):  # Existing Task12 subclasses have this no-argument seam.
                self.override_called = True
                super().close()
        actual_temp = tempfile.TemporaryDirectory
        with patch.object(native_client.tempfile, "TemporaryDirectory",
                          side_effect=lambda **kw: actual_temp(**{**kw, "dir": self.root})), \
             patch.object(native_client.socket, "socket") as socket, \
             patch.object(native_client.subprocess, "Popen") as spawn, \
             patch.object(native_client.NativeServer, "request") as request:
            socket.return_value.__enter__.return_value.getsockname.return_value = ("127.0.0.1", 12345)
            for phase in ("body", "enter"):
                for times_out in (False, True):
                    with self.subTest(phase=phase, times_out=times_out):
                        process = MagicMock(); process.poll.return_value = None
                        original = ValueError("original " + phase)
                        def wait(timeout):
                            if timeout == 10 or times_out:
                                raise subprocess.TimeoutExpired("owned native", timeout)
                            process.poll.return_value = -9
                        process.wait.side_effect = wait; spawn.return_value = process
                        request.side_effect = original if phase == "enter" else None
                        request.return_value = {}
                        server = OverrideServer(self.root, {}, self.root / "native.log")
                        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(ValueError) as caught:
                            with server:
                                raise original
                        self.assertIs(caught.exception, original)
                        self.assertTrue(server.override_called)
                        self.assertTrue(any(note.startswith("Native cleanup:") for note in original.__notes__))
                        self.assertTrue(Path(server.temporary.name).exists())
                        self.assertTrue(Path(server.task_temporary.name).exists())
                        for name in ("task_temporary", "temporary"):
                            getattr(server, name).cleanup()  # Fake-process cleanup only.
                            setattr(server, name, None)

    def test_native_private_temp_is_unique_and_preserves_unrelated_files(self):
        class OverrideServer(native_client.NativeServer):
            def close(self):
                self.override_called = True
                super().close()
        actual_temp = tempfile.TemporaryDirectory
        sentinel = self.root / "unrelated-temp"
        sentinel.write_text("preserve")
        with patch.object(native_client.tempfile, "TemporaryDirectory",
                          side_effect=lambda **kw: actual_temp(**{**kw, "dir": self.root})), \
             patch.object(native_client.socket, "socket") as socket, \
             patch.object(native_client.subprocess, "Popen") as spawn, \
             patch.object(native_client.NativeServer, "request", return_value={}):
            socket.return_value.__enter__.return_value.getsockname.return_value = ("127.0.0.1", 12345)
            processes = [MagicMock(), MagicMock()]
            for process in processes:
                process.poll.return_value = None
                process.wait.side_effect = lambda timeout, proc=process: setattr(proc.poll, "return_value", 0)
            spawn.side_effect = processes
            with OverrideServer(self.root, {}, self.root / "first.log") as first:
                with native_client.NativeServer(self.root, {}, self.root / "second.log") as second:
                    paths = [Path(s.env["TMPDIR"]) for s in (first, second)]
                    private_paths = [Path(s.temporary.name) for s in (first, second)]
                    self.assertNotEqual(*paths)
                    self.assertEqual(len(set(paths + private_paths)), 4)
                    self.assertTrue(all(p.exists() for p in paths + private_paths))
                self.assertTrue(paths[0].exists())
                self.assertTrue(private_paths[0].exists())
                self.assertFalse(paths[1].exists())
                self.assertFalse(private_paths[1].exists())
            self.assertFalse(paths[0].exists())
            self.assertFalse(private_paths[0].exists())
            self.assertTrue(first.override_called)
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_shell_config_is_explicit_and_does_not_mutate_caller(self):
        cfg = {"plugins": ["one", "-opencode.config.shell", "two"]}
        before = copy.deepcopy(cfg)
        with patch.object(native_client.socket, "socket"):
            server = native_client.NativeServer(self.root, cfg)
            effective = json.loads(server.env["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(effective["shell"], str(native_client.SHELL_SHIM))
            self.assertEqual(effective["plugins"], ["one", "two", "opencode.config.shell"])
            self.assertEqual(cfg, before)
            with self.assertRaisesRegex(RuntimeError, "conflicts"):
                native_client.NativeServer(self.root, {"shell": "/bin/zsh"})

    def test_project_scratch_refuses_unsafe_project_before_allocation(self):
        link = self.root / "project-link"
        link.symlink_to(self.root, target_is_directory=True)
        for directory in (Path.home(), self.native_root / "models/project", self.root / "missing", link):
            with self.subTest(directory=directory), patch.object(native_client.socket, "socket"), \
                 patch.object(native_client.tempfile, "TemporaryDirectory") as allocation, \
                 patch.object(native_client.subprocess, "Popen") as spawn:
                server = native_client.NativeServer(directory, {}, self.root / "native.log")
                with self.assertRaises(RuntimeError):
                    server.__enter__()
                allocation.assert_not_called()
                spawn.assert_not_called()
                self.assertIsNone(server.temporary)
                self.assertIsNone(server.task_temporary)
        self.assertFalse((self.root / "missing").exists())
        self.assertFalse((self.native_root / "models").exists())

    def test_project_scratch_partial_startup_cleans_only_new_roots(self):
        actual_temp, actual_open = tempfile.TemporaryDirectory, Path.open
        sentinel = self.root / ".gitignore"
        sentinel.write_text("existing-ignore\n")
        before = sentinel.stat()
        for failure in ("private-allocation", "task-allocation", "ignore", "browser"):
            paths = []
            def allocate(**kwargs):
                if failure == "private-allocation" or (failure == "task-allocation" and paths):
                    raise OSError("allocation failed")
                result = actual_temp(**{**kwargs, "dir": self.root})
                paths.append(Path(result.name))
                return result
            def opened(path, *args, **kwargs):
                if failure == "ignore" and path.name == ".gitignore" and path != sentinel:
                    raise OSError("new ignore failed")
                return actual_open(path, *args, **kwargs)
            cfg = {"mcp": {"servers": {"browser": {"type": "remote"}}}} if failure == "browser" else {}
            with self.subTest(failure=failure), patch.object(native_client.socket, "socket"), \
                 patch.object(native_client.tempfile, "TemporaryDirectory", side_effect=allocate), \
                 patch.object(Path, "open", opened), patch.object(native_client.subprocess, "Popen") as spawn:
                server = native_client.NativeServer(self.root, cfg, self.root / "native.log")
                with self.assertRaises((OSError, RuntimeError)):
                    server.__enter__()
                self.assertTrue(all(not path.exists() for path in paths))
                self.assertIsNone(server.temporary)
                self.assertIsNone(server.task_temporary)
                spawn.assert_not_called()
            self.assertEqual(sentinel.read_text(), "existing-ignore\n")
            self.assertEqual(sentinel.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(sentinel.stat().st_ino, before.st_ino)

    def test_browser_temp_override_preserves_config_and_native_project_defaults(self):
        actual_temp = tempfile.TemporaryDirectory
        cfg = {"mcp": {"servers": {"browser": {"type": "local", "command": ["node", "owned-mcp", "--isolated"],
                "codemode": False, "environment": {"PRESERVE_ME": "unchanged", "TMPDIR": "/unrelated",
                                                     "MAC_CHROMIUM_TMPDIR": "/unrelated"}},
                "search": {"type": "remote", "url": "https://example.invalid"}}}, "permissions": [{"action": "shell", "value": "ask"}]}
        before = copy.deepcopy(cfg)
        with patch.object(native_client.tempfile, "TemporaryDirectory", side_effect=lambda **kw: actual_temp(**{**kw, "dir": self.root})), \
             patch.object(native_client.socket, "socket"), patch.object(native_client.subprocess, "Popen") as spawn, \
             patch.object(native_client.NativeServer, "request", return_value={}):
            process = spawn.return_value
            process.poll.return_value = None
            process.wait.side_effect = lambda timeout: setattr(process.poll, "return_value", 0)
            with native_client.NativeServer(self.root, cfg, self.root / "native.log") as server:
                effective = json.loads(server.env["OPENCODE_CONFIG_CONTENT"])
                browser = effective["mcp"]["servers"]["browser"]
                private, task = Path(server.temporary.name), Path(server.task_temporary.name)
                self.assertEqual(task.parent, self.root)
                self.assertTrue(task.name.startswith(".localai-tmp-"))
                for key in ("TMPDIR", "TMP", "TEMP"):
                    self.assertEqual(server.env[key], str(task))
                    self.assertEqual(browser["environment"][key], str(private))
                for key in ("MAC_CHROMIUM_TMPDIR", "BREAKPAD_DUMP_LOCATION", "PWTEST_SERVER_REGISTRY"):
                    self.assertEqual(browser["environment"][key], server.env[key])
                self.assertEqual(browser["environment"]["TMPPREFIX"], str(private / "zsh"))
                self.assertEqual(browser["environment"]["PRESERVE_ME"], "unchanged")
                self.assertEqual(server.env["TMPPREFIX"], str(task / "zsh"))
                del effective["shell"], effective["plugins"]
                browser["environment"] = before["mcp"]["servers"]["browser"]["environment"]
                self.assertEqual(effective, before)
                self.assertEqual(cfg, before)
            self.assertFalse(private.exists())
            self.assertFalse(task.exists())

    def test_both_temp_cleanups_attempted_and_original_error_preserved(self):
        actual_temp = tempfile.TemporaryDirectory
        for failing in ("task_temporary", "temporary"):
            for body_error in (False, True):
                with self.subTest(failing=failing, body_error=body_error), patch.object(native_client.socket, "socket"):
                    server = native_client.NativeServer(self.root, {}, self.root / "native.log")
                    server.temporary = actual_temp(dir=self.root, delete=False)
                    server.task_temporary = actual_temp(dir=self.root, delete=False)
                    failed = getattr(server, failing)
                    other = server.temporary if failing == "task_temporary" else server.task_temporary
                    failed_path, other_path = Path(failed.name), Path(other.name)
                    original = ValueError("original body")
                    cleanup_error = OSError("one cleanup failed")
                    with patch.object(failed, "cleanup", side_effect=cleanup_error):
                        if body_error:
                            server.__exit__(ValueError, original, None)
                            self.assertTrue(any("one cleanup failed" in note for note in original.__notes__))
                        else:
                            with self.assertRaises(OSError) as caught:
                                server.close()
                            self.assertIs(caught.exception, cleanup_error)
                    self.assertTrue(failed_path.exists())
                    self.assertFalse(other_path.exists())
                    self.assertIs(getattr(server, failing), failed)
                    failed.cleanup()  # Fake owner; the retained root alone remains.
                    setattr(server, failing, None)

    def test_shell_shim_admission_refuses_missing_changed_and_nonexecutable(self):
        shim = self.native_root / "native-shell"
        for state in ("missing", "changed", "nonexecutable", "symlink", "shared"):
            with self.subTest(state=state), patch.object(native_client, "SHELL_SHIM", shim), \
                 patch.object(native_client.socket, "socket"), \
                 patch.object(native_client.subprocess, "Popen") as spawn:
                if state == "symlink":
                    shim.symlink_to(Path(native_client.__file__).resolve())
                elif state != "missing":
                    shim.write_bytes(b"changed" if state == "changed" else native_client.SHELL_SHIM_BYTES)
                    shim.chmod(0o600 if state == "nonexecutable" else 0o777 if state == "shared" else 0o700)
                server = native_client.NativeServer(self.root, {}, self.root / "native.log")
                with self.assertRaises((OSError, RuntimeError)):
                    server.__enter__()
                spawn.assert_not_called()
                self.assertIsNone(server.temporary)
                if shim.exists() or shim.is_symlink(): shim.unlink()

    def test_guarded_shell_preserves_command_and_frozen_roots(self):
        private, env = self.native_boundary_fixture()
        helper, python, digest = native_client._shell_identity()
        env.update(LOCALAI_SHELL_HELPER=str(helper), LOCALAI_SHELL_PYTHON=str(python),
                   LOCALAI_SHELL_HELPER_SHA256=digest, LOCALAI_SHELL_PROJECT=str(self.root),
                   LOCALAI_SHELL_TEMP=str(private), LOCALAI_SHELL_LOG_DIR=str(self.root / "evidence"),
                   PWD="/unrelated/command/cwd")
        command = "printf '%s\\n' \"quotes ' $() `text` < >\"\n# two lines"
        with patch.dict(native_client.os.environ, env, clear=True), \
             patch.object(native_client.os, "execve") as execute:
            native_client.guarded_shell(["-c", command])
            executable, argv, forwarded = execute.call_args.args
            self.assertEqual(executable, "/usr/bin/sandbox-exec")
            self.assertEqual(argv[-3:], ["/bin/zsh", "-c", command])
            self.assertIn("PROJECT=" + str(self.root), argv)
            self.assertNotIn("PROJECT=" + env["PWD"], argv)
            self.assertEqual(forwarded["LOCALAI_SHELL_PROJECT"], str(self.root))
            self.assertEqual(forwarded["TMPPREFIX"], str(Path(env["LOCALAI_TASK_TMP"]) / "zsh"))
            execute.reset_mock()
            for args in ([], ["-l"], ["-c"], ["-c", "one", "two"]):
                with self.assertRaises(RuntimeError): native_client.guarded_shell(args)
            with patch.dict(native_client.os.environ, {"LOCALAI_SHELL_HELPER_SHA256": "0" * 64}):
                with self.assertRaises(RuntimeError): native_client.guarded_shell(["-c", ":"])
            execute.assert_not_called()

    def test_shell_boundary_rejects_implementation_in_any_write_root(self):
        private, env = self.native_boundary_fixture()
        for writable in (self.root, self.root / "evidence", self.native_root / "xdg/data", private):
            with self.subTest(writable=writable), \
                 patch.object(native_client, "SHELL_SHIM", writable / "native-shell"), \
                 self.assertRaises(RuntimeError):
                native_client._sandbox_prefix(self.root, private, self.root / "evidence", env)

    def test_shell_startup_canary_requires_actual_resolution_and_cleanup(self):
        self.canary_patch.stop()
        command = "/bin/cat <<'LOCALAI_HEREDOC'\nowned-nonce\nLOCALAI_HEREDOC\n"
        for failure in (None, "wrong-shell", "command", "exit", "completed", "owner", "plugin", "delete", "timeout",
                        "output", "truncated", "cursor", "size", "missing-output", "output-error",
                        "delayed-output", "delayed-sized-output", "output-timeout", "oversized"):
            clock = [0, 1, 2, 14] if failure == "output-timeout" else range(0, 100, 20 if failure == "timeout" else 1)
            with self.subTest(failure=failure), patch.object(native_client.socket, "socket"), \
                 patch.object(native_client.secrets, "token_hex", return_value="owned-nonce"), \
                 patch.object(native_client.time, "sleep"), \
                 patch.object(native_client.time, "monotonic", side_effect=clock):
                server = native_client.NativeServer(self.root, {})
                server.log_file = io.BytesIO()
                info = {"id": "sh_owned", "command": command, "cwd": str(self.root),
                        "shell": str(native_client.SHELL_SHIM), "status": "exited", "exit": 0,
                        "metadata": {"localai_shell_admission": "owned-nonce"}, "time": {"completed": 1}}
                if failure == "wrong-shell": info["shell"] = "/bin/zsh"
                if failure == "command": info["command"] = ":"
                if failure == "exit": info["exit"] = 1
                if failure == "completed": info["time"] = {}
                if failure == "owner": info["metadata"] = {}
                if failure == "timeout": info["status"] = "running"
                pending_output = iter(["", "owned-", "owned-nonce\n"])
                output_reads = []
                def request(method, endpoint, body=None, timeout=30):
                    if endpoint == "/api/plugin":
                        return {"location": {"directory": str(self.root)}, "data": [{"id": "opencode.config.shell",
                                "source": {"type": "builtin"}, "state": {"status": "failed" if failure == "plugin" else "active"}}]}
                    if method == "POST":
                        self.assertEqual(body["command"], command)
                        self.assertEqual(body["cwd"], str(self.root))
                        self.assertEqual(body["timeout"], 10000)
                        return {"data": copy.deepcopy(info)}
                    if method == "DELETE":
                        self.assertEqual(endpoint, "/api/shell/sh_owned")
                        if failure == "delete": raise OSError("delete failed")
                        return None
                    if "/output?" in endpoint:
                        output_reads.append(endpoint)
                        self.assertEqual(endpoint, "/api/shell/sh_owned/output?cursor=0&limit=1024")
                        if failure == "output-error": raise OSError("output read failed")
                        output = {"output": "owned-nonce\n", "cursor": 12, "size": 12, "truncated": False}
                        if failure in ("delayed-output", "delayed-sized-output", "output-timeout"):
                            content = "" if failure == "output-timeout" else next(pending_output)
                            output.update(output=content, cursor=len(content),
                                          size=len(content) if failure == "delayed-output" else 12)
                        if failure == "output": output["output"] += "unexpected stderr"
                        if failure == "truncated": output["truncated"] = True
                        if failure in ("cursor", "size"): output[failure] = 11
                        if failure == "oversized": output["size"] = 13
                        return {"data": {} if failure == "missing-output" else output}
                    return {"data": copy.deepcopy(info)}
                with patch.object(server, "request", side_effect=request) as call:
                    if failure in (None, "delayed-output", "delayed-sized-output"):
                        server._verify_guarded_shell()
                        admission = json.loads(server.log_file.getvalue())["shell_admission"]
                        self.assertEqual(admission["scope"], "operator startup heredoc; no inference")
                        self.assertTrue(admission["heredoc_output_verified"])
                    else:
                        with self.assertRaises((RuntimeError, OSError)): server._verify_guarded_shell()
                    deletes = [c for c in call.call_args_list if c.args[0] == "DELETE"]
                    self.assertEqual(len(deletes), 0 if failure in ("owner", "plugin", "command") else 1)
                    if failure in ("delayed-output", "delayed-sized-output"): self.assertEqual(len(output_reads), 3)
                    if failure in ("output", "truncated", "cursor", "size", "missing-output", "output-error", "output-timeout", "oversized"):
                        self.assertEqual(len(output_reads), 1)

    def native_boundary_fixture(self):
        private = self.root / "private"
        private.mkdir(mode=0o700)
        task = self.root / ".localai-tmp-test"
        task.mkdir(mode=0o700)
        env = native_client.environment({})
        env.update({key: str(task) for key in ("TMPDIR", "TMP", "TEMP", "LOCALAI_TASK_TMP")})
        env.update({key: str(private) for key in ("MAC_CHROMIUM_TMPDIR", "BREAKPAD_DUMP_LOCATION")})
        env["PWTEST_SERVER_REGISTRY"] = str(private / "pw-registry")
        env["TMPPREFIX"] = str(task / "zsh")
        return private, env

    def test_native_write_boundary_prefix_and_owned_roots(self):
        private, env = self.native_boundary_fixture()
        prefix, metadata = native_client._sandbox_prefix(self.root, private, self.root / "evidence", env)
        self.assertEqual(prefix[:3], ["/usr/bin/sandbox-exec", "-p", native_client.WRITE_PROFILE])
        self.assertEqual(metadata["profile_sha256"], "2ebaf76bcc65b6626df7a5904a21c3979e4334469fc4c20d795ec6b163321585")
        self.assertEqual(set(metadata["roots"]), {"PROJECT", "XDG_DATA", "XDG_CACHE", "XDG_STATE",
                                                 "PRIVATE_TMP", "BROWSER_OUTPUT", "LOG_DIR"})
        self.assertEqual(prefix[3::2], ["-D"] * 7)
        self.assertEqual(set(prefix[4::2]), {name + "=" + path for name, path in metadata["roots"].items()})
        for name, path in metadata["roots"].items():
            self.assertTrue(Path(path).is_dir())
            self.assertEqual(Path(path).resolve(), Path(path))
        self.assertNotIn("XDG_CONFIG", metadata["roots"])
        self.assertFalse((self.native_root / "xdg/config").exists())
        self.assertFalse((self.native_root / "models").exists())
        # The daily log root is the only dynamic target admitted inside LocalAI.
        prefix, metadata = native_client._sandbox_prefix(self.root, private, self.native_root / "runs", env)
        self.assertEqual(metadata["roots"]["LOG_DIR"], str(self.native_root / "runs"))

    def test_native_write_boundary_rejects_broad_protected_and_redirected_roots(self):
        private, env = self.native_boundary_fixture()
        invalid = [Path.home(), Path.home() / "Documents", Path("/private/tmp"), self.native_root,
                   self.native_root / "xdg/config", self.native_root / "models/project",
                   self.native_root / "challenger/models", self.native_root / "opencode",
                   self.native_root / "client", Path.home() / ".omlx", Path.home() / "Applications/oMLX.app",
                   self.native_root.with_name("localai"), self.native_root.with_name("LOCALAI") / "xdg/config",
                   self.native_root / "XDg/ConFIG"]
        for target in invalid:
            for name in ("PROJECT", "LOG_DIR"):
                with self.subTest(target=target, name=name), self.assertRaises(RuntimeError):
                    native_client._sandbox_prefix(target if name == "PROJECT" else self.root, private,
                                                  target if name == "LOG_DIR" else self.root / "evidence", env)
        for key in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "TMPDIR", "TMP", "TEMP", "TMPPREFIX", "LOCALAI_TASK_TMP", "MAC_CHROMIUM_TMPDIR", "BREAKPAD_DUMP_LOCATION", "PWTEST_SERVER_REGISTRY"):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                native_client._sandbox_prefix(self.root, private, self.root / "evidence", {**env, key: "/tmp"})
        with self.assertRaises(RuntimeError):
            native_client._sandbox_prefix(self.root, private, self.root / "evidence",
                                          {k: v for k, v in env.items() if k != "TMPPREFIX"})
        for name in ("link", "dangling"):
            link = self.root / name
            link.symlink_to(self.root if name == "link" else self.root / "absent", target_is_directory=True)
            with self.subTest(symlink=name), self.assertRaises(RuntimeError):
                native_client._sandbox_prefix(link, private, self.root / "evidence", env)
            with self.subTest(log_symlink=name), self.assertRaises(RuntimeError):
                native_client._sandbox_prefix(self.root, private, link / "logs", env)
        ambient = self.root / "ambient-user-temp"
        ambient.mkdir(mode=0o700)
        with patch.object(native_client.tempfile, "gettempdir", return_value=str(ambient)):
            for name in ("PROJECT", "LOG_DIR"):
                with self.subTest(ambient_temp=name), self.assertRaises(RuntimeError):
                    native_client._sandbox_prefix(ambient if name == "PROJECT" else self.root, private,
                                                  ambient if name == "LOG_DIR" else self.root / "evidence", env)
        # Every failed preflight above happened before state/log creation.
        self.assertFalse((self.root / "evidence").exists())
        self.assertFalse((self.native_root / "xdg").exists())
        private.chmod(0o755)
        with self.assertRaises(RuntimeError):
            native_client._sandbox_prefix(self.root, private, self.root / "evidence", env)
        private.chmod(0o700)
        self.native_root.chmod(0o777)
        try:
            with self.assertRaises(RuntimeError):
                native_client._sandbox_prefix(self.root, private, self.root / "evidence", env)
        finally:
            self.native_root.chmod(0o700)

    def test_task_temp_binding_requires_private_direct_project_child(self):
        private, env = self.native_boundary_fixture()
        task = Path(env["LOCALAI_TASK_TMP"])
        outside = self.native_root / ".localai-tmp-outside"
        outside.mkdir(mode=0o700)
        nested = task / ".localai-tmp-nested"
        nested.mkdir(mode=0o700)
        link = self.root / ".localai-tmp-link"
        link.symlink_to(task, target_is_directory=True)
        for bad in ("", str(private), str(outside), str(nested), str(link), str(self.root)):
            bad_env = {**env, **{k: bad for k in ("TMPDIR", "TMP", "TEMP", "LOCALAI_TASK_TMP")},
                       "TMPPREFIX": str(Path(bad) / "zsh")}
            with self.subTest(bad=bad), self.assertRaises(RuntimeError):
                native_client._sandbox_prefix(self.root, private, self.root / "evidence", bad_env)
        task.chmod(0o755)
        with self.assertRaises(RuntimeError):
            native_client._sandbox_prefix(self.root, private, self.root / "evidence", env)
        self.assertFalse((self.root / "evidence").exists())
        self.assertFalse((self.native_root / "xdg").exists())

    def test_native_boundary_path_comparison_refuses_case_and_unicode_aliases(self):
        root = Path("/Users/example/LocalAI")
        self.assertTrue(native_client._within(root / "xdg/config", Path("/users/EXAMPLE/localai")))
        self.assertTrue(native_client._within(Path("/users/EXAMPLE/localai"), root))
        self.assertTrue(native_client._within(Path("/A/Cafe\u0301/logs"), Path("/a/Caf\u00e9")))
        self.assertFalse(native_client._within(Path("/Users/example/LocalAI-other"), root))
        self.assertFalse(native_client._within(root, root / "xdg"))

    def test_native_log_refuses_links_and_preserves_targets(self):
        target = self.root / "sentinel"
        target.write_bytes(b"preserve")
        before = target.stat()
        for name, kind in (("symlink.log", "symlink"), ("hardlink.log", "hardlink")):
            link = self.root / name
            if kind == "symlink": link.symlink_to(target)
            else: os.link(target, link)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                native_client._open_owned_log(link)
            self.assertEqual(target.read_bytes(), b"preserve")
            self.assertEqual(target.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(target.stat().st_mode, before.st_mode)
            link.unlink()
        path = self.root / "owned.log"
        with native_client._open_owned_log(path) as output:
            output.write(b"owned")
        self.assertEqual(path.read_bytes(), b"owned")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        # A sibling fake installation keeps pure native lifecycle checks isolated.
        self.native_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.native_tmp.cleanup)
        self.native_root = Path(self.native_tmp.name).resolve() / "LocalAI"
        self.native_root.mkdir(mode=0o700)
        self.canary_patch = patch.object(native_client.NativeServer, "_verify_guarded_shell")
        self.canary_mock = self.canary_patch.start()
        self.addCleanup(self.canary_patch.stop)
        for name, value in (("ROOT", self.native_root),
                            ("BINARY", self.native_root / "opencode/2.0.10/package/bin/opencode")):
            change = patch.object(native_client, name, value)
            change.start()
            self.addCleanup(change.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_uses_only_explicit_local_models_and_correct_budgets(self):
        root = self.root / 'A space and "quote"'
        cfg = setup.render(root, self.root / "node")
        model = cfg["providers"]["local"]["models"]["qwen"]
        self.assertEqual(cfg["default_agent"], "build")
        self.assertEqual(model["limit"], {"context": 16384, "output": 4096})
        self.assertEqual(model["body"]["max_tokens"], model["limit"]["output"])
        self.assertEqual(cfg["compaction"]["buffer"], 2048)
        self.assertEqual(cfg["providers"]["local"]["settings"]["baseURL"], "http://127.0.0.1:8000/v1")
        self.assertTrue(all(a["model"].startswith("local/qwen#") for a in cfg["agents"].values()))
        self.assertTrue(all(c["model"].startswith("local/qwen#") for c in cfg["commands"].values()))
        self.assertFalse(cfg["mcp"]["servers"]["search"]["oauth"])
        self.assertNotIn("agent_run", cfg["mcp"]["servers"]["search"]["url"])
        self.assertIn(str(root / "browser/node_modules/@playwright/mcp/cli.js"), cfg["mcp"]["servers"]["browser"]["command"])
        self.assertEqual(setup.runtime_settings(root)["scheduler"]["max_concurrent_requests"], 1)
        self.assertEqual(setup.runtime_settings(root)["idle_timeout"], {"idle_timeout_seconds": 300})
        self.assertFalse(setup.runtime_settings(root)["server"]["auto_start_on_launch"])
        self.assertEqual(setup.model_settings()["models"][setup.MODEL]["max_tokens"], 4096)
        self.assertTrue(setup.model_settings()["models"][setup.MODEL]["is_default"])
        self.assertNotIn("__ROOT__", json.dumps(cfg))

    def test_reruns_preserve_changed_files_and_reject_symlinks(self):
        target = self.root / "config.json"
        setup.write_same(target, "original")
        setup.write_same(target, "original")
        with self.assertRaises(RuntimeError):
            setup.write_same(target, "replacement")
        self.assertEqual(target.read_text(), "original")
        link = self.root / "link"
        link.symlink_to(target)
        with self.assertRaises(RuntimeError):
            setup.write_same(link, "original")

    def test_model_guard_preserves_unowned_and_symlinked_destinations(self):
        destination = self.root / "models" / setup.MODEL
        destination.mkdir(parents=True)
        with self.assertRaises(RuntimeError):
            setup.model_destination(self.root)
        destination.rmdir()
        other = self.root / "other"
        other.mkdir()
        destination.symlink_to(other, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            setup.model_destination(self.root)
        self.assertEqual(list(other.iterdir()), [])

    def test_model_marker_allows_retry_but_rejects_nested_symlinks(self):
        destination, marker, identity = setup.model_destination(self.root)
        setup.write_same(marker, identity)
        self.assertEqual(setup.model_destination(self.root)[0], destination)
        (destination / "shard").symlink_to(self.root / "unrelated")
        with self.assertRaises(RuntimeError):
            setup.model_destination(self.root)

    def test_unrelated_files_do_not_reduce_disk_reserve(self):
        unrelated = self.root / "browser-output"
        unrelated.write_bytes(b"unrelated")
        with self.assertRaises(RuntimeError):
            setup.require_space(110 * setup.GIB, "core")
        setup.require_space(140 * setup.GIB, "core")
        with self.assertRaises(RuntimeError):
            setup.require_space(103 * setup.GIB, "documents")

    def test_verified_download_is_reused_and_bad_hash_fails_offline(self):
        target = self.root / "download"
        target.write_bytes(b"known artifact")
        with patch.object(setup.urllib.request, "urlopen", side_effect=AssertionError("network forbidden")):
            setup.download("https://example.invalid/file", target, "sha256", hashlib.sha256(target.read_bytes()).hexdigest())
            with self.assertRaises(RuntimeError):
                setup.download("https://example.invalid/file", target, "sha256", "0" * 64)

    def test_archive_traversal_rejected_before_writes(self):
        archive = self.root / "hostile.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            member = tarfile.TarInfo("../../outside")
            member.size = 3
            bundle.addfile(member, io.BytesIO(b"bad"))
        destination = self.root / "out"
        with self.assertRaises(RuntimeError):
            setup.extract_cli(archive, destination)
        self.assertFalse(destination.exists())

    def test_expected_archive_and_executable_change_detection(self):
        archive = self.root / "cli.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            for name, data in [("package/bin/opencode", b"test fixture"), ("package/package.json", b"{}")]:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                bundle.addfile(member, io.BytesIO(data))
        destination = self.root / "out"
        setup.extract_cli(archive, destination)
        setup.extract_cli(archive, destination)
        executable = destination / "package/bin/opencode"
        executable.write_bytes(b"modified")
        with self.assertRaises(RuntimeError):
            setup.extract_cli(archive, destination)
        self.assertEqual(executable.read_bytes(), b"modified")

    def test_launcher_parses_and_quotes_paths(self):
        script = setup.launcher(self.root / "space ' quote $HOME `text`")
        result = subprocess.run(["/bin/zsh", "-n"], input=script, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--standalone", script)
        self.assertIn("-u OPENCODE_CONFIG_CONTENT", script)

    def test_default_preflight_cannot_download_write_or_install(self):
        fake_socket = MagicMock()
        fake_socket.__enter__.return_value.connect_ex.return_value = 1
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(sys, "argv", ["setup.py"]))
            stack.enter_context(patch.object(Path, "home", return_value=self.root))
            # Supply dependencies only; all target files and directories remain absent.
            stack.enter_context(patch.object(Path, "exists", lambda p: str(p).endswith(("/uv", "/node", "/npm", "Google Chrome.app"))))
            stack.enter_context(patch.object(setup.platform, "system", return_value="Darwin"))
            stack.enter_context(patch.object(setup.platform, "machine", return_value="arm64"))
            stack.enter_context(patch.object(setup.platform, "mac_ver", return_value=("26.6.2", (), "")))
            stack.enter_context(patch.object(setup.subprocess, "check_output", side_effect=lambda cmd, **kw: "arm64 22.23.1" if "-p" in cmd else str(48 * setup.GIB).encode()))
            stack.enter_context(patch.object(setup.subprocess, "run", return_value=MagicMock(returncode=1)))
            stack.enter_context(patch.object(setup.socket, "socket", return_value=fake_socket))
            stack.enter_context(patch.object(setup.shutil, "disk_usage", return_value=MagicMock(free=180 * setup.GIB)))
            stack.enter_context(patch.dict(setup.os.environ, {}, clear=True))
            for name in ("download", "write_same", "run", "extract_cli", "npm_install"):
                stack.enter_context(patch.object(setup, name, side_effect=AssertionError(f"{name} forbidden")))
            output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            setup.main()
            self.assertIn("READ-ONLY preflight passed", output.getvalue())
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
