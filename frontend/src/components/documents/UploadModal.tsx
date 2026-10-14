import React, { useState, useRef, useEffect } from 'react';
import { AlertTriangle, FileUp, Loader2, Upload, X } from 'lucide-react';
import { api, ApiError } from '../../lib/api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (filename: string) => void;
  token?: string;
}

const ACCEPTED_EXTENSIONS = ['.pdf', '.txt', '.md', '.markdown', '.docx'];
const MAX_SIZE_MB = 5;

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  token,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Upload className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-slate-900">Upload Document</h2>
          </div>
          <button
            onClick={handleClose}
            disabled={isUploading}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Data handling disclaimer mandated by AGENTS.md §13 & §14 */}
          <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200/80 text-xs text-amber-900 flex items-start space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <p className="font-semibold text-amber-950">Free-Tier Data Handling Disclosure</p>
              <p className="mt-0.5">
                Model providers routed via OpenRouter free tier may log prompts/completions for abuse monitoring. Please upload public or synthetic documents only. Do not upload confidential or personal data.
              </p>
            </div>
          </div>

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-300 hover:border-indigo-500 rounded-xl p-6 text-center cursor-pointer transition-all bg-slate-50 hover:bg-indigo-50/20"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md,.markdown,.docx"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center mx-auto text-indigo-600 mb-3 border border-slate-200">
              <FileUp className="w-6 h-6" />
            </div>
            {file ? (
              <div>
                <p className="text-sm font-semibold text-slate-800">{file.name}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-medium text-slate-700">
                  Click to select or drag and drop a file
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  PDF, TXT, Markdown, or DOCX (max 5 MB)
                </p>
              </div>
            )}
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end space-x-3 pt-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || isUploading}
              className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-sm transition-colors"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <span>Upload Document</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
