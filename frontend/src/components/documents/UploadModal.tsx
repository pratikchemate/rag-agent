import React, { useState, useRef, useEffect } from 'react';
import { AlertTriangle, CheckCircle, FileUp, Info, Loader2, Upload, X } from 'lucide-react';
import { api, ApiError } from '../../lib/api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (filename: string) => void;
  token?: string;
  onOpenAuth?: () => void;
}

const ACCEPTED_EXTENSIONS = ['.pdf', '.txt', '.md', '.markdown', '.docx'];
const MAX_SIZE_MB = 5;

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  token,
  onOpenAuth,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  if (!isOpen) return null;

  const handleClose = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    onClose();
  };

  const validateAndSetFile = (selectedFile: File) => {
    setError(null);
    const extension = '.' + selectedFile.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError(`Unsupported file format. Please upload ${ACCEPTED_EXTENSIONS.join(', ')}`);
      setFile(null);
      return;
    }

    if (selectedFile.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`File size exceeds the ${MAX_SIZE_MB}MB free-tier limit.`);
      setFile(null);
      return;
    }

    setFile(selectedFile);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError('Please sign in with a reviewer or registered account to upload documents.');
      return;
    }
    if (!file) {
      setError('Please select a file to upload.');
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    setIsUploading(true);
    setError(null);

    try {
      const res = await api.uploadDocument(file, token, controller.signal);
      onUploadSuccess(res.filename);
      onClose();
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        return;
      }
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError(`Duplicate file: This document has already been uploaded.`);
        } else {
          setError(err.message);
        }
      } else {
        setError('Failed to upload document. Please check your connection.');
      }
    } finally {
      setIsUploading(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center border border-brand-200/60">
              <Upload className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Upload Knowledge Document</h2>
              <p className="text-xs text-slate-500 font-medium">Automatic extraction, chunking, and vector embedding</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={isUploading}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {!token && (
            <div className="p-3.5 rounded-xl bg-brand-50/70 border border-brand-200/80 text-xs text-brand-900 flex items-start space-x-2.5">
              <Info className="w-4 h-4 text-brand-600 flex-shrink-0 mt-0.5" />
              <div className="leading-relaxed flex-1">
                <p className="font-bold text-brand-950">Reviewer Account Required</p>
                <p className="mt-0.5 text-slate-600">
                  Document uploads require an authenticated reviewer account to protect free-tier storage and ingestion quotas. In Demo Mode, you can query and explore all 4 pre-seeded documents without an account.
                </p>
                {onOpenAuth && (
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      onOpenAuth();
                    }}
                    className="mt-2.5 inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg shadow-xs transition-colors cursor-pointer"
                  >
                    <span>Sign In to Upload</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Data handling disclaimer */}
          <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200/80 text-xs text-amber-900 flex items-start space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <p className="font-bold text-amber-950">Free-Tier Data Handling Disclosure</p>
              <p className="mt-0.5 text-amber-800 text-[11px]">
                Model providers routed via OpenRouter free tier may log prompts/completions for abuse monitoring. Please upload public or synthetic documents only. Do not upload confidential or personal data.
              </p>
            </div>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
              isDragOver
                ? 'border-brand-500 bg-brand-50/60 scale-[1.01]'
                : file
                ? 'border-emerald-300 bg-emerald-50/20'
                : 'border-slate-300 hover:border-brand-500 bg-slate-50/70 hover:bg-brand-50/20'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md,.markdown,.docx"
              onChange={handleFileChange}
              className="hidden"
            />
            <div
              className={`w-12 h-12 rounded-2xl shadow-xs flex items-center justify-center mx-auto mb-3 border ${
                file
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                  : 'bg-white border-slate-200 text-brand-600'
              }`}
            >
              {file ? <CheckCircle className="w-6 h-6" /> : <FileUp className="w-6 h-6" />}
            </div>
            {file ? (
              <div>
                <p className="text-sm font-bold text-slate-800">{file.name}</p>
                <p className="text-xs text-emerald-700 font-semibold mt-1">
                  Ready to index • {(file.size / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-semibold text-slate-700">
                  Click to select or drag and drop a file
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  PDF, TXT, Markdown, or DOCX (max 5 MB)
                </p>
              </div>
            )}
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 font-medium">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || isUploading || !token}
              className="inline-flex items-center space-x-2 px-4 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl shadow-xs transition-all cursor-pointer active:scale-95"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing & Indexing...</span>
                </>
              ) : (
                <span>Upload & Ingest</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
