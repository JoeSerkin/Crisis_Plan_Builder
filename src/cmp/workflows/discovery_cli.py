"""CLI entrypoint for Client Discovery Agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cmp.agents.discovery import run_discovery
from cmp.models.schemas import ClientIntake, EngagementRecord
from cmp.storage.engagement_store import EngagementStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Client Discovery Agent")
    parser.add_argument("--engagement", required=True, help="Engagement identifier")
    parser.add_argument("--input", required=True, help="Path to intake JSON file")
    parser.add_argument(
        "--output",
        help="Optional output path (default: storage/engagements/{id}/discovery/vN.json)",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use Gemini to rephrase questions (requires GEMINI_API_KEY)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Force template questions without LLM",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    intake_data = json.loads(input_path.read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(intake_data)

    store = EngagementStore()
    record = store.get_engagement(args.engagement)
    if record is None:
        record = EngagementRecord(
            engagement_id=args.engagement,
            client_name=intake.company_name,
            industry=intake.industry,
        )
        store.upsert_engagement(record)
    store.save_intake(args.engagement, intake)

    use_llm = None
    if args.use_llm:
        use_llm = True
    elif args.no_llm:
        use_llm = False

    output = run_discovery(
        intake,
        engagement_id=args.engagement,
        resolved_requirement_ids=record.resolved_requirement_ids,
        use_llm_questions=use_llm,
    )

    payload = output.model_dump_json_ready()
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        out_path = store.save_artifact(args.engagement, "discovery", payload)

    print(json.dumps(payload, indent=2))
    print(f"\nWrote discovery artifact: {out_path}", file=sys.stderr)
    print(
        f"Planning readiness score: {output.planning_readiness_score}/100 "
        f"({len(output.critical_gaps)} critical gaps)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
