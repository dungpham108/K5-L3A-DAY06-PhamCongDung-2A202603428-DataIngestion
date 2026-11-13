"""End-to-end Day 06 Data Ingestion & Retrieval Benchmark Pipeline."""
from __future__ import annotations

import json
import os
import shutil
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import _clean_for_match, evaluate_query, summarize
from .ingestion import INGESTION_DIAGNOSTICS, load_pdf
from .models import Chunk, DocumentPage
from .store import PgVectorStore, QdrantLocalStore

STARTER_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = STARTER_DIR.parent


def _load_manifest_and_pages() -> tuple[dict[str, Any], list[DocumentPage]]:
    manifest_path = ROOT_DIR / "data" / "manifest.json"
    if not manifest_path.exists():
        manifest_path = STARTER_DIR / "data" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Không tìm thấy data/manifest.json. Hãy chạy: python starter/scripts/build_corpus.py"
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    INGESTION_DIAGNOSTICS.clear()

    all_valid_pages: list[DocumentPage] = []
    for doc_entry in manifest["documents"]:
        doc_id = doc_entry["document_id"]
        rel_source = doc_entry["source_path_or_url"]
        pdf_path = ROOT_DIR / rel_source
        if not pdf_path.exists():
            pdf_path = STARTER_DIR / doc_entry.get("starter_path", "")
        pages = load_pdf(pdf_path, document_id=doc_id, source=rel_source)
        all_valid_pages.extend(pages)

    if len(all_valid_pages) < 30:
        raise RuntimeError(
            f"Corpus chỉ có {len(all_valid_pages)} trang nội dung hợp lệ (< 30 trang tối thiểu theo GUIDE.md)."
        )
    return manifest, all_valid_pages


def _verify_benchmark_evidence(
    questions: list[dict[str, Any]], pages: list[DocumentPage]
) -> list[dict[str, Any]]:
    page_lookup = {(p.document_id, int(p.page)): p for p in pages}
    verification_log: list[dict[str, Any]] = []

    for q in questions:
        qid = q["id"]
        gold_key = (q["gold_source_id"], int(q["gold_page"]))
        if gold_key not in page_lookup:
            raise ValueError(
                f"Câu hỏi {qid} tham chiếu tới trang không tồn tại trong tập trang hợp lệ: {gold_key}"
            )
        page_obj = page_lookup[gold_key]
        page_norm = _clean_for_match(page_obj.text)
        quote_norm = _clean_for_match(q["evidence_quote"])
        verified = quote_norm in page_norm
        if not verified:
            raise ValueError(
                f"Evidence quote của câu hỏi {qid} không khớp nguyên văn trên {gold_key}:\n"
                f"Quote: {q['evidence_quote']}"
            )
        verification_log.append(
            {
                "question_id": qid,
                "split": q["split"],
                "gold_source_id": q["gold_source_id"],
                "gold_page": int(q["gold_page"]),
                "evidence_char_len": len(q["evidence_quote"]),
                "verified_in_normalized_page": True,
            }
        )
    return verification_log


def _compute_chunk_stats(chunks: list[Chunk]) -> dict[str, Any]:
    lengths = [len(c.text) for c in chunks]
    total_chars = sum(lengths)
    # Approximate token count for Vietnamese/multilingual subword tokenizer (~3.8 chars/token)
    approx_tokens = int(round(total_chars / 3.8))
    return {
        "chunk_count": len(chunks),
        "total_chars": total_chars,
        "approx_tokens": approx_tokens,
        "min_chars": min(lengths) if lengths else 0,
        "max_chars": max(lengths) if lengths else 0,
        "mean_chars": round(statistics.mean(lengths), 1) if lengths else 0.0,
        "median_chars": round(statistics.median(lengths), 1) if lengths else 0.0,
        "stdev_chars": round(statistics.stdev(lengths), 1) if len(lengths) > 1 else 0.0,
    }


def _init_store(dimensions: int) -> PgVectorStore | QdrantLocalStore:
    backend = os.getenv("VECTOR_BACKEND", "qdrant").strip().lower()
    if backend == "pgvector":
        db_url = os.getenv("DATABASE_URL", "")
        store = PgVectorStore(database_url=db_url, dimensions=dimensions)
        store.create_schema()
        return store

    qdrant_rel = os.getenv("QDRANT_PATH", "results/qdrant_storage")
    qdrant_path = ROOT_DIR / qdrant_rel
    store = QdrantLocalStore(storage_path=qdrant_path, dimensions=dimensions)
    store.create_schema()
    return store


def main() -> None:
    """Run the complete Day 06 ingestion, indexing, retrieval, and evaluation pipeline."""
    load_dotenv(STARTER_DIR / ".env")
    run_started_at = datetime.now(timezone.utc).isoformat()

    # 1. Load corpus and verify >= 30 valid content pages
    manifest, valid_pages = _load_manifest_and_pages()
    print(
        f"[1/5] Loaded corpus: {len(valid_pages)} valid content pages "
        f"(from {len(INGESTION_DIAGNOSTICS)} physical pages)."
    )

    # Load benchmark and verify gold evidence before running retrieval
    bench_path = ROOT_DIR / "benchmark" / "questions.json"
    if not bench_path.exists():
        bench_path = STARTER_DIR / "data" / "benchmark.json"
    bench_data = json.loads(bench_path.read_text(encoding="utf-8"))
    questions: list[dict[str, Any]] = bench_data["questions"]
    evidence_verification = _verify_benchmark_evidence(questions, valid_pages)
    print(
        f"[2/5] Verified all {len(questions)} benchmark questions "
        f"({bench_data['dev_count']} dev / {bench_data['test_count']} test) against normalized pages."
    )

    # 2. Initialize real semantic embedder and persistent vector store
    model_name = os.getenv("EMBEDDING_MODEL", "minishlab/potion-multilingual-128M").strip()
    embedder = MyEmbedder(model_name=model_name)
    store = _init_store(dimensions=embedder.dimensions)
    print(
        f"[3/5] Initialized Embedder '{embedder.model_name}' (dim={embedder.dimensions}) "
        f"and Vector Store '{store.backend_name}'."
    )

    # 3. Build, embed, and index Strategies A, B, and C
    strategies_config: dict[str, dict[str, Any]] = {
        "A": {
            "name": "A",
            "description": "Fixed-size chunking (size=500, overlap=50), attach metadata, no filter at retrieval",
            "chunking_type": "fixed_size",
            "chunk_size": 500,
            "overlap": 50,
            "apply_filter": False,
        },
        "B": {
            "name": "B",
            "description": "Structure-aware paragraph/heading chunking (max_size=750), same metadata, no filter at retrieval",
            "chunking_type": "by_paragraph",
            "chunk_size": 750,
            "overlap": 0,
            "apply_filter": False,
        },
        "C": {
            "name": "C",
            "description": "Identical paragraph/heading chunking as B (max_size=750) + pre-retrieval metadata filtering when question has filter",
            "chunking_type": "by_paragraph",
            "chunk_size": 750,
            "overlap": 0,
            "apply_filter": True,
        },
    }

    strategy_chunks: dict[str, list[Chunk]] = {}
    strategy_stats: dict[str, dict[str, Any]] = {}
    reingestion_checks: dict[str, Any] = {}

    for strat_key, cfg in strategies_config.items():
        t0 = time.perf_counter()
        chunks: list[Chunk] = []
        for page in valid_pages:
            if cfg["chunking_type"] == "fixed_size":
                page_chunks = fixed_size(page, size=cfg["chunk_size"], overlap=cfg["overlap"])
            else:
                page_chunks = by_paragraph(page, max_size=cfg["chunk_size"])
            chunks.extend(page_chunks)

        texts = [c.text for c in chunks]
        vectors = embedder.embed_documents(texts)
        store.upsert(strategy=strat_key, chunks=chunks, vectors=vectors)
        ingest_elapsed = round(time.perf_counter() - t0, 4)

        count_after_first = store.count_chunks(strat_key)
        # Re-ingest the exact same chunks to verify idempotency (no duplicates)
        store.upsert(strategy=strat_key, chunks=chunks, vectors=vectors)
        count_after_second = store.count_chunks(strat_key)

        cstats = _compute_chunk_stats(chunks)
        cstats["ingest_time_sec"] = ingest_elapsed
        cstats["cost_usd"] = 0.0
        cstats["stored_count_first_ingest"] = count_after_first
        cstats["stored_count_reingest"] = count_after_second
        cstats["idempotent_no_duplicates"] = count_after_first == count_after_second == len(chunks)

        strategy_chunks[strat_key] = chunks
        strategy_stats[strat_key] = {**cfg, **cstats}
        reingestion_checks[strat_key] = {
            "expected_chunks": len(chunks),
            "count_after_first_upsert": count_after_first,
            "count_after_second_upsert": count_after_second,
            "no_duplicates_verified": count_after_first == count_after_second == len(chunks),
        }
        print(
            f"  -> Strategy {strat_key}: {len(chunks)} chunks | mean={cstats['mean_chars']} chars | "
            f"ingest={ingest_elapsed}s | idempotent={cstats['idempotent_no_duplicates']}"
        )

    # Also verify obsolete chunk deletion when a source document shrinks/changes
    sample_three = strategy_chunks["B"][:3]
    sample_vecs = embedder.embed_documents([c.text for c in sample_three])
    store.upsert("test_obsolete_cleanup", sample_three, sample_vecs)
    cnt_3 = store.count_chunks("test_obsolete_cleanup")
    store.upsert("test_obsolete_cleanup", sample_three[:2], sample_vecs[:2])
    cnt_2 = store.count_chunks("test_obsolete_cleanup")
    # Clean up the temporary test strategy
    if isinstance(store, QdrantLocalStore):
        from qdrant_client import models as qmodels

        store.client.delete(
            collection_name=store.COLLECTION_NAME,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="strategy", match=qmodels.MatchValue(value="test_obsolete_cleanup")
                        )
                    ]
                )
            ),
        )
    reingestion_checks["obsolete_chunk_cleanup_test"] = {
        "initial_doc_chunks": cnt_3,
        "after_doc_shrunk_to_2_chunks": cnt_2,
        "obsolete_chunk_removed_verified": (cnt_3 == 3 and cnt_2 == 2),
    }

    # 4. Run all 20 benchmark questions across Strategies A, B, and C
    all_traces: list[dict[str, Any]] = []
    for strat_key, cfg in strategies_config.items():
        q_t0 = time.perf_counter()
        for q in questions:
            q_vec = embedder.embed_query(q["question"])
            active_filter = q.get("filter") if cfg["apply_filter"] else None
            hits = store.search(
                strategy=strat_key,
                query_vector=q_vec,
                top_k=3,
                filters=active_filter,
            )
            q_with_ctx = {
                **q,
                "_strategy": strat_key,
                "_filter_applied": active_filter,
            }
            trace = evaluate_query(q_with_ctx, hits)
            all_traces.append(trace)
        strategy_stats[strat_key]["query_time_sec"] = round(time.perf_counter() - q_t0, 4)
        strategy_stats[strat_key]["total_time_sec"] = round(
            strategy_stats[strat_key]["ingest_time_sec"]
            + strategy_stats[strat_key]["query_time_sec"],
            4,
        )

    metrics_by_strategy = summarize(all_traces)
    print("[4/5] Completed retrieval evaluation across Strategies A, B, and C:")
    for strat_key in ["A", "B", "C"]:
        dev_m = metrics_by_strategy[strat_key]["dev"]
        test_m = metrics_by_strategy[strat_key]["test"]
        print(
            f"  Strategy {strat_key} | DEV Hit@1={dev_m['hit_at_1_fraction']} "
            f"Hit@3={dev_m['evidence_hit_at_3_fraction']} (Filter={dev_m['filter_compliance_fraction']}) | "
            f"TEST Hit@1={test_m['hit_at_1_fraction']} "
            f"Hit@3={test_m['evidence_hit_at_3_fraction']} (Filter={test_m['filter_compliance_fraction']})"
        )

    # 5. Prepare the pre-registered 10 source positions (first 10 sorted valid page IDs) for Chunk Coherence
    sorted_first_10_pages = sorted(valid_pages, key=lambda p: (p.document_id, p.page))[:10]
    coherence_positions: list[dict[str, Any]] = []
    for pos_idx, page in enumerate(sorted_first_10_pages, start=1):
        # Anchor at Điều X.2 on each of the first 10 sorted pages (middle article of the page)
        paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
        anchor_para = next((p for p in paragraphs if ".2." in p[:12]), paragraphs[-1])
        anchor_snippet = anchor_para[:90]

        covering_by_strategy: dict[str, list[dict[str, Any]]] = {}
        for strat_key in ["A", "B", "C"]:
            page_chunks = [
                c
                for c in strategy_chunks[strat_key]
                if c.document_id == page.document_id and c.page == page.page
            ]
            # Chunks that overlap with the anchor paragraph
            matching = [
                {
                    "chunk_id": c.chunk_id,
                    "char_len": len(c.text),
                    "text": c.text,
                }
                for c in page_chunks
                if anchor_snippet[:35] in c.text or anchor_para[-35:] in c.text
            ]
            covering_by_strategy[strat_key] = matching

        coherence_positions.append(
            {
                "position_id": f"pos_{pos_idx:02d}",
                "page_id": f"{page.document_id}_p{page.page:02d}",
                "document_id": page.document_id,
                "source": page.source,
                "page": page.page,
                "section": page.metadata.get("section"),
                "anchor_clause": anchor_para,
                "covering_chunks": covering_by_strategy,
            }
        )

    # Save all outputs to both results/ and starter/results/
    for out_dir in [ROOT_DIR / "results", STARTER_DIR / "results"]:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "ingestion_log.json").write_text(
            json.dumps(
                {
                    "run_timestamp": run_started_at,
                    "total_physical_pages": len(INGESTION_DIAGNOSTICS),
                    "valid_content_pages": len(valid_pages),
                    "excluded_pages": len(INGESTION_DIAGNOSTICS) - len(valid_pages),
                    "page_diagnostics": INGESTION_DIAGNOSTICS,
                    "benchmark_evidence_verification": evidence_verification,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (out_dir / "reingestion_check.json").write_text(
            json.dumps(reingestion_checks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out_dir / "metrics_summary.json").write_text(
            json.dumps(
                {
                    "run_timestamp": run_started_at,
                    "embedding_model": {
                        "provider": embedder.provider,
                        "model_name": embedder.model_name,
                        "dimensions": embedder.dimensions,
                        "query_document_handling": "Cùng không gian vector L2-normalized 256 chiều (StaticModel distillation từ BAAI/bge-m3)",
                        "cost_usd": 0.0,
                    },
                    "vector_store": {
                        "backend": store.backend_name,
                        "distance_metric": "Cosine Similarity (Exact Search)",
                        "persistent_path": str(getattr(store, "storage_path", "postgresql")),
                    },
                    "strategy_stats": strategy_stats,
                    "retrieval_metrics": metrics_by_strategy,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (out_dir / "traces_all.json").write_text(
            json.dumps(all_traces, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_dir / "traces_dev.json").write_text(
            json.dumps([t for t in all_traces if t["split"] == "dev"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out_dir / "traces_test.json").write_text(
            json.dumps([t for t in all_traces if t["split"] == "test"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out_dir / "coherence_samples_raw.json").write_text(
            json.dumps(coherence_positions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if isinstance(store, QdrantLocalStore):
        store.close()
        # Copy persistent Qdrant storage to starter/results/qdrant_storage as well
        src_qdrant = ROOT_DIR / "results" / "qdrant_storage"
        dst_qdrant = STARTER_DIR / "results" / "qdrant_storage"
        if src_qdrant.exists() and src_qdrant.resolve() != dst_qdrant.resolve():
            if dst_qdrant.exists():
                shutil.rmtree(dst_qdrant)
            shutil.copytree(src_qdrant, dst_qdrant)

    print("[5/5] Saved all traces, metrics, ingestion logs, and audit samples to results/ and starter/results/.")


if __name__ == "__main__":
    main()
