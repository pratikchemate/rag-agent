export interface DocumentItem {
  id: string;
  filename: string;
  content_type: string;
  file_size_bytes: number;
  status: 'processing' | 'ready' | 'failed';
  chunk_count: number;
  error_code?: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunkPreview {
  id?: string;
  document_id?: string;
  chunk_index: number;
  page_number: number | null;
  start_index: number | null;
  content: string;
}

export interface DocumentPreview {
  document: DocumentItem;
  total_chunks: number;
  chunks: DocumentChunkPreview[];
}

export interface Citation {
  label: string;
  document_id: string;
  chunk_id: string;
  filename: string;
  page_number: number | null;
  excerpt: string;
}

export interface RetrievalMetadata {
  mode: string;
  attempts: number;
  returned_chunks: number;
  vector_count?: number;
  keyword_count?: number;
  top_similarity?: number;
}

export interface ChatResponse {
  request_id: string;
  answer: string;
  abstained: boolean;
  citations: Citation[];
  retrieval: RetrievalMetadata;
  timings_ms: {
    retrieval?: number;
    generation?: number;
    total?: number;
  };
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  abstained?: boolean;
  citations?: Citation[];
  retrieval?: RetrievalMetadata;
  timings_ms?: {
    retrieval?: number;
    generation?: number;
    total?: number;
  };
  timestamp: Date;
  error?: string;
  errorCode?: string;
  resetAt?: string;
  feedbackSubmitted?: boolean;
}

export interface FeedbackRequest {
  request_id: string;
  rating: number; // 1 or -1
  comment?: string;
}

export interface FeedbackResponse {
  id: string;
  request_id: string;
  status: string;
  message?: string;
}

