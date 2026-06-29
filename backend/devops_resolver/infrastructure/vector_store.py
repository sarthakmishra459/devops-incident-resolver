import hashlib
import math
from dataclasses import dataclass

import faiss
import numpy as np
from numpy.typing import NDArray

from devops_resolver.domain.models import KnowledgeDocument
from devops_resolver.domain.repositories import KnowledgeRepository


def _tokenize(text: str) -> list[str]:
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in text)
    return [token for token in cleaned.split() if len(token) > 2]


class HashingEmbeddingModel:
    """Deterministic embedding model that works without external services."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> NDArray[np.float32]:
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for token in _tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector /= norm
        return vector


@dataclass(frozen=True)
class SearchResult:
    document: KnowledgeDocument
    score: float


class FaissKnowledgeIndex:
    def __init__(
        self, repository: KnowledgeRepository, embeddings: HashingEmbeddingModel | None = None
    ) -> None:
        self._repository = repository
        self._embeddings = embeddings or HashingEmbeddingModel()
        self._documents: list[KnowledgeDocument] = []
        self._index: faiss.IndexFlatIP | None = None

    async def hydrate(self) -> None:
        self._documents = await self._repository.all_documents()
        index = faiss.IndexFlatIP(self._embeddings.dimensions)
        if self._documents:
            matrix = np.vstack(
                [self._embeddings.embed(f"{doc.title}\n{doc.content}") for doc in self._documents]
            )
            index.add(matrix)
        self._index = index

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if self._index is None:
            await self.hydrate()
        if self._index is None or not self._documents:
            return []

        query_vector = self._embeddings.embed(query).reshape(1, -1)
        scores, indexes = self._index.search(query_vector, min(limit, len(self._documents)))
        results: list[SearchResult] = []
        for score, index in zip(scores[0], indexes[0], strict=True):
            if index < 0 or math.isnan(float(score)):
                continue
            results.append(SearchResult(document=self._documents[int(index)], score=float(score)))
        return results
