"""Prepare explicitly simulated analyst projections; never creates human feedback."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.config import Settings
from backend.projected_reviews import prepare
from backend.repository import Repository

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = prepare(Repository(Settings.load()), apply=args.apply)
    print(json.dumps(result, indent=2))
