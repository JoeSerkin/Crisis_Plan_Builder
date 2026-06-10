"""Client intake form API."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from cmp.api.deps import get_store
from cmp.intake.client_workflow import (
    bootstrap_engagement,
    build_gap_form_schema,
    client_workflow_status,
    confirm_client_intake,
    process_uploaded_documents,
    submit_gap_answers,
)
from cmp.intake.form_schema import answers_to_intake, build_client_form_schema, validate_intake_payload
from cmp.storage.engagement_store import EngagementStore

router = APIRouter(prefix="/intake-form", tags=["intake-form"])

ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".json", ".csv"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class IntakeFormSubmitRequest(BaseModel):
    answers: dict[str, Any]
    industry: str | None = None


class BootstrapRequest(BaseModel):
    company_name: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    countries: list[str] = Field(default_factory=list)


class ConfirmRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return cleaned or "upload"


def _uploads_dir(store: EngagementStore, engagement_id: str) -> Path:
    path = store.engagement_dir(engagement_id) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("/schema")
def get_intake_form_schema(
    industry: str | None = Query(default=None, description="Filter industry-specific questions"),
) -> dict[str, Any]:
    return build_client_form_schema(industry)


@router.get("/{engagement_id}/status")
def get_client_workflow_status(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    return client_workflow_status(store, engagement_id)


@router.post("/{engagement_id}/bootstrap")
def bootstrap_client_engagement(
    engagement_id: str,
    body: BootstrapRequest,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = bootstrap_engagement(
        store,
        engagement_id,
        company_name=body.company_name.strip(),
        industry=body.industry.strip(),
        countries=body.countries,
    )
    intake = store.load_intake(engagement_id)
    return {
        "engagement_id": engagement_id,
        "status": record.status,
        "intake": intake.model_dump(mode="json") if intake else None,
    }


@router.post("/{engagement_id}/upload", status_code=201)
async def upload_client_document(
    engagement_id: str,
    file: UploadFile = File(...),
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found — complete setup first")

    original_name = file.filename or "upload.bin"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_SUFFIXES))}",
        )

    payload = await file.read()
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 20 MB upload limit")

    safe_name = _safe_filename(Path(original_name).stem) + suffix
    target = _uploads_dir(store, engagement_id) / safe_name
    if target.exists():
        stem = target.stem
        counter = 2
        while target.exists():
            target = target.with_name(f"{stem}-{counter}{suffix}")
            counter += 1

    target.write_bytes(payload)
    return {
        "document_id": target.name,
        "filename": original_name,
        "stored_as": target.name,
        "size_bytes": len(payload),
    }


@router.post("/{engagement_id}/process-documents")
def process_client_documents(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    try:
        return process_uploaded_documents(store, engagement_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.get("/{engagement_id}/gaps-schema")
def get_gap_form_schema(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    try:
        return build_gap_form_schema(store, engagement_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{engagement_id}/submit-gaps")
def submit_gap_form(
    engagement_id: str,
    body: IntakeFormSubmitRequest,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    try:
        return submit_gap_answers(store, engagement_id, body.answers)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{engagement_id}/confirm")
def confirm_client_submission(
    engagement_id: str,
    body: ConfirmRequest,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    try:
        return confirm_client_intake(store, engagement_id, answers=body.answers or None)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/submit")
def submit_intake_form(body: IntakeFormSubmitRequest) -> dict[str, Any]:
    payload = answers_to_intake(body.answers, body.industry)
    try:
        intake = validate_intake_payload(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result: dict[str, Any] = {
        "intake": intake.model_dump(mode="json"),
        "field_count": len(intake.flatten()),
    }
    return result


@router.post("/submit/{engagement_id}")
def submit_intake_to_engagement(
    engagement_id: str,
    body: IntakeFormSubmitRequest,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    payload = answers_to_intake(body.answers, body.industry)
    try:
        intake = validate_intake_payload(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if record is None:
        from cmp.models.schemas import EngagementRecord

        record = EngagementRecord(
            engagement_id=engagement_id,
            client_name=intake.company_name,
            industry=intake.industry,
            status="awaiting_client",
        )
        store.upsert_engagement(record)

    store.save_intake(engagement_id, intake)
    record.client_name = intake.company_name
    record.industry = intake.industry
    store.upsert_engagement(record)

    return {
        "engagement_id": engagement_id,
        "intake": intake.model_dump(mode="json"),
        "message": "Intake saved. Run discovery to calculate readiness score.",
    }
