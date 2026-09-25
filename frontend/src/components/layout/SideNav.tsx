import { Link, useLocation } from 'react-router-dom';
import * as Avatar from '@radix-ui/react-avatar';
import * as Separator from '@radix-ui/react-separator';
import * as Tooltip from '@radix-ui/react-tooltip';
import * as ScrollArea from '@radix-ui/react-scroll-area';
import { PlusCircle, History, Settings, User, X } from 'lucide-react';

export interface SavedSession {
  sessionId: string;
  topic: string;
  category: string;
  status: 'active' | 'ended';
  timestamp: string;
}

interface SideNavProps {
  onNewResearch: () => void;
  sessions: SavedSession[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onGoToLanding: () => void;
}

export function SideNav({
  onNewResearch,
  sessions,
  activeSessionId,
  onSelectSession,
  onGoToLanding,
}: SideNavProps) {
  const location = useLocation();

  return (
    <aside className="sidenav">
      {/* Brand header */}
      <div 
        onClick={onGoToLanding}
        style={{
          marginBottom: '1rem',
          padding: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          cursor: 'pointer',
        }}
      >
        <Avatar.Root className="avatar-root" style={{ width: 40, height: 40 }}>
          <Avatar.Fallback className="avatar-fallback" style={{ fontSize: '1.125rem' }}>
            X
          </Avatar.Fallback>
        </Avatar.Root>
        <div>
          <h1 className="font-headline" style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            color: 'var(--color-primary)',
            lineHeight: 1.2,
          }}>
            Professor X
          </h1>
          <p className="text-label-md" style={{ color: 'var(--color-on-surface-variant)' }}>
            AI Research Assistant
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <button className="nav-item" onClick={onNewResearch} style={{
              color: 'var(--color-primary)',
              width: '100%',
            }}>
              <PlusCircle size={20} />
              <span>New Research</span>
            </button>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content className="tooltip-content" side="right" sideOffset={8}>
              Start a new research session
              <Tooltip.Arrow className="tooltip-arrow" />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </nav>

      {/* Recent Research History */}
      <div style={{ marginTop: '1.5rem', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{
          color: 'var(--color-on-surface-variant)',
          padding: '0.5rem 1rem',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          fontSize: '0.75rem',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          marginBottom: '0.5rem',
        }}>
          <History size={14} />
          <span>Recent Research</span>
        </div>
        
        {sessions.length === 0 ? (
          <div className="font-body" style={{
            fontSize: '0.75rem',
            color: 'var(--color-outline)',
            padding: '1rem',
            textAlign: 'center',
            fontStyle: 'italic',
          }}>
            No history yet
          </div>
        ) : (
          <ScrollArea.Root className="scroll-area-root" style={{ flex: 1, overflow: 'hidden' }}>
            <ScrollArea.Viewport className="scroll-area-viewport">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', padding: '0 0.5rem' }}>
                {sessions.map((s) => (
                  <div
                    key={s.sessionId}
                    className={`nav-item ${activeSessionId === s.sessionId ? 'active' : ''}`}
                    onClick={() => onSelectSession(s.sessionId)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      cursor: 'pointer',
                      opacity: s.status === 'ended' ? 0.65 : 1,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden', flex: 1 }}>
                      <span className="dot" style={{
                        width: '0.5rem',
                        height: '0.5rem',
                        borderRadius: 'var(--radius-full)',
                        background: s.status === 'active' ? 'var(--color-primary)' : 'var(--color-outline)',
                        flexShrink: 0,
                      }} />
                      <span style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontWeight: activeSessionId === s.sessionId ? 600 : 400,
                        fontSize: '0.875rem',
                      }}>
                        {s.topic}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea.Viewport>
            <ScrollArea.Scrollbar className="scroll-area-scrollbar" orientation="vertical">
              <ScrollArea.Thumb className="scroll-area-thumb" />
            </ScrollArea.Scrollbar>
          </ScrollArea.Root>
        )}
      </div>

      {/* Footer */}
      <div style={{ marginTop: 'auto' }}>
        <Separator.Root className="separator" style={{ margin: '1rem 0' }} />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <button className="nav-item">
                <Settings size={20} />
                <span>Settings</span>
              </button>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content className="tooltip-content" side="right" sideOffset={8}>
                App settings
                <Tooltip.Arrow className="tooltip-arrow" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>

          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <Link
                to="/account"
                className={`nav-item ${location.pathname === '/account' ? 'active' : ''}`}
              >
                <User size={20} />
                <span>Account</span>
              </Link>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content className="tooltip-content" side="right" sideOffset={8}>
                Account settings
                <Tooltip.Arrow className="tooltip-arrow" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </div>
      </div>
    </aside>
  );
}
