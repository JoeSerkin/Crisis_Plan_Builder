"""FastAPI dependency helpers."""

from __future__ import annotations

from cmp.storage.engagement_store import EngagementStore


def get_store() -> EngagementStore:
    return EngagementStore()
