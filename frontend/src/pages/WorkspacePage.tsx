import { useEffect, useRef } from 'react';
import { useOutletContext } from 'react-router-dom';
import * as ScrollArea from '@radix-ui/react-scroll-area';
import { Brain, PlusCircle, BookOpen, PenLine, Sparkles } from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { ChatBubble } from '../components/ui/ChatBubble';
import { ChatInput } from '../components/ui/ChatInput';
import type { WorkspaceContext } from '../components/layout/AppLayout';

export function WorkspacePage() {
  const { openChooseBrain, sessionId, sessionStatus } = useOutletContext<WorkspaceContext>();
  const { messages, isLoading, send } = useChat(sessionId);
  const viewportRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    const scrollToBottom = () => {
      if (viewportRef.current) {
        viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
      }
    };
    // Scroll immediately
    scrollToBottom();
    // Scroll after a small timeout to account for dynamic height changes/images/rendering
    const timer1 = setTimeout(scrollToBottom, 50);
    const timer2 = setTimeout(scrollToBottom, 150);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [messages, isLoading]);

  // State 1: Landing — no active session
  if (!sessionId) {
    return (
      <>
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* Organic background blobs */}
          <div style={{
            position: 'absolute',
            top: '-10%',
            right: '-10%',
            width: '40%',
            height: '40%',
            background: 'color-mix(in srgb, var(--color-primary) 5%, transparent)',
            borderRadius: 'var(--radius-full)',
            filter: 'blur(64px)',
            pointerEvents: 'none',
          }} />
          <div style={{
            position: 'absolute',
            bottom: '-5%',
            left: '-5%',
            width: '30%',
            height: '30%',
            background: 'color-mix(in srgb, var(--color-tertiary) 5%, transparent)',
            borderRadius: 'var(--radius-full)',
            filter: 'blur(64px)',
            pointerEvents: 'none',
          }} />

          <div style={{
            maxWidth: '42rem',
            width: '100%',
            textAlign: 'center',
            zIndex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '2rem',
          }}>
            {/* Icon motif */}
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'color-mix(in srgb, var(--color-primary) 10%, transparent)',
                borderRadius: 'var(--radius-full)',
                filter: 'blur(20px)',
                transform: 'scale(1.5)',
              }} />
              <div style={{
                position: 'relative',
                background: 'var(--color-surface-container-high)',
                padding: '2rem',
                borderRadius: 'var(--radius-full)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Brain size={48} style={{ color: 'var(--color-primary)' }} strokeWidth={1.5} />
              </div>
            </div>

            {/* Primary message */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <h2 className="text-display-lg" style={{
                color: 'var(--color-on-background)',
                lineHeight: 1.1,
              }}>
                Begin a New Research to Chat with Professor
              </h2>
              <p className="text-body-lg" style={{
                color: 'var(--color-on-surface-variant)',
                maxWidth: '32rem',
                margin: '0 auto',
                lineHeight: 1.6,
              }}>
                Your workspace is a sanctuary for exploration. Start a fresh inquiry to unlock
                insights, synthesize knowledge, and discover new frontiers.
              </p>
            </div>

            {/* CTA button */}
            <div style={{ paddingTop: '1rem' }}>
              <button
                className="btn btn-primary"
                onClick={openChooseBrain}
                style={{ fontSize: '1.125rem', padding: '1rem 2rem' }}
              >
                <PlusCircle size={20} />
                New Research
              </button>
            </div>

            {/* Decorative feature icons */}
            <div style={{
              paddingTop: '3rem',
              display: 'flex',
              justifyContent: 'center',
              gap: '2rem',
              opacity: 0.4,
            }}>
              {[
                { icon: BookOpen, label: 'Read' },
                { icon: PenLine, label: 'Synthesize' },
                { icon: Sparkles, label: 'Discover' },
              ].map(({ icon: Icon, label }) => (
                <div key={label} style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}>
                  <Icon size={20} />
                  <span className="text-label-md" style={{
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                  }}>
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer style={{
          padding: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'color-mix(in srgb, var(--color-surface-container-low) 50%, transparent)',
          backdropFilter: 'blur(4px)',
          borderTop: '1px solid color-mix(in srgb, var(--color-outline-variant) 30%, transparent)',
        }}>
          <p className="font-body" style={{
            fontSize: '0.75rem',
            color: 'var(--color-on-surface-variant)',
            fontStyle: 'italic',
          }}>
            "The search for knowledge is the beginning of wisdom."
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span className="text-label-md" style={{
              color: 'var(--color-on-surface-variant)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
            }}>
              <span className="animate-pulse" style={{
                width: '0.5rem',
                height: '0.5rem',
                borderRadius: 'var(--radius-full)',
                background: 'var(--color-primary)',
                display: 'inline-block',
              }} />
              AI Engine Ready
            </span>
            <span className="text-label-md" style={{ color: 'var(--color-on-surface-variant)' }}>
              v2.4.0
            </span>
          </div>
        </footer>
      </>
    );
  }

  // State 2: Empty chat — session active but no messages
  if (messages.length === 0) {
    return (
      <>
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          textAlign: 'center',
        }}>
          <h1 className="text-display-lg" style={{
            color: 'var(--color-primary)',
            marginBottom: '1rem',
          }}>
            Professor X
          </h1>
          <p className="text-title-lg" style={{
            color: 'var(--color-secondary)',
          }}>
            Scientific research assistant
          </p>
        </div>

        <div className="chat-input-container">
          <div className="chat-input-box">
            <ChatInput onSend={send} isLoading={isLoading} disabled={sessionStatus === 'ended'} />
          </div>
        </div>
      </>
    );
  }

  // State 3: Active chat — messages exist
  return (
    <>
      <ScrollArea.Root
        className="scroll-area-root"
        style={{ flex: 1, overflow: 'hidden' }}
      >
        <ScrollArea.Viewport ref={viewportRef} className="scroll-area-viewport">
          <div className="chat-container">
            {messages.map((msg) => (
              <ChatBubble
                key={msg.id}
                role={msg.role}
                content={msg.content}
                citations={msg.citations}
                repos={msg.repos}
              />
            ))}

            {isLoading && (
              <div className="typing-indicator animate-slide-up">
                <div className="chat-ai-avatar" style={{ marginRight: '0.75rem' }}>
                  <span>X</span>
                </div>
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
            )}
          </div>
        </ScrollArea.Viewport>
        <ScrollArea.Scrollbar className="scroll-area-scrollbar" orientation="vertical">
          <ScrollArea.Thumb className="scroll-area-thumb" />
        </ScrollArea.Scrollbar>
      </ScrollArea.Root>

      <div className="chat-input-container">
        <div className="chat-input-box">
          <ChatInput onSend={send} isLoading={isLoading} disabled={sessionStatus === 'ended'} />
        </div>
      </div>
    </>
  );
}
