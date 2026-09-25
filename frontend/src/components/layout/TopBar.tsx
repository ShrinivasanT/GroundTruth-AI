import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Avatar from '@radix-ui/react-avatar';
import { Share2, MoreVertical, LogOut, Download, Info } from 'lucide-react';

interface TopBarProps {
  sessionId: string | null;
  onEndSession: () => void;
  onGoToLanding: () => void;
}

export function TopBar({ sessionId, onEndSession, onGoToLanding }: TopBarProps) {
  return (
    <header className="topbar">
      <div 
        onClick={onGoToLanding}
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem',
          cursor: 'pointer',
        }}
      >
        <span className="font-headline" style={{
          fontWeight: 700,
          color: 'var(--color-primary)',
          fontSize: '1.125rem',
        }}>
          Professor X
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <button className="btn btn-icon" aria-label="Share">
          <Share2 size={18} />
        </button>

        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button className="btn btn-icon" aria-label="More options">
              <MoreVertical size={18} />
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content className="dropdown-content" sideOffset={4} align="end">
              <DropdownMenu.Item
                className="dropdown-item"
                disabled={!sessionId}
                onClick={onEndSession}
              >
                <LogOut size={16} />
                End Session
              </DropdownMenu.Item>
              <DropdownMenu.Item className="dropdown-item">
                <Download size={16} />
                Export Chat
              </DropdownMenu.Item>
              <DropdownMenu.Separator className="dropdown-separator" />
              <DropdownMenu.Item className="dropdown-item">
                <Info size={16} />
                About
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>

        <Avatar.Root className="avatar-root" style={{ width: 32, height: 32 }}>
          <Avatar.Fallback className="avatar-fallback" style={{ fontSize: '0.75rem' }}>
            CX
          </Avatar.Fallback>
        </Avatar.Root>
      </div>
    </header>
  );
}
