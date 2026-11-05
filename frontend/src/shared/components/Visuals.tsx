import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

export function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem('derma-theme') === 'dark';
    } catch {
      return false;
    }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    try {
      localStorage.setItem('derma-theme', dark ? 'dark' : 'light');
    } catch {
      /* The preference is optional. */
    }
  }, [dark]);
  return (
    <button
      className="theme-toggle"
      onClick={() => setDark((value) => !value)}
      aria-label={dark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
      aria-pressed={dark}
      title={dark ? 'Giao diện sáng' : 'Giao diện tối'}
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}

export function LoadingSkeleton() {
  return (
    <div className="loading-skeleton" role="status" aria-label="Đang tải thư viện">
      <span className="skeleton skeleton-eyebrow" />
      <span className="skeleton skeleton-heading" />
      <span className="skeleton skeleton-description" />
      <div className="skeleton skeleton-hero" />
      <div className="skeleton-grid">
        {[0, 1, 2].map((i) => (
          <div className="skeleton skeleton-card" key={i} />
        ))}
      </div>
      <span className="visually-hidden">Đang mở thư viện…</span>
    </div>
  );
}
