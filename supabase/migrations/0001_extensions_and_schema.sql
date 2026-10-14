-- 0001_extensions_and_schema.sql
-- Enables extensions and creates primary tables with Row-Level Security enabled.

-- Enable pgvector extension (schema-qualified for Supabase compatibility)
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- Function and trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 1. documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')),
    chunk_count INTEGER NOT NULL DEFAULT 0,
    error_code TEXT NULL,
    is_public BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trigger_update_documents_updated_at ON documents;
CREATE TRIGGER trigger_update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 2. document_chunks table
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER NULL,
    start_index INTEGER NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_chunk_index UNIQUE (document_id, chunk_index)
);

-- 3. feedback table
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    request_id UUID NOT NULL,
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    comment TEXT NULL CHECK (char_length(comment) <= 1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. daily_usage_counters table (survives worker restarts/spindowns)
CREATE TABLE IF NOT EXISTS daily_usage_counters (
    usage_date DATE PRIMARY KEY,
    call_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Mandatory Row Level Security (RLS) - Deny by default on all tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_usage_counters ENABLE ROW LEVEL SECURITY;

-- Note: No permissive policies are granted to 'anon' or 'authenticated' roles.
-- The FastAPI backend connects with database credentials/service role that bypasses RLS.
-- This ensures Supabase Data API access with publishable/anon key returns 0 rows.
