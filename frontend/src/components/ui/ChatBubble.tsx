import * as Tooltip from '@radix-ui/react-tooltip';
import { ExternalLink } from 'lucide-react';
import type { Citation } from '../../lib/api';

interface ChatBubbleProps {
  role: 'user' | 'ai';
  content: string;
  citations?: Citation[];
  repos?: Array<{ url: string; name: string }>;
}

function formatContent(text: string): string {
  // Convert **bold** to <strong>
  let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Convert newlines to <br>
  html = html.replace(/\n/g, '<br />');
  return html;
}

export function ChatBubble({ role, content, citations, repos }: ChatBubbleProps) {
  if (role === 'user') {
    return (
      <div className="chat-bubble chat-bubble-user">
        <div dangerouslySetInnerHTML={{ __html: formatContent(content) }} />
      </div>
    );
  }

  return (
    <div className="chat-bubble chat-bubble-ai">
      <div className="chat-ai-avatar">
        <span>X</span>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div dangerouslySetInnerHTML={{ __html: formatContent(content) }} />

        {/* Citations */}
        {citations && citations.length > 0 && (
          <div style={{
            marginTop: '0.75rem',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.375rem',
          }}>
            {citations.map((citation, idx) => {
              const title = citation.title || citation.metadata?.title || 'Unknown Title';
              const arxivId = citation.paper_id || citation.metadata?.arxiv_id;
              const page = citation.page !== undefined ? citation.page : citation.metadata?.page;
              return (
                <Tooltip.Root key={idx}>
                  <Tooltip.Trigger asChild>
                    <span className="citation-badge">[{idx + 1}]</span>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content className="tooltip-content" side="top" sideOffset={4}>
                      <strong>{title}</strong>
                      {arxivId && (
                        <div style={{
                          marginTop: '0.25rem',
                          fontSize: '0.75rem',
                          opacity: 0.8,
                        }}>
                          arXiv: {arxivId}
                          {page ? ` • Page ${page}` : ''}
                        </div>
                      )}
                      <Tooltip.Arrow className="tooltip-arrow" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              );
            })}
          </div>
        )}

        {/* Repos */}
        {repos && repos.length > 0 && (
          <div style={{
            marginTop: '0.75rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid color-mix(in srgb, var(--color-outline-variant) 20%, transparent)',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.5rem',
            alignItems: 'center',
          }}>
            {repos.map((repo, idx) => (
              <a
                key={idx}
                href={repo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="chip chip-filled"
                style={{ textDecoration: 'none', fontSize: '0.8125rem' }}
              >
                <ExternalLink size={12} />
                {repo.name}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
