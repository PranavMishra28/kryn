"""Frozen public development fixture for the three-stage local-model screen."""
import json
import re

SEED = '''import json
import sys

if __name__ == "__main__":
    json.load(sys.stdin)
    print(json.dumps({"error": "missing"}))
'''
REFERENCE = '''import json
import re
import sys
from pathlib import Path

def normalize(text):
    return text.strip().casefold()

def slug(text):
    separator = json.loads(Path("rules.json").read_text())["separator"]
    return re.sub(r"\\s+", separator, normalize(text))

def solve(request):
    if request["op"] == "normalize":
        return {"value": normalize(request["text"])}
    if request["op"] == "slug":
        return {"value": slug(request["text"])}
    if request["op"] == "unique":
        separator = json.loads(Path("rules.json").read_text())["separator"]
        seen, values = set(), []
        for text in request["items"]:
            base = slug(text)
            value, number = base, 2
            while value in seen:
                value = base + separator + str(number)
                number += 1
            seen.add(value)
            values.append(value)
        return {"values": values}
    raise ValueError("unknown op")

if __name__ == "__main__":
    print(json.dumps(solve(json.load(sys.stdin))))
'''
PROMPTS = [
    'Read solve.py and rules.json first. Implement the normalize operation: input {"op":"normalize","text":string}; output {"value": text.strip().casefold()}. Preserve internal whitespace. Keep JSON stdin/stdout. Run a relevant check before declaring completion.',
    'Continue the same task. Add the slug operation: input {"op":"slug","text":string}; output {"value":normalized text with every maximal Unicode-whitespace run replaced by the current separator from rules.json}. Preserve punctuation. Keep normalize working. Read the current files and run a relevant check.',
    'The tracked rules.json was changed by the task owner after your previous turn. Read it again before editing. Add the unique operation: input {"op":"unique","items":[strings]}; output {"values":[unique slugs in input order]}. Form each base slug with the current separator; on collisions append that separator and the smallest integer starting at 2 that is not already used. Preserve normalize and slug, including their current-rule behavior. Run a relevant check.',
]
CASES = [
    [
        {"input": {"op": "normalize", "text": "  MiXeD  "}, "expected": {"value": "mixed"}},
        {"input": {"op": "normalize", "text": "  Café \tNOIR "}, "expected": {"value": "café \tnoir"}},
        {"input": {"op": "normalize", "text": "Straße"}, "expected": {"value": "strasse"}},
    ],
    [
        {"input": {"op": "slug", "text": "  A\t B  C  "}, "expected": {"value": "a-b-c"}},
        {"input": {"op": "slug", "text": ""}, "expected": {"value": ""}},
        {"input": {"op": "slug", "text": " A+B! "}, "expected": {"value": "a+b!"}},
    ],
    [
        {"input": {"op": "slug", "text": "  A\t B  C  "}, "expected": {"value": "a_b_c"}},
        {"input": {"op": "slug", "text": ""}, "expected": {"value": ""}},
        {"input": {"op": "slug", "text": " A+B! "}, "expected": {"value": "a+b!"}},
        {"input": {"op": "unique", "items": [" A B ", "a\tb", "a_b_2", "A B", "Z"]},
         "expected": {"values": ["a_b", "a_b_2", "a_b_2_2", "a_b_3", "z"]}},
        {"input": {"op": "unique", "items": []}, "expected": {"values": []}},
        {"input": {"op": "unique", "items": ["A+B", "a+b"]},
         "expected": {"values": ["a+b", "a+b_2"]}},
    ],
]


def oracle(stage):
    """Return cumulative, independently specified cases for the given stage."""
    if stage not in {1, 2, 3}:
        raise ValueError("stage must be 1, 2 or 3")
    groups = CASES[:stage] if stage < 3 else [CASES[0], CASES[2]]
    return [item for group in groups for item in group]


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
