import React, { useState, useRef, useEffect, useLayoutEffect } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Bot,
  Check,
  Clock,
  Copy,
  CornerDownLeft,
  FileText,
  Info,
  Loader2,
  Lock,
  Menu,
  PlusCircle,
  Send,
  ServerCrash,
  ShieldCheck,
  Sparkles,
  Square,
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
}

interface SamplePrompt {
  category: string;
  question: string;
}

const SAMPLE_PROMPTS: SamplePrompt[] = [
  {
    category: 'Neural Networks & LSTMs',
    question: 'How do LSTM networks work and what are their gates?',
  },
  {
    category: 'Security & Isolation',
    question: 'What are the tenant isolation and Row-Level Security guarantees?',
  },
  {
    category: 'API Specifications',
    question: 'What retry policy and rate limits are documented for API endpoints?',
  },
  {
    category: 'Operations & Incident',
    question: 'Summarize the incident response steps and escalation path.',
  },
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
      // Cap at 180px
      textareaRef.current.style.height = `${Math.min(scrollHeight, 180)}px`;
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
    <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] bg-slate-50/60">
      {/* Scope bar & Mobile toggle */}
      <div className="h-11 px-4 border-b border-slate-200/80 bg-white/90 backdrop-blur-md flex items-center justify-between text-xs text-slate-600 z-10">
        <div className="flex items-center space-x-2.5">
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-1.5 text-slate-500 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors"
            title="Toggle Documents"
          >
            <Menu className="w-4 h-4" />
          </button>

          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${selectedDocCount > 0 ? 'bg-indigo-400' : 'bg-emerald-400'}`} />
              <span className={`relative inline-flex rounded-full h-2 w-2 ${selectedDocCount > 0 ? 'bg-indigo-500' : 'bg-emerald-500'}`} />
            </span>
            <span className="font-medium text-slate-800">
              {selectedDocCount > 0 ? (
                <span>
                  Searching <span className="font-semibold text-indigo-700">{selectedDocCount}</span> selected document{selectedDocCount > 1 ? 's' : ''}
                </span>
              ) : (
                'Searching entire knowledge base'
              )}
            </span>
            {selectedDocCount > 0 && (
              <button
                onClick={onClearDocSelection}
                className="text-[11px] font-medium text-indigo-600 hover:text-indigo-800 hover:underline cursor-pointer ml-1"
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
              className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
              title="Start a new conversation"
            >
              <PlusCircle className="w-3.5 h-3.5 text-slate-500" />
              <span>New Chat</span>
            </button>
          )}

          <div className="hidden sm:flex items-center space-x-1.5 text-[11px] font-medium text-slate-500 bg-slate-100/80 px-2 py-0.5 rounded-md border border-slate-200/60">
            <Zap className="w-3 h-3 text-amber-500" />
            <span>OpenRouter Free Reasoner</span>
          </div>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto py-10 px-4 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white flex items-center justify-center mx-auto shadow-lg shadow-indigo-200 mb-5 ring-4 ring-indigo-50">
              <Sparkles className="w-7 h-7" />
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/60 text-indigo-700 text-xs font-semibold mb-3">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
              <span>Strict Grounding & Sentence Citations</span>
            </div>

            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Enterprise Knowledge Assistant
            </h2>
            <p className="text-sm text-slate-600 mt-2 max-w-md mx-auto leading-relaxed">
              Ask questions backed by your uploaded documentation. Every claim includes verifiable chunk-level source citations.
            </p>

            <div className="mt-8 text-left">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 text-center">
                Try asking about your documents:
              </p>
              <div className="grid sm:grid-cols-2 gap-3 max-w-xl mx-auto">
                {SAMPLE_PROMPTS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSendMessage(item.question)}
                    className="p-3.5 text-left bg-white hover:bg-indigo-50/40 border border-slate-200/80 hover:border-indigo-300 rounded-xl transition-all shadow-2xs hover:shadow-sm flex flex-col justify-between group cursor-pointer"
                  >
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600 group-hover:text-indigo-700">
                      {item.category}
                    </span>
                    <span className="text-[13px] font-medium text-slate-800 group-hover:text-slate-900 mt-1 line-clamp-2">
                      {item.question}
                    </span>
                    <div className="flex items-center justify-end mt-2 text-slate-300 group-hover:text-indigo-600 transition-colors">
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
                className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-xs ${
                  msg.sender === 'user'
                    ? 'bg-slate-900 text-white'
                    : 'bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white'
                }`}
              >
                {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Bubble */}
              <div
                className={`flex-1 rounded-2xl p-5 shadow-2xs ${
                  msg.sender === 'user'
                    ? 'bg-slate-900 text-slate-100 rounded-tr-xs text-[13.5px] leading-relaxed'
                    : 'bg-white border border-slate-200/90 text-slate-800 rounded-tl-xs'
                }`}
              >
                {msg.sender === 'user' ? (
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                ) : msg.error ? (
                  /* Error states mandated by AGENTS.md §12 & §14 */
                  <div className="space-y-2">
                    {msg.errorCode === 'unauthorized' ? (
                      <div className="p-4 rounded-xl bg-violet-50 border border-violet-200 text-violet-900 space-y-1.5">
                        <div className="flex items-center space-x-2 font-bold text-violet-950">
                          <Lock className="w-4 h-4 text-violet-700" />
                          <span>Authentication Required</span>
                        </div>
                        <p className="leading-relaxed text-xs">
                          Your session has expired or requires authentication. Please sign in via the header menu to submit questions.
                        </p>
                      </div>
                    ) : msg.errorCode === 'llm_daily_budget_exhausted' || msg.errorCode === 'rate_limit_exceeded' ? (
                      <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 space-y-1.5">
                        <div className="flex items-center space-x-2 font-bold text-amber-950">
                          <AlertTriangle className="w-4 h-4 text-amber-700" />
                          <span>
                            {msg.errorCode === 'rate_limit_exceeded'
                              ? 'Rate Limit Exceeded'
                              : 'Daily Free-Tier Quota Reached'}
                          </span>
                        </div>
                        <p className="leading-relaxed text-xs">
                          {msg.errorCode === 'rate_limit_exceeded'
                            ? 'Too many requests in a short period. Please slow down and wait a moment before trying again.'
                            : 'The shared portfolio demo daily request limit has been reached for today to prevent billing overruns.'}
                        </p>
                        {msg.resetAt && (
                          <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-amber-100 text-amber-900 font-mono text-[11px] font-semibold mt-1">
                            <Clock className="w-3.5 h-3.5" />
                            <span>Resets at: {msg.resetAt}</span>
                          </div>
                        )}
                      </div>
                    ) : msg.errorCode === 'service_unavailable' || msg.errorCode === 'gateway_timeout' ? (
                      <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 space-y-1.5">
                        <div className="flex items-center space-x-2 font-bold text-amber-950">
                          <ServerCrash className="w-4 h-4 text-amber-700" />
                          <span>LLM Generation Unavailable</span>
                        </div>
                        <p className="leading-relaxed text-xs">
                          {msg.text ||
                            'The backend service or upstream free model is spinning up from inactivity. Please wait 30-45 seconds and try again.'}
                        </p>
                      </div>
                    ) : (
                      <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 space-y-1">
                        <div className="flex items-center space-x-2 font-bold">
                          <AlertCircle className="w-4 h-4 text-rose-600" />
                          <span>Unable to complete request</span>
                        </div>
                        <p className="text-xs">{msg.text}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Abstention state mandated by AGENTS.md §14 */}
                    {msg.abstained ? (
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 space-y-1.5">
                        <div className="flex items-center space-x-2 font-semibold text-slate-900 text-xs">
                          <Info className="w-4 h-4 text-slate-500" />
                          <span>Insufficient Evidence in Indexed Documents</span>
                        </div>
                        <p className="leading-relaxed text-xs text-slate-600">
                          {msg.text}
                        </p>
                      </div>
                    ) : (
                      <MessageContent
                        text={msg.text}
                        citations={msg.citations}
                        onOpenCitation={onOpenCitation}
                      />
                    )}

                    {/* Grounding Source Cards */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="pt-3 border-t border-slate-100 space-y-2">
                        <div className="flex items-center justify-between">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" />
                            <span>Verified Sources ({msg.citations.length})</span>
                          </p>
                          <span className="text-[10px] text-slate-400">Click card to inspect evidence</span>
                        </div>

                        <div className="grid sm:grid-cols-2 gap-2.5">
                          {msg.citations.map((c) => (
                            <div
                              key={c.label}
                              onClick={() => onOpenCitation(c)}
                              className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/80 hover:border-indigo-300 hover:bg-indigo-50/40 cursor-pointer transition-all flex items-start space-x-2.5 group shadow-2xs"
                            >
                              <span className="w-5 h-5 rounded-md bg-indigo-600 text-white font-mono text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5 shadow-xs">
                                {c.label}
                              </span>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-1">
                                  <div className="flex items-center gap-1.5 min-w-0">
                                    <FileText className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0" />
                                    <p className="font-semibold text-slate-800 text-xs truncate group-hover:text-indigo-900">
                                      {c.filename}
                                    </p>
                                  </div>
                                  {c.page_number && (
                                    <span className="text-[10px] font-mono text-slate-400 bg-slate-200/60 px-1.5 py-0.2 rounded">
                                      p.{c.page_number}
                                    </span>
                                  )}
                                </div>
                                <p className="text-[11px] text-slate-500 line-clamp-2 mt-1 leading-snug">
                                  {c.excerpt}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Diagnostics & Actions */}
                    <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                      <div className="flex items-center space-x-2">
                        {msg.retrieval && (
                          <span className="font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                            {msg.retrieval.mode} ({msg.retrieval.returned_chunks} chunks)
                          </span>
                        )}
                        {msg.timings_ms?.total && (
                          <span className="font-mono text-slate-500">
                            ⚡ {(msg.timings_ms.total / 1000).toFixed(2)}s
                          </span>
                        )}
                      </div>

                      <div className="flex items-center space-x-1.5">
                        <button
                          onClick={() => handleCopy(msg.id, msg.text)}
                          className="p-1 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
                          title="Copy Answer"
                        >
                          {copiedId === msg.id ? (
                            <span className="flex items-center gap-1 text-emerald-600 font-medium text-[11px]">
                              <Check className="w-3.5 h-3.5" />
                              <span>Copied</span>
                            </span>
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                        {!msg.feedbackSubmitted && (
                          <>
                            <button
                              onClick={() => onOpenFeedback(msg.id, 1)}
                              className="p-1 hover:text-emerald-600 hover:bg-emerald-50 rounded-md transition-colors"
                              title="Helpful Answer"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => onOpenFeedback(msg.id, -1)}
                              className="p-1 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                              title="Unhelpful / Inaccurate"
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {/* Live Loading State */}
        {isLoading && (
          <div className="flex items-start space-x-3.5 max-w-2xl animate-in fade-in duration-200">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-xs">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-2 text-xs text-slate-600">
              <div className="flex items-center space-x-2.5">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                <span className="font-medium text-slate-800">
                  Retrieving chunks & generating grounded response...
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px] text-slate-400 pl-6">
                <span>Dense vector + keyword RRF fusion • Grounding verification</span>
                {onStopGeneration && (
                  <button
                    type="button"
                    onClick={onStopGeneration}
                    className="text-rose-600 hover:text-rose-700 hover:underline font-medium ml-2 cursor-pointer"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <div className="p-4 border-t border-slate-200/80 bg-white shadow-lg shadow-slate-100/50">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-2">
          {/* Status hint & limits */}
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <span className="flex items-center space-x-1">
              <Info className="w-3 h-3 text-slate-400" />
              <span>
                Each question is answered independently of prior turns (single-turn stateless RAG).
              </span>
            </span>
            <span className={input.length > 1800 ? 'text-amber-600 font-semibold' : ''}>
              {input.length} / 2000
            </span>
          </div>

          <div className="relative flex items-end rounded-2xl border border-slate-200 bg-white focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500 transition-all shadow-xs">
            <textarea
              ref={textareaRef}
              rows={1}
              maxLength={2000}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Ask a question about your knowledge base (Enter to submit, Shift+Enter for new line)..."
              className="w-full text-[13.5px] rounded-2xl pl-4 pr-14 py-3 focus:outline-none placeholder:text-slate-400 resize-none max-h-44 min-h-[46px] leading-relaxed"
            />

            <div className="absolute right-2.5 bottom-2 flex items-center">
              {isLoading ? (
                <button
                  type="button"
                  onClick={onStopGeneration}
                  className="p-2 rounded-xl bg-rose-50 text-rose-600 hover:bg-rose-100 transition-colors shadow-2xs"
                  title="Stop generating"
                >
                  <Square className="w-4 h-4 fill-current" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="p-2 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-xs hover:shadow cursor-pointer"
                  title="Send Question"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
