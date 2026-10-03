#!/usr/bin/env python3
"""No-model Mac Seatbelt smoke for the plugin's Git and syntax observations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_client import background_boundary  # noqa: E402


NODE_SMOKE = r"""
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import plugin from './plugin.mjs';
const workspace = process.cwd(), privateDir = process.argv[2], node = process.execPath;
const hash = text => createHash('sha256').update(text).digest('hex');
const hooks = new Map();
const domain = prefix => ({ hook: async (name, callback) => hooks.set(prefix + '.' + name, callback) });
const ctx = { location: { directory: workspace, project: { canonical: workspace } },
  options: { stateDir: privateDir, profileId: 'git-smoke', modelID: 'test-Q4',
    champion: { instructions: '', revision: hash('') }, nodeBinary: node },
  session: { ...domain('session'), context: async () => [] },
  tool: domain('tool'), permission: domain('permission'),
  event: { async *subscribe({ signal }) {
    await new Promise(resolve => signal.addEventListener('abort', resolve, { once: true }));
  } } };
const stop = await plugin.setup(ctx);
try {
  hooks.get('session.prompt')({ sessionID: 'ses_smoke', prompt: { text: 'Inspect the Python file.' } });
  const compaction = { sessionID: 'ses_smoke', agent: 'agent', system: [] };
  await hooks.get('session.compaction')(compaction);
  const gitSnapshot = compaction.system.some(part => part.text?.includes('Current repository observation'));
  const call = (id) => {
    const event = { sessionID: 'ses_smoke', messageID: 'msg_' + id, id: 'call_' + id,
      agent: 'agent', tool: 'shell', input: { command: 'python3 -B app.py' },
      status: 'completed', result: { output: { exit: 0, status: 'completed', output: '' },
        content: [{ type: 'text', text: 'Command exited with code 0.' }] } };
    hooks.get('tool.execute.after')(event);
    return event.result.content.map(part => part.text).join('\n');
  };
  const pythonWarning = /could not inspect every changed JavaScript file/.test(call('python'));
  fs.writeFileSync(path.join(workspace, 'broken.js'), 'const = ;\n');
  const jsFeedback = /JavaScript syntax check failed/.test(call('js'));
  console.log(JSON.stringify({ git_snapshot: gitSnapshot, python_warning: pythonWarning,
    js_feedback: jsFeedback }));
} finally { await stop(); }
"""


def run(plugin_bytes: bytes, label: str, node: Path, git: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="kryn-git-evidence-", dir="/private/tmp") as folder:
        root = Path(folder).resolve()
        workspace, private = root / "workspace", root / "private"
        workspace.mkdir(mode=0o700)
        private.mkdir(mode=0o700)
        (workspace / "app.py").write_text("print('base')\n")
        subprocess.run([str(git), "init", "-q", str(workspace)], check=True)
        subprocess.run([str(git), "-C", str(workspace), "add", "app.py"], check=True)
        subprocess.run([str(git), "-C", str(workspace), "-c", "user.name=KRYN Research",
                        "-c", "user.email=research@localhost", "commit", "-qm", "seed"], check=True)
        (workspace / "app.py").write_text("print('changed')\n")
        (workspace / "plugin.mjs").write_bytes(plugin_bytes)
        (workspace / "smoke.mjs").write_text(NODE_SMOKE)
        prefix = background_boundary(workspace, private, [node, git], None)
        completed = subprocess.run(prefix + [str(node), "smoke.mjs", str(private)],
                                   cwd=workspace, env={**os.environ, "TMPDIR": str(private),
                                   "TMP": str(private), "TEMP": str(private), "HOME": str(workspace),
                                   "GIT_CONFIG_NOSYSTEM": "1"}, capture_output=True,
                                   text=True, timeout=30)
        lines = completed.stdout.splitlines()
        try:
            observation = json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError):
            observation = None
        return {"arm": label, "plugin_sha256": hashlib.sha256(plugin_bytes).hexdigest(),
                "exit": completed.returncode, "observation": observation,
                "stderr": completed.stderr[-1000:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--node-binary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    node = args.node_binary.resolve()
    git = Path("/Library/Developer/CommandLineTools/usr/bin/git")
    if sys.platform != "darwin" or not node.is_file() or not git.is_file():
        parser.error("This screen requires macOS, Node and installed Command Line Tools Git")
    baseline = subprocess.check_output([str(git), "-C", str(root), "show",
        args.baseline_commit + ":tools/kryn_plugin.mjs"])
    candidate = (root / "tools/kryn_plugin.mjs").read_bytes()
    result = {"schema": 1, "kind": "direct_git_evidence_no_model_screen",
              "baseline_commit": args.baseline_commit,
              "candidate_commit": subprocess.check_output([str(git), "-C", str(root),
                  "rev-parse", "HEAD"], text=True).strip(),
              "node_sha256": hashlib.sha256(node.read_bytes()).hexdigest(),
              "git_sha256": hashlib.sha256(git.read_bytes()).hexdigest(),
              "arms": [run(baseline, "baseline", node, git),
                       run(candidate, "candidate", node, git)]}
    expected = {"git_snapshot": True, "python_warning": False, "js_feedback": True}
    baseline_observed, candidate_observed = (arm["observation"] for arm in result["arms"])
    result["passed"] = (baseline_observed is not None and
        (not baseline_observed["git_snapshot"] or baseline_observed["python_warning"]) and
        candidate_observed == expected and result["arms"][1]["exit"] == 0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "arms": result["arms"]}, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
