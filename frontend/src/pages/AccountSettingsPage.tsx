import { useState } from 'react';
import * as Avatar from '@radix-ui/react-avatar';
import * as Popover from '@radix-ui/react-popover';
import * as RadioGroup from '@radix-ui/react-radio-group';
import * as ScrollArea from '@radix-ui/react-scroll-area';
import {
  Camera, X, Plus, Beaker, Palette, Sun, Moon, ArrowLeft,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';

export function AccountSettingsPage() {
  const { theme, setTheme } = useTheme();
  const [interests, setInterests] = useState([
    'Genetic Mutation',
    'Evolutionary Ethics',
    'Artificial Intelligence',
  ]);
  const [newTopic, setNewTopic] = useState('');
  const [popoverOpen, setPopoverOpen] = useState(false);

  const addInterest = () => {
    const trimmed = newTopic.trim();
    if (trimmed && !interests.includes(trimmed)) {
      setInterests((prev) => [...prev, trimmed]);
      setNewTopic('');
      setPopoverOpen(false);
    }
  };

  const removeInterest = (topic: string) => {
    setInterests((prev) => prev.filter((t) => t !== topic));
  };

  return (
    <ScrollArea.Root className="scroll-area-root" style={{ flex: 1 }}>
      <ScrollArea.Viewport className="scroll-area-viewport">
        <div style={{
          maxWidth: '72rem',
          margin: '0 auto',
          padding: '2rem',
        }}>
          {/* Back navigation */}
          <Link to="/" className="btn btn-ghost" style={{
            marginBottom: '1.5rem',
            display: 'inline-flex',
          }}>
            <ArrowLeft size={18} />
            Back to Workspace
          </Link>

          {/* Page header */}
          <div style={{ marginBottom: '2.5rem' }}>
            <h1 className="text-display-md" style={{
              color: 'var(--color-on-background)',
              marginBottom: '0.75rem',
            }}>
              Account Overview
            </h1>
            <p className="text-body-lg" style={{ color: 'var(--color-on-surface-variant)' }}>
              Manage your profile, preferences, and subscription details.
            </p>
          </div>

          {/* Bento grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(12, 1fr)',
            gap: '1.5rem',
          }}>
            {/* Profile Card — spans 8 columns */}
            <div className="card" style={{
              gridColumn: 'span 8',
            }}>
              <div style={{
                display: 'flex',
                gap: '2rem',
                alignItems: 'flex-start',
                marginBottom: '2rem',
              }}>
                {/* Avatar with edit overlay */}
                <div style={{ position: 'relative', flexShrink: 0 }}>
                  <Avatar.Root className="avatar-root" style={{ width: 128, height: 128 }}>
                    <Avatar.Fallback className="avatar-fallback" style={{
                      fontSize: '3rem',
                      background: 'var(--color-primary-container)',
                    }}>
                      CX
                    </Avatar.Fallback>
                  </Avatar.Root>
                  <button className="btn btn-icon" style={{
                    position: 'absolute',
                    bottom: 0,
                    right: 0,
                    background: 'var(--color-primary)',
                    color: 'var(--color-on-primary)',
                    width: '2.25rem',
                    height: '2.25rem',
                    borderRadius: 'var(--radius-full)',
                    boxShadow: 'var(--shadow-md)',
                  }}>
                    <Camera size={16} />
                  </button>
                </div>

                {/* Info */}
                <div style={{ flex: 1 }}>
                  <h2 className="text-headline-lg" style={{
                    color: 'var(--color-on-surface)',
                    marginBottom: '0.25rem',
                  }}>
                    Charles Xavier
                  </h2>
                  <p className="text-body-lg" style={{
                    color: 'var(--color-primary)',
                    marginBottom: '1.5rem',
                  }}>
                    charles.xavier@mutant-research.edu
                  </p>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '1rem',
                  }}>
                    <div style={{
                      padding: '1rem',
                      background: 'var(--color-surface-container)',
                      borderRadius: 'var(--radius-lg)',
                    }}>
                      <p className="text-label-md" style={{
                        color: 'var(--color-on-surface-variant)',
                        marginBottom: '0.25rem',
                      }}>
                        Role
                      </p>
                      <p className="text-title-md" style={{ color: 'var(--color-on-surface)' }}>
                        Lead Researcher
                      </p>
                    </div>
                    <div style={{
                      padding: '1rem',
                      background: 'var(--color-surface-container)',
                      borderRadius: 'var(--radius-lg)',
                    }}>
                      <p className="text-label-md" style={{
                        color: 'var(--color-on-surface-variant)',
                        marginBottom: '0.25rem',
                      }}>
                        Institution
                      </p>
                      <p className="text-title-md" style={{ color: 'var(--color-on-surface)' }}>
                        Xavier Institute
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Spacer for 4 remaining columns on first row */}
            <div style={{ gridColumn: 'span 4' }} />

            {/* Research Interests Card — spans 6 columns */}
            <div className="card" style={{ gridColumn: 'span 6' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '1.5rem',
              }}>
                <Beaker size={20} style={{ color: 'var(--color-tertiary)' }} />
                <h3 className="text-title-lg" style={{ color: 'var(--color-on-surface)', flex: 1 }}>
                  Research Interests
                </h3>
              </div>

              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '0.5rem',
              }}>
                {interests.map((topic) => (
                  <span key={topic} className="chip chip-filled" style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                  }}>
                    {topic}
                    <button
                      className="btn btn-icon"
                      onClick={() => removeInterest(topic)}
                      style={{ padding: '0.125rem' }}
                      aria-label={`Remove ${topic}`}
                    >
                      <X size={14} />
                    </button>
                  </span>
                ))}

                <Popover.Root open={popoverOpen} onOpenChange={setPopoverOpen}>
                  <Popover.Trigger asChild>
                    <button className="chip" style={{
                      border: '2px dashed color-mix(in srgb, var(--color-outline-variant) 50%, transparent)',
                      background: 'transparent',
                      color: 'var(--color-on-surface-variant)',
                    }}>
                      <Plus size={14} />
                      Add Topic
                    </button>
                  </Popover.Trigger>
                  <Popover.Portal>
                    <Popover.Content className="popover-content" sideOffset={8}>
                      <p className="text-label-lg" style={{
                        color: 'var(--color-on-surface)',
                        marginBottom: '0.75rem',
                      }}>
                        Add a research interest
                      </p>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <input
                          className="input"
                          placeholder="e.g. Quantum Computing"
                          value={newTopic}
                          onChange={(e) => setNewTopic(e.target.value)}
                          onKeyDown={(e) => { if (e.key === 'Enter') addInterest(); }}
                          style={{ flex: 1 }}
                        />
                        <button
                          className="btn btn-primary"
                          onClick={addInterest}
                          disabled={!newTopic.trim()}
                          style={{ padding: '0.5rem 1rem' }}
                        >
                          Add
                        </button>
                      </div>
                      <Popover.Arrow className="popover-arrow" />
                    </Popover.Content>
                  </Popover.Portal>
                </Popover.Root>
              </div>
            </div>

            {/* Workspace Preferences Card — spans 6 columns */}
            <div className="card" style={{ gridColumn: 'span 6' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '1.5rem',
              }}>
                <Palette size={20} style={{ color: 'var(--color-primary)' }} />
                <h3 className="text-title-lg" style={{ color: 'var(--color-on-surface)' }}>
                  Workspace Preferences
                </h3>
              </div>

              <p className="text-label-lg" style={{
                color: 'var(--color-on-surface-variant)',
                marginBottom: '1rem',
              }}>
                Theme Preference
              </p>

              <RadioGroup.Root
                className="radio-group-root"
                value={theme}
                onValueChange={(val) => setTheme(val as 'light' | 'dark')}
              >
                <RadioGroup.Item value="light" className="radio-card" asChild>
                  <button style={{
                    background: theme === 'light'
                      ? 'var(--color-surface-container-low)'
                      : 'var(--color-surface-container)',
                    textAlign: 'left',
                    width: '100%',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <Sun size={20} style={{
                        color: theme === 'light' ? 'var(--color-primary)' : 'var(--color-on-surface-variant)',
                      }} />
                      <div>
                        <p className="text-title-md" style={{ color: 'var(--color-on-surface)' }}>
                          Terra Light
                        </p>
                        <p className="text-label-md" style={{ color: 'var(--color-on-surface-variant)' }}>
                          Warm, earthy tones
                        </p>
                      </div>
                    </div>
                    <div className="radio-indicator" />
                  </button>
                </RadioGroup.Item>

                <RadioGroup.Item value="dark" className="radio-card" asChild>
                  <button style={{
                    background: theme === 'dark'
                      ? 'var(--color-surface-container-low)'
                      : 'var(--color-surface-container)',
                    textAlign: 'left',
                    width: '100%',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <Moon size={20} style={{
                        color: theme === 'dark' ? 'var(--color-primary)' : 'var(--color-on-surface-variant)',
                      }} />
                      <div>
                        <p className="text-title-md" style={{ color: 'var(--color-on-surface)' }}>
                          Terra Dark
                        </p>
                        <p className="text-label-md" style={{ color: 'var(--color-on-surface-variant)' }}>
                          Deep, calming tones
                        </p>
                      </div>
                    </div>
                    <div className="radio-indicator" />
                  </button>
                </RadioGroup.Item>
              </RadioGroup.Root>
            </div>
          </div>
        </div>
      </ScrollArea.Viewport>
      <ScrollArea.Scrollbar className="scroll-area-scrollbar" orientation="vertical">
        <ScrollArea.Thumb className="scroll-area-thumb" />
      </ScrollArea.Scrollbar>
    </ScrollArea.Root>
  );
}
