"""Isolated package/transaction checks; no model, services or home activation."""
import hashlib
from contextlib import nullcontext
import importlib.util
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
from kryn import installer
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

    def test_bootstrap_owner_policy_precedes_private_release_access(self):
        status = {"hosts": {"github.com": [{"active": True, "state": "success", "tokenSource": "keyring"}]}}
        responses = [status, {"id": 90290458, "type": "User"}, {"isPrivate": True}]
        def github(args, **kwargs):
            self.assertTrue(kwargs["capture_output"])
            return subprocess.CompletedProcess(args, 0, json.dumps(responses.pop(0)), "")
        with patch.dict(os.environ, {"GH_CONFIG_DIR": str(self.root)}, clear=True), patch.object(bootstrap.subprocess, "run", side_effect=github) as runner:
            bootstrap.secure_owner("/test/gh")
            self.assertEqual(runner.call_count, 3)
            responses[:] = [status, {"id": 1, "type": "User"}]
            runner.reset_mock()
            with self.assertRaisesRegex(RuntimeError, "only the verified"):
                bootstrap.secure_owner("/test/gh")
            self.assertEqual(runner.call_count, 2)
            self.assertFalse(any("release" in call.args[0] for call in runner.call_args_list))
            (self.root / "hosts.yml").write_text("github.com:\n  oauth_token: synthetic-secret\n")
            runner.reset_mock()
            with self.assertRaisesRegex(RuntimeError, "Plaintext"):
                bootstrap.secure_owner("/test/gh")
            runner.assert_not_called()

    def test_bootstrap_auth_failures_do_not_relay_captured_secrets(self):
        with patch.dict(os.environ, {"GH_CONFIG_DIR": str(self.root)}, clear=True):
            for result in (subprocess.CompletedProcess([], 1, "synthetic-secret", "synthetic-secret"),
                           subprocess.CompletedProcess([], 0, '["synthetic-secret"]', ""),
                           subprocess.CompletedProcess([], 0, '{"hosts": []}', "")):
                with patch.object(bootstrap.subprocess, "run", return_value=result):
                    with self.assertRaises(RuntimeError) as raised:
                        bootstrap.secure_owner("/test/gh")
                    self.assertNotIn("synthetic-secret", str(raised.exception))
            with patch.object(bootstrap.subprocess, "run", side_effect=subprocess.TimeoutExpired([], 30, "synthetic-secret")):
                with self.assertRaises(RuntimeError) as raised:
                    bootstrap.secure_owner("/test/gh")
                self.assertNotIn("synthetic-secret", str(raised.exception))

    def test_bootstrap_token_environment_denied_before_auth_or_download(self):
        with patch.dict(os.environ, {"GH_TOKEN": "synthetic-secret"}, clear=True), \
                patch.object(sys, "argv", ["install-kryn.py", "--tag", "v0.1.0"]), \
                patch.object(bootstrap.platform, "system", return_value="Darwin"), \
                patch.object(bootstrap.platform, "machine", return_value="arm64"), \
                patch.object(bootstrap.shutil, "which", return_value="/test/gh"), \
                patch.object(bootstrap.subprocess, "run") as runner:
            with self.assertRaisesRegex(RuntimeError, "environment"):
                bootstrap.main()
            runner.assert_not_called()

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
        auth, learning = Mock(), Mock()
        learning.foreground.side_effect = lambda _: nullcontext()
        original_is_dir = Path.is_dir
        with patch.object(installer, "verify_payload", return_value={}), \
                patch.object(installer, "module", side_effect=lambda name: {"setup": setup, "owner_auth": auth, "learning": learning}[name]), \
                patch.object(installer, "root_path", return_value=root), \
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
