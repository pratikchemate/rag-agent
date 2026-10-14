"""Document chunking service using LangChain RecursiveCharacterTextSplitter."""

from dataclasses import dataclass
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.services.document_parser import ParsedDocument


@dataclass
class DocumentChunkData:
    """Prepared chunk data prior to embedding."""

    chunk_index: int
    page_number: Optional[int]
    start_index: Optional[int]
    content: str


class ChunkingService:
    """Splits parsed documents into stable, sized chunks with page metadata."""

    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.max_chunks = settings.MAX_CHUNKS_PER_DOCUMENT

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            add_start_index=True,
            strip_whitespace=True,
        )

    def chunk_document(self, parsed_doc: ParsedDocument) -> List[DocumentChunkData]:
        """Split parsed pages into chunks preserving page numbers and bounds."""
        chunks: List[DocumentChunkData] = []
        global_chunk_index = 0

        for page in parsed_doc.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            # Split individual page text to prevent cross-page citation drift
            split_docs = self.splitter.create_documents(
                texts=[page_text],
                metadatas=[{"page_number": page.page_number}],
            )

            for doc in split_docs:
                content = doc.page_content.strip()
                if not content:
                    continue

                chunks.append(
                    DocumentChunkData(
                        chunk_index=global_chunk_index,
                        page_number=page.page_number,
                        start_index=doc.metadata.get("start_index"),
                        content=content,
                    )
                )
                global_chunk_index += 1

                if global_chunk_index > self.max_chunks:
                    raise BadRequestError(
                        f"Document produced {global_chunk_index} chunks, exceeding limit of {self.max_chunks} chunks."
                    )

        if not chunks:
            raise BadRequestError("Document produced no valid text chunks after splitting.")

        return chunks


_default_chunker: Optional[ChunkingService] = None


def get_chunking_service() -> ChunkingService:
    """Return default chunking service."""
    global _default_chunker
    if _default_chunker is None:
        _default_chunker = ChunkingService()
    return _default_chunker
