"""Real semantic embedding provider adapter (supports local Model2Vec/SentenceTransformers and APIs).
Never silently falls back to random or mock vectors.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Real semantic embedder adapter with explicit error handling (no silent mock fallback)."""

    def __init__(self, model_name: str = "minishlab/potion-multilingual-128M") -> None:
        if not model_name or not model_name.strip():
            raise ValueError("model_name must be provided (e.g. 'minishlab/potion-multilingual-128M')")

        self.model_name = model_name.strip()
        self.provider = "local_model2vec"
        self.cost_usd = 0.0
        self._model = None

        # Configure local HuggingFace cache inside starter/.cache/huggingface if present
        starter_dir = Path(__file__).resolve().parents[1]
        local_hf_cache = starter_dir / ".cache" / "huggingface"
        if local_hf_cache.exists():
            os.environ.setdefault("HF_HOME", str(local_hf_cache))
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

        if self.model_name.startswith("minishlab/"):
            try:
                from model2vec import StaticModel
            except ImportError as exc:
                raise RuntimeError(
                    "Thư viện 'model2vec' chưa được cài đặt. Chạy: pip install model2vec"
                ) from exc

            try:
                self._model = StaticModel.from_pretrained(self.model_name)
                sample_vec = self._model.encode(["kiểm tra kích thước vector"])
                self.dimensions = int(sample_vec.shape[1])
            except Exception as exc:
                raise RuntimeError(
                    f"Không thể khởi tạo mô hình embedding thật '{self.model_name}': {exc}. "
                    "Hệ thống từ chối fallback sang vector ngẫu nhiên/mock theo đúng quy tắc."
                ) from exc
        elif self.model_name.startswith("sentence-transformers/"):
            self.provider = "local_sentence_transformers"
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                self.dimensions = int(self._model.get_sentence_embedding_dimension())
            except Exception as exc:
                raise RuntimeError(
                    f"Không thể khởi tạo SentenceTransformer '{self.model_name}': {exc}"
                ) from exc
        else:
            raise RuntimeError(
                f"Mô hình '{self.model_name}' không được hỗ trợ hoặc thiếu cấu hình provider hợp lệ. "
                "Không tự động fallback sang mock vector."
            )

    @staticmethod
    def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        return matrix / norms

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Encode document chunks into L2-normalized semantic vectors in the same order."""
        if not texts:
            return []
        if self._model is None:
            raise RuntimeError("Embedder chưa được khởi tạo hợp lệ.")

        raw = np.asarray(self._model.encode(texts), dtype=np.float32)
        if raw.ndim != 2 or raw.shape[0] != len(texts) or raw.shape[1] != self.dimensions:
            raise RuntimeError(
                f"Kích thước vector trả về không hợp lệ: {raw.shape}, kỳ vọng ({len(texts)}, {self.dimensions})"
            )
        normed = self._l2_normalize(raw)
        return normed.tolist()

    def embed_query(self, question: str) -> list[float]:
        """Encode a single search query into a compatible L2-normalized semantic vector."""
        if not question or not question.strip():
            raise ValueError("Câu hỏi truy vấn (question) không được rỗng.")
        vectors = self.embed_documents([question.strip()])
        return vectors[0]
