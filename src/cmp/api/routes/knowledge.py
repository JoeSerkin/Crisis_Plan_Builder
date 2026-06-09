"""Knowledge search API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from cmp.knowledge.search import search_knowledge

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search")
def knowledge_search(
    q: str = Query(min_length=2, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict[str, str | float]]:
    return search_knowledge(q, limit=limit)
