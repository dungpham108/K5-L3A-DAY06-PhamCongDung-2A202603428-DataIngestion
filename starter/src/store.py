"""Store and search vectors with persistent storage, cosine similarity, and safe metadata filtering.
Provides both PgVectorStore (PostgreSQL + pgvector) and QdrantLocalStore (Qdrant persistent on-disk store).
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import psycopg
from qdrant_client import QdrantClient, models

from .models import Chunk

ALLOWED_FILTER_KEYS = {
    "year",
    "section",
    "category",
    "audience",
    "version",
    "document_id",
    "source",
    "page",
}


def _validate_inputs(
    strategy: str, chunks: list[Chunk], vectors: list[list[float]], dimensions: int
) -> None:
    if not strategy or not strategy.strip():
        raise ValueError("strategy must be a non-empty string")
    if len(chunks) != len(vectors):
        raise ValueError(
            f"Length mismatch: got {len(chunks)} chunks vs {len(vectors)} vectors"
        )
    for i, vec in enumerate(vectors):
        if len(vec) != dimensions:
            raise ValueError(
                f"Vector at index {i} has dimension {len(vec)}, expected {dimensions}"
            )


def _validate_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    if not filters:
        return {}
    clean: dict[str, Any] = {}
    for k, v in filters.items():
        if k not in ALLOWED_FILTER_KEYS:
            raise ValueError(
                f"Disallowed metadata filter key '{k}'. Allowed keys: {sorted(ALLOWED_FILTER_KEYS)}"
            )
        if v is not None:
            clean[k] = v
    return clean


class PgVectorStore:
    """PostgreSQL + pgvector persistent store using cosine distance (<=>) and parameterized SQL."""

    def __init__(self, database_url: str, dimensions: int) -> None:
        if not database_url or not database_url.strip():
            raise ValueError("database_url must be non-empty")
        if dimensions <= 0:
            raise ValueError("dimensions must be a positive integer")
        self.database_url = database_url.strip()
        self.dimensions = int(dimensions)
        self.backend_name = "postgresql_pgvector"

    def create_schema(self) -> None:
        """Create pgvector extension and chunks table with metadata and cosine support."""
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS chunks (
                        strategy TEXT NOT NULL,
                        chunk_id TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INTEGER NOT NULL,
                        year INTEGER,
                        section TEXT,
                        category TEXT,
                        audience TEXT,
                        version TEXT,
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.dimensions}) NOT NULL,
                        PRIMARY KEY (strategy, chunk_id)
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chunks_strategy_filter "
                    "ON chunks (strategy, year, section, category);"
                )
            conn.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate dimensions, remove obsolete chunks for re-ingested documents, and upsert without duplicates."""
        _validate_inputs(strategy, chunks, vectors, self.dimensions)
        if not chunks:
            return

        doc_to_chunk_ids: dict[str, list[str]] = {}
        for c in chunks:
            doc_to_chunk_ids.setdefault(c.document_id, []).append(c.chunk_id)

        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Remove obsolete chunks belonging to re-ingested source documents
                for doc_id, active_ids in doc_to_chunk_ids.items():
                    cur.execute(
                        """
                        DELETE FROM chunks
                        WHERE strategy = %s
                          AND document_id = %s
                          AND NOT (chunk_id = ANY(%s));
                        """,
                        (strategy, doc_id, active_ids),
                    )

                for chunk, vec in zip(chunks, vectors):
                    vec_literal = "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"
                    meta = {
                        **chunk.metadata,
                        "document_id": chunk.document_id,
                        "source": chunk.source,
                        "page": chunk.page,
                    }
                    cur.execute(
                        """
                        INSERT INTO chunks (
                            strategy, chunk_id, document_id, source, page,
                            year, section, category, audience, version,
                            text, metadata, embedding
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s::jsonb, %s::vector
                        )
                        ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                            document_id = EXCLUDED.document_id,
                            source = EXCLUDED.source,
                            page = EXCLUDED.page,
                            year = EXCLUDED.year,
                            section = EXCLUDED.section,
                            category = EXCLUDED.category,
                            audience = EXCLUDED.audience,
                            version = EXCLUDED.version,
                            text = EXCLUDED.text,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding;
                        """,
                        (
                            strategy,
                            chunk.chunk_id,
                            chunk.document_id,
                            chunk.source,
                            int(chunk.page),
                            meta.get("year"),
                            meta.get("section"),
                            meta.get("category"),
                            meta.get("audience"),
                            meta.get("version"),
                            chunk.text,
                            json.dumps(meta, ensure_ascii=False),
                            vec_literal,
                        ),
                    )
            conn.commit()

    def count_chunks(self, strategy: str) -> int:
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chunks WHERE strategy = %s;", (strategy,))
                row = cur.fetchone()
                return int(row[0]) if row else 0

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter permitted metadata with parameterized SQL, rank by cosine distance, return top-k."""
        if len(query_vector) != self.dimensions:
            raise ValueError(
                f"Query vector dimension {len(query_vector)} != store dimension {self.dimensions}"
            )
        clean_filters = _validate_filters(filters)
        vec_literal = "[" + ",".join(f"{float(x):.8f}" for x in query_vector) + "]"

        where_clauses = ["strategy = %s"]
        params: list[Any] = [vec_literal, strategy]

        for col, val in clean_filters.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        params.append(vec_literal)
        params.append(int(top_k))

        where_sql = " AND ".join(where_clauses)
        query_sql = f"""
            SELECT
                chunk_id,
                document_id,
                source,
                page,
                text,
                metadata,
                1.0 - (embedding <=> %s::vector) AS cosine_similarity
            FROM chunks
            WHERE {where_sql}
            ORDER BY embedding <=> %s::vector ASC
            LIMIT %s;
        """

        results: list[dict[str, Any]] = []
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(query_sql, tuple(params))
                for row in cur.fetchall():
                    chunk_id, doc_id, source, page, text, metadata, score = row
                    meta_dict = metadata if isinstance(metadata, dict) else json.loads(metadata)
                    results.append(
                        {
                            "chunk_id": chunk_id,
                            "document_id": doc_id,
                            "source": source,
                            "page": int(page),
                            "text": text,
                            "score": round(float(score), 6),
                            "metadata": meta_dict,
                        }
                    )
        return results


class QdrantLocalStore:
    """Persistent on-disk Qdrant vector store with cosine similarity and payload metadata filtering."""

    COLLECTION_NAME = "day06_knowledge_chunks"

    def __init__(self, storage_path: str | Path, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be a positive integer")
        self.storage_path = Path(storage_path).resolve()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.dimensions = int(dimensions)
        self.backend_name = "qdrant_persistent_local"
        self.client = QdrantClient(path=str(self.storage_path))

    def create_schema(self) -> None:
        """Create persistent Qdrant collection with Cosine distance if not already present."""
        existing = [c.name for c in self.client.get_collections().collections]
        if self.COLLECTION_NAME in existing:
            info = self.client.get_collection(self.COLLECTION_NAME)
            current_dim = info.config.params.vectors.size  # type: ignore[union-attr]
            if current_dim != self.dimensions:
                self.client.delete_collection(self.COLLECTION_NAME)
                existing.remove(self.COLLECTION_NAME)

        if self.COLLECTION_NAME not in existing:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.dimensions,
                    distance=models.Distance.COSINE,
                ),
            )

    @staticmethod
    def _point_uuid(strategy: str, chunk_id: str) -> str:
        """Generate a deterministic UUID5 from (strategy, chunk_id) for idempotent upserts."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"day06:{strategy}:{chunk_id}"))

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths/dimensions, delete obsolete chunks for changed docs, and upsert deterministically."""
        _validate_inputs(strategy, chunks, vectors, self.dimensions)
        if not chunks:
            return

        doc_to_active_ids: dict[str, set[str]] = {}
        for c in chunks:
            doc_to_active_ids.setdefault(c.document_id, set()).add(c.chunk_id)

        # Clean up obsolete chunks belonging to any re-ingested document_id under this strategy
        for doc_id, active_chunk_ids in doc_to_active_ids.items():
            existing_points, _ = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="strategy", match=models.MatchValue(value=strategy)
                        ),
                        models.FieldCondition(
                            key="document_id", match=models.MatchValue(value=doc_id)
                        ),
                    ]
                ),
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )
            obsolete_point_ids = [
                pt.id
                for pt in existing_points
                if pt.payload and pt.payload.get("chunk_id") not in active_chunk_ids
            ]
            if obsolete_point_ids:
                self.client.delete(
                    collection_name=self.COLLECTION_NAME,
                    points_selector=models.PointIdsList(points=obsolete_point_ids),
                )

        points: list[models.PointStruct] = []
        for chunk, vec in zip(chunks, vectors):
            meta = {
                **chunk.metadata,
                "document_id": chunk.document_id,
                "source": chunk.source,
                "page": int(chunk.page),
            }
            payload = {
                "strategy": strategy,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "source": chunk.source,
                "page": int(chunk.page),
                "year": meta.get("year"),
                "section": meta.get("section"),
                "category": meta.get("category"),
                "audience": meta.get("audience"),
                "version": meta.get("version"),
                "text": chunk.text,
                "metadata": meta,
            }
            points.append(
                models.PointStruct(
                    id=self._point_uuid(strategy, chunk.chunk_id),
                    vector=[float(x) for x in vec],
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=self.COLLECTION_NAME, points=points)

    def count_chunks(self, strategy: str) -> int:
        res = self.client.count(
            collection_name=self.COLLECTION_NAME,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="strategy", match=models.MatchValue(value=strategy)
                    )
                ]
            ),
            exact=True,
        )
        return int(res.count)

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter permitted metadata in Qdrant payload, rank by exact cosine similarity, return top-k."""
        if len(query_vector) != self.dimensions:
            raise ValueError(
                f"Query vector dimension {len(query_vector)} != store dimension {self.dimensions}"
            )
        clean_filters = _validate_filters(filters)

        must_conditions: list[models.Condition] = [
            models.FieldCondition(key="strategy", match=models.MatchValue(value=strategy))
        ]
        for key, value in clean_filters.items():
            must_conditions.append(
                models.FieldCondition(key=key, match=models.MatchValue(value=value))
            )

        response = self.client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=[float(x) for x in query_vector],
            query_filter=models.Filter(must=must_conditions),
            limit=int(top_k),
            with_payload=True,
            with_vectors=False,
        )

        hits: list[dict[str, Any]] = []
        for pt in response.points:
            payload = pt.payload or {}
            hits.append(
                {
                    "chunk_id": payload.get("chunk_id"),
                    "document_id": payload.get("document_id"),
                    "source": payload.get("source"),
                    "page": int(payload.get("page", 0)),
                    "text": payload.get("text", ""),
                    "score": round(float(pt.score), 6),
                    "metadata": payload.get("metadata", {}),
                }
            )
        return hits

    def close(self) -> None:
        self.client.close()
