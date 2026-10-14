-- 0002_indexes_and_search.sql
-- Indexes for ownership lookups, deduplication, full-text search, and vector search.

-- Partial unique index on documents to deduplicate while permitting retry on failed uploads
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_owner_checksum 
ON documents (owner_id, checksum_sha256) 
WHERE status <> 'failed';

-- Index for listing documents by owner and public flag
CREATE INDEX IF NOT EXISTS idx_documents_owner_id ON documents (owner_id);
CREATE INDEX IF NOT EXISTS idx_documents_is_public ON documents (is_public) WHERE is_public = true;

-- Indexes for document chunks lookup by document and owner
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_owner_id ON document_chunks (owner_id);

-- GIN index for full-text search on search_vector
CREATE INDEX IF NOT EXISTS idx_document_chunks_search_vector ON document_chunks USING GIN (search_vector);
