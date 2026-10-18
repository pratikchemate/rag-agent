import { useCallback, useEffect, useRef, useState } from 'react';
import { Header } from './components/layout/Header';
import { DocumentSidebar } from './components/documents/DocumentSidebar';
import { ChatArea } from './components/chat/ChatArea';
import { UploadModal } from './components/documents/UploadModal';
import { PreviewModal } from './components/documents/PreviewModal';
import { CitationDrawer } from './components/citations/CitationDrawer';
import { FeedbackModal } from './components/chat/FeedbackModal';
import { AuthModal } from './features/auth/AuthModal';
import { api, ApiError } from './lib/api';
import { isSupabaseConfigured, supabase } from './lib/supabase';
import { ChatMessage, Citation, DocumentItem } from './types';

export function App() {
  // Theme state: dark / light
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme');
      if (saved === 'dark' || saved === 'light') return saved;
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    }
    return 'light';
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    try {
      localStorage.setItem('theme', theme);
    } catch {
      // ignore
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  // Auth state
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [token, setToken] = useState<string | undefined>(undefined);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);
  const [isAuthOpen, setIsAuthOpen] = useState(false);

  // Documents state
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);

  // Sidebar retraction state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isSidebarMobileOpen, setIsSidebarMobileOpen] = useState(false);

  const toggleSidebarCollapse = () => {
    setIsSidebarCollapsed((prev) => !prev);
  };

  // Keyboard shortcut Ctrl+B / Cmd+B for sidebar toggle
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        if (window.innerWidth < 1024) {
          setIsSidebarMobileOpen((prev) => !prev);
        } else {
          toggleSidebarCollapse();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatAbortRef = useRef<AbortController | null>(null);

  // Modals & Panels state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [previewDocId, setPreviewDocId] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [feedbackState, setFeedbackState] = useState<{ id: string; rating: number } | null>(null);

  // Initialize Auth
  useEffect(() => {
    if (isSupabaseConfigured && supabase) {
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session) {
          setUserEmail(session.user.email || null);
          setToken(session.access_token);
          setIsDemoMode(false);
        } else {
          setIsDemoMode(true);
        }
      });

      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange((_event, session) => {
        if (session) {
          setUserEmail(session.user.email || null);
          setToken(session.access_token);
          setIsDemoMode(false);
        } else {
          setUserEmail(null);
          setToken(undefined);
          setIsDemoMode(true);
        }
      });

      return () => subscription.unsubscribe();
    } else {
      // Unconfigured / offline fallback defaults to guest demo mode
      setIsDemoMode(true);
      setUserEmail(null);
      setToken(undefined);
    }
  }, []);

  // Fetch Documents
  const loadDocuments = useCallback(async (signal?: unknown) => {
    setIsLoadingDocs(true);
    try {
      const validSignal = signal instanceof AbortSignal ? signal : undefined;
      const docs = await api.fetchDocuments(token, validSignal);
      setDocuments(docs);
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        console.error('Failed to load documents:', err);
      }
    } finally {
      setIsLoadingDocs(false);
    }
  }, [token]);

  useEffect(() => {
    const controller = new AbortController();
    loadDocuments(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadDocuments]);

  // Handle Document selection
  const handleToggleSelectDoc = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const handleSelectAllDocs = (select: boolean) => {
    if (select) {
      setSelectedDocIds(documents.map((d) => d.id));
    } else {
      setSelectedDocIds([]);
    }
  };

  // Handle Document deletion
  const handleDeleteDocument = async (id: string) => {
    const doc = documents.find((d) => d.id === id);
    if (!doc) return;
    if (doc.is_public) {
      alert('Public demo documents cannot be deleted.');
      return;
    }
    if (!confirm(`Are you sure you want to delete "${doc.filename}"?`)) return;

    try {
      await api.deleteDocument(id, token);
      setSelectedDocIds((prev) => prev.filter((docId) => docId !== id));
      await loadDocuments();
    } catch (err: any) {
      alert(`Failed to delete document: ${err.message || 'Unknown error'}`);
    }
  };

  // Handle Chat Message
  const handleSendMessage = async (question: string) => {
    const userMsg: ChatMessage = {
      id: 'user-' + Date.now(),
      sender: 'user',
      text: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);

    const abortController = new AbortController();
    chatAbortRef.current = abortController;

    try {
      const res = await api.sendChatMessage(
        question,
        selectedDocIds,
        token,
        abortController.signal
      );

      const assistantMsg: ChatMessage = {
        id: res.request_id,
        sender: 'assistant',
        text: res.answer,
        citations: res.citations,
        abstained: res.abstained,
        timings_ms: res.timings_ms,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        return;
      }

      let errorText = 'An unexpected error occurred while communicating with the agent.';
      let code = 'unknown_error';
      let resetAt: string | undefined;

      if (err instanceof ApiError) {
        errorText = err.message;
        code = err.code;
        resetAt = err.resetAt;
      }

      const errorMsg: ChatMessage = {
        id: 'error-' + Date.now(),
        sender: 'assistant',
        text: errorText,
        error: errorText,
        errorCode: code,
        resetAt,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      if (chatAbortRef.current === abortController) {
        setIsChatLoading(false);
      }
    }
  };

  const handleSignOut = async () => {
    try {
      if (supabase) {
        await supabase.auth.signOut();
      }
    } catch (err) {
      console.error('Error during Supabase sign-out:', err);
    } finally {
      setUserEmail(null);
      setToken(undefined);
      setIsDemoMode(true);
      try {
        for (let i = localStorage.length - 1; i >= 0; i--) {
          const key = localStorage.key(i);
          if (key && (key.includes('sb-') || key.includes('supabase'))) {
            localStorage.removeItem(key);
          }
        }
      } catch {
        // ignore
      }
      loadDocuments();
    }
  };

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans antialiased">
      <Header
        userEmail={userEmail}
        isDemoMode={isDemoMode}
        onOpenAuth={() => setIsAuthOpen(true)}
        onSignOut={handleSignOut}
        theme={theme}
        onToggleTheme={toggleTheme}
        isSidebarCollapsed={isSidebarCollapsed}
        onToggleSidebarCollapse={toggleSidebarCollapse}
      />

      <div className="flex-1 flex overflow-hidden min-h-0">
        <DocumentSidebar
          documents={documents}
          selectedDocIds={selectedDocIds}
          onToggleSelectDoc={handleToggleSelectDoc}
          onSelectAllDocs={handleSelectAllDocs}
          onOpenUpload={() => setIsUploadOpen(true)}
          onOpenPreview={(id) => setPreviewDocId(id)}
          onDeleteDocument={handleDeleteDocument}
          onRefresh={() => loadDocuments()}
          isLoading={isLoadingDocs}
          isOpenMobile={isSidebarMobileOpen}
          onCloseMobile={() => setIsSidebarMobileOpen(false)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapse}
        />

        <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
          <ChatArea
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isChatLoading}
            selectedDocCount={selectedDocIds.length}
            onClearDocSelection={() => setSelectedDocIds([])}
            onOpenCitation={(citation) => setActiveCitation(citation)}
            onOpenFeedback={(requestId, rating) => setFeedbackState({ id: requestId, rating })}
            onToggleSidebar={() => {
              if (window.innerWidth < 1024) {
                setIsSidebarMobileOpen((prev) => !prev);
              } else {
                toggleSidebarCollapse();
              }
            }}
            onClearMessages={() => setMessages([])}
            onStopGeneration={() => {
              if (chatAbortRef.current) {
                chatAbortRef.current.abort();
                setIsChatLoading(false);
              }
            }}
            isSidebarCollapsed={isSidebarCollapsed}
          />
        </main>
      </div>

      {/* Modals & Drawers */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={(_filename) => {
          loadDocuments();
        }}
        token={token}
        onOpenAuth={() => setIsAuthOpen(true)}
      />

      <PreviewModal
        documentId={previewDocId}
        isOpen={Boolean(previewDocId)}
        onClose={() => setPreviewDocId(null)}
        token={token}
      />

      <CitationDrawer
        citation={activeCitation}
        isOpen={Boolean(activeCitation)}
        onClose={() => setActiveCitation(null)}
        onOpenDocumentPreview={(docId) => setPreviewDocId(docId)}
      />

      {feedbackState && (
        <FeedbackModal
          requestId={feedbackState.id}
          initialRating={feedbackState.rating}
          isOpen={Boolean(feedbackState)}
          onClose={() => setFeedbackState(null)}
          onSuccess={(reqId) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === reqId ? { ...m, feedbackSubmitted: true } : m))
            );
          }}
          token={token}
        />
      )}

      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onSuccess={(email, userToken) => {
          setUserEmail(email);
          setToken(userToken);
          setIsDemoMode(false);
          loadDocuments();
        }}
        onContinueDemo={() => {
          setIsDemoMode(true);
          setUserEmail(null);
          setToken(undefined);
          loadDocuments();
        }}
      />
    </div>
  );
}

export default App;
