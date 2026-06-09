"""Client intake form API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from cmp.api.deps import get_store
from cmp.intake.form_schema import answers_to_intake, build_client_form_schema, validate_intake_payload
from cmp.storage.engagement_store import EngagementStore

router = APIRouter(prefix="/intake-form", tags=["intake-form"])


class IntakeFormSubmitRequest(BaseModel):
    answers: dict[str, Any]
    industry: str | None = None


@router.get("/schema")
def get_intake_form_schema(
    industry: str | None = Query(default=None, description="Filter industry-specific questions"),
) -> dict[str, Any]:
    return build_client_form_schema(industry)


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
