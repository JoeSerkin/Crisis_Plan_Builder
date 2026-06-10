"""Pydantic schemas for crisis management planner engagements."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class GapPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FieldConfidence(str, Enum):
    STATED_BY_CLIENT = "stated_by_client"
    VERIFIED = "verified"
    INFERRED = "inferred"


class KnownField(BaseModel):
    value: Any
    source: str = "intake"
    confidence: FieldConfidence = FieldConfidence.STATED_BY_CLIENT


class ClientIntake(BaseModel):
    company_name: str
    industry: str
    employees: int | None = None
    countries: list[str] = Field(default_factory=list)
    headquarters_country: str | None = None
    organization_size: str | None = None
    crisis_program_maturity: str | None = None
    staffing_model: str | None = None
    legal_entities: list[dict[str, Any]] | None = None
    sites: list[dict[str, Any]] | None = None
    additional_context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("company_name", "industry")
    @classmethod
    def strip_required_strings(cls, v: str) -> str:
        return v.strip()

    @field_validator("legal_entities", mode="before")
    @classmethod
    def coerce_legal_entities(cls, v: Any) -> Any:
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, dict):
            notes = str(v.get("notes") or "").strip()
            if notes:
                return [{"name": notes, "role": "other"}]
            return None
        return v

    def flatten(self) -> dict[str, Any]:
        """Flatten intake into a field_path -> value map for gap detection."""
        data: dict[str, Any] = {
            "company_name": self.company_name,
            "industry": self.industry,
            "employees": self.employees,
            "countries": self.countries,
        }
        if self.headquarters_country is not None:
            data["headquarters_country"] = self.headquarters_country
        if self.organization_size is not None:
            data["organization_size"] = self.organization_size
        if self.crisis_program_maturity is not None:
            data["crisis_program_maturity"] = self.crisis_program_maturity
        if self.staffing_model is not None:
            data["staffing_model"] = self.staffing_model
        if self.legal_entities is not None:
            data["legal_entities"] = self.legal_entities
        if self.sites is not None:
            data["sites"] = self.sites
        data.update(self.additional_context)
        return data

    def is_field_present(self, field_path: str) -> bool:
        flat = self.flatten()
        value = flat.get(field_path)
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True


class RequirementGap(BaseModel):
    requirement_id: str
    domain: str
    label: str
    priority: GapPriority
    why_it_matters: str
    unlocks_agents: list[str] = Field(default_factory=list)
    field_path: str


class ConsultantQuestion(BaseModel):
    id: str
    targets_gap: str
    question: str
    rationale: str
    priority: GapPriority


class OrganizationContextSummary(BaseModel):
    size_tier: str
    employee_count: int | None = None
    country_count: int = 0
    site_count: int = 0
    headquarters_country: str | None = None
    crisis_maturity: str | None = None
    staffing_model: str | None = None
    min_cmt_roles: int = 5
    min_procedures: int = 3
    readiness_gate: int = 60
    flexibility_notes: list[str] = Field(default_factory=list)
    jurisdiction_notes: list[str] = Field(default_factory=list)


class DiscoveryOutput(BaseModel):
    known_information: dict[str, KnownField | dict[str, Any]]
    missing_information: list[RequirementGap]
    critical_gaps: list[str]
    recommended_questions: list[ConsultantQuestion]
    assumptions: list[str] = Field(default_factory=list)
    organization_context: OrganizationContextSummary | None = None
    planning_readiness_score: int = Field(ge=0, le=100)
    readiness_breakdown: dict[str, int] = Field(default_factory=dict)
    engagement_id: str | None = None
    version: int = 1
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def model_dump_json_ready(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EngagementRecord(BaseModel):
    engagement_id: str
    client_name: str
    industry: str
    status: str = "discovery"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    resolved_requirement_ids: list[str] = Field(default_factory=list)
    notes: str = ""


class RiskItem(BaseModel):
    id: str
    title: str
    tier: int = Field(ge=1, le=3)
    rationale: str
    likelihood: str = "medium"
    impact: str = "high"
    affected_domains: list[str] = Field(default_factory=list)


class RiskProfileOutput(BaseModel):
    tier_1_risks: list[RiskItem]
    tier_2_risks: list[RiskItem]
    tier_3_risks: list[RiskItem]
    risk_rationale: dict[str, str] = Field(default_factory=dict)
    engagement_id: str | None = None
    version: int = 1
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


class CrisisLevel(BaseModel):
    level: int
    name: str
    description: str
    activation_triggers: list[str] = Field(default_factory=list)


class EscalationStep(BaseModel):
    severity: str
    notify_within_minutes: int
    roles: list[str]
    channel: str


class CrisisTeamRole(BaseModel):
    role: str
    responsibilities: list[str]
    primary_authority: list[str] = Field(default_factory=list)
    alternate_role: str | None = None


class DecisionAuthority(BaseModel):
    decision_type: str
    authority_role: str
    backup_role: str | None = None
    notes: str = ""


class GovernanceOutput(BaseModel):
    crisis_levels: list[CrisisLevel]
    escalation_matrix: list[EscalationStep]
    crisis_team_roles: list[CrisisTeamRole]
    decision_authorities: list[DecisionAuthority]
    engagement_id: str | None = None
    version: int = 1
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


class RoleAction(BaseModel):
    role: str
    summary: str


class ProcedureSection(BaseModel):
    purpose: str
    scope: str
    activation_summary: str
    crisis_level: int
    crisis_level_name: str
    opening_steps: str
    activated_roles: list[str]
    role_actions: list[RoleAction]
    escalation_summary: str
    recovery_summary: str


class PlaybookRole(BaseModel):
    role: str
    alternate_role: str | None = None
    activates_when: str
    purpose: str
    first_15_minutes: str
    during_response: str
    decisions: list[str]
    coordinates_with: list[str]
    stand_down: str


class PlaybookBundle(BaseModel):
    roles: list[PlaybookRole]
    engagement_id: str | None = None
    version: int = 1


class ProcedureOutput(BaseModel):
    risk_id: str
    title: str
    procedure: ProcedureSection
    engagement_id: str | None = None


class ProceduresBundle(BaseModel):
    procedures: list[ProcedureOutput]
    engagement_id: str | None = None
    version: int = 1
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


class ChecklistVerification(BaseModel):
    item: str
    status: str
    note: str = ""


class StandardsReviewOutput(BaseModel):
    strengths: list[str]
    gaps: list[str]
    recommendations: list[str]
    framework_coverage_score: int = Field(ge=0, le=100)
    checklist_verifications: list[ChecklistVerification] = Field(default_factory=list)
    engagement_id: str | None = None
    version: int = 1
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


class TabletopInject(BaseModel):
    time_offset_minutes: int
    inject: str
    expected_actions: list[str] = Field(default_factory=list)


class TabletopOutput(BaseModel):
    scenario: str
    injects: list[TabletopInject]
    learning_objectives: list[str]
    evaluation_criteria: list[str]
    engagement_id: str | None = None
    version: int = 1
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
