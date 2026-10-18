import React, { useState } from 'react';
import { Check, Copy, ExternalLink, FileText, Quote, ShieldCheck, X } from 'lucide-react';
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
  const [copied, setCopied] = useState(false);

  if (!isOpen || !citation) return null;

  const handleCopyExcerpt = () => {
    navigator.clipboard.writeText(citation.excerpt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center sm:justify-end p-4 sm:p-0 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl sm:rounded-none sm:rounded-l-2xl max-w-md w-full h-[90vh] sm:h-full flex flex-col shadow-2xl border-l border-slate-200 animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <span className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 text-white font-extrabold text-xs flex items-center justify-center shadow-xs shadow-brand-500/20 font-mono">
              {citation.label}
            </span>
            <div>
              <div className="flex items-center space-x-1.5">
                <h3 className="text-sm font-bold text-slate-900">Source Evidence</h3>
                <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <ShieldCheck className="w-3 h-3 mr-0.5 text-emerald-600" />
                  Verified
                </span>
              </div>
              <p className="text-[11px] text-slate-500">PostgreSQL pgvector chunk record</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg transition-colors cursor-pointer"
            title="Close Drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* File Card */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 space-y-2">
            <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
              <span className="flex items-center space-x-1.5">
                <FileText className="w-4 h-4 text-brand-600" />
                <span>Source Document</span>
              </span>
              {citation.page_number && (
                <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 font-mono text-[11px]">
                  Page {citation.page_number}
                </span>
              )}
            </div>
            <p className="text-sm font-bold text-slate-900 break-words">
              {citation.filename}
            </p>
          </div>

          {/* Excerpt Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-1.5">
                <Quote className="w-4 h-4 text-brand-600" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Exact Grounding Excerpt
                </h4>
              </div>
              <button
                onClick={handleCopyExcerpt}
                className="inline-flex items-center space-x-1 text-[11px] font-semibold text-slate-500 hover:text-slate-800 px-2 py-0.5 rounded hover:bg-slate-100 transition-colors cursor-pointer"
                title="Copy excerpt"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-600" />
                    <span className="text-emerald-600">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <div className="p-4 rounded-xl bg-brand-50/40 border border-brand-100 text-xs text-slate-800 font-mono whitespace-pre-wrap leading-relaxed shadow-2xs">
              {citation.excerpt}
            </div>
          </div>

          {/* Integrity Guarantee Card */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
            <p className="font-bold text-slate-800 flex items-center space-x-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Grounded Evidence Pipeline</span>
            </p>
            <p className="text-[11px] leading-relaxed text-slate-500">
              This citation was mapped to an authentic embedded chunk in Supabase pgvector. The model factory enforces regex-level claim verification to prevent hallucinated URLs or false references.
            </p>
          </div>
        </div>

        {/* Drawer Footer Actions */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-white">
          <button
            onClick={() => {
              onClose();
              onOpenDocumentPreview(citation.document_id);
            }}
            className="inline-flex items-center space-x-1.5 text-xs font-bold text-brand-600 hover:text-brand-700 hover:bg-brand-50 px-3.5 py-2 rounded-xl border border-brand-200 transition-colors cursor-pointer"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Open Full Document</span>
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};
