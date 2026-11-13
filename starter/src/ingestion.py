"""Read and normalize source data, preserving provenance and logging excluded/empty pages."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .models import DocumentPage

# Global log populated during load_pdf calls so the pipeline can persist full diagnostics
INGESTION_DIAGNOSTICS: list[dict[str, Any]] = []

_PARAGRAPH_START_RE = re.compile(
    r"^("
    r"Chương\s+\d+|"
    r"Phần\s+\d+|"
    r"Điều\s+\d+\.\d+|"
    r"\[Mã tài liệu:|"
    r"\[LOẠI TRANG:|"
    r"\[\d+\]\s+|"
    r"Trang\s+\d+:|"
    r"TRƯỜNG\s+ĐẠI\s+HỌC|"
    r"TRUNG\s+TÂM\s+HẠ\s+TẦNG|"
    r"SỔ\s+TAY\s+QUY\s+CHẾ|"
    r"QUY\s+ĐỊNH\s+KỸ\s+THUẬT|"
    r"MỤC\s+LỤC|"
    r"TÀI\s+LIỆU\s+THAM\s+KHẢO|"
    r"DANH\s+MỤC\s+TIÊU\s+CHUẨN"
    r")"
)

_METADATA_HEADER_RE = re.compile(
    r"\[Mã tài liệu:\s*(?P<doc_id>[^|\]]+?)\s*"
    r"\|\s*Năm ban hành:\s*(?P<year>\d{4})\s*"
    r"\|\s*Phiên bản:\s*(?P<version>[^|\]]+?)\s*"
    r"(?:\|\s*Danh mục:\s*(?P<category>[^|\]]+?)\s*)?"
    r"(?:\|\s*Đối tượng:\s*(?P<audience>[^|\]]+?)\s*)?"
    r"(?:\|\s*Chuyên mục:\s*(?P<section>[^|\]]+?)\s*)?\]"
)


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC) and whitespace while preserving paragraph structure."""
    if not text:
        return ""

    # 1. Normalize Unicode to canonical composition (NFC) for Vietnamese diacritics
    cleaned = unicodedata.normalize("NFC", text)

    # 2. Remove zero-width characters, BOM, soft hyphens, and replace common ligatures
    cleaned = (
        cleaned.replace("\u200b", "")
        .replace("\ufeff", "")
        .replace("\u00ad", "")
        .replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
        .replace("\u00a0", " ")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    # 3. Reconstruct paragraphs from PDF line-wrapped text while preserving explicit breaks
    raw_lines = cleaned.split("\n")
    paragraphs: list[str] = []
    current_lines: list[str] = []

    for raw_line in raw_lines:
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if current_lines:
                paragraphs.append(" ".join(current_lines))
                current_lines = []
            continue

        if _PARAGRAPH_START_RE.match(line) and current_lines:
            paragraphs.append(" ".join(current_lines))
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        paragraphs.append(" ".join(current_lines))

    normalized = "\n\n".join(p.strip() for p in paragraphs if p.strip())
    return normalized.strip()


def _extract_page_metadata(
    norm_text: str, document_id: str, source: str, page_number: int
) -> dict[str, Any]:
    """Extract deterministic metadata fields directly from the normalized page header."""
    meta: dict[str, Any] = {
        "document_id": document_id,
        "source": source,
        "page": page_number,
    }
    match = _METADATA_HEADER_RE.search(norm_text)
    if match:
        groups = match.groupdict()
        if groups.get("year"):
            meta["year"] = int(groups["year"].strip())
        if groups.get("version"):
            meta["version"] = groups["version"].strip()
        if groups.get("category"):
            meta["category"] = groups["category"].strip()
        if groups.get("audience"):
            meta["audience"] = groups["audience"].strip()
        if groups.get("section"):
            meta["section"] = groups["section"].strip()

    first_line = norm_text.split("\n\n", 1)[0].strip() if norm_text else ""
    if first_line and not first_line.startswith("["):
        meta["heading"] = first_line
    meta["char_count"] = len(norm_text)
    return meta


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical page; keep its page number and source.

    Detects and records pages with no text (empty/blank scan pages) as well as
    non-content pages (cover, table of contents, references-only pages) in
    INGESTION_DIAGNOSTICS, returning only valid content pages.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF source file not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    valid_pages: list[DocumentPage] = []

    for idx, pdf_page in enumerate(reader.pages):
        page_num = idx + 1
        raw_text = pdf_page.extract_text() or ""
        norm_text = normalize_text(raw_text)
        char_count = len(norm_text)

        # Classify page to exclude empty, cover, TOC, and reference-only pages per GUIDE.md
        if char_count < 50:
            INGESTION_DIAGNOSTICS.append(
                {
                    "document_id": document_id,
                    "source": source,
                    "page": page_num,
                    "status": "excluded",
                    "reason": "empty_or_unreadable_page",
                    "detail": f"Trang trống hoặc không trích xuất được văn bản ({char_count} ký tự < 50 ký tự tối thiểu).",
                    "char_count": char_count,
                }
            )
            continue

        if "[LOẠI TRANG: TRANG BÌA]" in norm_text:
            INGESTION_DIAGNOSTICS.append(
                {
                    "document_id": document_id,
                    "source": source,
                    "page": page_num,
                    "status": "excluded",
                    "reason": "cover_page",
                    "detail": "Trang bìa tài liệu (cover page) — loại trừ theo quy tắc đếm trang nội dung.",
                    "char_count": char_count,
                }
            )
            continue

        if "[LOẠI TRANG: MỤC LỤC]" in norm_text:
            INGESTION_DIAGNOSTICS.append(
                {
                    "document_id": document_id,
                    "source": source,
                    "page": page_num,
                    "status": "excluded",
                    "reason": "toc_page",
                    "detail": "Trang mục lục (table of contents) — loại trừ theo quy tắc đếm trang nội dung.",
                    "char_count": char_count,
                }
            )
            continue

        if "[LOẠI TRANG: TÀI LIỆU THAM KHẢO]" in norm_text:
            INGESTION_DIAGNOSTICS.append(
                {
                    "document_id": document_id,
                    "source": source,
                    "page": page_num,
                    "status": "excluded",
                    "reason": "references_page",
                    "detail": "Trang chỉ chứa danh mục tài liệu tham khảo (references only) — loại trừ theo quy tắc.",
                    "char_count": char_count,
                }
            )
            continue

        metadata = _extract_page_metadata(norm_text, document_id, source, page_num)
        INGESTION_DIAGNOSTICS.append(
            {
                "document_id": document_id,
                "source": source,
                "page": page_num,
                "status": "accepted",
                "reason": "valid_content_page",
                "section": metadata.get("section"),
                "year": metadata.get("year"),
                "category": metadata.get("category"),
                "char_count": char_count,
            }
        )
        valid_pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_num,
                text=norm_text,
                metadata=metadata,
            )
        )

    return valid_pages
