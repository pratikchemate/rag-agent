import React, { useState } from 'react';
import { Check, Loader2, MessageSquare, ThumbsDown, ThumbsUp, X } from 'lucide-react';
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <MessageSquare className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">Answer Feedback</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Was this answer helpful and properly grounded?
            </label>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={() => setRating(1)}
                className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl border text-xs font-medium transition-all ${
                  rating === 1
                    ? 'bg-emerald-50 border-emerald-500 text-emerald-800 shadow-sm'
                    : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <ThumbsUp className="w-4 h-4 text-emerald-600" />
                <span>Helpful & Cited</span>
              </button>
              <button
                type="button"
                onClick={() => setRating(-1)}
                className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl border text-xs font-medium transition-all ${
                  rating === -1
                    ? 'bg-rose-50 border-rose-500 text-rose-800 shadow-sm'
                    : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <ThumbsDown className="w-4 h-4 text-rose-600" />
                <span>Unhelpful / Inaccurate</span>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Optional Comment (max 1000 characters)
            </label>
            <textarea
              rows={3}
              maxLength={1000}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Tell us what was good or what could be improved..."
              className="w-full text-xs rounded-xl border border-slate-200 p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder:text-slate-400"
            />
            <div className="text-right text-[11px] text-slate-400 mt-0.5">
              {comment.length} / 1000
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 text-red-700 text-xs border border-red-200">
              {error}
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center space-x-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg shadow-sm transition-colors"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Submit Feedback</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
