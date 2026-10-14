import React from 'react';
import { BookOpen, LogIn, LogOut, ShieldCheck, Sparkles } from 'lucide-react';

interface HeaderProps {
  userEmail: string | null;
  isDemoMode: boolean;
  onOpenAuth: () => void;
  onSignOut: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  userEmail,
  isDemoMode,
  onOpenAuth,
  onSignOut,
}) => {
  return (
    <header className="h-16 border-b border-slate-200 bg-white px-4 md:px-6 flex items-center justify-between shadow-sm sticky top-0 z-20">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-100">
          <BookOpen className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base font-bold text-slate-900 leading-none">
              Enterprise Knowledge AI
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
              <Sparkles className="w-3 h-3 mr-1" />
              Evidence RAG
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Grounded multi-source retrieval & deterministic citations
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {userEmail ? (
          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-700">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span className="font-medium truncate max-w-[180px]">{userEmail}</span>
            </div>
            <button
              onClick={onSignOut}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-transparent hover:border-red-200"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        ) : isDemoMode ? (
          <div className="flex items-center space-x-3">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
              Demo Corpus Mode
            </span>
            <button
              onClick={onOpenAuth}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
};
