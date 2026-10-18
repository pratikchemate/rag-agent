import React, { useEffect, useMemo, useState } from 'react';
import { BookOpen, FileText, Loader2, Search, X } from 'lucide-react';
import { api } from '../../lib/api';
import { DocumentPreview } from '../../types';

interface PreviewModalProps {
  documentId: string | null;
  isOpen: boolean;
  onClose: () => void;
  token?: string;
}

export const PreviewModal: React.FC<PreviewModalProps> = ({
  documentId,
  isOpen,
  onClose,
  token,
}) => {
  const [preview, setPreview] = useState<DocumentPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chunkFilter, setChunkFilter] = useState('');

  useEffect(() => {
    if (!isOpen || !documentId) {
      setPreview(null);
      setChunkFilter('');
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    api
      .getDocumentPreview(documentId, token, controller.signal)
      .then((res) => setPreview(res))
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Failed to load document preview.');
        }
      })
      .finally(() => setLoading(false));

    return () => {
      controller.abort();
    };
  }, [isOpen, documentId, token]);

  const filteredChunks = useMemo(() => {
    if (!preview?.chunks) return [];
    if (!chunkFilter.trim()) return preview.chunks;
    return preview.chunks.filter((c) =>
      c.content.toLowerCase().includes(chunkFilter.toLowerCase())
    );
  }, [preview, chunkFilter]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[88vh] flex flex-col shadow-2xl border border-slate-200">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center border border-brand-200/60">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 truncate max-w-md">
                {preview?.document?.filename || 'Document Preview'}
              </h2>
              {preview && (
                <p className="text-xs text-slate-500 font-medium">
                  {preview.total_chunks} indexed chunks • {preview.document.content_type}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg transition-colors cursor-pointer"
            title="Close Preview"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Chunks Filter Bar */}
        {preview?.chunks && preview.chunks.length > 1 && (
          <div className="px-5 py-2.5 border-b border-slate-100 bg-white">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search within indexed chunks..."
                value={chunkFilter}
                onChange={(e) => setChunkFilter(e.target.value)}
                className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-slate-50/60 placeholder:text-slate-400"
              />
            </div>
          </div>
        )}

        {/* Chunks List */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <div className="py-20 text-center text-slate-500 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
              <p className="text-sm font-semibold">Loading document chunks from pgvector...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-50 text-red-700 text-xs font-medium border border-red-200">
              {error}
            </div>
          ) : filteredChunks.length > 0 ? (
            filteredChunks.map((chunk) => (
              <div
                key={chunk.chunk_index}
                className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-slate-300 transition-colors shadow-2xs"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-brand-100 text-brand-800">
                      Chunk #{chunk.chunk_index + 1}
                    </span>
                    {chunk.page_number && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-slate-200 text-slate-700">
                        Page {chunk.page_number}
                      </span>
                    )}
                  </div>
                  {chunk.start_index !== null && (
                    <span className="text-[11px] text-slate-400 font-mono">
                      byte offset: {chunk.start_index}
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-800 font-mono whitespace-pre-wrap leading-relaxed bg-white p-3.5 rounded-lg border border-slate-200/90 shadow-2xs">
                  {chunk.content}
                </div>
              </div>
            ))
          ) : (
            <div className="py-14 text-center text-slate-400">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm font-medium">No chunks match your search query.</p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/50">
          <span className="text-xs text-slate-500">
            {preview ? `Showing ${filteredChunks.length} of ${preview.total_chunks} chunks` : ''}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
