import { useState, useCallback, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { SideNav, type SavedSession } from './SideNav';
import { TopBar } from './TopBar';
import { ChooseBrainModal } from '../modals/ChooseBrainModal';
import { endSession } from '../../lib/api';

export interface WorkspaceContext {
  openChooseBrain: () => void;
  sessionId: string | null;
  sessionTopic: string | null;
  sessionStatus: 'active' | 'ended' | null;
}

export function AppLayout() {
  const [modalOpen, setModalOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionTopic, setSessionTopic] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<'active' | 'ended' | null>(null);
  const [sessions, setSessions] = useState<SavedSession[]>([]);

  // 1. Initial load: restore history
  useEffect(() => {
    try {
      const savedStr = localStorage.getItem('prof_x_chat_sessions');
      if (savedStr) {
        const parsedSessions = JSON.parse(savedStr) as SavedSession[];
        setSessions(parsedSessions);
      }
    } catch (err) {
      console.error('Failed to restore sessions from localStorage', err);
    }
  }, []);

  // 2. Handle session creation
  const handleSessionCreated = useCallback((id: string, topic: string, category: string) => {
    setSessionId(id);
    setSessionTopic(topic);
    setSessionStatus('active');
    setModalOpen(false);

    try {
      const savedStr = localStorage.getItem('prof_x_chat_sessions') || '[]';
      const parsedSessions = JSON.parse(savedStr) as SavedSession[];
      
      const exists = parsedSessions.some((s) => s.sessionId === id);
      if (!exists) {
        const newSession: SavedSession = {
          sessionId: id,
          topic,
          category,
          status: 'active',
          timestamp: new Date().toISOString(),
        };
        const updated = [newSession, ...parsedSessions];
        setSessions(updated);
        localStorage.setItem('prof_x_chat_sessions', JSON.stringify(updated));
      }
      localStorage.setItem('prof_x_active_session_id', id);
    } catch (err) {
      console.error('Failed to save new session to localStorage', err);
    }
  }, []);

  // 3. Handle ending session
  const handleEndSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await endSession(sessionId);
      
      // Update session status in state
      setSessionStatus('ended');
      
      // Update session status in localStorage
      const savedStr = localStorage.getItem('prof_x_chat_sessions');
      if (savedStr) {
        const parsedSessions = JSON.parse(savedStr) as SavedSession[];
        const updated = parsedSessions.map((s) => {
          if (s.sessionId === sessionId) {
            return { ...s, status: 'ended' as const };
          }
          return s;
        });
        setSessions(updated);
        localStorage.setItem('prof_x_chat_sessions', JSON.stringify(updated));
      }
      
      localStorage.removeItem('prof_x_active_session_id');
    } catch (err) {
      console.error('Failed to end session', err);
    }
  }, [sessionId]);

  // 4. Handle selecting session from sidebar
  const handleSelectSession = useCallback((id: string) => {
    try {
      const savedStr = localStorage.getItem('prof_x_chat_sessions');
      if (savedStr) {
        const parsedSessions = JSON.parse(savedStr) as SavedSession[];
        const session = parsedSessions.find((s) => s.sessionId === id);
        if (session) {
          setSessionId(session.sessionId);
          setSessionTopic(session.topic);
          setSessionStatus(session.status);
          if (session.status === 'active') {
            localStorage.setItem('prof_x_active_session_id', session.sessionId);
          } else {
            localStorage.removeItem('prof_x_active_session_id');
          }
        }
      }
    } catch (err) {
      console.error('Failed to select session', err);
    }
  }, []);

  // 5. Handle navigating back to landing page
  const handleGoToLanding = useCallback(() => {
    setSessionId(null);
    setSessionTopic(null);
    setSessionStatus(null);
    localStorage.removeItem('prof_x_active_session_id');
  }, []);

  const context: WorkspaceContext = {
    openChooseBrain: () => setModalOpen(true),
    sessionId,
    sessionTopic,
    sessionStatus,
  };

  return (
    <div className="app-shell">
      <SideNav
        onNewResearch={() => setModalOpen(true)}
        sessions={sessions}
        activeSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onGoToLanding={handleGoToLanding}
      />
      <main className="main-content">
        <TopBar 
          sessionId={sessionId} 
          onEndSession={handleEndSession} 
          onGoToLanding={handleGoToLanding} 
        />
        <Outlet context={context} />
      </main>
      <ChooseBrainModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSessionCreated={handleSessionCreated}
      />
    </div>
  );
}
