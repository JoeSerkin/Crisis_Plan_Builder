"""Client-first intake workflow: documents → auto-apply → gap questions → confirm."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cmp.agents.discovery import run_discovery
from cmp.intake.document_extract import propose_updates_from_document
from cmp.intake.form_schema import answers_to_intake, build_client_form_schema, validate_intake_payload
from cmp.models.schemas import ClientIntake, EngagementRecord
from cmp.storage.engagement_store import EngagementStore

AUTO_APPLY_CONFIDENCE = frozenset({"high", "medium"})


def _uploads_dir(store: EngagementStore, engagement_id: str) -> Path:
    path = store.engagement_dir(engagement_id) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


from cmp.intake.extraction_gaps import catalog_gaps_for_extraction


def bootstrap_engagement(
    store: EngagementStore,
    engagement_id: str,
    *,
    company_name: str,
    industry: str,
    countries: list[str] | None = None,
) -> EngagementRecord:
    record = store.get_engagement(engagement_id)
    if record is None:
        record = EngagementRecord(
            engagement_id=engagement_id,
            client_name=company_name,
            industry=industry,
            status="awaiting_client",
        )
    else:
        record.client_name = company_name or record.client_name
        record.industry = industry or record.industry
        if record.status == "discovery":
            record.status = "awaiting_client"

    store.upsert_engagement(record)

    existing = store.load_intake(engagement_id)
    if existing is None:
        intake = ClientIntake(
            company_name=company_name,
            industry=industry,
            countries=countries or [],
        )
        store.save_intake(engagement_id, intake)
    return record


def _proposal_should_auto_apply(confidence: str, source: str) -> bool:
    if source == "structured":
        return True
    return confidence in AUTO_APPLY_CONFIDENCE


def process_uploaded_documents(
    store: EngagementStore,
    engagement_id: str,
) -> dict[str, Any]:
    """Extract all uploaded documents and auto-apply confident field proposals."""
    intake = store.load_intake(engagement_id)
    if intake is None:
        raise FileNotFoundError(f"No intake found for engagement {engagement_id}")

    uploads = _uploads_dir(store, engagement_id)
    gaps = catalog_gaps_for_extraction(store, engagement_id)
    applied: dict[str, Any] = {}
    document_results: list[dict[str, Any]] = []

    for path in sorted(uploads.iterdir()):
        if not path.is_file():
            continue
        try:
            _, proposals = propose_updates_from_document(path, gaps, intake=intake)
        except (ImportError, ValueError) as exc:
            document_results.append(
                {"document_id": path.name, "error": str(exc), "applied_count": 0}
            )
            continue

        updates: dict[str, Any] = {}
        for proposal in proposals:
            if not _proposal_should_auto_apply(proposal.confidence, proposal.source):
                continue
            if proposal.field_path in applied:
                continue
            updates[proposal.field_path] = proposal.proposed_value

        if updates:
            intake = store.merge_intake(engagement_id, updates)
            applied.update(updates)
            gaps = catalog_gaps_for_extraction(store, engagement_id)

        document_results.append(
            {
                "document_id": path.name,
                "proposal_count": len(proposals),
                "applied_count": len(updates),
                "applied_fields": sorted(updates.keys()),
            }
        )

    discovery_payload = _run_discovery(store, engagement_id, intake)

    record = store.get_engagement(engagement_id)
    if record:
        record.status = "gap_review"
        if intake.company_name:
            record.client_name = intake.company_name
        if intake.industry:
            record.industry = intake.industry
        store.upsert_engagement(record)

    gap_summary = summarize_client_gaps(store, engagement_id)
    return {
        "documents": document_results,
        "applied_fields": sorted(applied.keys()),
        "applied_count": len(applied),
        "discovery": discovery_payload,
        **gap_summary,
    }


def _run_discovery(
    store: EngagementStore,
    engagement_id: str,
    intake: ClientIntake | None = None,
) -> dict[str, Any]:
    if intake is None:
        intake = store.load_intake(engagement_id)
    if intake is None:
        raise FileNotFoundError(f"No intake found for engagement {engagement_id}")
    record = store.get_engagement(engagement_id)
    resolved = record.resolved_requirement_ids if record else []
    output = run_discovery(
        intake,
        engagement_id=engagement_id,
        resolved_requirement_ids=resolved,
        use_llm_questions=False,
    )
    payload = output.model_dump_json_ready()
    store.save_artifact(engagement_id, "discovery", payload)
    return payload


def summarize_client_gaps(store: EngagementStore, engagement_id: str) -> dict[str, Any]:
    discovery = store.load_latest_artifact(engagement_id, "discovery")
    record = store.get_engagement(engagement_id)
    resolved = set(record.resolved_requirement_ids if record else [])

    if not discovery:
        return {
            "open_gap_count": 0,
            "critical_gap_count": 0,
            "readiness_score": None,
            "readiness_threshold": 60,
            "gate_passed": False,
            "gaps": [],
        }

    questions = {
        item.get("targets_gap"): item.get("question")
        for item in discovery.get("recommended_questions") or []
    }
    gaps: list[dict[str, Any]] = []
    for item in discovery.get("missing_information") or []:
        requirement_id = item.get("requirement_id")
        if requirement_id in resolved:
            continue
        gaps.append(
            {
                **item,
                "question": questions.get(requirement_id) or item.get("label"),
            }
        )

    score = discovery.get("planning_readiness_score")
    threshold = int((discovery.get("organization_context") or {}).get("readiness_gate") or 60)
    critical = discovery.get("critical_gaps") or []

    return {
        "open_gap_count": len(gaps),
        "critical_gap_count": len(critical),
        "readiness_score": score,
        "readiness_threshold": threshold,
        "gate_passed": score is not None and score >= threshold,
        "gaps": gaps,
    }


def build_gap_form_schema(store: EngagementStore, engagement_id: str) -> dict[str, Any]:
    intake = store.load_intake(engagement_id)
    if intake is None:
        raise FileNotFoundError(f"No intake found for engagement {engagement_id}")

    summary = summarize_client_gaps(store, engagement_id)
    gap_paths = {gap["field_path"] for gap in summary["gaps"]}
    gap_questions = {gap["field_path"]: gap.get("question") for gap in summary["gaps"]}

    full_schema = build_client_form_schema(intake.industry)
    sections: list[dict[str, Any]] = []
    field_count = 0

    for section in full_schema["sections"]:
        section_fields = []
        for field in section["fields"]:
            if field["field_path"] not in gap_paths:
                continue
            enriched = dict(field)
            if gap_questions.get(field["field_path"]):
                enriched["question"] = gap_questions[field["field_path"]]
            enriched["gap"] = True
            section_fields.append(enriched)
        if section_fields:
            sections.append(
                {
                    "id": section["id"],
                    "label": section["label"],
                    "fields": section_fields,
                }
            )
            field_count += len(section_fields)

    return {
        "engagement_id": engagement_id,
        "industry": intake.industry,
        "field_count": field_count,
        "open_gap_count": summary["open_gap_count"],
        "readiness_score": summary["readiness_score"],
        "sections": sections,
        "known_field_count": len(intake.flatten()) - len(gap_paths),
    }


def submit_gap_answers(
    store: EngagementStore,
    engagement_id: str,
    answers: dict[str, Any],
) -> dict[str, Any]:
    intake = store.load_intake(engagement_id)
    if intake is None:
        raise FileNotFoundError(f"No intake found for engagement {engagement_id}")

    payload = answers_to_intake(answers, intake.industry)
    updates: dict[str, Any] = {}
    top_level = {
        "company_name",
        "industry",
        "employees",
        "countries",
        "headquarters_country",
        "organization_size",
        "crisis_program_maturity",
        "staffing_model",
        "legal_entities",
        "sites",
    }
    for key, value in payload.items():
        if key == "additional_context" and isinstance(value, dict):
            updates.update(value)
        elif key in top_level:
            updates[key] = value

    merged = store.merge_intake(engagement_id, updates) if updates else intake
    discovery_payload = _run_discovery(store, engagement_id, merged)
    gap_summary = summarize_client_gaps(store, engagement_id)

    record = store.get_engagement(engagement_id)
    if record and record.status == "awaiting_client":
        record.status = "gap_review"
        store.upsert_engagement(record)

    return {
        "intake": merged.model_dump(mode="json"),
        "discovery": discovery_payload,
        **gap_summary,
    }


def confirm_client_intake(
    store: EngagementStore,
    engagement_id: str,
    *,
    answers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if answers:
        submit_gap_answers(store, engagement_id, answers)

    intake = store.load_intake(engagement_id)
    if intake is None:
        raise FileNotFoundError(f"No intake found for engagement {engagement_id}")

    try:
        validate_intake_payload(intake.model_dump(mode="json"))
    except Exception as exc:
        raise ValueError(f"Intake validation failed: {exc}") from exc

    discovery_payload = _run_discovery(store, engagement_id, intake)
    gap_summary = summarize_client_gaps(store, engagement_id)

    record = store.get_engagement(engagement_id)
    if record:
        record.status = "client_confirmed"
        record.client_name = intake.company_name
        record.industry = intake.industry
        store.upsert_engagement(record)

    return {
        "engagement_id": engagement_id,
        "status": "client_confirmed",
        "intake": intake.model_dump(mode="json"),
        "discovery": discovery_payload,
        "message": (
            "Thank you — your information has been saved. "
            "Your consultant will review everything and compile your crisis management plan."
        ),
        **gap_summary,
    }


def client_workflow_status(store: EngagementStore, engagement_id: str) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        return {"engagement_id": engagement_id, "exists": False}

    intake = store.load_intake(engagement_id)
    uploads = list(_uploads_dir(store, engagement_id).glob("*"))
    upload_files = [path.name for path in uploads if path.is_file()]
    gap_summary = summarize_client_gaps(store, engagement_id)

    phase = "setup"
    if record.status == "client_confirmed":
        phase = "complete"
    elif record.status == "gap_review":
        phase = "gaps" if gap_summary["open_gap_count"] else "confirm"
    elif upload_files:
        phase = "review"
    elif intake and intake.company_name:
        phase = "upload"

    return {
        "engagement_id": engagement_id,
        "exists": True,
        "status": record.status,
        "phase": phase,
        "client_name": record.client_name,
        "industry": record.industry,
        "upload_count": len(upload_files),
        "uploads": upload_files,
        "intake_present": intake is not None,
        **gap_summary,
    }
