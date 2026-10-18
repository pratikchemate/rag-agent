import React, { useState } from 'react';
import { Loader2, MessageSquare, ThumbsDown, ThumbsUp, X } from 'lucide-react';
import { api } from '../../lib/api';

interface FeedbackModalProps {
  requestId: string;
  initialRating: number;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (requestId: string) => void;
  token?: string;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  requestId,
  initialRating,
  isOpen,
  onClose,
  onSuccess,
  token,
}) => {
  const [rating, setRating] = useState<number>(initialRating);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await api.submitFeedback(
        {
          request_id: requestId,
          rating,
          comment: comment.trim() || undefined,
        },
        token
      );
      onSuccess(requestId);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit feedback.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 flex items-center justify-center">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">Answer Feedback</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Help refine retrieval precision & grounding</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 p-1.5 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
              Was this answer helpful and properly grounded?
            </label>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={() => setRating(1)}
                className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl border text-xs font-bold transition-all cursor-pointer ${
                  rating === 1
                    ? 'bg-emerald-50 dark:bg-emerald-950/50 border-emerald-500 text-emerald-800 dark:text-emerald-300 shadow-2xs ring-1 ring-emerald-500/20'
                    : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-750'
                }`}
              >
                <ThumbsUp className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>Helpful & Cited</span>
              </button>
              <button
                type="button"
                onClick={() => setRating(-1)}
                className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl border text-xs font-bold transition-all cursor-pointer ${
                  rating === -1
                    ? 'bg-rose-50 dark:bg-rose-950/50 border-rose-500 text-rose-800 dark:text-rose-300 shadow-2xs ring-1 ring-rose-500/20'
                    : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-750'
                }`}
              >
                <ThumbsDown className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                <span>Needs Improvement</span>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Optional Comment (max 1000 characters)
            </label>
            <textarea
              rows={3}
              maxLength={1000}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Tell us what was good or what could be improved with citations or relevance..."
              className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 p-3 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-slate-50/60 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
            />
            <div className="text-right text-[11px] text-slate-400 dark:text-slate-500 mt-0.5 font-mono">
              {comment.length} / 1000
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 text-xs border border-rose-200 dark:border-rose-800 font-medium">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center space-x-2 px-4 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 disabled:opacity-50 rounded-xl shadow-xs transition-all cursor-pointer active:scale-95"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <span>Submit Feedback</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
