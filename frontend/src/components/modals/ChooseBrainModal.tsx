import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Sparkles, FolderArchive, ArrowRight, Loader2, X } from 'lucide-react';
import { startSession, getSession } from '../../lib/api';

interface ChooseBrainModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSessionCreated: (sessionId: string, topic: string, category: string) => void;
}

export function ChooseBrainModal({ open, onOpenChange, onSessionCreated }: ChooseBrainModalProps) {
  const [topic, setTopic] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingDomain, setLoadingDomain] = useState<string | null>(null);

  const showLoadingScreen = isLoading || loadingDomain !== null;
  const loadingTopic = isLoading ? topic : loadingDomain;

  const handleFreshStart = async () => {
    if (!topic.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);

    try {
      let res = await startSession(topic.trim());
      
      // Poll session status until paper ingestion completes or fails
      while (res.ingestion_status && res.ingestion_status !== 'completed' && res.ingestion_status !== 'failed') {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        res = await getSession(res.session_id);
      }

      if (res.ingestion_status === 'failed') {
        throw new Error('Paper ingestion failed. Please try a different topic.');
      }

      setTopic('');
      onSessionCreated(res.session_id, res.topic, res.category);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDomainSelect = async (domain: string) => {
    if (isLoading || loadingDomain !== null) return;
    setLoadingDomain(domain);
    setError(null);

    try {
      let res = await startSession(domain);

      // Poll session status until paper ingestion completes or fails
      while (res.ingestion_status && res.ingestion_status !== 'completed' && res.ingestion_status !== 'failed') {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        res = await getSession(res.session_id);
      }

      if (res.ingestion_status === 'failed') {
        throw new Error('Paper ingestion failed. Please try a different domain.');
      }

      onSessionCreated(res.session_id, res.topic, res.category);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
    } finally {
      setLoadingDomain(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleFreshStart();
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(val) => {
      if (showLoadingScreen) return;
      onOpenChange(val);
    }}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content
          className="dialog-content"
          aria-describedby="choose-brain-desc"
          onPointerDownOutside={(e) => {
            if (showLoadingScreen) e.preventDefault();
          }}
          onEscapeKeyDown={(e) => {
            if (showLoadingScreen) e.preventDefault();
          }}
        >
          {!showLoadingScreen && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem' }}>
              <Dialog.Close asChild>
                <button className="btn btn-icon" aria-label="Close">
                  <X size={20} />
                </button>
              </Dialog.Close>
            </div>
          )}

          {showLoadingScreen ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '3rem 1.5rem',
              textAlign: 'center',
              minHeight: '350px',
              animation: 'fadeIn 0.3s ease forwards',
              position: 'relative',
            }}>
              {/* Organic glowing background blobs */}
              <div style={{
                position: 'absolute',
                top: '20%',
                left: '30%',
                width: '12rem',
                height: '12rem',
                background: 'color-mix(in srgb, var(--color-primary) 12%, transparent)',
                borderRadius: 'var(--radius-full)',
                filter: 'blur(32px)',
                animation: 'pulse 3s ease-in-out infinite',
                pointerEvents: 'none',
              }} />
              <div style={{
                position: 'absolute',
                bottom: '20%',
                right: '30%',
                width: '10rem',
                height: '10rem',
                background: 'color-mix(in srgb, var(--color-tertiary) 8%, transparent)',
                borderRadius: 'var(--radius-full)',
                filter: 'blur(32px)',
                animation: 'pulse 4s ease-in-out infinite',
                pointerEvents: 'none',
              }} />

              {/* Pulsing/spinning premium loader */}
              <div style={{ position: 'relative', marginBottom: '2.5rem', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{
                  position: 'absolute',
                  width: '5rem',
                  height: '5rem',
                  borderRadius: 'var(--radius-full)',
                  border: '3px solid color-mix(in srgb, var(--color-primary) 15%, transparent)',
                  borderTopColor: 'var(--color-primary)',
                  animation: 'spin 1.2s linear infinite',
                }} />
                <div style={{
                  position: 'absolute',
                  width: '6.5rem',
                  height: '6.5rem',
                  borderRadius: 'var(--radius-full)',
                  border: '2px dashed color-mix(in srgb, var(--color-tertiary) 25%, transparent)',
                  animation: 'spin 8s linear infinite reverse',
                }} />
                <div style={{
                  background: 'var(--color-surface-container-high)',
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-full)',
                  boxShadow: 'var(--shadow-md)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 1,
                  animation: 'pulse 2s ease-in-out infinite',
                }}>
                  <Sparkles size={32} style={{ color: 'var(--color-primary)' }} />
                </div>
              </div>

              <h3 className="font-headline" style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color: 'var(--color-on-surface)',
                marginBottom: '0.75rem',
                zIndex: 1,
              }}>
                Initializing Research Session
              </h3>
              
              {loadingTopic && (
                <p className="font-body text-body-lg" style={{
                  color: 'var(--color-primary)',
                  fontWeight: 600,
                  marginBottom: '0.5rem',
                  zIndex: 1,
                }}>
                  Curating archives for "{loadingTopic}"
                </p>
              )}

              <p className="font-body" style={{
                color: 'var(--color-on-surface-variant)',
                maxWidth: '26rem',
                lineHeight: 1.6,
                fontSize: '0.9375rem',
                zIndex: 1,
              }}>
                Please wait a moment while Professor X configures your dedicated workspace, compiles relevant documents, and synchronizes the retrieval pipeline.
              </p>
            </div>
          ) : (
            <>
              <Dialog.Title className="font-headline" style={{
                fontSize: '2rem',
                fontWeight: 700,
                color: 'var(--color-primary)',
                textAlign: 'center',
                marginBottom: '0.75rem',
              }}>
                Choose your Brain
              </Dialog.Title>

              <Dialog.Description id="choose-brain-desc" className="font-body" style={{
                fontSize: '1.125rem',
                color: 'var(--color-on-surface-variant)',
                textAlign: 'center',
                marginBottom: '2.5rem',
              }}>
                Select a starting point for your research session.
              </Dialog.Description>

              {error && (
                <div style={{
                  background: 'var(--color-error-container)',
                  color: 'var(--color-on-error-container)',
                  padding: '0.75rem 1rem',
                  borderRadius: 'var(--radius-lg)',
                  marginBottom: '1.5rem',
                  fontSize: '0.875rem',
                  fontFamily: 'var(--font-body)',
                }}>
                  {error}
                </div>
              )}

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '1.5rem',
              }}>
                {/* Fresh Start Card */}
                <div className="card card-interactive" style={{
                  display: 'flex',
                  flexDirection: 'column',
                  background: 'var(--color-surface-container-low)',
                  border: '1px solid transparent',
                }}>
                  <div style={{
                    width: '4rem',
                    height: '4rem',
                    borderRadius: 'var(--radius-full)',
                    background: 'color-mix(in srgb, var(--color-primary-container) 50%, transparent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '1.5rem',
                    transition: 'transform var(--transition-normal)',
                    color: 'var(--color-primary)',
                  }}>
                    <Sparkles size={28} />
                  </div>

                  <h3 className="font-headline" style={{
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: 'var(--color-on-surface)',
                    marginBottom: '0.5rem',
                  }}>
                    Fresh
                  </h3>

                  <p className="font-body" style={{
                    color: 'var(--color-on-surface-variant)',
                    lineHeight: 1.6,
                    marginBottom: '2rem',
                    flex: 1,
                  }}>
                    A fresh start with a curated, general knowledge base. Ideal for open-ended
                    exploration and initial brainstorming.
                  </p>

                  <div>
                    <label className="text-label-lg" style={{
                      display: 'block',
                      color: 'var(--color-secondary)',
                      marginBottom: '0.5rem',
                    }}>
                      Action
                    </label>
                    <div style={{ position: 'relative' }}>
                      <input
                        className="input"
                        type="text"
                        placeholder="What do you want to learn today?"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        style={{ paddingRight: '2.5rem' }}
                      />
                      <button
                        onClick={handleFreshStart}
                        disabled={!topic.trim() || isLoading}
                        className="btn btn-icon"
                        style={{
                          position: 'absolute',
                          right: '0.5rem',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          color: 'var(--color-outline)',
                        }}
                      >
                        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Xavier Files Card */}
                <div className="card card-interactive" style={{
                  display: 'flex',
                  flexDirection: 'column',
                  background: 'var(--color-surface-container-lowest)',
                  border: '1px solid color-mix(in srgb, var(--color-outline-variant) 40%, transparent)',
                  position: 'relative',
                  overflow: 'hidden',
                }}>
                  {/* Decorative blob */}
                  <div style={{
                    position: 'absolute',
                    top: 0,
                    right: 0,
                    width: '8rem',
                    height: '8rem',
                    background: 'color-mix(in srgb, var(--color-tertiary-container) 10%, transparent)',
                    borderRadius: 'var(--radius-full)',
                    filter: 'blur(32px)',
                    marginRight: '-2.5rem',
                    marginTop: '-2.5rem',
                    pointerEvents: 'none',
                  }} />

                  <div style={{
                    width: '4rem',
                    height: '4rem',
                    borderRadius: 'var(--radius-full)',
                    background: 'color-mix(in srgb, var(--color-tertiary-container) 30%, transparent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '1.5rem',
                    transition: 'transform var(--transition-normal)',
                    color: 'var(--color-tertiary)',
                  }}>
                    <FolderArchive size={28} />
                  </div>

                  <h3 className="font-headline" style={{
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: 'var(--color-on-surface)',
                    marginBottom: '0.5rem',
                  }}>
                    Xavier Files
                  </h3>

                  <p className="font-body" style={{
                    color: 'var(--color-on-surface-variant)',
                    lineHeight: 1.6,
                    marginBottom: '2rem',
                    flex: 1,
                  }}>
                    Access existing vector databases and deeply researched archives. Perfect for
                    continuing previous investigations.
                  </p>

                  <div>
                    <label className="text-label-lg" style={{
                      display: 'block',
                      color: 'var(--color-secondary)',
                      marginBottom: '0.5rem',
                    }}>
                      Choose domain
                    </label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {['AI', 'Healthcare', 'Social'].map((domain) => (
                        <button
                          key={domain}
                          className="chip chip-outlined"
                          onClick={() => handleDomainSelect(domain)}
                          disabled={loadingDomain !== null}
                        >
                          {loadingDomain === domain ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : null}
                          {domain}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
