"""Run full planner workflow (requires langgraph optional dependency)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cmp.models.schemas import ClientIntake, EngagementRecord
from cmp.storage.engagement_store import EngagementStore
from cmp.workflows.planner_graph import run_planner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run full crisis management planner workflow")
    parser.add_argument("--engagement", required=True)
    parser.add_argument("--input", required=True, help="Path to intake JSON")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    intake = ClientIntake.model_validate(json.loads(input_path.read_text(encoding="utf-8")))
    store = EngagementStore()
    if store.get_engagement(args.engagement) is None:
        store.upsert_engagement(
            EngagementRecord(
                engagement_id=args.engagement,
                client_name=intake.company_name,
                industry=intake.industry,
            )
        )

    try:
        result = run_planner(args.engagement, intake)
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps({k: v for k, v in result.items() if k != "intake"}, indent=2, default=str))
    if result.get("status") == "blocked_readiness_gate":
        print(f"\nBlocked: {result.get('error')}", file=sys.stderr)
        return 2
    if result.get("deliverable_paths"):
        print("\nDeliverables written:", file=sys.stderr)
        for name, path in result["deliverable_paths"].items():
            print(f"  {name}: {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
