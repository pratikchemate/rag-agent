import React, { useState } from 'react';
import { AlertCircle, BookOpen, Info, Loader2, Lock, Mail, Sparkles, X } from 'lucide-react';
import { isSupabaseConfigured, supabase } from '../../lib/supabase';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (email: string, token: string) => void;
  onContinueDemo: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onContinueDemo,
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide email and password.');
      return;
    }

    if (!isSupabaseConfigured || !supabase) {
      // Local dev mode fallback: simulate token
      onSuccess(email, `test-token-${email}`);
      onClose();
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) {
        setError(authError.message);
        return;
      }

      if (data?.session) {
        onSuccess(data.session.user.email || email, data.session.access_token);
        onClose();
      } else {
        setError('No active session returned. Please check your credentials.');
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center">
              <BookOpen className="w-4 h-4" />
            </div>
            <h2 className="text-base font-bold text-slate-900">Sign In</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Invite-only rationale mandated by AGENTS.md §6 & §13 */}
        <div className="mt-4 p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-100 text-xs text-indigo-900 space-y-1">
          <div className="flex items-center space-x-1.5 font-semibold text-indigo-950">
            <Info className="w-4 h-4 text-indigo-600 flex-shrink-0" />
            <span>Invite-Only Access Notice</span>
          </div>
          <p className="leading-relaxed">
            Public self-registration is closed to protect shared free-tier daily LLM and email quotas. Reviewers can use <strong>Demo Corpus Mode</strong> without an account.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full text-xs pl-9 pr-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder:text-slate-400"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full text-xs pl-9 pr-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder:text-slate-400"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-medium flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full inline-flex items-center justify-center space-x-2 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl shadow-sm transition-colors mt-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Signing in...</span>
              </>
            ) : (
              <span>Sign In with Credentials</span>
            )}
          </button>
        </form>

        <div className="mt-4 pt-4 border-t border-slate-100 text-center">
          <button
            type="button"
            onClick={() => {
              onContinueDemo();
              onClose();
            }}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-indigo-600 px-3 py-2 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            <span>Continue as Guest in Demo Mode</span>
          </button>
        </div>
      </div>
    </div>
  );
};
