"""Isolated package/transaction checks; no model, services or home activation."""
import hashlib
from contextlib import nullcontext, redirect_stdout
import importlib.util
import io
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "src"))
from kryn import cli, installer
spec = importlib.util.spec_from_file_location("kryn_builder", SOURCE / "build_package.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
spec = importlib.util.spec_from_file_location("kryn_bootstrap", SOURCE / "install-kryn.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kryn package with spaces ")
        self.root = Path(self.temp.name).resolve()
        self.root.chmod(0o700)

    def tearDown(self):
        self.temp.cleanup()

    def owned_installation(self):
        """Receipt-valid disposable installation; no dependencies or services."""
        root, home = self.root, self.root / "home"
        self.enterContext(patch.object(Path, "home", return_value=home))
        self.enterContext(patch.object(installer, "root_path", return_value=root))
        self.enterContext(patch.object(installer, "verify_payload", return_value={"source_revision": "a" * 40}))
        setup, learning = Mock(), Mock()
        setup.encode.side_effect = lambda value: json.dumps(value, indent=2) + "\n"
        learning.foreground.side_effect = lambda _: nullcontext()
        self.enterContext(patch.object(installer, "module", side_effect=lambda name: {"setup": setup, "learning": learning}[name]))
        self.enterContext(redirect_stdout(io.StringIO()))
        self.runtime_guard = self.enterContext(patch.object(installer, "guard_runtime"))
        directory = root / "client" / ("a" * 16)
        files = {"setup/opencode.template.json": "{}", "setup/install-profile.json": "{}",
                 "setup/runtime-profile.json": json.dumps({"global": {"owned": True}, "model": {"models": {}}}),
                 "setup/AGENTS.md": (SOURCE / "setup/AGENTS.md").read_text()}
        for name, text in files.items(): installer.atomic_write(directory / name, text.encode())
        receipt = {"directory": str(directory), "launcher": "#!/bin/sh\n# owned launcher\n",
                   "files": {name: installer.digest(directory / name) for name in files}}
        for path in installer.activation_paths(root): installer.atomic_write(path, b"{}")
        for path in installer.aliases(root): installer.atomic_write(path, receipt["launcher"].encode(), 0o700)
        installer.atomic_write(root / "client/deployment.json", json.dumps(receipt).encode())
        installer.atomic_write(root / "xdg/config/opencode/AGENTS.md", (files["setup/AGENTS.md"] +
                              f"\nIf installed, use {root}/artifacts/.venv/bin/python for document/data tasks.\n").encode())
        installer.atomic_write(home / ".omlx/settings.json", b'{"owned": true, "unrelated": "keep"}')
        installer.atomic_write(home / ".omlx/model_settings.json", b'{"models": {}}')
        installer.atomic_write(root / "packages/active.json", json.dumps({"schema": 1,
                              "payload_manifest_sha256": "same", "transaction": "unused"}).encode())
        for name in ("models/retained", "xdg/data/session", "cache/retained", "owner-session"):
            installer.atomic_write(root / name, b"private retained data")
        return setup, receipt

    def test_curated_stage_is_self_contained_and_corruption_is_detected(self):
        manifest = builder.stage(SOURCE, self.root, "a" * 40)
        base = self.root / "src/kryn/payload"
        self.assertGreater(len(installer.verify_payload(base, manifest)["files"]), 30)
        self.assertTrue((base / "tools/learning.py").is_file())
        self.assertTrue((base / "tools/kryn_plugin.mjs").is_file())
        self.assertTrue((base / "setup/accepted-profile.json").is_file())
        self.assertFalse(any("runs/" in name or name.endswith(".safetensors") or "test_kryn" in name for name in manifest["files"]))
        (base / "setup/opencode.template.json").write_text("{}")
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            installer.verify_payload(base, manifest)

    def test_transaction_recovers_failure_and_exact_rollback_preserves_user_changes(self):
        existing, new = self.root / "config.json", self.root / "launcher"
        existing.write_bytes(b"before"); existing.chmod(0o640)
        first = installer.Transaction(self.root / "failure", [existing, new])
        installer.atomic_write(existing, b"changed")
        installer.atomic_write(new, b"created", 0o700)
        first.restore()
        self.assertEqual(existing.read_bytes(), b"before")
        self.assertEqual(existing.stat().st_mode & 0o777, 0o640)
        self.assertFalse(new.exists())
        second = installer.Transaction(self.root / "success", [existing, new])
        installer.atomic_write(existing, b"release-two")
        installer.atomic_write(new, b"owned alias", 0o700)
        second.finish()
        installer.atomic_write(existing, b"user edit")
        with self.assertRaisesRegex(RuntimeError, "Preserving changed"):
            second.restore(require_after=True)
        self.assertEqual(new.read_bytes(), b"owned alias")
        self.assertEqual(json.loads((second.folder / "transaction.json").read_text())["status"], "committed")
        installer.atomic_write(existing, b"release-two")
        second.restore(require_after=True)
        self.assertEqual(existing.read_bytes(), b"before")
        self.assertFalse(new.exists())

    def test_interrupted_activation_recovers_only_before_or_planned_bytes(self):
        one, two = self.root / "one", self.root / "two"
        one.write_bytes(b"old")
        transaction = installer.Transaction(self.root / "interrupted", [one, two],
                                             {one: b"new", two: b"newly-created"})
        installer.atomic_write(one, b"new")
        installer.atomic_write(two, b"unrelated user edit")
        with self.assertRaisesRegex(RuntimeError, "unknown change"):
            transaction.restore(require_planned=True)
        self.assertEqual(one.read_bytes(), b"new")
        installer.atomic_write(two, b"newly-created")
        transaction.restore(require_planned=True)
        self.assertEqual(one.read_bytes(), b"old")
        self.assertFalse(two.exists())

    def test_interrupted_rollback_resumes_without_rolling_back_another_generation(self):
        learning = Mock()
        learning.foreground.side_effect = lambda _: nullcontext()
        count = len(installer.activation_paths(self.root))
        # Cut after the intent journal and after every restored activation file,
        # including active.json, which already selects the previous generation.
        for cut in range(-1, count):
            with self.subTest(cut=cut):
                root = self.root / str(cut)
                home = root / "home"
                folder = root / "packages/transactions/new"
                with patch.object(Path, "home", return_value=home), \
                        patch.object(installer, "root_path", return_value=root), \
                        patch.object(installer, "verify_payload", return_value={}), \
                        patch.object(installer, "module", side_effect=lambda name: {"learning": learning}[name]), \
                        patch.object(installer, "guard_runtime"):
                    paths = installer.activation_paths(root)
                    active = root / "packages/active.json"
                    before = {p: ("old-" + str(i)).encode() for i, p in enumerate(paths)}
                    before[active] = json.dumps({"transaction": str(folder.parent / "older")}).encode()
                    after = {p: ("new-" + str(i)).encode() for i, p in enumerate(paths)}
                    after[active] = json.dumps({"transaction": str(folder)}).encode()
                    for path, data in before.items(): installer.atomic_write(path, data)
                    transaction = installer.Transaction(folder, paths, after)
                    for path, data in after.items(): installer.atomic_write(path, data)
                    transaction.finish()
                    journal = folder / "transaction.json"
                    target = journal if cut == -1 else list(reversed(paths))[cut]
                    write = installer.atomic_write
                    def interrupt(path, *args, **kwargs):
                        write(path, *args, **kwargs)
                        if path == target: raise KeyboardInterrupt("simulated interruption")
                    with patch.object(installer, "atomic_write", side_effect=interrupt):
                        with self.assertRaises(KeyboardInterrupt): installer.rollback()
                    self.assertEqual(json.loads(journal.read_text())["status"], "rolling_back")
                    # A user edit during interruption blocks every recovery write.
                    previous = paths[0].read_bytes()
                    paths[0].write_bytes(b"unrelated user edit")
                    snapshot = {p: p.read_bytes() for p in paths}
                    with self.assertRaisesRegex(RuntimeError, "interrupted rollback"):
                        installer.rollback()
                    self.assertEqual({p: p.read_bytes() for p in paths}, snapshot)
                    self.assertEqual(json.loads(journal.read_text())["status"], "rolling_back")
                    paths[0].write_bytes(previous)
                    installer.rollback()
                    self.assertEqual({p: p.read_bytes() for p in paths}, before)
                    self.assertEqual(json.loads(journal.read_text())["status"], "rolled_back")

    def test_symlinks_hardlinks_and_corrupt_backups_fail_before_restore(self):
        target = self.root / "target"; target.write_bytes(b"safe")
        link = self.root / "link"; link.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, "Linked"):
            installer.Transaction(self.root / "symlink", [link])
        hard = self.root / "hard"; os.link(target, hard)
        with self.assertRaisesRegex(RuntimeError, "unowned"):
            installer.Transaction(self.root / "hardlink", [hard])
        hard.unlink()
        transaction = installer.Transaction(self.root / "backup", [target])
        installer.atomic_write(target, b"after")
        transaction.finish()
        (transaction.folder / "0").write_bytes(b"bad")
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            transaction.restore(require_after=True)
        self.assertEqual(target.read_bytes(), b"after")

    def test_preserve_unrelated_runtime_settings_and_reject_customized_owned_values(self):
        actual = {"server": {"port": 8000, "extension": True}, "private_extra": "keep"}
        old = {"server": {"port": 8000}}
        self.assertTrue(installer.contains_settings(actual, old))
        self.assertFalse(installer.contains_settings(actual, {"server": {"port": 1}}))
        result = installer.merge_settings(actual, {"server": {"port": 9000}})
        self.assertEqual(result, {"server": {"port": 9000, "extension": True}, "private_extra": "keep"})
        self.assertEqual(actual["server"]["port"], 8000)

    def test_unsupported_platform_refused_before_dependency_actions(self):
        with patch.object(installer.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(RuntimeError, "Apple Silicon"):
                installer.platform_check({"memory_gib": 8})

    def test_package_manifest_rejects_added_file_and_path_escape(self):
        manifest = builder.stage(SOURCE, self.root, "a" * 40)
        base = self.root / "src/kryn/payload"
        (base / "unexpected.txt").write_text("not shipped")
        with self.assertRaisesRegex(RuntimeError, "unexpected"):
            installer.verify_payload(base, manifest)
        manifest["files"]["../escape"] = "a" * 64
        with self.assertRaises(RuntimeError):
            installer.verify_payload(base, manifest)

    def test_bootstrap_downloads_publicly_without_using_account_credentials(self):
        wheel_bytes = b"synthetic-wheel"
        wheel_name = "kryn-0.1.0-py3-none-any.whl"
        sums = (hashlib.sha256(wheel_bytes).hexdigest() + "  " + wheel_name + "\n" +
                "a" * 64 + "  install-kryn.py\n").encode()
        base = "https://github.com/" + bootstrap.REPO + "/releases/download/v0.1.0/"
        seen = []
        def open_public(request, **kwargs):
            seen.append(request.full_url)
            self.assertIsNone(request.get_header("Authorization"))
            self.assertEqual(kwargs["timeout"], 60)
            return io.BytesIO(sums if request.full_url.endswith("SHA256SUMS") else wheel_bytes)
        opener = Mock(open=open_public)
        with patch.dict(os.environ, {"GH_TOKEN": "synthetic-secret", "GITHUB_TOKEN": "another-secret"}), \
                patch.object(bootstrap.urllib.request, "build_opener", return_value=opener):
            wheel, digest = bootstrap.public_release("v0.1.0", self.root)
        self.assertEqual(seen, [base + "SHA256SUMS", base + wheel_name])
        self.assertEqual(wheel.read_bytes(), wheel_bytes)
        self.assertEqual(digest, hashlib.sha256(wheel_bytes).hexdigest())
        corrupt = self.root / "corrupt"; corrupt.mkdir()
        def changed(request, **kwargs):
            return io.BytesIO(sums if request.full_url.endswith("SHA256SUMS") else b"changed-wheel")
        with patch.object(bootstrap.urllib.request, "build_opener", return_value=Mock(open=changed)):
            with self.assertRaisesRegex(RuntimeError, "checksum failed"):
                bootstrap.public_release("v0.1.0", corrupt)

    def test_bootstrap_rejects_insecure_release_redirects(self):
        request = bootstrap.urllib.request.Request("https://github.com/PranavMishra28/kryn")
        redirect = bootstrap.HTTPSReleaseRedirect()
        for target in ("http://github.com/file", "https://untrusted.invalid/file"):
            with self.subTest(target=target), self.assertRaisesRegex(RuntimeError, "trusted HTTPS"):
                redirect.redirect_request(request, None, 302, "Found", {}, target)

    def test_runtime_stop_uses_installed_profile_and_rejects_unrelated_or_busy(self):
        directory = self.root / "client" / ("a" * 16)
        tools = directory / "tools"; tools.mkdir(parents=True)
        stopped = self.root / "stopped"
        def write_client(identity, state):
            code = "from pathlib import Path\nMODEL_ID = 'old-installed-model'\n"
            code += "def runtime_identity():\n    " + identity + "\n"
            code += "def runtime_metadata():\n    assert MODEL_ID == 'old-installed-model'\n    return " + repr(state) + "\n"
            code += "def runtime_command(action):\n    Path(" + repr(str(stopped)) + ").write_text(action)\n"
            file = tools / "localai.py"; file.write_text(code)
            (directory.parent / "deployment.json").write_text(json.dumps({"directory": str(directory), "files": {"tools/localai.py": installer.digest(file)}}))
        with patch.object(installer.socket, "socket") as connection:
            connection.return_value.__enter__.return_value.connect_ex.return_value = 0
            for identity, state in (("raise RuntimeError('unrelated listener')", {}),
                                    ("return 123", {"active_requests": 1, "waiting_requests": 0}),
                                    ("return 123", {"active_requests": 0, "waiting_requests": False}),
                                    ("return 123", {})):
                write_client(identity, state)
                with self.assertRaises(subprocess.CalledProcessError):
                    installer.guard_runtime(self.root, stop=True)
                self.assertFalse(stopped.exists())
            write_client("return 123", {"active_requests": 0, "waiting_requests": 0})
            installer.guard_runtime(self.root, stop=False)
            self.assertFalse(stopped.exists())
            connection.return_value.__enter__.return_value.connect_ex.side_effect = [0, 61]
            installer.guard_runtime(self.root, stop=True)
            self.assertEqual(stopped.read_text(), "stop")

    def test_runtime_stop_acknowledgement_is_not_enough_for_activation(self):
        with patch.object(installer.socket, "socket") as connection, \
                patch.object(installer, "installed_client", return_value={"directory": str(self.root)}), \
                patch.object(installer.subprocess, "run") as child, \
                patch.object(installer.time, "monotonic", side_effect=[0, 16]), \
                patch.object(installer.time, "sleep") as sleep:
            connection.return_value.__enter__.return_value.connect_ex.return_value = 0
            with self.assertRaisesRegex(RuntimeError, "remains occupied"):
                installer.guard_runtime(self.root, stop=True)
            self.assertEqual(child.call_args.args[0][-1], "stop")
            sleep.assert_not_called()

    def test_same_package_rechecks_model_and_app_before_idempotent_success(self):
        root = self.root
        (root / "packages").mkdir()
        (root / "packages/active.json").write_text(json.dumps({"payload_manifest_sha256": "same"}))
        model = root / "model"; model.mkdir(); (model / "shard").write_text("model")
        setup = Mock()
        setup.load_profile.return_value = {"files": {"shard": "hash"}}
        setup.model_destination.return_value = (model, model / "marker", "marker")
        setup.plugin_files.return_value = {}
        learning = Mock()
        learning.foreground.side_effect = lambda _: nullcontext()
        original_is_dir = Path.is_dir
        with patch.object(installer, "verify_payload", return_value={}), \
                patch.object(installer, "module", side_effect=lambda name: {"setup": setup, "learning": learning}[name]), \
                patch.object(installer, "root_path", return_value=root), \
                patch.object(installer, "activation_paths", return_value=[root / "packages/active.json"]), \
                patch.object(installer, "platform_check"), patch.object(installer, "recover"), \
                patch.object(installer, "check_existing"), patch.object(installer, "digest", return_value="same"), \
                patch.object(installer, "verify_browser"), \
                patch.object(installer, "selected_node", return_value=Path(sys.executable)), \
                patch.object(installer.shutil, "which", return_value=sys.executable), \
                patch.object(Path, "is_dir", lambda p: str(p) == "/Applications/Google Chrome.app" or original_is_dir(p)), \
                patch.object(installer, "Transaction") as transaction:
            setup.download_model.side_effect = RuntimeError("changed model shard")
            with self.assertRaisesRegex(RuntimeError, "changed model shard"):
                installer.install()
            setup.install_app.assert_not_called()
            setup.download_model.side_effect = None
            installer.install()
            setup.install_app.assert_called_once()
            transaction.assert_not_called()

    def test_uninstall_preserves_data_and_modified_files_and_is_idempotent(self):
        setup, _ = self.owned_installation()
        paths = installer.activation_paths(self.root)
        original = {p: p.read_bytes() for p in paths}
        launcher = installer.aliases(self.root)[0]
        launcher.write_bytes(b"user change")
        with self.assertRaisesRegex(RuntimeError, "changed or unowned launcher"):
            installer.uninstall()
        self.runtime_guard.assert_not_called()
        self.assertEqual({p: p.read_bytes() for p in paths if p != launcher}, {p: v for p, v in original.items() if p != launcher})
        launcher.write_bytes(original[launcher])
        self.runtime_guard.side_effect = RuntimeError("busy runtime")
        with self.assertRaisesRegex(RuntimeError, "busy runtime"): installer.uninstall()
        self.assertEqual({p: p.read_bytes() for p in paths}, original)
        self.runtime_guard.reset_mock(side_effect=True)
        retained = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file() and p not in paths}
        installer.uninstall()
        self.runtime_guard.assert_called_once_with(self.root, stop=True)
        self.assertFalse(any(p.exists() for p in installer.aliases(self.root)))
        active = self.root / "packages/active.json"
        self.assertTrue(json.loads(active.read_text())["deactivated"])
        for path in paths:
            if path not in installer.aliases(self.root) and path != active:
                self.assertEqual(path.read_bytes(), original[path])
        for path, data in retained.items(): self.assertEqual(path.read_bytes(), data)
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        installer.uninstall()
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before)
        self.assertEqual(self.runtime_guard.call_count, 1)

    def test_interrupted_deactivation_recovers_removed_launchers(self):
        self.owned_installation()
        paths = installer.activation_paths(self.root)
        original = {p: p.read_bytes() for p in paths}
        active = self.root / "packages/active.json"
        write = installer.atomic_write
        def interrupt(path, *args, **kwargs):
            if path == active: raise KeyboardInterrupt("simulated termination after launcher removal")
            write(path, *args, **kwargs)
        # A killed process cannot execute the exception cleanup. Retain its
        # prepared journal, then exercise normal recovery in a fresh call.
        with patch.object(installer, "atomic_write", side_effect=interrupt), \
                patch.object(installer.Transaction, "restore", side_effect=KeyboardInterrupt("process gone")):
            with self.assertRaises(KeyboardInterrupt): installer.uninstall()
        self.assertFalse(any(p.exists() for p in installer.aliases(self.root)))
        installer.recover(self.root)
        self.assertEqual({p: p.read_bytes() for p in paths}, original)

    def test_rollback_recovers_prepared_upgrade_without_removing_incumbent(self):
        self.owned_installation()
        paths = installer.activation_paths(self.root)
        active = self.root / "packages/active.json"
        older = self.root / "packages/transactions/100-installed"
        newer = older.with_name("200-interrupted-upgrade")
        incumbent = {p: p.read_bytes() for p in paths}
        incumbent[active] = json.dumps({"schema": 1, "transaction": str(older)}).encode()
        for path in paths: path.unlink()
        installed = installer.Transaction(older, paths, incumbent)
        for path, data in incumbent.items(): installer.atomic_write(path, data)
        installed.finish()
        upgrade = {**incumbent, paths[0]: b"new config", active: json.dumps({"transaction": str(newer)}).encode()}
        installer.Transaction(newer, paths, upgrade)
        installer.atomic_write(paths[0], upgrade[paths[0]])
        installer.atomic_write(active, upgrade[active])
        installer.rollback()
        self.assertEqual({p: p.read_bytes() for p in paths}, incumbent)
        self.assertEqual(json.loads((older / "transaction.json").read_text())["status"], "committed")
        self.assertEqual(json.loads((newer / "transaction.json").read_text())["status"], "rolled_back")

    def test_same_package_repairs_missing_activation_and_reactivates(self):
        setup, receipt = self.owned_installation()
        setup.load_profile.return_value = {"files": {"shard": "hash"}}
        model = self.root / "model"; model.mkdir(); (model / "shard").write_bytes(b"model")
        setup.model_destination.return_value = (model, model / "marker", "marker")
        setup.plugin_files.return_value = {}
        setup.render.return_value = {}
        setup.runtime_settings.return_value = {"owned": True}
        setup.model_settings.return_value = {"models": {}}
        original_digest, original_is_dir = installer.digest, Path.is_dir
        def digest(path):
            return "same" if Path(path) == Path(installer.__file__).parent / "manifest.json" else original_digest(path)
        def deploy(*_, **__):
            installer.atomic_write(self.root / "client/deployment.json", (json.dumps(receipt, indent=2) + "\n").encode())
            for path in installer.aliases(self.root): installer.atomic_write(path, receipt["launcher"].encode(), 0o700)
        # Use real receipt checks and activation transactions; dependencies and
        # the separately tested deployment subprocess are disposable stand-ins.
        with patch.object(installer, "platform_check"), patch.object(installer, "payload", return_value=SOURCE), \
                patch.object(installer, "digest", side_effect=digest), \
                patch.object(installer, "selected_node", return_value=Path(sys.executable)), \
                patch.object(installer.shutil, "which", return_value=sys.executable), \
                patch.object(Path, "is_dir", lambda p: str(p) == "/Applications/Google Chrome.app" or original_is_dir(p)), \
                patch.object(installer, "verify_browser"), \
                patch.object(installer.subprocess, "check_output", return_value=json.dumps(receipt)), \
                patch.object(installer.subprocess, "run", side_effect=deploy) as applied:
            for missing in (installer.aliases(self.root)[-1], self.root / "xdg/config/opencode/AGENTS.md"):
                missing.unlink()
                installer.install()
                self.assertTrue(missing.is_file())
            self.assertEqual(applied.call_count, 2)
            installer.uninstall()
            installer.install()
            self.assertTrue(all(p.is_file() for p in installer.activation_paths(self.root)))
            self.assertNotIn("deactivated", json.loads((self.root / "packages/active.json").read_text()))
            self.assertEqual(applied.call_count, 3)
            installer.install()
            self.assertEqual(applied.call_count, 3)

    def test_package_cli_uninstall_rejects_extra_arguments_before_mutation(self):
        with patch.object(cli, "uninstall") as remove, patch.object(sys, "argv", ["kryn", "uninstall", "--purge"]):
            with self.assertRaisesRegex(SystemExit, "Usage: kryn uninstall"): cli.main()
            remove.assert_not_called()
        with patch.object(cli, "uninstall") as remove, patch.object(sys, "argv", ["kryn", "uninstall"]):
            cli.main()
            remove.assert_called_once()

    def test_recovery_stops_only_verified_idle_runtime_before_restoring_settings(self):
        folder = self.root / "packages/transactions/interrupted"
        folder.mkdir(parents=True); (folder / "transaction.json").write_text("{}")
        transaction = Mock()
        order = []
        with patch.object(installer, "load_transaction", return_value=(transaction, "prepared")), \
                patch.object(installer, "guard_runtime", side_effect=RuntimeError("busy runtime")) as guard:
            with self.assertRaisesRegex(RuntimeError, "busy runtime"):
                installer.recover(self.root)
            guard.assert_called_once_with(self.root, stop=True)
            transaction.restore.assert_not_called()
            guard.side_effect = lambda *_, **__: order.append("verified-and-stopped")
            transaction.restore.side_effect = lambda **_: order.append("restored")
            installer.recover(self.root)
            self.assertEqual(order, ["verified-and-stopped", "restored"])

    def test_existing_browser_is_publisher_compared_then_receipt_checked_without_overwrite(self):
        lock = SOURCE / "setup/browser-package-lock.json"
        def npm(destination, *_):
            base = destination / "browser"
            package = base / "node_modules/@playwright/mcp/package.json"
            package.parent.mkdir(parents=True)
            package.write_text('{"version": "0.0.82"}')
            (package.parent / "cli.js").write_text("original publisher JS")
            (base / "package-lock.json").write_bytes(lock.read_bytes())
            (base / "node_modules/.bin").mkdir()
            (base / "node_modules/.bin/mcp").symlink_to("../@playwright/mcp/cli.js")
        npm(self.root)
        setup = Mock(); setup.npm_install.side_effect = npm
        with patch.object(installer, "payload", return_value=SOURCE):
            with self.assertRaisesRegex(RuntimeError, "Existing browser integrity receipt"):
                installer.verify_browser(self.root, setup, adopt=False)
            setup.npm_install.assert_not_called()
            receipt = installer.verify_browser(self.root, setup, Path("/test/node"), {})
            setup.npm_install.assert_called_once()
            data = json.loads(receipt.read_text())
            self.assertEqual(data["files"][".bin/mcp"], ["link", "../@playwright/mcp/cli.js"])
            installer.verify_browser(self.root, setup, Path("/test/node"), {})
            self.assertEqual(setup.npm_install.call_count, 1)
            self.assertEqual(installer.verify_browser(self.root, adopt=False), receipt)
            script = self.root / "browser/node_modules/@playwright/mcp/cli.js"
            script.write_text("changed local script")
            with self.assertRaisesRegex(RuntimeError, "integrity receipt"):
                installer.verify_browser(self.root, setup, Path("/test/node"), {})
            with self.assertRaisesRegex(RuntimeError, "integrity receipt"):
                installer.verify_browser(self.root, adopt=False)
            receipt.unlink()
            with self.assertRaisesRegex(RuntimeError, "original-publisher comparison"):
                installer.verify_browser(self.root, setup, Path("/test/node"), {})
            self.assertEqual(script.read_text(), "changed local script")
            self.assertFalse(receipt.exists())

    def test_browser_read_only_verification_never_installs_missing_tree(self):
        receipt = self.root / "browser/integrity.json"
        receipt.parent.mkdir(); receipt.write_text("{}")
        setup = Mock()
        with self.assertRaisesRegex(RuntimeError, "read-only verification cannot reinstall"):
            installer.verify_browser(self.root, setup, adopt=False)
        setup.npm_install.assert_not_called()
        self.assertEqual(receipt.read_text(), "{}")
        self.assertFalse((receipt.parent / "node_modules").exists())

    def test_browser_inventory_rejects_external_links(self):
        tree = self.root / "node_modules"; tree.mkdir()
        (tree / "escape").symlink_to("../private-data")
        with self.assertRaisesRegex(RuntimeError, "leaves"):
            installer.browser_inventory(tree)


if __name__ == "__main__":
    unittest.main()
