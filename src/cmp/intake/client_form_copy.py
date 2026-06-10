"""Plain-language labels and questions for the client intake form."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from cmp.models.requirements import Requirement, knowledge_root, load_yaml

CLIENT_DOMAIN_LABELS = {
    "org_profile": "About your organization",
    "operations_sites": "Locations and daily operations",
    "governance": "Leadership during an emergency",
    "communications": "Communicating during an incident",
    "risk_bcp": "Risks, insurance, and business recovery",
}

# Shown to clients instead of consultant priority labels (critical/high/medium/low).
CLIENT_PRIORITY_LABELS = {
    "critical": "Needed to start",
    "high": "Important",
    "medium": "Helpful",
    "low": "Optional",
}

ACRONYM_EXPANSIONS: list[tuple[str, str]] = [
    (r"\bOT/ICS\b", "factory or plant control systems"),
    (r"\bBCP\b", "business continuity plan"),
    (r"\bCMT\b", "crisis management team"),
    (r"\bIR\b", "incident response"),
    (r"\bRTO\b", "recovery time"),
    (r"\bRPO\b", "acceptable data loss window"),
    (r"\bSDS\b", "safety data sheets"),
    (r"\bD&O\b", "directors and officers insurance"),
    (r"\bJV\b", "joint venture"),
    (r"\bJVs\b", "joint ventures"),
    (r"\bHQ\b", "headquarters"),
    (r"\bMSPs\b", "managed service providers"),
    (r"\bSaaS\b", "cloud software services"),
    (r"\bAED\b", "automated external defibrillator"),
    (r"\bDPO\b", "data protection officer"),
    (r"\bGDPR\b", "EU data privacy law"),
    (r"\bCCPA\b", "California privacy law"),
    (r"\bFDA\b", "U.S. Food and Drug Administration"),
    (r"\bEMA\b", "European Medicines Agency"),
    (r"\bK&R\b", "kidnap and ransom"),
    (r"\bNERC\b", "North American electric reliability regulator"),
    (r"\bFERC\b", "U.S. Federal Energy Regulatory Commission"),
]

PHRASE_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\btabletop\b", "practice exercise"),
    (r"\btabletops\b", "practice exercises"),
    (r"\bdark site\b", "standby crisis website"),
    (r"\bdark website\b", "standby crisis website"),
    (r"\bmutual aid\b", "emergency support from neighboring organizations"),
    (r"\btier-1\b", "most critical"),
    (r"\btier 1\b", "most critical"),
    (r"\bsole-source\b", "single-source"),
    (r"\bspokesperson\b", "official media contact"),
    (r"\bcrisis activation\b", "formal emergency response"),
    (r"\bescalation matrix\b", "notification chain"),
    (r"\bBIA\b", "business impact review"),
    (r"\bpharmacovigilance\b", "drug safety reporting"),
    (r"\bprocess safety management\b", "major hazard safety program"),
    (r"\bprocess hazard analysis\b", "safety risk review"),
    (r"\bmajor accident hazard\b", "high-consequence safety incident"),
    (r"\bcyber-physical\b", "cyber attack affecting physical operations"),
    (r"\bwelfare checks?\b", "check-ins to confirm people are safe"),
    (r"\bduty-of-care\b", "responsibility to protect"),
    (r"\bGxP\b", "pharmaceutical quality rules"),
    (r"\bGMP\b", "good manufacturing practice"),
    (r"\bGCP\b", "good clinical practice"),
    (r"\bCSR\b", "community and social responsibility"),
    (r"\bESG\b", "environmental and social responsibility"),
]


@lru_cache(maxsize=1)
def _field_copy_map() -> dict[str, dict[str, str]]:
    path = knowledge_root() / "crisis_management" / "client_intake_copy.yaml"
    if not path.exists():
        return {}
    raw = load_yaml(path)
    return raw.get("fields") or {}


def _apply_replacements(text: str, pairs: list[tuple[str, str]]) -> str:
    result = text
    for pattern, replacement in pairs:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def clientize_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = _apply_replacements(cleaned, ACRONYM_EXPANSIONS)
    cleaned = _apply_replacements(cleaned, PHRASE_REPLACEMENTS)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def client_field_copy(req: Requirement) -> dict[str, str]:
    explicit = _field_copy_map().get(req.field_path, {})
    label = explicit.get("label") or clientize_text(req.label)
    question = explicit.get("question") or clientize_text(req.question_template)
    help_text = explicit.get("help")
    if not help_text and req.why_it_matters:
        help_text = clientize_text(req.why_it_matters)
    return {
        "label": label,
        "question": question,
        "help": help_text or "",
        "priority_label": CLIENT_PRIORITY_LABELS.get(req.priority.value, req.priority.value.title()),
    }


def client_section_label(domain_id: str, catalog_labels: dict[str, str]) -> str:
    return CLIENT_DOMAIN_LABELS.get(domain_id, catalog_labels.get(domain_id, domain_id))
