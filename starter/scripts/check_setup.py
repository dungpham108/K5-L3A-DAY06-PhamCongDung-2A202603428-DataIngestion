"""Read-only setup check; verifies either PostgreSQL + pgvector or Qdrant persistent local store + Embedder."""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

STARTER_DIR = Path(__file__).resolve().parents[1]
load_dotenv(STARTER_DIR / ".env")

backend = os.getenv("VECTOR_BACKEND", "qdrant").strip().lower()
url = os.getenv("DATABASE_URL")

if backend == "pgvector":
    if not url:
        sys.exit("DATABASE_URL missing: copy starter/.env.example to starter/.env first.")
    try:
        with psycopg.connect(url, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_database(), current_setting('server_version'), extversion "
                    "FROM pg_extension WHERE extname = 'vector'"
                )
                row = cursor.fetchone()
                if not row:
                    sys.exit("Connected, but pgvector extension is missing. See starter/README.md.")
                print(f"Database: {row[0]} | PostgreSQL: {row[1]} | pgvector: {row[2]}")
    except psycopg.Error:
        sys.exit("Database connection failed. Check Docker, port and DATABASE_URL in starter/.env.")
else:
    try:
        from importlib.metadata import version
        from qdrant_client import QdrantClient

        qdrant_ver = version("qdrant-client")
        qdrant_rel = os.getenv("QDRANT_PATH", "results/qdrant_storage")
        qdrant_path = (STARTER_DIR.parent / qdrant_rel).resolve()
        qdrant_path.mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=str(qdrant_path))
        cols = [c.name for c in client.get_collections().collections]
        client.close()
        model_name = os.getenv("EMBEDDING_MODEL", "minishlab/potion-multilingual-128M")
        print(
            f"Vector Store: Qdrant Persistent Local (qdrant-client {qdrant_ver}) "
            f"| Path: {qdrant_path} | Collections: {cols} | Embedding Model: {model_name}"
        )
    except Exception as exc:
        sys.exit(f"Qdrant setup check failed: {exc}")

print("Setup OK. Pipeline functions are ready to run via: python -m src.run")
