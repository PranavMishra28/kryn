import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run_external_patch as runner


class CandidatePluginLoaderTest(unittest.TestCase):
    def test_exact_source_payload_and_kryn_only_override(self):
        with tempfile.TemporaryDirectory(prefix="kryn-candidate-plugin-") as folder:
            root = Path(folder)
            source = root / "source"
            tools = source / "tools"
            tools.mkdir(parents=True)
            files = {"kryn_plugin.mjs": b"export default {id:'fixture'};\n",
                     "kryn_tui.tsx": b"export default function Fixture() {}\n",
                     "permission_display.mjs": b"export const label = 'fixture';\n",
                     "update_notice.mjs": b"export const notice = 'fixture';\n"}
            for name, data in files.items():
                (tools / name).write_bytes(data)
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "tools"], check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Test",
                            "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)
            evidence = root / "evidence"
            evidence.mkdir()
            package, hashes = runner.candidate_plugin_package(source, evidence)
            self.assertEqual(set(hashes), {"server.js", "tui.tsx", "permission_display.mjs",
                                           "update_notice.mjs", "package.json"})
            self.assertEqual((package / "server.js").read_bytes(), files["kryn_plugin.mjs"])
            self.assertEqual(hashes["server.js"], hashlib.sha256(files["kryn_plugin.mjs"]).hexdigest())
            config = {"plugins": [{"package": "/installed/plugin", "options": {
                "profileId": "fixture", "nodeBinary": "/usr/bin/node"}}],
                "mcp": {"servers": {}}, "skills": [], "permissions": [],
                "providers": {"local": {"settings": {}, "models": {"qwen": {
                    "settings": {}, "variants": []}}}}}
            with patch.object(runner, "owned_config", return_value=config), \
                 patch.object(runner.learning, "python_dependencies", return_value=[]):
                result, products, dependencies = runner.configuration(
                    source, root, "kryn", "http://127.0.0.1:43210/v1",
                    candidate_package=package)
            self.assertEqual(result["plugins"][0]["package"], str(package))
            self.assertEqual(products[0]["package"], str(package))
            self.assertIn(package.resolve(), dependencies)
            self.assertEqual(config["plugins"][0]["package"], "/installed/plugin")
            with self.assertRaisesRegex(ValueError, "Native OpenCode"):
                runner.run(type("Args", (), {"candidate_product_source": True,
                                               "arm": "native"})())
            (tools / "kryn_plugin.mjs").write_text("changed")
            with self.assertRaisesRegex(ValueError, "clean checkout"):
                runner.candidate_plugin_package(source, root / "unused")


if __name__ == "__main__":
    unittest.main()
