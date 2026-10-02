"""Behavioral checks for control matching across disposable trial paths."""
import json
from pathlib import Path
import tempfile
import unittest

from compare_pair import effective_permissions


class EffectivePermissionsTest(unittest.TestCase):
    def inventory(self, root, name, *, effect="allow", candidate=False):
        run = root / name
        folder = run / "evidence/attempt1"
        config = (folder / "candidate-inputs/config" if candidate
                  else run / "trial-inputs/frozen/config")
        config.mkdir(parents=True)
        folder.mkdir(parents=True, exist_ok=True)
        permissions = [
            {"action": "external_directory", "effect": "allow",
             "resource": str(run / "workspace/.localai-tmp-x_42/opencode/*")},
            {"action": "external_directory", "effect": effect,
             "resource": str(config / "*")},
        ]
        (folder / "agent-inventory.json").write_text(
            json.dumps({"data": [{"id": "build", "permissions": permissions}]}))
        return run, folder

    def test_random_paths_do_not_change_effective_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = self.inventory(root, "native", candidate=False)
            b = self.inventory(root, "kryn", candidate=True)
            self.assertEqual(effective_permissions(*a), effective_permissions(*b))

    def test_permission_change_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = self.inventory(root, "native", candidate=False)
            b = self.inventory(root, "kryn", effect="deny", candidate=True)
            self.assertNotEqual(effective_permissions(*a), effective_permissions(*b))


if __name__ == "__main__":
    unittest.main()
