"""Local FastEmbed embeddings service."""

from typing import List, Optional

from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_embedding_instance: Optional[TextEmbedding] = None


class EmbeddingService(Embeddings):
    """Provides local embedding generation using FastEmbed, compliant with LangChain Embeddings."""

    def __init__(self, model_name: Optional[str] = None, cache_dir: Optional[str] = None):
        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.cache_dir = cache_dir or settings.EMBEDDING_CACHE_DIR
        self.threads = settings.EMBEDDING_THREADS
        self.batch_size = settings.EMBEDDING_BATCH_SIZE

    def _get_model(self) -> TextEmbedding:
        """Lazily initialize the FastEmbed model once per process."""
        global _embedding_instance
        if _embedding_instance is None:
            logger.info(
                f"Initializing FastEmbed model '{self.model_name}' (threads={self.threads})"
            )
            _embedding_instance = TextEmbedding(
                model_name=self.model_name,
                cache_dir=self.cache_dir,
                threads=self.threads,
            )
        return _embedding_instance

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document chunk texts."""
        if not texts:
            return []
        model = self._get_model()
        # FastEmbed returns a generator of numpy arrays
        embeddings_gen = model.embed(texts, batch_size=self.batch_size)
        return [embedding.tolist() for embedding in embeddings_gen]

    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query."""
        model = self._get_model()
        # bge models can be queried via query_embed or standard embed
        # FastEmbed's query_embed applies the bge query instruction prefix
        embeddings_gen = model.query_embed([query])
        return next(embeddings_gen).tolist()


_default_service: Optional[EmbeddingService] = None

# Alias for standard LangChain component convention
FastEmbedEmbeddings = EmbeddingService


def get_embedding_service() -> EmbeddingService:
    """Return default embedding service."""
    global _default_service
    if _default_service is None:
        _default_service = EmbeddingService()
    return _default_service
