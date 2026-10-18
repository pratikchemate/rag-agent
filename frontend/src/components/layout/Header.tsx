import React from 'react';
import {
  Activity,
  BookOpen,
  LogIn,
  LogOut,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  ShieldCheck,
  Sparkles,
  Sun,
} from 'lucide-react';

interface HeaderProps {
  userEmail: string | null;
  isDemoMode: boolean;
  onOpenAuth: () => void;
  onSignOut: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  isSidebarCollapsed: boolean;
  onToggleSidebarCollapse: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  userEmail,
  isDemoMode,
  onOpenAuth,
  onSignOut,
  theme,
  onToggleTheme,
  isSidebarCollapsed,
  onToggleSidebarCollapse,
}) => {
  return (
    <header className="h-16 border-b border-slate-200/90 dark:border-slate-800/90 glass-header px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs flex-shrink-0 transition-colors">
      {/* Brand & Sidebar Toggle */}
      <div className="flex items-center space-x-3 sm:space-x-4">
        {/* Sidebar Collapse Toggle */}
        <button
          onClick={onToggleSidebarCollapse}
          className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-all cursor-pointer"
          title={isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          aria-label={isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isSidebarCollapsed ? (
            <PanelLeftOpen className="w-5 h-5 text-brand-600 dark:text-brand-400" />
          ) : (
            <PanelLeftClose className="w-5 h-5 text-slate-600 dark:text-slate-300" />
          )}
        </button>

        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20 ring-1 ring-white/20 flex-shrink-0">
          <BookOpen className="w-4 h-4 sm:w-5 sm:h-5" />
        </div>

        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-[14px] sm:text-base font-extrabold text-slate-900 dark:text-slate-100 tracking-tight leading-none">
              Enterprise Knowledge AI
            </h1>
            <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-brand-50 dark:bg-brand-950/70 text-brand-700 dark:text-brand-300 border border-brand-200/70 dark:border-brand-800/60">
              <Sparkles className="w-3 h-3 text-brand-600 dark:text-brand-400" />
              Grounded RAG
            </span>
          </div>
          <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 font-medium mt-0.5 hidden md:block">
            Multi-tenant evidence retrieval • Deterministic sentence citations
          </p>
        </div>
      </div>

      {/* Right Controls: Theme, Status & Auth */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Live System Indicator */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100/90 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 text-[11px] font-semibold text-slate-600 dark:text-slate-300">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <Activity className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
          <span>API Connected</span>
        </div>

        {/* Dark Mode Toggle */}
        <button
          onClick={onToggleTheme}
          className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-amber-300 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-all cursor-pointer border border-slate-200/60 dark:border-slate-800"
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400 transition-transform hover:rotate-45" />
          ) : (
            <Moon className="w-4 h-4 text-slate-600 transition-transform hover:-rotate-12" />
          )}
        </button>

        {userEmail ? (
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-200">
              <div className="w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[9px] font-bold">
                {userEmail.charAt(0).toUpperCase()}
              </div>
              <span className="font-semibold truncate max-w-[110px] sm:max-w-[160px]">
                {userEmail}
              </span>
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 hidden sm:inline" />
            </div>
            <button
              onClick={onSignOut}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded-xl transition-colors border border-transparent hover:border-rose-200 dark:hover:border-rose-800 cursor-pointer"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        ) : isDemoMode ? (
          <div className="flex items-center space-x-2">
            <span className="hidden sm:inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-300 border border-amber-200/90 dark:border-amber-800/60 shadow-2xs">
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
