#!/usr/bin/env python3
"""Validate a storyboard JSON against schemas/storyboard.schema.json.

Usage: validate_storyboard.py storyboard.json [--max-scenes N]
Exit 0 = valid, 1 = invalid (errors on stderr).
"""
import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "storyboard.schema.json"


def validate(data: dict, max_scenes: int | None = None) -> list[str]:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
    errors = [e.message for e in validator.iter_errors(data)]
    if max_scenes and len(data.get("scenes", [])) > max_scenes:
        errors.append(f"too many scenes (> {max_scenes})")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--max-scenes", type=int)
    args = ap.parse_args()
    errors = validate(json.loads(Path(args.path).read_text()), args.max_scenes)
    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
