import React, { useState, useRef, useEffect } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Bot,
  Check,
  Clock,
  Copy,
  CornerDownLeft,
  Info,
  Loader2,
  Lock,
  Menu,
  Send,
  ServerCrash,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  User,
  Zap,
} from 'lucide-react';
import { ChatMessage, Citation } from '../../types';

interface ChatAreaProps {
  messages: ChatMessage[];
  onSendMessage: (question: string) => void;
  isLoading: boolean;
  selectedDocCount: number;
  onClearDocSelection: () => void;
  onOpenCitation: (citation: Citation) => void;
  onOpenFeedback: (requestId: string, rating: number) => void;
  onToggleSidebar: () => void;
}

const SAMPLE_QUESTIONS = [
  'What retry policy is documented for payment endpoints?',
  'Summarize the error handling conventions and error codes.',
  'What are the tenant isolation and Row-Level Security guarantees?',
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
}) => {
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Render text with clickable [S1], [S2] citation chips
  const renderFormattedAnswer = (text: string, citations?: Citation[]) => {
    if (!text) return null;
    const parts = text.split(/(\[S\d+\])/g);

    return parts.map((part, i) => {
      const match = part.match(/^\[(S\d+)\]$/);
      if (match) {
        const label = match[1];
        const citation = citations?.find((c) => c.label === label);
        return (
          <button
            key={i}
            onClick={() => citation && onOpenCitation(citation)}
            disabled={!citation}
            title={citation ? `Source: ${citation.filename}` : 'Unknown source'}
            className="inline-flex items-center mx-1 px-1.5 py-0.5 rounded text-[11px] font-bold font-mono bg-indigo-100 hover:bg-indigo-200 text-indigo-800 transition-colors cursor-pointer border border-indigo-300 align-baseline"
          >
            {label}
          </button>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] bg-slate-50/50">
      {/* Scope bar & Mobile toggle */}
      <div className="h-10 px-4 border-b border-slate-200 bg-white/80 backdrop-blur-xs flex items-center justify-between text-xs text-slate-600">
        <div className="flex items-center space-x-2">
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-1 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100"
            title="Toggle Documents"
          >
            <Menu className="w-4 h-4" />
          </button>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="font-medium text-slate-700">
              {selectedDocCount > 0
                ? `Retrieving from ${selectedDocCount} selected document${
                    selectedDocCount > 1 ? 's' : ''
                  }`
                : 'Searching entire knowledge base'}
            </span>
            {selectedDocCount > 0 && (
              <button
                onClick={onClearDocSelection}
                className="text-[11px] text-indigo-600 hover:text-indigo-800 underline ml-1 cursor-pointer"
              >
                Clear filter
              </button>
            )}
          </div>
        </div>

        <div className="hidden sm:flex items-center space-x-1 text-[11px] text-slate-400">
          <Zap className="w-3 h-3 text-amber-500" />
          <span>OpenRouter Free Reasoner</span>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto py-12 px-4 text-center">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600 text-white flex items-center justify-center mx-auto shadow-lg shadow-indigo-200 mb-4">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-slate-900">
              Evidence-Grounded Assistant
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-md mx-auto">
              Ask questions backed by your uploaded documentation. Every claim includes verified source citations.
            </p>

            <div className="mt-8 text-left">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 text-center">
                Suggested questions to try:
              </p>
              <div className="grid gap-2.5 max-w-lg mx-auto">
                {SAMPLE_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSendMessage(q)}
                    className="p-3.5 text-xs text-left bg-white hover:bg-indigo-50/50 border border-slate-200 hover:border-indigo-300 rounded-xl transition-all shadow-xs flex items-center justify-between group"
                  >
                    <span className="text-slate-800 font-medium group-hover:text-indigo-900">
                      {q}
                    </span>
                    <CornerDownLeft className="w-3.5 h-3.5 text-slate-300 group-hover:text-indigo-600 transition-colors flex-shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 max-w-3xl ${
                msg.sender === 'user' ? 'ml-auto flex-row-reverse space-x-reverse' : ''
              }`}
            >
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-xs ${
                  msg.sender === 'user'
                    ? 'bg-slate-800 text-white'
                    : 'bg-indigo-600 text-white'
                }`}
              >
                {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div
                className={`flex-1 rounded-2xl p-4.5 text-xs shadow-xs ${
                  msg.sender === 'user'
                    ? 'bg-slate-800 text-white rounded-tr-xs'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-tl-xs'
                }`}
              >
                {msg.sender === 'user' ? (
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                ) : msg.error ? (
                  /* Error states mandated by AGENTS.md §12 & §14 */
                  <div className="space-y-2">
                    {msg.errorCode === 'unauthorized' ? (
                      <div className="p-3.5 rounded-xl bg-violet-50 border border-violet-200 text-violet-900 space-y-1.5">
                        <div className="flex items-center space-x-2 font-bold text-violet-950">
                          <Lock className="w-4 h-4 text-violet-700" />
                          <span>Authentication Required</span>
                        </div>
                        <p className="leading-relaxed text-xs">
                          Your session has expired or requires authentication. Please sign in via the header menu to submit questions.
                        </p>
                      </div>
                    ) : msg.errorCode === 'llm_daily_budget_exhausted' || msg.errorCode === 'rate_limit_exceeded' ? (
                      <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 space-y-1.5">
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
                      <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 text-sky-900 space-y-1.5">
                        <div className="flex items-center space-x-2 font-bold text-sky-950">
                          <ServerCrash className="w-4 h-4 text-sky-700" />
                          <span>Instance Cold-Start / Upstream Unavailable</span>
                        </div>
                        <p className="leading-relaxed text-xs">
                          The backend service or upstream free model is spinning up from inactivity. Please wait 30-45 seconds and try again.
                        </p>
                      </div>
                    ) : (
                      <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 space-y-1">
                        <div className="flex items-center space-x-2 font-bold">
                          <AlertCircle className="w-4 h-4" />
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
                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 space-y-1">
                        <div className="flex items-center space-x-2 font-semibold text-slate-900">
                          <Info className="w-4 h-4 text-slate-500" />
                          <span>Insufficient Evidence in Indexed Documents</span>
                        </div>
                        <p className="leading-relaxed text-slate-600">
                          {msg.text}
                        </p>
                      </div>
                    ) : (
                      <div className="leading-relaxed whitespace-pre-wrap space-y-2">
                        {renderFormattedAnswer(msg.text, msg.citations)}
                      </div>
                    )}

                    {/* Grounding Source Cards */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="pt-3 border-t border-slate-100 space-y-2">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                          Verified Sources ({msg.citations.length})
                        </p>
                        <div className="grid sm:grid-cols-2 gap-2">
                          {msg.citations.map((c) => (
                            <div
                              key={c.label}
                              onClick={() => onOpenCitation(c)}
                              className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 cursor-pointer transition-all flex items-start space-x-2 group"
                            >
                              <span className="w-5 h-5 rounded bg-indigo-600 text-white font-mono text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                                {c.label}
                              </span>
                              <div className="flex-1 min-w-0">
                                <p className="font-semibold text-slate-800 truncate group-hover:text-indigo-900">
                                  {c.filename}
                                </p>
                                <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                                  {c.page_number ? `Page ${c.page_number} • ` : ''}
                                  {c.excerpt}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Diagnostics & Actions */}
                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                      <div className="flex items-center space-x-2">
                        {msg.retrieval && (
                          <span className="font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                            {msg.retrieval.mode} ({msg.retrieval.returned_chunks} chunks)
                          </span>
                        )}
                        {msg.timings_ms?.total && (
                          <span className="font-mono">
                            {msg.timings_ms.total.toFixed(0)}ms
                          </span>
                        )}
                      </div>

                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleCopy(msg.id, msg.text)}
                          className="p-1 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors"
                          title="Copy Answer"
                        >
                          {copiedId === msg.id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                        {!msg.feedbackSubmitted && (
                          <>
                            <button
                              onClick={() => onOpenFeedback(msg.id, 1)}
                              className="p-1 hover:text-emerald-600 hover:bg-emerald-50 rounded transition-colors"
                              title="Helpful Answer"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => onOpenFeedback(msg.id, -1)}
                              className="p-1 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
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

        {isLoading && (
          <div className="flex items-start space-x-3 max-w-2xl">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-xs">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center space-x-3 text-xs text-slate-600">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
              <span>Retrieving chunks & generating grounded response...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <div className="p-4 border-t border-slate-200 bg-white shadow-lg shadow-slate-100">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-2">
          {/* Single-turn notice mandated by AGENTS.md §14 */}
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <span className="flex items-center space-x-1">
              <Info className="w-3 h-3 text-slate-400" />
              <span>
                Each question is answered independently of prior turns (no multi-turn memory).
              </span>
            </span>
            <span>{input.length} / 2000</span>
          </div>

          <div className="relative flex items-center">
            <textarea
              ref={textareaRef}
              rows={2}
              maxLength={2000}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Ask a question about your knowledge base (Enter to submit, Shift+Enter for new line)..."
              className="w-full text-xs rounded-xl border border-slate-200 pl-4 pr-12 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder:text-slate-400 resize-none"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2.5 p-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
