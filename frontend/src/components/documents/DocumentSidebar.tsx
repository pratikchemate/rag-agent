import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Eye,
  FileCode,
  FileText,
  Filter,
  Globe,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react';
import { DocumentItem } from '../../types';

interface DocumentSidebarProps {
  documents: DocumentItem[];
  selectedDocIds: string[];
  onToggleSelectDoc: (id: string) => void;
  onSelectAllDocs: (select: boolean) => void;
  onOpenUpload: () => void;
  onOpenPreview: (id: string) => void;
  onDeleteDocument: (id: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
}

export const DocumentSidebar: React.FC<DocumentSidebarProps> = ({
  documents,
  selectedDocIds,
  onToggleSelectDoc,
  onSelectAllDocs,
  onOpenUpload,
  onOpenPreview,
  onDeleteDocument,
  onRefresh,
  isLoading,
  isOpenMobile,
  onCloseMobile,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  // Auto-poll if any document is in 'processing' status
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === 'processing');
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      onRefresh();
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, onRefresh]);

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const allSelected =
    filteredDocs.length > 0 &&
    filteredDocs.every((d) => selectedDocIds.includes(d.id));

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getFileIcon = (contentType: string) => {
    if (contentType.includes('pdf')) return <FileText className="w-4 h-4 text-rose-500" />;
    if (contentType.includes('markdown') || contentType.includes('text')) {
      return <FileCode className="w-4 h-4 text-indigo-500" />;
    }
    return <FileText className="w-4 h-4 text-slate-500" />;
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpenMobile && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-slate-900/50 z-30 lg:hidden backdrop-blur-sm"
        />
      )}

      <aside
        className={`fixed lg:static top-16 bottom-0 left-0 z-30 w-80 bg-white border-r border-slate-200 flex flex-col transition-transform duration-200 ease-in-out ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Header & Actions */}
        <div className="p-4 border-b border-slate-100 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-slate-900">Knowledge Base</h2>
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">
                {documents.length}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <button
                onClick={onRefresh}
                disabled={isLoading}
                title="Refresh documents"
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={onOpenUpload}
                className="inline-flex items-center space-x-1 px-2.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Upload</span>
              </button>
            </div>
          </div>

          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Filter documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-slate-50 placeholder:text-slate-400"
            />
          </div>

          {/* Scope selection helper */}
          {filteredDocs.length > 0 && (
            <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
              <span className="flex items-center space-x-1">
                <Filter className="w-3 h-3 text-slate-400" />
                <span>
                  {selectedDocIds.length > 0
                    ? `${selectedDocIds.length} scoped for chat`
                    : 'Searching all documents'}
                </span>
              </span>
              <button
                onClick={() => onSelectAllDocs(!allSelected)}
                className="text-indigo-600 hover:text-indigo-700 font-medium"
              >
                {allSelected ? 'Clear selection' : 'Select all'}
              </button>
            </div>
          )}
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoading && documents.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center space-y-2">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
              <span>Loading documents...</span>
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-30 text-slate-400" />
              <p className="font-medium text-slate-600">No documents found</p>
              <p className="mt-1 text-slate-400">
                Upload a document or search with another term.
              </p>
            </div>
          ) : (
            filteredDocs.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.id);
              return (
                <div
                  key={doc.id}
                  className={`p-3 rounded-xl border transition-all text-xs group relative ${
                    isSelected
                      ? 'border-indigo-400 bg-indigo-50/40 shadow-xs'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-xs'
                  }`}
                >
                  <div className="flex items-start space-x-2.5">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelectDoc(doc.id)}
                      className="mt-1 h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                      title="Select for chat scope"
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-1.5">
                        {getFileIcon(doc.content_type)}
                        <span
                          className="font-semibold text-slate-800 truncate block cursor-pointer hover:text-indigo-600"
                          onClick={() => onOpenPreview(doc.id)}
                          title={doc.filename}
                        >
                          {doc.filename}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 mt-1.5 text-[11px] text-slate-500">
                        <span>{formatFileSize(doc.file_size_bytes)}</span>
                        <span>•</span>
                        {doc.status === 'ready' && (
                          <span className="inline-flex items-center text-emerald-700 font-medium">
                            <CheckCircle2 className="w-3 h-3 mr-0.5 text-emerald-600" />
                            {doc.chunk_count} chunks
                          </span>
                        )}
                        {doc.status === 'processing' && (
                          <span className="inline-flex items-center text-amber-700 font-medium animate-pulse">
                            <Clock className="w-3 h-3 mr-0.5 text-amber-600" />
                            Indexing...
                          </span>
                        )}
                        {doc.status === 'failed' && (
                          <span className="inline-flex items-center text-rose-700 font-medium">
                            <AlertCircle className="w-3 h-3 mr-0.5 text-rose-600" />
                            Failed
                          </span>
                        )}
                      </div>

                      {doc.is_public && (
                        <div className="mt-1.5">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <Globe className="w-2.5 h-2.5 mr-1" />
                            Public Demo Document
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => onOpenPreview(doc.id)}
                        className="p-1 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                        title="Preview chunks"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>

                      {!doc.is_public && (
                        <button
                          onClick={() => onDeleteDocument(doc.id)}
                          className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                          title="Delete document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/50 text-[11px] text-slate-400 text-center">
          FastEmbed (384-dim) • Hybrid pgvector + tsquery
        </div>
      </aside>
    </>
  );
};
