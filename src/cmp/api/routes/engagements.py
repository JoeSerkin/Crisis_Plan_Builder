"""Engagement workflow API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cmp.agents.discovery import run_discovery
from cmp.api.deps import get_store
from cmp.models.requirements import repo_root
from cmp.models.schemas import ClientIntake, EngagementRecord
from cmp.storage.engagement_store import EngagementStore
from cmp.workflows.planner_graph import run_planner

router = APIRouter(prefix="/engagements", tags=["engagements"])


class CreateEngagementRequest(BaseModel):
    engagement_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
    )
    intake: ClientIntake


class MergeIntakeRequest(BaseModel):
    updates: dict[str, Any]
    resolve: list[str] = Field(default_factory=list)


@router.get("")
def list_engagements(store: EngagementStore = Depends(get_store)) -> list[EngagementRecord]:
    return store.list_engagements()


@router.post("", status_code=201)
def create_engagement(
    body: CreateEngagementRequest,
    store: EngagementStore = Depends(get_store),
) -> EngagementRecord:
    if store.get_engagement(body.engagement_id):
        raise HTTPException(status_code=409, detail="Engagement already exists")
    record = EngagementRecord(
        engagement_id=body.engagement_id,
        client_name=body.intake.company_name,
        industry=body.intake.industry,
    )
    store.upsert_engagement(record)
    store.save_intake(body.engagement_id, body.intake)
    return record


@router.get("/{engagement_id}")
def get_engagement(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    intake = store.load_intake(engagement_id)
    discovery = store.load_latest_artifact(engagement_id, "discovery")
    return {
        "engagement": record.model_dump(mode="json"),
        "intake": intake.model_dump(mode="json") if intake else None,
        "discovery": discovery,
    }


@router.put("/{engagement_id}/intake")
def upsert_intake(
    engagement_id: str,
    intake: ClientIntake,
    store: EngagementStore = Depends(get_store),
) -> ClientIntake:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    store.save_intake(engagement_id, intake)
    record.client_name = intake.company_name
    record.industry = intake.industry
    store.upsert_engagement(record)
    return intake


@router.post("/{engagement_id}/discovery")
def run_discovery_route(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    intake = store.load_intake(engagement_id)
    if intake is None:
        raise HTTPException(status_code=400, detail="Intake not found for engagement")

    output = run_discovery(
        intake,
        engagement_id=engagement_id,
        resolved_requirement_ids=record.resolved_requirement_ids,
        use_llm_questions=False,
    )
    payload = output.model_dump_json_ready()
    store.save_artifact(engagement_id, "discovery", payload)
    record.status = "discovery"
    store.upsert_engagement(record)
    return payload


@router.post("/{engagement_id}/merge")
def merge_intake_route(
    engagement_id: str,
    body: MergeIntakeRequest,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    try:
        merged = store.merge_intake(engagement_id, body.updates)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if body.resolve:
        store.mark_resolved(engagement_id, body.resolve)
    return merged.model_dump(mode="json")


@router.post("/{engagement_id}/plan")
def run_plan_route(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    intake = store.load_intake(engagement_id)
    if intake is None:
        raise HTTPException(status_code=400, detail="Intake not found for engagement")

    try:
        result = run_planner(engagement_id, intake)
    except ImportError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    status = result.get("status", "unknown")
    if status == "complete":
        record.status = "complete"
        store.upsert_engagement(record)
    elif status == "blocked_readiness_gate":
        record.status = "blocked"
        store.upsert_engagement(record)

    return {k: v for k, v in result.items() if k != "intake"}


@router.get("/{engagement_id}/deliverables")
def list_deliverables(engagement_id: str) -> dict[str, str]:
    output_dir = repo_root() / "output" / engagement_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="No deliverables generated yet")
    files: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and "docx" not in path.parts:
            rel = path.relative_to(output_dir)
            files[str(rel).replace("\\", "/")] = str(path)
    if not files:
        raise HTTPException(status_code=404, detail="No deliverables generated yet")
    return files


@router.get("/{engagement_id}/deliverables/{file_path:path}")
def get_deliverable(engagement_id: str, file_path: str) -> dict[str, str]:
    output_dir = (repo_root() / "output" / engagement_id).resolve()
    target = (output_dir / file_path).resolve()
    if not str(target).startswith(str(output_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return {
        "path": file_path,
        "content": target.read_text(encoding="utf-8"),
    }


@router.post("/{engagement_id}/export/docx")
def export_docx(engagement_id: str) -> dict[str, str]:
    from cmp.render.docx_export import export_engagement_docx

    try:
        paths = export_engagement_docx(engagement_id)
    except ImportError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {name: str(path) for name, path in paths.items()}
