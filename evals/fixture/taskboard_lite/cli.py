import argparse
import json
from pathlib import Path
from .parse import parse_rows
from .report import summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("summary", "validate"))
    parser.add_argument("csv", type=Path)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--project")
    args = parser.parse_args()
    try:
        rows = parse_rows(args.csv.read_text(encoding="utf-8"))
        result = rows if args.command == "validate" else summarize(rows, args.start, args.end, args.project)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
