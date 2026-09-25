import asyncio
from collections.abc import Sequence

from fastembed import TextEmbedding

from app.core.config import Settings


class FastEmbedService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = TextEmbedding(model_name=settings.embedding_model)

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, list(texts))

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for start in range(0, len(texts), self._settings.embedding_batch_size):
            batch = texts[start : start + self._settings.embedding_batch_size]
            embeddings = list(self._model.embed(batch))
            results.extend(embedding.tolist() for embedding in embeddings)
        return results
