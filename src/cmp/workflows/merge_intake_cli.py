"""Merge consultant answers into engagement intake."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cmp.storage.engagement_store import EngagementStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge fields into engagement intake")
    parser.add_argument("--engagement", required=True)
    parser.add_argument(
        "--updates",
        required=True,
        help="JSON file with field updates (top-level or additional_context keys)",
    )
    parser.add_argument(
        "--resolve",
        nargs="*",
        default=[],
        help="Requirement IDs to mark as resolved",
    )
    args = parser.parse_args(argv)

    updates_path = Path(args.updates)
    if not updates_path.exists():
        print(f"Updates file not found: {updates_path}", file=sys.stderr)
        return 1

    updates = json.loads(updates_path.read_text(encoding="utf-8"))
    store = EngagementStore()
    try:
        merged = store.merge_intake(args.engagement, updates)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.resolve:
        store.mark_resolved(args.engagement, args.resolve)

    print(json.dumps(merged.model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
