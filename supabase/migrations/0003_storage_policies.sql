-- 0003_storage_policies.sql
-- Storage bucket initialization and access control policies for Supabase Storage.

-- Insert private storage bucket if storage schema exists (in Supabase environments)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'storage') THEN
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'source-documents',
            'source-documents',
            false,
            5242880, -- 5MB in bytes
            ARRAY['application/pdf', 'text/plain', 'text/markdown', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        )
        ON CONFLICT (id) DO UPDATE SET
            public = false,
            file_size_limit = 5242880,
            allowed_mime_types = ARRAY['application/pdf', 'text/plain', 'text/markdown', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    END IF;
END $$;
