"""Evaluate retrieved evidence and preserve per-query top-3 traces and split summaries."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def _clean_for_match(text: str) -> str:
    """Normalize Unicode NFC and collapse whitespace for verbatim evidence substring check."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFC", text)
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def _check_filter_compliance(hit_meta: dict[str, Any], required_filter: dict[str, Any] | None) -> bool:
    if not required_filter:
        return True
    for k, expected_val in required_filter.items():
        if hit_meta.get(k) != expected_val:
            return False
    return True


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and full gold evidence containment; preserve full top-3 trace.

    A hit requires BOTH:
      1. Matching gold_source_id and gold_page (or a documented alternative gold source/page).
      2. Containing the full gold evidence_quote (or a documented alternative evidence quote).
    Also detects when evidence on the gold page was split across multiple chunks.
    """
    gold_source = question["gold_source_id"]
    gold_page = int(question["gold_page"])
    gold_quote_norm = _clean_for_match(question["evidence_quote"])

    alt_sources: list[tuple[str, int]] = [
        ( item["gold_source_id"], int(item["gold_page"]) )
        for item in question.get("alt_gold_locations", [])
    ]
    valid_locations = {(gold_source, gold_page), *alt_sources}

    alt_quotes_norm = [
        _clean_for_match(q) for q in question.get("alt_evidence_quotes", []) if q
    ]
    valid_quotes = [gold_quote_norm, *alt_quotes_norm]

    req_filter = question.get("filter")
    top_hits = hits[:3]
    evaluated_hits: list[dict[str, Any]] = []

    for rank_idx, h in enumerate(top_hits, start=1):
        h_doc = h.get("document_id") or h.get("metadata", {}).get("document_id")
        h_page = int(h.get("page") or h.get("metadata", {}).get("page") or 0)
        h_text_norm = _clean_for_match(h.get("text", ""))
        h_meta = h.get("metadata", {})

        loc_match = (h_doc, h_page) in valid_locations
        quote_match = any(q and q in h_text_norm for q in valid_quotes)
        is_hit = bool(loc_match and quote_match)

        # Check if chunk is on the right page and has at least a 40-char prefix or suffix of the gold quote
        partial_overlap = False
        if loc_match and not quote_match and len(gold_quote_norm) >= 40:
            prefix = gold_quote_norm[:40]
            suffix = gold_quote_norm[-40:]
            if prefix in h_text_norm or suffix in h_text_norm:
                partial_overlap = True

        filter_ok = _check_filter_compliance(h_meta, req_filter)

        evaluated_hits.append(
            {
                "rank": rank_idx,
                "chunk_id": h.get("chunk_id"),
                "document_id": h_doc,
                "source": h.get("source"),
                "page": h_page,
                "score": h.get("score"),
                "text": h.get("text"),
                "metadata": h_meta,
                "location_match": loc_match,
                "evidence_quote_match": quote_match,
                "is_evidence_hit": is_hit,
                "partial_evidence_fragment": partial_overlap,
                "matches_question_filter": filter_ok,
            }
        )

    hit_at_1 = 1 if (evaluated_hits and evaluated_hits[0]["is_evidence_hit"]) else 0
    evidence_hit_at_3 = 1 if any(item["is_evidence_hit"] for item in evaluated_hits) else 0
    page_hit_at_3 = 1 if any(item["location_match"] for item in evaluated_hits) else 0

    # Check if combining text of top-3 chunks from the gold page reconstructs the split evidence
    gold_page_combined = " ".join(
        _clean_for_match(item["text"]) for item in evaluated_hits if item["location_match"]
    )
    multi_chunk_union_hit = 1 if any(q and q in gold_page_combined for q in valid_quotes) else 0
    evidence_split_error = bool(page_hit_at_3 == 1 and evidence_hit_at_3 == 0)

    has_filter = bool(req_filter)
    top3_filter_compliant = (
        all(item["matches_question_filter"] for item in evaluated_hits)
        if (has_filter and evaluated_hits)
        else (False if has_filter else None)
    )

    return {
        "question_id": question["id"],
        "split": question["split"],
        "question_type": question.get("type", "general"),
        "question": question["question"],
        "expected_answer": question.get("expected_answer", ""),
        "gold_source_id": gold_source,
        "gold_page": gold_page,
        "evidence_quote": question["evidence_quote"],
        "question_filter": req_filter,
        "strategy": question.get("_strategy", ""),
        "filter_applied_in_search": question.get("_filter_applied", None),
        "hit_at_1": hit_at_1,
        "evidence_hit_at_3": evidence_hit_at_3,
        "page_hit_at_3_diagnostic": page_hit_at_3,
        "multi_chunk_union_hit_at_3_diagnostic": multi_chunk_union_hit,
        "evidence_split_across_chunks_error": evidence_split_error,
        "top3_filter_compliant": top3_filter_compliant,
        "top_3_hits": evaluated_hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1, Evidence Hit@3, and filter compliance by strategy and dev/test split."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for tr in traces:
        strat = tr.get("strategy", "unknown")
        split = tr.get("split", "unknown")
        grouped.setdefault((strat, split), []).append(tr)

    summary_rows: dict[str, dict[str, Any]] = {}
    for (strat, split), items in sorted(grouped.items()):
        n_total = len(items)
        hit1_sum = sum(int(x["hit_at_1"]) for x in items)
        hit3_sum = sum(int(x["evidence_hit_at_3"]) for x in items)
        page_hit3_sum = sum(int(x.get("page_hit_at_3_diagnostic", 0)) for x in items)
        split_err_sum = sum(1 for x in items if x.get("evidence_split_across_chunks_error"))

        filter_items = [x for x in items if x.get("question_filter")]
        n_filter = len(filter_items)
        if n_filter > 0:
            n_filter_ok = sum(1 for x in filter_items if x.get("top3_filter_compliant") is True)
            filter_fraction = f"{n_filter_ok}/{n_filter}"
            filter_rate = round(n_filter_ok / n_filter, 4)
        else:
            n_filter_ok = 0
            filter_fraction = "N/A"
            filter_rate = None

        summary_rows.setdefault(strat, {})[split] = {
            "strategy": strat,
            "split": split,
            "total_questions": n_total,
            "hit_at_1_count": hit1_sum,
            "hit_at_1_fraction": f"{hit1_sum}/{n_total}",
            "hit_at_1_rate": round(hit1_sum / n_total, 4) if n_total else 0.0,
            "evidence_hit_at_3_count": hit3_sum,
            "evidence_hit_at_3_fraction": f"{hit3_sum}/{n_total}",
            "evidence_hit_at_3_rate": round(hit3_sum / n_total, 4) if n_total else 0.0,
            "page_hit_at_3_diagnostic_fraction": f"{page_hit3_sum}/{n_total}",
            "evidence_split_error_count": split_err_sum,
            "filter_questions_count": n_filter,
            "filter_compliant_count": n_filter_ok,
            "filter_compliance_fraction": filter_fraction,
            "filter_compliance_rate": filter_rate,
        }

    return summary_rows
