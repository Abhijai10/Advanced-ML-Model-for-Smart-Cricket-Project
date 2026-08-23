'use client';

import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';

interface AppLayoutProps {
  children: React.ReactNode;
  activePath: string;
}

type Theme = 'violet' | 'cyber';

export default function AppLayout({ children, activePath }: AppLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
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

  return (
    <div className="flex h-screen bg-background overflow-hidden" data-theme={theme}>
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((p) => !p)}
        activePath={activePath}
        theme={theme}
        onThemeChange={setTheme}
      />
      <main
        className="flex-1 overflow-y-auto scrollbar-thin transition-all duration-300"
        style={{ minWidth: 0 }}
      >
        {children}
      </main>
    </div>
  );
}
