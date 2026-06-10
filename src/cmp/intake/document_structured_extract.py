"""Structured field extraction for crisis and emergency plan documents."""

from __future__ import annotations

import re
from typing import Any

from cmp.intake.form_widgets import COUNTRY_OPTIONS

StructuredHit = tuple[str, Any, str, str]  # field_path, value, confidence, snippet

PLAN_TITLE_RE = re.compile(
    r"\b("
    r"emergency\s+(?:contingency|response)\s+plan|"
    r"crisis\s+management\s+plan|"
    r"business\s+continuity\s+plan|"
    r"emergency\s+response\s+plan|"
    r"contingency\s+and\s+response\s+plan"
    r")\b",
    re.I,
)

ORG_NAME_RE = re.compile(r"\b(IsraAID|ISRAAID)\b", re.I)

ROLE_NAME_LINE_RE = re.compile(
    r"^(?P<role>"
    r"Incident Commander|"
    r"Country Director|"
    r"Regional Director|"
    r"Security and Compliance Director|"
    r"Security/?\s*Procurement Manager|"
    r"Security/\s*Procurement Manager|"
    r"Disaster Field Operation|"
    r"CERT|"
    r"Admin Manager|"
    r"Accounts manager|"
    r"Crisis (?:Management )?Team Leader|"
    r"Emergency (?:Coordinator|Director)|"
    r"Communications? (?:Officer|Manager)|"
    r"Comunication officer|"
    r"Logistic(?:s)?(?: Manager)?|"
    r"Team [Ll]eader|"
    r"Field Security (?:Officer|Manager)"
    r")"
    r"\s*[-–—:]+\s*"
    r"(?P<name>[A-Za-z][A-Za-z'. \u00c0-\u024f-]{1,50})\s*$",
    re.UNICODE,
)

GENERIC_ROLE_NAME_RE = re.compile(
    r"^(?P<role>[A-Z][A-Za-z0-9\s/&'-]{2,50}?)\s*[-–—:]\s*(?P<name>[A-Z][A-Za-z][A-Za-z'. \u00c0-\u024f-]{1,40})\s*$",
    re.UNICODE,
)

CRISIS_LEVEL_RE = re.compile(
    r"Level\s+(one|two|three|1|2|3)\s+[Ee]mergency\s*[-–—:]?\s*(.+)",
    re.I,
)

COMMS_STRATEGY_RE = re.compile(
    r"Communication\s+strategy\s*[:\-–—]\s*(.+)",
    re.I,
)

HAZARD_LINE_RE = re.compile(
    r"^(?:Hurricanes?|Floods?|Earthquakes?|Tsunamis?|Fire|Intruder|Break-?IN|"
    r"Utility failure|ELECTRICITY|TORRENTIAL RAINS?|VOLCANIC|HURRICANE|TSUNAMI|"
    r"Infection|Human disease|outbreaks?|INTRUDERS|EARTHQUAKE)\b",
    re.I,
)

UTILITY_FAILURE_RE = re.compile(r"Utility failure\s*[-–—]?\s*(Electricity|Water|Communications)", re.I)

TABLE_ROW_RE = re.compile(r"\s*\|\s*")

ROLE_HINT_RE = re.compile(
    r"\b(director|manager|commander|officer|lead|coordinator|admin|accounts|logistic|"
    r"communication|comunication|cert|liaison|specialist|counsel|operation)\b",
    re.I,
)

EXTRA_COUNTRY_NAMES = (
    "Dominica",
    "Grenada",
    "Haiti",
    "Jamaica",
    "Barbados",
    "Trinidad and Tobago",
    "South Sudan",
    "Ukraine",
    "Myanmar",
)

_COUNTRY_LOOKUP = {
    country.lower(): country for country in (*COUNTRY_OPTIONS, *EXTRA_COUNTRY_NAMES) if country != "Other"
}


def _normalize_text(text: str) -> str:
    cleaned = text.replace("\u00a0", " ").replace("\ufffd", "")
    cleaned = re.sub(r"[•]\s*", "", cleaned)
    return cleaned


def _find_countries(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for key, country in sorted(_COUNTRY_LOOKUP.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(key)}\b", lowered) and country not in found:
            found.append(country)
    return found


def _extract_existing_plan(text: str) -> StructuredHit | None:
    match = PLAN_TITLE_RE.search(text)
    if not match:
        return None
    return (
        "existing_crisis_plan",
        "yes",
        "high",
        match.group(0)[:240],
    )


def _extract_organization(text: str) -> StructuredHit | None:
    match = ORG_NAME_RE.search(text)
    if not match:
        return None
    name = "IsraAID" if match.group(1).upper() == "ISRAAID" else match.group(1)
    return ("company_name", name, "high", match.group(0)[:240])


def _extract_countries(text: str) -> list[StructuredHit]:
    countries = _find_countries(text)
    if not countries:
        return []
    hits: list[StructuredHit] = []
    primary = countries[0]
    snippet = ", ".join(countries[:5])
    hits.append(("countries", countries, "high", snippet))
    hits.append(("headquarters_country", primary, "medium", f"Primary country referenced: {primary}"))
    return hits


def _extract_role_contacts(text: str, country: str | None = None) -> list[dict[str, str]]:
    contacts: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("•") or "\t" in stripped[:3]:
            continue
        if CRISIS_LEVEL_RE.search(stripped):
            continue
        if re.match(r"^Level\s+(one|two|three|\d)\b", stripped, re.I):
            continue
        match = ROLE_NAME_LINE_RE.match(stripped)
        if not match:
            generic = GENERIC_ROLE_NAME_RE.match(stripped)
            if not generic:
                continue
            role = re.sub(r"\s+", " ", generic.group("role").strip())
            name = generic.group("name").strip()
            if not ROLE_HINT_RE.search(role):
                continue
        else:
            role = re.sub(r"\s+", " ", match.group("role").strip())
            name = match.group("name").strip()
        if len(role) < 3 or len(name) < 2:
            continue
        if any(word in role.lower() for word in ("activate", "evaluate", "confirm", "communicate", "emergency")):
            continue
        if name.lower().startswith(("localized", "emergencies", "large scale")):
            continue
        key = f"{role}|{name}".lower()
        if key in seen:
            continue
        seen.add(key)
        contact: dict[str, str] = {"name": f"{role} — {name}"}
        if country:
            contact["country"] = country
        contacts.append(contact)
    return contacts


def _extract_crisis_team(text: str, country: str | None) -> StructuredHit | None:
    contacts = _extract_role_contacts(text, country)
    if not contacts:
        return None
    snippet = contacts[0]["name"]
    return ("crisis_team_structure", contacts, "high", snippet)


def _extract_after_hours(text: str, country: str | None) -> StructuredHit | None:
    leadership_roles = (
        "Country Director",
        "Regional Director",
        "Security and Compliance Director",
        "Incident Commander",
    )
    contacts = [
        contact
        for contact in _extract_role_contacts(text, country)
        if any(role in contact["name"] for role in leadership_roles)
    ]
    if not contacts:
        return None
    return ("after_hours_escalation", contacts, "medium", contacts[0]["name"])


def _extract_crisis_levels(text: str) -> StructuredHit | None:
    levels: list[dict[str, str]] = []
    for line in text.splitlines():
        match = CRISIS_LEVEL_RE.search(line.strip())
        if not match:
            continue
        token = match.group(1).lower()
        number = {"one": "1", "two": "2", "three": "3"}.get(token, token)
        levels.append({"level": number, "description": match.group(2).strip().rstrip(".")})
    if not levels:
        return None
    formatted = "; ".join(f"Level {item['level']}: {item['description']}" for item in levels)
    return ("crisis_levels", formatted, "high", formatted[:240])


def _extract_activation_criteria(text: str) -> StructuredHit | None:
    triggers: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.search(
            r"\b(alert to hq|decide the type and level of emergency|activate the emergency response team)\b",
            stripped,
            re.I,
        ):
            triggers.append(stripped)
    if not triggers:
        return None
    value = "\n".join(triggers[:8])
    return ("crisis_activation_criteria", value, "medium", triggers[0][:240])


def _extract_hazards(text: str) -> StructuredHit | None:
    hazards: list[str] = []
    in_hazard_section = False
    for line in text.splitlines():
        stripped = line.strip().rstrip(":")
        if re.search(r"Hazard Identification", stripped, re.I):
            in_hazard_section = True
            continue
        if in_hazard_section and re.match(r"^SCENARIO\b", stripped, re.I):
            break
        if not in_hazard_section:
            continue
        if not stripped or "|" in stripped:
            continue
        if re.match(r"^(Natural|Technological|Biological)$", stripped, re.I):
            continue
        if HAZARD_LINE_RE.match(stripped) or (
            len(stripped) < 45 and stripped[0].isupper() and " " not in stripped[:20]
        ):
            hazards.append(stripped)
    if not hazards:
        scenario_block = re.search(r"Scenarios:\s*(.+?)(?:Levels of emergency|OFFICE RESPONSE)", text, re.I | re.S)
        if scenario_block:
            for token in re.split(r"[\n:]+", scenario_block.group(1)):
                cleaned = token.strip().rstrip(":")
                if cleaned and len(cleaned) < 30 and cleaned.isupper():
                    hazards.append(cleaned.title())
    if not hazards:
        return None
    unique = list(dict.fromkeys(hazards))
    value = ", ".join(unique)
    return ("risk_register", value, "high", value[:240])


def _extract_utilities(text: str) -> StructuredHit | None:
    services: list[str] = []
    details: list[str] = []
    for line in text.splitlines():
        match = UTILITY_FAILURE_RE.search(line)
        if match:
            label = match.group(1).lower()
            if label == "electricity":
                services.append("electricity")
            elif label == "water":
                services.append("water")
            elif label == "communications":
                services.append("internet")
            details.append(line.strip())
    if not services:
        return None
    return (
        "utilities_dependencies",
        {"services": list(dict.fromkeys(services)), "details": "; ".join(details)},
        "medium",
        details[0][:240] if details else ", ".join(services),
    )


def _extract_internal_comms(text: str) -> StructuredHit | None:
    for line in text.splitlines():
        match = COMMS_STRATEGY_RE.search(line)
        if match:
            value = match.group(1).strip()
            return ("internal_comms_channels", value, "high", line.strip()[:240])
    if re.search(r"\bcall tree\b|\bwhatsapp\b", text, re.I):
        return ("internal_comms_channels", "Call tree and WhatsApp", "medium", "Call tree / WhatsApp referenced")
    return None


def _extract_escalation_matrix(text: str) -> StructuredHit | None:
    steps: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.search(r"\b(alert to hq|communication to hq|comunication to hq|give instructions to the team)\b", stripped, re.I):
            steps.append(stripped)
    if len(steps) < 2:
        return None
    value = "\n".join(steps)
    return ("escalation_matrix", value, "medium", steps[0][:240])


def _extract_sites(text: str, country: str | None) -> StructuredHit | None:
    sites: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not TABLE_ROW_RE.search(line):
            continue
        cells = [cell.strip() for cell in TABLE_ROW_RE.split(line) if cell.strip()]
        if len(cells) < 2:
            continue
        if cells[0].lower() == "area":
            for site_name in cells[1:]:
                if site_name.lower() in {"north", "south"}:
                    continue
                site: dict[str, Any] = {"name": site_name}
                if country:
                    site["country"] = country
                sites.append(site)
    roseau_match = re.search(r"\b(Roseau)\s+office\b", text, re.I)
    if roseau_match:
        sites.append(
            {
                "name": "Roseau office",
                "country": country or "Dominica",
                "primary_function": "country office",
            }
        )
    if not sites:
        return None
    deduped = list({site["name"]: site for site in sites}.values())
    return ("sites", deduped, "high", deduped[0]["name"])


def _extract_field_security(text: str) -> StructuredHit | None:
    sections: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.search(r"Shelter Plan|Office Security Bag|Go-Bags|Satellite Phones", stripped, re.I):
            capture = True
        if capture and stripped:
            sections.append(stripped)
        if capture and len(sections) >= 12:
            break
    if not sections:
        return None
    value = "\n".join(sections[:15])
    return ("field_team_security", value, "medium", sections[0][:240])


def _extract_drills(text: str) -> StructuredHit | None:
    if not re.search(r"\bDrills\b", text):
        return None
    for line in text.splitlines():
        if re.search(r"\bDrills\b", line):
            return ("emergency_drills_schedule", "Planned — see document", "low", line.strip()[:240])
    return None


def extract_structured_fields(text: str) -> list[StructuredHit]:
    """Return high-confidence field proposals detected in crisis-plan style documents."""
    normalized = _normalize_text(text)
    hits: list[StructuredHit] = []
    seen_fields: set[str] = set()

    def add(hit: StructuredHit | None) -> None:
        if hit is None:
            return
        field_path, _, _, _ = hit
        if field_path in seen_fields:
            return
        hits.append(hit)
        seen_fields.add(field_path)

    def add_many(items: list[StructuredHit]) -> None:
        for item in items:
            add(item)

    country = _find_countries(normalized)[0] if _find_countries(normalized) else None

    add(_extract_existing_plan(normalized))
    add(_extract_organization(normalized))
    add_many(_extract_countries(normalized))
    add(_extract_crisis_team(normalized, country))
    add(_extract_after_hours(normalized, country))
    add(_extract_crisis_levels(normalized))
    add(_extract_activation_criteria(normalized))
    add(_extract_hazards(normalized))
    add(_extract_utilities(normalized))
    add(_extract_internal_comms(normalized))
    add(_extract_escalation_matrix(normalized))
    add(_extract_sites(normalized, country))
    add(_extract_field_security(normalized))
    add(_extract_drills(normalized))

    return hits
