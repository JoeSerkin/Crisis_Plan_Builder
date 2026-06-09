"""Convert markdown deliverables to DOCX for client delivery."""

from __future__ import annotations

import re
from pathlib import Path

from cmp.models.requirements import repo_root

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^(\s*)[-*]\s+(.*)$")
_TABLE_ROW = re.compile(r"^\|(.+)\|$")


def _require_docx():
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError as exc:
        raise ImportError(
            "python-docx is required for DOCX export. Install with: pip install -e '.[docx]'"
        ) from exc
    return Document, Pt


def markdown_to_docx(markdown_text: str, title: str | None = None) -> "Document":
    Document, Pt = _require_docx()
    doc = Document()
    if title:
        doc.add_heading(title, level=0)

    for line in markdown_text.splitlines():
        if not line.strip():
            continue
        heading = _HEADING.match(line)
        if heading:
            level = min(len(heading.group(1)), 4)
            doc.add_heading(heading.group(2).strip(), level=level)
            continue
        bullet = _BULLET.match(line)
        if bullet:
            doc.add_paragraph(bullet.group(2).strip(), style="List Bullet")
            continue
        if _TABLE_ROW.match(line):
            doc.add_paragraph(line.strip())
            continue
        doc.add_paragraph(line.strip())

    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(11)
    return doc


def export_engagement_docx(
    engagement_id: str,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    source_dir = repo_root() / "output" / engagement_id
    if not source_dir.exists():
        raise FileNotFoundError(f"No deliverables found for engagement {engagement_id}")

    target_dir = output_dir or (source_dir / "docx")
    target_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    markdown_files = [
        path
        for path in source_dir.rglob("*.md")
        if "docx" not in path.parts
    ]
    if not markdown_files:
        raise FileNotFoundError(f"No markdown deliverables in {source_dir}")

    for md_path in markdown_files:
        rel = md_path.relative_to(source_dir)
        docx_name = rel.with_suffix(".docx")
        docx_path = target_dir / docx_name
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        content = md_path.read_text(encoding="utf-8")
        title = md_path.stem.replace("_", " ").title()
        doc = markdown_to_docx(content, title=title)
        doc.save(str(docx_path))
        paths[str(rel.with_suffix(".docx")).replace("\\", "/")] = docx_path

    return paths
