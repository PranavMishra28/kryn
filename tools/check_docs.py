"""Check repository entry points and local Markdown link destinations."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ("AGENTS.md", "CONTRIBUTING.md", "plan.md", "README.md", "SECURITY.md", "evals/README.md")
REQUIRED = ("AGENTS.md", "CONTRIBUTING.md", "plan.md", "README.md", "SECURITY.md", "Makefile")
errors = []
for name in REQUIRED:
    if not (ROOT / name).is_file():
        errors.append(f"Missing repository entry point: {name}")
for name in DOCS:
    file = ROOT / name
    if not file.is_file():
        continue
    for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", file.read_text()):
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        destination = (file.parent / unquote(parsed.path)).resolve()
        if not destination.is_relative_to(ROOT) or not destination.exists():
            errors.append(f"{name}: broken local link {target}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"Checked {len(DOCS)} documentation entry points and local links")
