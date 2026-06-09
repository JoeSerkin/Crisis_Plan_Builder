"""Index and search knowledge base content (RAG foundation)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cmp.models.requirements import knowledge_root, load_requirements_catalog

_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    heading: str
    text: str

    def score(self, terms: set[str]) -> int:
        haystack = f"{self.heading} {self.text}".lower()
        return sum(haystack.count(term) for term in terms)


def _tokenize(query: str) -> set[str]:
    return {token for token in _TOKEN.findall(query.lower()) if len(token) > 2}


def _chunk_markdown(path: Path, root: Path) -> list[KnowledgeChunk]:
    rel = str(path.relative_to(root)).replace("\\", "/")
    text = path.read_text(encoding="utf-8")
    chunks: list[KnowledgeChunk] = []
    heading = path.stem
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if body:
                chunks.append(
                    KnowledgeChunk(
                        source=rel,
                        heading=heading,
                        text="\n".join(body).strip(),
                    )
                )
                body = []
            heading = line.lstrip("#").strip()
        else:
            body.append(line)
    if body:
        chunks.append(KnowledgeChunk(source=rel, heading=heading, text="\n".join(body).strip()))
    return [chunk for chunk in chunks if chunk.text]


def _chunk_requirements() -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for req in load_requirements_catalog():
        text = " ".join(
            part
            for part in (
                req.label,
                req.why_it_matters,
                req.question_template,
                " ".join(req.industry_tags or []),
            )
            if part
        )
        chunks.append(
            KnowledgeChunk(
                source="crisis_management/requirements_catalog.yaml",
                heading=f"{req.id} — {req.label}",
                text=text,
            )
        )
    return chunks


@lru_cache(maxsize=1)
def build_knowledge_index() -> tuple[KnowledgeChunk, ...]:
    root = knowledge_root()
    chunks: list[KnowledgeChunk] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml"}:
            continue
        if path.name == "requirements_catalog.yaml":
            continue
        if path.suffix.lower() == ".md":
            chunks.extend(_chunk_markdown(path, root))
    chunks.extend(_chunk_requirements())
    return tuple(chunks)


def search_knowledge(query: str, limit: int = 10) -> list[dict[str, str | float]]:
    terms = _tokenize(query)
    if not terms:
        return []

    scored: list[tuple[int, KnowledgeChunk]] = []
    for chunk in build_knowledge_index():
        score = chunk.score(terms)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, str | float]] = []
    for score, chunk in scored[:limit]:
        results.append(
            {
                "source": chunk.source,
                "heading": chunk.heading,
                "excerpt": chunk.text[:400],
                "score": float(score),
            }
        )
    return results


def clear_index_cache() -> None:
    build_knowledge_index.cache_clear()
