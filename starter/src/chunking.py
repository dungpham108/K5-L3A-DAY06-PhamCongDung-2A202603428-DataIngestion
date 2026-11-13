"""Implement fixed-size and structure-aware (paragraph/heading) chunking."""
from __future__ import annotations

import re
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split page text into overlapping fixed-size character windows and retain page metadata."""
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")

    text = page.text.strip()
    if not text:
        return []

    step = size - overlap
    chunks: list[Chunk] = []
    start = 0
    idx = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + size, text_len)
        window = text[start:end].strip()
        if window:
            idx += 1
            chunk_id = f"{page.document_id}_p{page.page:02d}_fix_{idx:02d}"
            meta = {
                **page.metadata,
                "document_id": page.document_id,
                "source": page.source,
                "page": page.page,
                "chunk_index": idx,
                "char_start": start,
                "char_end": end,
                "char_len": len(window),
                "chunking_method": f"fixed_size_{size}_{overlap}",
            }
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=window,
                    metadata=meta,
                )
            )
        if end >= text_len:
            break
        start += step

    return chunks


def _split_oversized_paragraph(paragraph: str, max_size: int) -> list[str]:
    """Split a paragraph larger than max_size along sentence boundaries before hard slicing."""
    sentences = re.split(r"(?<=[.!?;])\s+", paragraph.strip())
    pieces: list[str] = []
    current = ""

    for sent in sentences:
        if not sent:
            continue
        candidate = f"{current} {sent}".strip() if current else sent
        if len(candidate) <= max_size:
            current = candidate
        else:
            if current:
                pieces.append(current)
            if len(sent) <= max_size:
                current = sent
            else:
                # Hard slice if a single sentence is still longer than max_size
                for i in range(0, len(sent), max_size):
                    part = sent[i : i + max_size].strip()
                    if part:
                        pieces.append(part)
                current = ""

    if current:
        pieces.append(current)
    return pieces


def by_paragraph(page: DocumentPage, max_size: int = 750) -> list[Chunk]:
    """Group paragraphs by heading/clause structure, split oversized paragraphs, and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")

    raw_paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
    if not raw_paragraphs:
        return []

    # Separate header lines (chapter title & metadata tag) from substantive articles (Điều X.Y)
    header_lines: list[str] = []
    body_paragraphs: list[str] = []
    for p in raw_paragraphs:
        if p.startswith("[Mã tài liệu:") or p.startswith("Chương ") or p.startswith("Phần "):
            header_lines.append(p)
        else:
            body_paragraphs.append(p)

    heading_prefix = ""
    for h in header_lines:
        if h.startswith("Chương ") or h.startswith("Phần "):
            heading_prefix = h
            break

    if not body_paragraphs:
        body_paragraphs = raw_paragraphs

    grouped_texts: list[str] = []
    current_group = ""

    for para in body_paragraphs:
        # Attach chapter heading context to each clause if it fits within max_size, or group short paragraphs
        enriched_para = f"{heading_prefix}\n{para}" if heading_prefix and not para.startswith(heading_prefix) else para
        if len(enriched_para) > max_size:
            if current_group:
                grouped_texts.append(current_group)
                current_group = ""
            # Try without heading_prefix first if para itself fits in max_size
            if len(para) <= max_size:
                grouped_texts.append(para)
            else:
                grouped_texts.extend(_split_oversized_paragraph(para, max_size))
        else:
            if not current_group:
                current_group = enriched_para
            else:
                combined = f"{current_group}\n\n{para}"
                if len(combined) <= max_size:
                    current_group = combined
                else:
                    grouped_texts.append(current_group)
                    current_group = enriched_para

    if current_group:
        grouped_texts.append(current_group)

    chunks: list[Chunk] = []
    for idx, chunk_text in enumerate(grouped_texts, start=1):
        chunk_id = f"{page.document_id}_p{page.page:02d}_para_{idx:02d}"
        meta = {
            **page.metadata,
            "document_id": page.document_id,
            "source": page.source,
            "page": page.page,
            "chunk_index": idx,
            "char_len": len(chunk_text),
            "chunking_method": f"by_paragraph_{max_size}",
        }
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=meta,
            )
        )

    return chunks
