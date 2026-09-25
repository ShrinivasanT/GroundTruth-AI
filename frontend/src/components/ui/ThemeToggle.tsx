import * as Switch from '@radix-ui/react-switch';
import { Sun, Moon } from 'lucide-react';

interface ThemeToggleProps {
  theme: 'light' | 'dark';
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
    }}>
      <Sun
        size={16}
        style={{
          color: theme === 'light' ? 'var(--color-primary)' : 'var(--color-on-surface-variant)',
          transition: 'color var(--transition-fast)',
        }}
      />
      <Switch.Root
        className="switch-root"
        checked={theme === 'dark'}
        onCheckedChange={onToggle}
        aria-label="Toggle dark mode"
      >
        <Switch.Thumb className="switch-thumb" />
      </Switch.Root>
      <Moon
        size={16}
        style={{
          color: theme === 'dark' ? 'var(--color-primary)' : 'var(--color-on-surface-variant)',
          transition: 'color var(--transition-fast)',
        }}
      />
    </div>
  );
}
