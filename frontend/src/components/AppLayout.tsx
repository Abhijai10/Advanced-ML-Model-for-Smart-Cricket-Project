'use client';

import React, { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import Sidebar from './Sidebar';
import AppLogo from '@/components/ui/AppLogo';

interface AppLayoutProps {
  children: React.ReactNode;
  activePath: string;
}

type Theme = 'violet' | 'cyber';

export default function AppLayout({ children, activePath }: AppLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>('violet');

  useEffect(() => {
    const stored = localStorage.getItem('sc-theme') as Theme | null;
    if (stored === 'violet' || stored === 'cyber') {
      setTheme(stored);
    }
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('sc-theme', theme);
  }, [theme]);

  useEffect(() => {
    if (!mobileOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileOpen]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  return (
    <div className="flex h-screen bg-background overflow-hidden" data-theme={theme}>
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-background/65 backdrop-blur-sm md:hidden"
          aria-label="Close menu"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((p) => !p)}
        activePath={activePath}
        theme={theme}
        onThemeChange={setTheme}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      <div className="flex flex-1 flex-col min-w-0">
        <header className="md:hidden flex items-center h-14 px-4 border-b border-border bg-card flex-shrink-0 z-30">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="w-10 h-10 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            aria-label="Open menu"
            aria-expanded={mobileOpen}
            aria-controls="app-sidebar"
          >
            <Menu size={20} />
          </button>
          <div className="flex items-center gap-2 ml-2">
            <AppLogo size={28} />
            <span className="font-bold text-sm text-foreground tracking-tight">SmartCricket</span>
          </div>
        </header>

        <main
          className="flex-1 overflow-y-auto scrollbar-thin transition-all duration-300"
          style={{ minWidth: 0 }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
