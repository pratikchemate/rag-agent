import React, { useState, useRef, useEffect, useLayoutEffect } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Bot,
  Check,
  Clock,
  Copy,
  CornerDownLeft,
  Cpu,
  FileText,
  Loader2,
  Lock,
  Menu,
  PanelLeft,
  RotateCcw,
  Send,
  ServerCrash,
  ShieldCheck,
  Sparkles,
  Square,
  Terminal,
  ThumbsDown,
  ThumbsUp,
  User,
  Zap,
} from 'lucide-react';
import { ChatMessage, Citation } from '../../types';
import { MessageContent } from './MessageContent';

interface ChatAreaProps {
  messages: ChatMessage[];
  onSendMessage: (question: string) => void;
  isLoading: boolean;
  selectedDocCount: number;
  onClearDocSelection: () => void;
  onOpenCitation: (citation: Citation) => void;
  onOpenFeedback: (requestId: string, rating: number) => void;
  onToggleSidebar: () => void;
  onClearMessages?: () => void;
  onStopGeneration?: () => void;
  isSidebarCollapsed?: boolean;
}

interface SamplePrompt {
  category: string;
  question: string;
  icon: React.ReactNode;
}

const SAMPLE_PROMPTS: SamplePrompt[] = [
  {
    category: 'Security & Auth',
    question: 'What is the token expiration time and MFA policy?',
    icon: <Lock className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />,
  },
  {
    category: 'Incident Ops',
    question: 'Summarize the P0 incident response steps and escalation path.',
    icon: <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />,
  },
  {
    category: 'Architecture & Isolation',
    question: 'How does Row-Level Security guarantee tenant isolation in pgvector?',
    icon: <ShieldCheck className="w-4 h-4 text-brand-600 dark:text-brand-400" />,
  },
  {
    category: 'API Specifications',
    question: 'What are the rate limit ceilings and retry headers for the chat endpoint?',
    icon: <Terminal className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />,
  },
];

const QUICK_CHIPS = [
  'Token expiration in security policy?',
  'P0 incident escalation path',
  'Multi-tenant RLS guarantees',
  'API rate limits and retry headers',
];

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  onSendMessage,
  isLoading,
  selectedDocCount,
  onClearDocSelection,
  onOpenCitation,
  onOpenFeedback,
  onToggleSidebar,
  onClearMessages,
  onStopGeneration,
  isSidebarCollapsed = false,
}) => {
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-grow textarea height
  useLayoutEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      // Cap at 160px
      textareaRef.current.style.height = `${Math.min(scrollHeight, 160)}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden bg-slate-50/70 dark:bg-slate-950/70">
      {/* Scope bar & Toggle */}
      <div className="h-11 px-4 sm:px-6 border-b border-slate-200/80 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md flex items-center justify-between text-xs text-slate-600 dark:text-slate-300 z-10 flex-shrink-0">
        <div className="flex items-center space-x-2.5">
          {/* Mobile sidebar toggle button */}
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-1.5 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            title="Toggle Documents Sidebar"
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* Desktop expand button if collapsed */}
          {isSidebarCollapsed && (
            <button
              onClick={onToggleSidebar}
              className="hidden lg:flex items-center gap-1.5 px-2 py-1 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer font-medium"
              title="Show Knowledge Base Sidebar"
            >
              <PanelLeft className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              <span className="text-[11px]">Show Sidebar</span>
            </button>
          )}

          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  selectedDocCount > 0 ? 'bg-brand-400' : 'bg-emerald-400'
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  selectedDocCount > 0 ? 'bg-brand-500' : 'bg-emerald-500'
                }`}
              />
            </span>
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {selectedDocCount > 0 ? (
                <span>
                  Filtering <span className="font-extrabold text-brand-700 dark:text-brand-400">{selectedDocCount}</span> selected document{selectedDocCount > 1 ? 's' : ''}
                </span>
              ) : (
                'Searching entire knowledge base'
              )}
            </span>
            {selectedDocCount > 0 && (
              <button
                onClick={onClearDocSelection}
                className="text-[11px] font-bold text-brand-600 dark:text-brand-400 hover:text-brand-800 dark:hover:text-brand-300 hover:underline cursor-pointer ml-1"
              >
                Clear filter
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {messages.length > 0 && onClearMessages && (
            <button
              onClick={onClearMessages}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors cursor-pointer"
              title="Start a new conversation"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
              <span>Reset Chat</span>
            </button>
          )}

          <div className="hidden sm:flex items-center space-x-1.5 text-[11px] font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 rounded-md border border-slate-200/80 dark:border-slate-700/80">
            <Zap className="w-3 h-3 text-amber-500" />
            <span>OpenRouter Free Reasoner</span>
          </div>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto min-h-0 p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto py-10 px-4 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-600 text-white flex items-center justify-center mx-auto shadow-lg shadow-brand-500/20 mb-5 ring-4 ring-brand-50 dark:ring-brand-950/60">
              <Sparkles className="w-7 h-7" />
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950/60 border border-brand-200/80 dark:border-brand-800/80 text-brand-700 dark:text-brand-300 text-xs font-bold mb-3">
              <ShieldCheck className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
              <span>Strict Grounding & Sentence Citations</span>
            </div>

            <h2 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Enterprise Knowledge Assistant
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-2 max-w-md mx-auto leading-relaxed">
              Query internal policies, deployment guides, and specs with complete confidence. Every claim is verified with chunk-level sentence citations.
            </p>

            <div className="mt-8 text-left">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3 text-center">
                Frequently Asked Inquiries:
              </p>
              <div className="grid sm:grid-cols-2 gap-3 max-w-xl mx-auto">
                {SAMPLE_PROMPTS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSendMessage(item.question)}
                    className="p-3.5 text-left bg-white dark:bg-slate-900 hover:bg-brand-50/40 dark:hover:bg-brand-950/40 border border-slate-200/90 dark:border-slate-800 hover:border-brand-300 dark:hover:border-brand-700 rounded-xl transition-all shadow-2xs hover:shadow-card flex flex-col justify-between group cursor-pointer"
                  >
                    <div className="flex items-center space-x-2 mb-1.5">
                      {item.icon}
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 group-hover:text-brand-700 dark:group-hover:text-brand-300">
                        {item.category}
                      </span>
                    </div>
                    <span className="text-[13px] font-semibold text-slate-800 dark:text-slate-200 group-hover:text-slate-900 dark:group-hover:text-white line-clamp-2 leading-snug">
                      {item.question}
                    </span>
                    <div className="flex items-center justify-end mt-2 text-slate-300 dark:text-slate-600 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                      <CornerDownLeft className="w-3.5 h-3.5" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3.5 max-w-3xl ${
                msg.sender === 'user' ? 'ml-auto flex-row-reverse space-x-reverse' : ''
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-2xs ${
                  msg.sender === 'user'
                    ? 'bg-slate-900 dark:bg-indigo-600 text-white'
                    : 'bg-gradient-to-tr from-brand-600 to-indigo-600 text-white shadow-brand-500/20'
                }`}
              >
                {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Bubble */}
              <div
                className={`flex-1 rounded-2xl p-5 shadow-2xs ${
                  msg.sender === 'user'
                    ? 'bg-slate-900 dark:bg-brand-600 text-slate-100 rounded-tr-xs text-[13.5px] leading-relaxed'
                    : 'bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 text-slate-800 dark:text-slate-100 rounded-tl-xs shadow-card'
                }`}
              >
                {msg.sender === 'user' ? (
                  <p className="whitespace-pre-wrap leading-relaxed font-medium">{msg.text}</p>
                ) : msg.error ? (
                  /* Error states */
                  <div className="space-y-2">
                    {msg.errorCode === 'unauthorized' ? (
                      <div className="p-4 rounded-xl bg-violet-50 dark:bg-violet-950/40 border border-violet-200 dark:border-violet-800 text-violet-900 dark:text-violet-200 space-y-1.5">
                        <div className="flex items-center space-x-2 font-bold text-violet-950 dark:text-violet-100">
                          <Lock className="w-4 h-4 text-violet-700 dark:text-violet-400" />
                          <span>Authentication Required</span>
                        </div>
                        <p className="text-xs leading-relaxed">
                          Your session has expired or requires authentication. Please sign in to query private tenant documents.
                        </p>
                      </div>
                    ) : msg.errorCode === 'rate_limit_exceeded' ? (
                      <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 space-y-1.5">
                        <div className="flex items-center space-x-2 font-bold text-amber-950 dark:text-amber-100">
                          <Clock className="w-4 h-4 text-amber-700 dark:text-amber-400" />
                          <span>Rate Limit Exceeded</span>
                        </div>
                        <p className="text-xs leading-relaxed">
                          {msg.error}
                          {msg.resetAt && (
                            <span className="block mt-1 font-semibold">
                              Resets at: {new Date(msg.resetAt).toLocaleTimeString()}
                            </span>
                          )}
                        </p>
                      </div>
                    ) : (
                      <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-200 space-y-1.5">
                        <div className="flex items-center space-x-2 font-bold text-rose-950 dark:text-rose-100">
                          <ServerCrash className="w-4 h-4 text-rose-700 dark:text-rose-400" />
                          <span>Processing Error</span>
                        </div>
                        <p className="text-xs leading-relaxed font-mono">
                          {msg.error}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3.5">
                    {/* Abstention Banner */}
                    {msg.abstained && (
                      <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-xs text-amber-900 dark:text-amber-200 flex items-start space-x-2.5">
                        <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="font-bold">Honest Abstention Guarantee</p>
                          <p className="mt-0.5 text-amber-800 dark:text-amber-300">
                            The retrieved documentation does not contain sufficient verified evidence to answer this inquiry with full certainty.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Markdown Content */}
                    <MessageContent
                      text={msg.text}
                      citations={msg.citations}
                      onOpenCitation={onOpenCitation}
                    />

                    {/* Source Citations Badges */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                        <div className="flex items-center space-x-1.5 text-xs text-slate-500 dark:text-slate-400 font-semibold mb-2">
                          <FileText className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                          <span>Verified Sources ({msg.citations.length}):</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((c) => (
                            <button
                              key={c.label}
                              onClick={() => onOpenCitation(c)}
                              className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-50 dark:bg-slate-800 hover:bg-brand-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 hover:text-brand-800 dark:hover:text-brand-300 border border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors cursor-pointer group shadow-2xs"
                              title={`View evidence chunk for ${c.filename}`}
                            >
                              <span className="font-mono text-brand-600 dark:text-brand-400 group-hover:text-brand-800 font-bold">
                                {c.label}
                              </span>
                              <span className="truncate max-w-[140px] text-slate-800 dark:text-slate-200">{c.filename}</span>
                              {c.page_number && (
                                <span className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">
                                  p.{c.page_number}
                                </span>
                              )}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Footer Actions & Performance Metrics */}
                    <div className="pt-2 flex items-center justify-between text-xs text-slate-400 dark:text-slate-500 border-t border-slate-100 dark:border-slate-800 flex-wrap gap-2">
                      <div className="flex items-center space-x-2">
                        {/* Copy Button */}
                        <button
                          onClick={() => handleCopy(msg.id, msg.text)}
                          className="inline-flex items-center space-x-1 text-[11px] font-semibold text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-100 p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                          title="Copy response"
                        >
                          {copiedId === msg.id ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                              <span className="text-emerald-600 dark:text-emerald-400">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>

                        {/* Feedback Thumbs */}
                        {msg.feedbackSubmitted ? (
                          <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold px-2 py-0.5 bg-emerald-50 dark:bg-emerald-950/40 rounded">
                            Feedback recorded
                          </span>
                        ) : (
                          <div className="flex items-center space-x-0.5">
                            <button
                              onClick={() => onOpenFeedback(msg.id, 1)}
                              className="p-1 text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-slate-800 rounded transition-colors cursor-pointer"
                              title="Helpful response"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => onOpenFeedback(msg.id, -1)}
                              className="p-1 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-slate-800 rounded transition-colors cursor-pointer"
                              title="Needs improvement"
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Performance Latency Stats */}
                      {msg.timings_ms && (
                        <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                          <Cpu className="w-3 h-3 text-brand-600 dark:text-brand-400" />
                          <span>
                            retrieval: {msg.timings_ms.retrieval || 0}ms • gen: {msg.timings_ms.generation || 0}ms
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {/* Loading Spinner */}
        {isLoading && (
          <div className="flex items-start space-x-3.5 max-w-3xl">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 text-white flex items-center justify-center flex-shrink-0 shadow-xs">
              <Bot className="w-4 h-4 animate-pulse" />
            </div>
            <div className="flex-1 rounded-2xl rounded-tl-xs p-5 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-card">
              <div className="flex items-center space-x-2 text-xs font-semibold text-slate-600 dark:text-slate-300">
                <Loader2 className="w-4 h-4 animate-spin text-brand-600 dark:text-brand-400" />
                <span>Searching hybrid vector index & synthesizing verified answer...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area (STATIC PINNED AT BOTTOM) */}
      <div className="flex-shrink-0 p-4 sm:p-5 border-t border-slate-200/90 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md">
        <div className="max-w-3xl mx-auto space-y-2.5">
          {/* Quick Suggestions Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar text-xs">
            <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 whitespace-nowrap mr-1">
              Suggestions:
            </span>
            {QUICK_CHIPS.map((chip, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setInput(chip);
                  textareaRef.current?.focus();
                }}
                className="px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-brand-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 hover:text-brand-800 dark:hover:text-brand-300 border border-slate-200/80 dark:border-slate-700 text-[11px] font-medium whitespace-nowrap transition-colors cursor-pointer"
              >
                {chip}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="relative">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your knowledge base... (Enter to send, Shift+Enter for new line)"
              className="w-full text-xs sm:text-[13px] pl-4 pr-24 py-3 rounded-2xl border border-slate-300 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 resize-none shadow-2xs leading-relaxed transition-all"
            />

            <div className="absolute right-2.5 bottom-2.5 flex items-center space-x-1.5">
              {isLoading && onStopGeneration ? (
                <button
                  type="button"
                  onClick={onStopGeneration}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-900 dark:bg-slate-700 dark:hover:bg-slate-600 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                  title="Stop generating"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="w-8 h-8 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 disabled:opacity-40 text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs disabled:cursor-not-allowed active:scale-95"
                  title="Send message"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
          </form>

          <div className="flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500 px-1">
            <span>Enterprise Knowledge AI • Strict Grounding</span>
            <span className="font-mono">Press ↵ to send</span>
          </div>
        </div>
      </div>
    </div>
  );
};
