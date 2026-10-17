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
  // Auth state
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [token, setToken] = useState<string | undefined>(undefined);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);
  const [isAuthOpen, setIsAuthOpen] = useState(false);

  // Documents state
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Modals & Panels state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [previewDocId, setPreviewDocId] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [feedbackState, setFeedbackState] = useState<{ id: string; rating: number } | null>(null);
  const [isSidebarMobileOpen, setIsSidebarMobileOpen] = useState(false);

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
      // Offline / dev mode default
      setIsDemoMode(true);
      setUserEmail('demo@enterprise.ai');
      setToken('test-token-00000000-0000-0000-0000-000000000001');
    }
  }, []);

  // Fetch Documents
  const loadDocuments = useCallback(async (signal?: AbortSignal) => {
    setIsLoadingDocs(true);
    try {
      const docs = await api.fetchDocuments(token, signal);
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
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setSelectedDocIds((prev) => prev.filter((d) => d !== id));
    } catch (err: any) {
      alert(err.message || 'Failed to delete document.');
    }
  };

  // Ref to abort ongoing chat requests
  const chatAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (chatAbortRef.current) {
        chatAbortRef.current.abort();
      }
    };
  }, []);

  // Handle Send Chat Message
  const handleSendMessage = async (question: string) => {
    if (chatAbortRef.current) {
      chatAbortRef.current.abort();
    }
    const abortController = new AbortController();
    chatAbortRef.current = abortController;

    const userMsgId = 'user-' + Date.now();
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);

    try {
      const response = await api.sendChatMessage(
        question,
        selectedDocIds.length > 0 ? selectedDocIds : undefined,
        token,
        abortController.signal
      );

      const assistantMsg: ChatMessage = {
        id: response.request_id,
        sender: 'assistant',
        text: response.answer,
        abstained: response.abstained,
        citations: response.citations,
        retrieval: response.retrieval,
        timings_ms: response.timings_ms,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        return;
      }
      let errorText = 'An unexpected error occurred while processing your request.';
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
    if (supabase) {
      await supabase.auth.signOut();
    }
    if (!isSupabaseConfigured) {
      setUserEmail('demo@enterprise.ai');
      setToken('test-token-00000000-0000-0000-0000-000000000001');
      setIsDemoMode(true);
    } else {
      setUserEmail(null);
      setToken(undefined);
      setIsDemoMode(true);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans antialiased">
      <Header
        userEmail={userEmail}
        isDemoMode={isDemoMode}
        onOpenAuth={() => setIsAuthOpen(true)}
        onSignOut={handleSignOut}
      />

      <div className="flex-1 flex overflow-hidden">
        <DocumentSidebar
          documents={documents}
          selectedDocIds={selectedDocIds}
          onToggleSelectDoc={handleToggleSelectDoc}
          onSelectAllDocs={handleSelectAllDocs}
          onOpenUpload={() => setIsUploadOpen(true)}
          onOpenPreview={(id) => setPreviewDocId(id)}
          onDeleteDocument={handleDeleteDocument}
          onRefresh={loadDocuments}
          isLoading={isLoadingDocs}
          isOpenMobile={isSidebarMobileOpen}
          onCloseMobile={() => setIsSidebarMobileOpen(false)}
        />

        <main className="flex-1 flex flex-col min-w-0">
          <ChatArea
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isChatLoading}
            selectedDocCount={selectedDocIds.length}
            onClearDocSelection={() => setSelectedDocIds([])}
            onOpenCitation={(citation) => setActiveCitation(citation)}
            onOpenFeedback={(requestId, rating) => setFeedbackState({ id: requestId, rating })}
            onToggleSidebar={() => setIsSidebarMobileOpen((prev) => !prev)}
            onClearMessages={() => setMessages([])}
            onStopGeneration={() => {
              if (chatAbortRef.current) {
                chatAbortRef.current.abort();
                setIsChatLoading(false);
              }
            }}
          />
        </main>
      </div>

      {/* Modals & Drawers */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={(filename) => {
          loadDocuments();
          console.log(`Uploaded ${filename}`);
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
