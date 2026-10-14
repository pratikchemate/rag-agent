import React, { useEffect, useState } from 'react';
import { BookOpen, FileText, Loader2, X } from 'lucide-react';
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

  useEffect(() => {
    if (!isOpen || !documentId) {
      setPreview(null);
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 truncate max-w-md">
                {preview?.document?.filename || 'Document Preview'}
              </h2>
              {preview && (
                <p className="text-xs text-slate-500">
                  {preview.total_chunks} indexed chunks
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <div className="py-16 text-center text-slate-500 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
              <p className="text-sm">Loading document chunks...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-50 text-red-700 text-xs font-medium border border-red-200">
              {error}
            </div>
          ) : preview?.chunks && preview.chunks.length > 0 ? (
            preview.chunks.map((chunk) => (
              <div
                key={chunk.chunk_index}
                className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                      Chunk #{chunk.chunk_index + 1}
                    </span>
                    {chunk.page_number && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                        Page {chunk.page_number}
                      </span>
                    )}
                  </div>
                  {chunk.start_index !== null && (
                    <span className="text-[11px] text-slate-400 font-mono">
                      offset: {chunk.start_index}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-700 font-mono whitespace-pre-wrap leading-relaxed bg-white p-3 rounded-lg border border-slate-200">
                  {chunk.content}
                </p>
              </div>
            ))
          ) : (
            <div className="py-12 text-center text-slate-400">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No chunks found for this document.</p>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
