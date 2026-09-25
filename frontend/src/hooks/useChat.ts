import { useState, useCallback, useRef, useEffect } from 'react';
import { sendQuery, type Citation, type ChatQueryResponse } from '../lib/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  content: string;
  citations?: Citation[];
  repos?: Array<{ url: string; name: string }>;
  recommendations?: string[];
  driftWarning?: string;
  timestamp: Date;
}

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageIdCounter = useRef(0);

  const genId = () => {
    messageIdCounter.current += 1;
    return `msg-${Date.now()}-${messageIdCounter.current}`;
  };

  // 1. Load messages from localStorage when sessionId changes
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }

    try {
      const savedStr = localStorage.getItem('prof_x_chat_sessions');
      if (savedStr) {
        const sessions = JSON.parse(savedStr);
        const currentSession = sessions.find((s: any) => s.sessionId === sessionId);
        if (currentSession && currentSession.messages) {
          // Parse timestamp ISO strings back to Date objects
          const parsedMsgs = currentSession.messages.map((m: any) => ({
            ...m,
            timestamp: new Date(m.timestamp),
          }));
          setMessages(parsedMsgs);
          return;
        }
      }
    } catch (err) {
      console.error('Error loading chat history from localStorage', err);
    }
    setMessages([]);
  }, [sessionId]);

  // 2. Helper to save messages to localStorage
  const saveMessagesToStorage = useCallback((msgs: ChatMessage[]) => {
    if (!sessionId) return;
    try {
      const savedStr = localStorage.getItem('prof_x_chat_sessions');
      if (savedStr) {
        const sessions = JSON.parse(savedStr);
        const updated = sessions.map((s: any) => {
          if (s.sessionId === sessionId) {
            return { ...s, messages: msgs };
          }
          return s;
        });
        localStorage.setItem('prof_x_chat_sessions', JSON.stringify(updated));
      }
    } catch (err) {
      console.error('Error saving chat history to localStorage', err);
    }
  }, [sessionId]);

  const send = useCallback(
    async (question: string) => {
      if (!sessionId || !question.trim()) return;

      const userMsg: ChatMessage = {
        id: genId(),
        role: 'user',
        content: question.trim(),
        timestamp: new Date(),
      };

      // We need to capture the updated state immediately for saving and rendering
      setMessages((prev) => {
        const updated = [...prev, userMsg];
        saveMessagesToStorage(updated);
        return updated;
      });
      setIsLoading(true);
      setError(null);

      try {
        const res: ChatQueryResponse = await sendQuery(sessionId, question.trim());
        const aiMsg: ChatMessage = {
          id: genId(),
          role: 'ai',
          content: res.answer,
          citations: res.citations,
          repos: res.repos,
          recommendations: res.recommendations,
          driftWarning: res.drift_warning ?? undefined,
          timestamp: new Date(),
        };
        setMessages((prev) => {
          const updated = [...prev, aiMsg];
          saveMessagesToStorage(updated);
          return updated;
        });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
        setError(errorMessage);

        // If session was terminated, update status in localStorage
        if (errorMessage.toLowerCase().includes('not found') || errorMessage.toLowerCase().includes('terminated')) {
          try {
            const savedStr = localStorage.getItem('prof_x_chat_sessions');
            if (savedStr) {
              const sessions = JSON.parse(savedStr);
              const updated = sessions.map((s: any) => {
                if (s.sessionId === sessionId) {
                  return { ...s, status: 'ended' };
                }
                return s;
              });
              localStorage.setItem('prof_x_chat_sessions', JSON.stringify(updated));
            }
            localStorage.removeItem('prof_x_active_session_id');
          } catch (e) {
            console.error('Failed to auto-expire session in localStorage', e);
          }
        }

        const errorMsg: ChatMessage = {
          id: genId(),
          role: 'ai',
          content: `I encountered an error processing your request: ${errorMessage}`,
          timestamp: new Date(),
        };
        setMessages((prev) => {
          const updated = [...prev, errorMsg];
          saveMessagesToStorage(updated);
          return updated;
        });
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, saveMessagesToStorage]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    saveMessagesToStorage([]);
    setError(null);
  }, [saveMessagesToStorage]);

  return { messages, isLoading, error, send, clearMessages };
}
