import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Eye,
  FileCode,
  FileText,
  Filter,
  Globe,
  Layers,
  Loader2,
  Lock,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
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

type FilterTab = 'all' | 'public' | 'private';

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
  const [activeTab, setActiveTab] = useState<FilterTab>('all');

  // Auto-poll if any document is in 'processing' status
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === 'processing');
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      onRefresh();
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, onRefresh]);

  const filteredDocs = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase());
      if (!matchesSearch) return false;

      if (activeTab === 'public') return doc.is_public;
      if (activeTab === 'private') return !doc.is_public;
      return true;
    });
  }, [documents, searchTerm, activeTab]);

  const publicCount = useMemo(() => documents.filter((d) => d.is_public).length, [documents]);
  const privateCount = useMemo(() => documents.filter((d) => !d.is_public).length, [documents]);

  const allFilteredSelected =
    filteredDocs.length > 0 &&
    filteredDocs.every((d) => selectedDocIds.includes(d.id));

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getFileBadge = (contentType: string) => {
    if (contentType.includes('pdf')) {
      return (
        <div className="w-8 h-8 rounded-lg bg-rose-50 border border-rose-200/80 text-rose-600 flex items-center justify-center flex-shrink-0">
          <FileText className="w-4 h-4" />
        </div>
      );
    }
    if (contentType.includes('markdown') || contentType.includes('text')) {
      return (
        <div className="w-8 h-8 rounded-lg bg-brand-50 border border-brand-200/80 text-brand-600 flex items-center justify-center flex-shrink-0">
          <FileCode className="w-4 h-4" />
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 flex items-center justify-center flex-shrink-0">
        <FileText className="w-4 h-4" />
      </div>
    );
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpenMobile && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-slate-900/60 z-30 lg:hidden backdrop-blur-xs transition-opacity"
        />
      )}

      <aside
        className={`fixed lg:static top-16 bottom-0 left-0 z-30 w-84 bg-white border-r border-slate-200/90 flex flex-col transition-transform duration-200 ease-in-out shadow-xs ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Header & Actions */}
        <div className="p-4 border-b border-slate-100 space-y-3 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                Knowledge Base
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700">
                {documents.length}
              </span>
            </div>
            <div className="flex items-center space-x-1.5">
              <button
                onClick={onRefresh}
                disabled={isLoading}
                title="Refresh documents"
                className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-brand-600' : ''}`} />
              </button>
              <button
                onClick={onOpenUpload}
                className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 rounded-lg shadow-2xs shadow-brand-500/20 transition-all cursor-pointer active:scale-95"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Upload</span>
              </button>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex rounded-lg bg-slate-100 p-0.5 text-[11px] font-medium text-slate-600">
            <button
              onClick={() => setActiveTab('all')}
              className={`flex-1 py-1 rounded-md transition-all ${
                activeTab === 'all'
                  ? 'bg-white text-slate-900 font-bold shadow-2xs'
                  : 'hover:text-slate-900'
              }`}
            >
              All ({documents.length})
            </button>
            <button
              onClick={() => setActiveTab('public')}
              className={`flex-1 py-1 rounded-md transition-all ${
                activeTab === 'public'
                  ? 'bg-white text-slate-900 font-bold shadow-2xs'
                  : 'hover:text-slate-900'
              }`}
            >
              Demo ({publicCount})
            </button>
            <button
              onClick={() => setActiveTab('private')}
              className={`flex-1 py-1 rounded-md transition-all ${
                activeTab === 'private'
                  ? 'bg-white text-slate-900 font-bold shadow-2xs'
                  : 'hover:text-slate-900'
              }`}
            >
              Private ({privateCount})
            </button>
          </div>

          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search documents by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full text-xs pl-8 pr-8 py-2 rounded-xl border border-slate-200/90 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-slate-50/70 placeholder:text-slate-400 transition-all"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Scope selection helper */}
          {filteredDocs.length > 0 && (
            <div className="flex items-center justify-between text-[11px] text-slate-500 pt-0.5">
              <span className="flex items-center space-x-1 font-medium">
                <Filter className="w-3 h-3 text-brand-600" />
                <span>
                  {selectedDocIds.length > 0 ? (
                    <span>
                      <strong className="text-brand-700 font-bold">{selectedDocIds.length}</strong> scoped for chat
                    </span>
                  ) : (
                    'Searching all files'
                  )}
                </span>
              </span>
              <button
                onClick={() => onSelectAllDocs(!allFilteredSelected)}
                className="text-brand-600 hover:text-brand-800 font-semibold cursor-pointer hover:underline"
              >
                {allFilteredSelected ? 'Clear selection' : 'Select all'}
              </button>
            </div>
          )}
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoading && documents.length === 0 ? (
            <div className="py-14 text-center text-slate-400 text-xs flex flex-col items-center justify-center space-y-2.5">
              <Loader2 className="w-5 h-5 animate-spin text-brand-600" />
              <span className="font-medium text-slate-600">Loading knowledge base...</span>
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="py-14 text-center text-slate-400 text-xs px-4">
              <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-2.5 text-slate-400">
                <FileText className="w-5 h-5" />
              </div>
              <p className="font-bold text-slate-700">No documents found</p>
              <p className="mt-1 text-slate-500 text-[11px]">
                {searchTerm
                  ? `No matches for "${searchTerm}". Clear search to see all.`
                  : activeTab === 'private'
                  ? 'No private documents uploaded yet. Sign in as reviewer to upload.'
                  : 'Your knowledge base is empty.'}
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
                      ? 'border-brand-500 bg-brand-50/40 shadow-xs ring-1 ring-brand-500/20'
                      : 'border-slate-200/90 bg-white hover:border-slate-300 hover:shadow-2xs'
                  }`}
                >
                  <div className="flex items-start space-x-2.5">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelectDoc(doc.id)}
                      className="mt-1 h-3.5 w-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                      title="Toggle chat scope"
                    />

                    {getFileBadge(doc.content_type)}

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-1.5">
                        <span
                          className="font-bold text-slate-900 truncate block cursor-pointer hover:text-brand-600 transition-colors"
                          onClick={() => onOpenPreview(doc.id)}
                          title={doc.filename}
                        >
                          {doc.filename}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 mt-1 text-[11px] text-slate-500">
                        <span>{formatFileSize(doc.file_size_bytes)}</span>
                        <span>•</span>
                        {doc.status === 'ready' && (
                          <span className="inline-flex items-center text-emerald-700 font-semibold">
                            <CheckCircle2 className="w-3 h-3 mr-0.5 text-emerald-600" />
                            {doc.chunk_count} chunks
                          </span>
                        )}
                        {doc.status === 'processing' && (
                          <span className="inline-flex items-center text-amber-700 font-semibold animate-pulse">
                            <Clock className="w-3 h-3 mr-0.5 text-amber-600" />
                            Indexing...
                          </span>
                        )}
                        {doc.status === 'failed' && (
                          <span className="inline-flex items-center text-rose-700 font-semibold">
                            <AlertCircle className="w-3 h-3 mr-0.5 text-rose-600" />
                            Failed
                          </span>
                        )}
                      </div>

                      <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                        {doc.is_public ? (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <Globe className="w-2.5 h-2.5 mr-1 text-emerald-600" />
                            Public Demo
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                            <Lock className="w-2.5 h-2.5 mr-1 text-slate-500" />
                            Private Tenant
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => onOpenPreview(doc.id)}
                        className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors cursor-pointer"
                        title="Preview chunks"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>

                      {!doc.is_public && (
                        <button
                          onClick={() => onDeleteDocument(doc.id)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
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

        {/* Footer info: Technical Transparency */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/80 text-[11px] text-slate-500 flex items-center justify-between">
          <div className="flex items-center space-x-1.5 truncate">
            <Layers className="w-3.5 h-3.5 text-brand-600 flex-shrink-0" />
            <span className="truncate">FastEmbed 384-dim • Hybrid RRF</span>
          </div>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-200/80 text-slate-700 font-semibold">
            pgvector
          </span>
        </div>
      </aside>
    </>
  );
};
