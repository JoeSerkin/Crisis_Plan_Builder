"""Uploaded document management and extraction API."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from cmp.api.deps import get_store
from cmp.intake.extraction_gaps import catalog_gaps_for_extraction
from cmp.intake.document_extract import propose_updates_from_document, propose_updates_from_text
from cmp.models.schemas import RequirementGap
from cmp.storage.engagement_store import EngagementStore

router = APIRouter(prefix="/engagements", tags=["documents"])

ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".json", ".csv"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class ExtractTextRequest(BaseModel):
    text: str = Field(min_length=1)


class ApplyProposalsRequest(BaseModel):
    updates: dict[str, Any]
    resolve: list[str] = Field(default_factory=list)
    rerun_discovery: bool = True


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return cleaned or "upload"


def _uploads_dir(store: EngagementStore, engagement_id: str) -> Path:
    path = store.engagement_dir(engagement_id) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _gaps_from_discovery(store: EngagementStore, engagement_id: str) -> list[RequirementGap]:
    discovery = store.load_latest_artifact(engagement_id, "discovery")
    if not discovery:
        return []
    gaps: list[RequirementGap] = []
    for item in discovery.get("missing_information") or []:
        gaps.append(RequirementGap.model_validate(item))
    return gaps


def _gaps_for_extraction(store: EngagementStore, engagement_id: str) -> list[RequirementGap]:
    return catalog_gaps_for_extraction(store, engagement_id)


@router.get("/{engagement_id}/documents")
def list_documents(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> list[dict[str, Any]]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    uploads = _uploads_dir(store, engagement_id)
    items: list[dict[str, Any]] = []
    for path in sorted(uploads.iterdir()):
        if not path.is_file():
            continue
        stat = path.stat()
        items.append(
            {
                "document_id": path.name,
                "filename": path.name,
                "size_bytes": stat.st_size,
                "suffix": path.suffix.lower(),
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }
        )
    return items


@router.post("/{engagement_id}/documents/upload", status_code=201)
async def upload_document(
    engagement_id: str,
    file: UploadFile = File(...),
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

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
    stat = target.stat()
    return {
        "document_id": target.name,
        "filename": original_name,
        "stored_as": target.name,
        "size_bytes": stat.st_size,
        "suffix": suffix,
    }


@router.post("/{engagement_id}/documents/{document_id}/extract")
def extract_document(
    engagement_id: str,
    document_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    uploads = _uploads_dir(store, engagement_id).resolve()
    target = (uploads / document_id).resolve()
    if not str(target).startswith(str(uploads)):
        raise HTTPException(status_code=400, detail="Invalid document id")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Document not found")

    gaps = _gaps_for_extraction(store, engagement_id)
    intake = store.load_intake(engagement_id)
    try:
        text, proposals = propose_updates_from_document(target, gaps, intake=intake)
    except ImportError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "document_id": target.name,
        "text_preview": text[:2000],
        "text_length": len(text),
        "open_gaps": len(gaps),
        "proposal_count": len(proposals),
        "proposals": [proposal.to_dict() for proposal in proposals],
    }


@router.post("/{engagement_id}/documents/extract-text")
def extract_text(
    engagement_id: str,
    body: ExtractTextRequest,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    gaps = _gaps_for_extraction(store, engagement_id)
    intake = store.load_intake(engagement_id)
    proposals = propose_updates_from_text(body.text, gaps, intake=intake)

    return {
        "text_length": len(body.text),
        "open_gaps": len(gaps),
        "proposal_count": len(proposals),
        "proposals": [proposal.to_dict() for proposal in proposals],
        "text_preview": body.text[:2000],
    }


@router.post("/{engagement_id}/documents/apply")
def apply_proposals(
    engagement_id: str,
    body: ApplyProposalsRequest,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if not body.updates and not body.resolve:
        raise HTTPException(status_code=400, detail="No updates or resolve IDs provided")

    try:
        merged = store.merge_intake(engagement_id, body.updates) if body.updates else store.load_intake(
            engagement_id
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if body.resolve:
        store.mark_resolved(engagement_id, body.resolve)

    discovery_payload = None
    if body.rerun_discovery and merged is not None:
        from cmp.agents.discovery import run_discovery

        record = store.get_engagement(engagement_id)
        resolved = record.resolved_requirement_ids if record else []
        discovery = run_discovery(
            merged,
            engagement_id=engagement_id,
            resolved_requirement_ids=resolved,
            use_llm_questions=False,
        )
        discovery_payload = discovery.model_dump_json_ready()
        store.save_artifact(engagement_id, "discovery", discovery_payload)
        if record:
            record.status = "discovery"
            store.upsert_engagement(record)

    return {
        "intake": merged.model_dump(mode="json") if merged else None,
        "discovery": discovery_payload,
        "resolved": body.resolve,
    }
