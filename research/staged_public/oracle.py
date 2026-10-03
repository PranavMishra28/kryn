"""Trusted post-generation oracle for the public staged development task."""
import importlib.util
from pathlib import Path
import sys


workspace = Path(sys.argv[1]).resolve()


def load(name):
    spec = importlib.util.spec_from_file_location(name, workspace / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Tracker = load("tracker").Tracker
parse_legacy_id = load("legacy").parse_legacy_id
tracker = Tracker()
assert tracker.add(" alpha ") == 1
assert tracker.add("beta") == 2
try:
    tracker.add("  ")
except ValueError:
    pass
else:
    raise AssertionError("Blank title accepted")
assert tracker.add("gamma") == 3
listed = tracker.list_items()
assert listed == [
    {"id": 1, "title": "alpha", "done": False},
    {"id": 2, "title": "beta", "done": False},
    {"id": 3, "title": "gamma", "done": False},
]
listed[0]["title"] = "tampered"
listed.append({"id": 999, "title": "bad", "done": True})
assert tracker.list_items()[0]["title"] == "alpha"
assert len(tracker.list_items()) == 3
before = tracker.snapshot()
assert before == ((1, "alpha", False), (2, "beta", False), (3, "gamma", False))
assert tracker.complete(2) is True
assert tracker.complete(2) is False
assert tracker.snapshot() == ((1, "alpha", False), (2, "beta", True), (3, "gamma", False))
assert before == ((1, "alpha", False), (2, "beta", False), (3, "gamma", False))
try:
    tracker.complete(999)
except KeyError:
    pass
else:
    raise AssertionError("Unknown ID accepted")
assert parse_legacy_id("12") == 12
assert parse_legacy_id(" #12 ") == 12
for bad in ("", "#", "0", "-1", "#-1", "2x", "# 3"):
    try:
        parse_legacy_id(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid legacy ID accepted: " + repr(bad))
print("staged_public_oracle_passed")
