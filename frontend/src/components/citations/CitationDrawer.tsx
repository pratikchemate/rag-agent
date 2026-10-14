import React from 'react';
import { ExternalLink, FileText, Quote, X } from 'lucide-react';
import { Citation } from '../../types';

interface CitationDrawerProps {
  citation: Citation | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenDocumentPreview: (docId: string) => void;
}

export const CitationDrawer: React.FC<CitationDrawerProps> = ({
  citation,
  isOpen,
  onClose,
  onOpenDocumentPreview,
}) => {
  if (!isOpen || !citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center sm:justify-end p-4 sm:p-0 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl sm:rounded-none sm:rounded-l-2xl max-w-md w-full h-[90vh] sm:h-full flex flex-col shadow-2xl border-l border-slate-200 animate-in slide-in-from-right duration-200">
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <span className="w-8 h-8 rounded-lg bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shadow-sm">
              {citation.label}
            </span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Source Evidence</h3>
              <p className="text-xs text-slate-500">Verified server-retrieved chunk</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center space-x-2 text-slate-500 text-xs font-medium">
              <FileText className="w-4 h-4 text-indigo-500" />
              <span>Document</span>
            </div>
            <p className="text-sm font-semibold text-slate-900 break-words">
              {citation.filename}
            </p>
            {citation.page_number && (
              <div className="inline-flex items-center px-2 py-0.5 rounded bg-slate-200 text-slate-700 text-xs font-medium">
                Page {citation.page_number}
              </div>
            )}
          </div>

          <div>
            <div className="flex items-center space-x-2 mb-2">
              <Quote className="w-4 h-4 text-indigo-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Grounding Excerpt
              </h4>
            </div>
            <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-100/80">
              <p className="text-xs text-slate-800 font-mono whitespace-pre-wrap leading-relaxed">
                {citation.excerpt}
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
            <p className="font-medium text-slate-700 mb-1">Citation Integrity</p>
            <p>
              This citation was mapped to an authenticated chunk record in PostgreSQL. The LLM cannot hallucinate arbitrary sources or URLs.
            </p>
          </div>
        </div>

        <div className="p-4 border-t border-slate-100 flex items-center justify-between">
          <button
            onClick={() => {
              onClose();
              onOpenDocumentPreview(citation.document_id);
            }}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 px-3 py-2 rounded-lg transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>View Full Document</span>
          </button>
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
