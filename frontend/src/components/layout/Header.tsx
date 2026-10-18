import React from 'react';
import { Activity, BookOpen, LogIn, LogOut, ShieldCheck, Sparkles } from 'lucide-react';

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
    <header className="h-16 border-b border-slate-200/90 glass-header px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs">
      {/* Brand & Tagline */}
      <div className="flex items-center space-x-3.5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20 ring-1 ring-white/20">
          <BookOpen className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-[15px] sm:text-base font-extrabold text-slate-900 tracking-tight leading-none">
              Enterprise Knowledge AI
            </h1>
            <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-brand-50 text-brand-700 border border-brand-200/70">
              <Sparkles className="w-3 h-3 text-brand-600" />
              Grounded RAG
            </span>
          </div>
          <p className="text-[11px] sm:text-xs text-slate-500 font-medium mt-0.5 hidden xs:block">
            Strict multi-tenant evidence retrieval • Deterministic sentence citations
          </p>
        </div>
      </div>

      {/* Right Controls: Status & Auth */}
      <div className="flex items-center space-x-2.5 sm:space-x-3.5">
        {/* Live System Indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100/90 border border-slate-200/80 text-[11px] font-medium text-slate-600">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <Activity className="w-3 h-3 text-emerald-600" />
          <span>API Connected</span>
        </div>

        {userEmail ? (
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-700">
              <div className="w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[9px] font-bold">
                {userEmail.charAt(0).toUpperCase()}
              </div>
              <span className="font-semibold text-slate-800 truncate max-w-[130px] sm:max-w-[180px]">
                {userEmail}
              </span>
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 hidden sm:inline" />
            </div>
            <button
              onClick={onSignOut}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors border border-transparent hover:border-rose-200 cursor-pointer"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        ) : isDemoMode ? (
          <div className="flex items-center space-x-2 sm:space-x-2.5">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-900 border border-amber-200/90 shadow-2xs">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5 animate-pulse" />
              Demo Mode
            </span>
            <button
              onClick={onOpenAuth}
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 rounded-xl shadow-xs shadow-brand-500/25 transition-all cursor-pointer active:scale-95"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
};
