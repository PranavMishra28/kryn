import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import owner_auth as auth


class OwnerSessionTests(unittest.TestCase):
    def test_owner_offline_expiry_logout_and_revocation(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"GH_CONFIG_DIR": folder}, clear=True), patch.object(auth.shutil, "which", return_value="/test/gh"):
            folder = str(Path(folder).resolve())
            path = Path(folder) / "owner.json"
            def github(args, **_):
                value = {"hosts": {"github.com": [{"active": True, "state": "success", "tokenSource": "keyring"}]}} if "status" in args else {"id": auth.OWNER_ID, "login": auth.OWNER_LOGIN, "type": "User"}
                return subprocess.CompletedProcess(args, 0, json.dumps(value), "")
            with self.assertRaises(auth.AuthorizationError):
                auth.authorize(path, 100)
            auth.login(path, 100, github)
            self.assertEqual(auth.authorize(path, 101)["owner_id"], auth.OWNER_ID)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(auth.AuthorizationError):
                auth.authorize(path, 100 + auth.TTL_SECONDS)
            with self.assertRaises(auth.AuthorizationError):
                auth.login(path, 102, lambda args, **_: subprocess.CompletedProcess(args, 1, "private diagnostic", "private diagnostic"))
            self.assertFalse(path.exists())
            auth.login(path, 103, github)
            auth.logout(path)
            self.assertFalse(path.exists())
            for malformed in ('[]', '{broken'):
                path.write_text(malformed)
                path.chmod(0o600)
                with self.assertRaises(auth.AuthorizationError):
                    auth.authorize(path, 104)
                auth.logout(path)  # Safe recovery must not require parseable cache content.
                self.assertFalse(path.exists())

    def test_nonowner_plaintext_environment_and_symlink_denied(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"GH_CONFIG_DIR": folder}, clear=True), patch.object(auth.shutil, "which", return_value="/test/gh"):
            folder = str(Path(folder).resolve())
            path = Path(folder) / "owner.json"
            def other(args, **_):
                value = {"hosts": {"github.com": [{"active": True, "state": "success", "tokenSource": "keyring"}]}} if "status" in args else {"id": 1, "type": "User"}
                return subprocess.CompletedProcess(args, 0, json.dumps(value), "")
            with self.assertRaisesRegex(auth.AuthorizationError, "only the verified repository owner"):
                auth.login(path, 100, other)
            with patch.dict(os.environ, {"GH_TOKEN": "synthetic-canary"}):
                with self.assertRaisesRegex(auth.AuthorizationError, "environment overrides"):
                    auth.login(path, 100, other)
            (Path(folder) / "hosts.yml").write_text("github.com:\n  oauth_token: synthetic-canary\n")
            with self.assertRaisesRegex(auth.AuthorizationError, "Plaintext"):
                auth.login(path, 100, other)
            target = Path(folder) / "untouched"; target.write_text("preserve")
            path.symlink_to(target)
            with self.assertRaises(auth.AuthorizationError):
                auth.logout(path)
            self.assertEqual(target.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
