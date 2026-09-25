import { useRef, useCallback, useState } from 'react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { SendHorizontal, Users, FileSearch, PenTool, Paperclip, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSend, isLoading, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoResize = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }, []);

  const handleSend = useCallback(() => {
    if (!value.trim() || isLoading || disabled) return;
    onSend(value.trim());
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, isLoading, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const prependTag = (tag: string) => {
    setValue((prev) => {
      const text = prev.trim();
      if (text.startsWith(tag)) return prev;
      return `${tag} ${text}`;
    });
    textareaRef.current?.focus();
  };

  const agentTags = [
    { tag: '@buddy', icon: Users, label: 'Collaborative research agent' },
    { tag: '@review', icon: FileSearch, label: 'Paper review & analysis agent' },
    { tag: '@writer', icon: PenTool, label: 'Academic writing assistant' },
  ];

  return (
    <div>
      <div className="chat-input-inner">
        <textarea
          ref={textareaRef}
          className="textarea"
          placeholder={disabled ? "This research session has been terminated." : "Ask Professor X anything..."}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            autoResize();
          }}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
          id="chat-input-textarea"
        />

        <div className="chat-input-actions">
          <div className="chat-input-tags">
            {agentTags.map(({ tag, icon: Icon, label }) => (
              <Tooltip.Root key={tag}>
                <Tooltip.Trigger asChild>
                  <button
                    className="chip chip-outlined"
                    onClick={() => prependTag(tag)}
                    disabled={disabled}
                    style={{ fontSize: '0.8125rem', padding: '0.375rem 0.75rem' }}
                  >
                    <Icon size={14} />
                    {tag}
                  </button>
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content className="tooltip-content" side="top" sideOffset={8}>
                    {label}
                    <Tooltip.Arrow className="tooltip-arrow" />
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            ))}

            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button className="btn btn-icon" disabled={disabled} aria-label="Attach file">
                  <Paperclip size={18} />
                </button>
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content className="tooltip-content" side="top" sideOffset={8}>
                  Attach a file
                  <Tooltip.Arrow className="tooltip-arrow" />
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          </div>

          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!value.trim() || isLoading || disabled}
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <SendHorizontal size={20} />
            )}
          </button>
        </div>
      </div>

      <p className="disclaimer">
        Professor X can make mistakes. Consider verifying important information.
      </p>
    </div>
  );
}
