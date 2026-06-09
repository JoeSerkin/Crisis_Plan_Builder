"""SQLite + JSON file engagement storage."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cmp.models.requirements import repo_root
from cmp.models.schemas import ClientIntake, EngagementRecord


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EngagementStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or repo_root()
        self.storage_dir = self.root / "storage" / "engagements"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "storage" / "engagements.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS engagements (
                    engagement_id TEXT PRIMARY KEY,
                    client_name TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'discovery',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_requirement_ids TEXT NOT NULL DEFAULT '[]',
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    engagement_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(engagement_id, artifact_type, version)
                )
                """
            )
            conn.commit()

    def engagement_dir(self, engagement_id: str) -> Path:
        path = self.storage_dir / engagement_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def upsert_engagement(self, record: EngagementRecord) -> None:
        record.updated_at = _utc_now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO engagements (
                    engagement_id, client_name, industry, status,
                    created_at, updated_at, resolved_requirement_ids, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(engagement_id) DO UPDATE SET
                    client_name=excluded.client_name,
                    industry=excluded.industry,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    resolved_requirement_ids=excluded.resolved_requirement_ids,
                    notes=excluded.notes
                """,
                (
                    record.engagement_id,
                    record.client_name,
                    record.industry,
                    record.status,
                    record.created_at,
                    record.updated_at,
                    json.dumps(record.resolved_requirement_ids),
                    record.notes,
                ),
            )
            conn.commit()

    def get_engagement(self, engagement_id: str) -> EngagementRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM engagements WHERE engagement_id = ?",
                (engagement_id,),
            ).fetchone()
        if row is None:
            return None
        return EngagementRecord(
            engagement_id=row["engagement_id"],
            client_name=row["client_name"],
            industry=row["industry"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            resolved_requirement_ids=json.loads(row["resolved_requirement_ids"]),
            notes=row["notes"] or "",
        )

    def save_intake(self, engagement_id: str, intake: ClientIntake) -> Path:
        path = self.engagement_dir(engagement_id) / "intake.json"
        path.write_text(
            json.dumps(intake.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    def load_intake(self, engagement_id: str) -> ClientIntake | None:
        path = self.engagement_dir(engagement_id) / "intake.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ClientIntake.model_validate(data)

    def merge_intake(self, engagement_id: str, updates: dict[str, Any]) -> ClientIntake:
        existing = self.load_intake(engagement_id)
        if existing is None:
            raise FileNotFoundError(f"No intake found for engagement {engagement_id}")
        base = existing.model_dump()
        additional = dict(base.get("additional_context") or {})
        for key, value in updates.items():
            if key in ("company_name", "industry", "employees", "countries", "legal_entities", "sites"):
                base[key] = value
            else:
                additional[key] = value
        base["additional_context"] = additional
        merged = ClientIntake.model_validate(base)
        self.save_intake(engagement_id, merged)
        record = self.get_engagement(engagement_id)
        if record:
            record.updated_at = _utc_now()
            self.upsert_engagement(record)
        return merged

    def mark_resolved(self, engagement_id: str, requirement_ids: list[str]) -> EngagementRecord:
        record = self.get_engagement(engagement_id)
        if record is None:
            raise FileNotFoundError(f"Engagement {engagement_id} not found")
        resolved = set(record.resolved_requirement_ids)
        resolved.update(requirement_ids)
        record.resolved_requirement_ids = sorted(resolved)
        self.upsert_engagement(record)
        return record

    def save_artifact(
        self,
        engagement_id: str,
        artifact_type: str,
        payload: dict[str, Any],
        version: int | None = None,
    ) -> Path:
        artifact_dir = self.engagement_dir(engagement_id) / artifact_type
        artifact_dir.mkdir(parents=True, exist_ok=True)
        if version is None:
            existing = list(artifact_dir.glob("v*.json"))
            version = len(existing) + 1
        path = artifact_dir / f"v{version}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO artifacts
                (engagement_id, artifact_type, version, path, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (engagement_id, artifact_type, version, str(path), _utc_now()),
            )
            conn.commit()
        return path

    def load_latest_artifact(self, engagement_id: str, artifact_type: str) -> dict[str, Any] | None:
        artifact_dir = self.engagement_dir(engagement_id) / artifact_type
        if not artifact_dir.exists():
            return None
        files = sorted(artifact_dir.glob("v*.json"))
        if not files:
            return None
        return json.loads(files[-1].read_text(encoding="utf-8"))
