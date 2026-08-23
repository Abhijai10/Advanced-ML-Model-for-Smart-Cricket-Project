'use client';

import React from 'react';
import Link from 'next/link';
import AppLogo from '@/components/ui/AppLogo';
import { Home, Video, ClipboardList, ChevronLeft, ChevronRight, LogOut, User } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useSmartCricket } from './SmartCricketProvider';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: number;
}

const navItems: NavItem[] = [
  {
    label: 'Home',
    href: '/home-screen',
    icon: <Home size={20} />,
  },
  {
    label: 'Live Analysis',
    href: '/live-analysis-page',
    icon: <Video size={20} />,
    badge: 0,
  },
  {
    label: 'Sessions',
    href: '/sessions',
    icon: <ClipboardList size={20} />,
  },
];

type Theme = 'violet' | 'cyber';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  activePath: string;
  theme?: Theme;
  onThemeChange?: (t: Theme) => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export default function Sidebar({
  collapsed,
  onToggle,
  activePath,
  theme = 'violet',
  onThemeChange,
  mobileOpen = false,
  onMobileClose,
}: SidebarProps) {
  const { displayName, signOut } = useSmartCricket();
  const router = useRouter();

  async function handleSignOut() {
    onMobileClose?.();
    await signOut();
    router.replace('/sign-up-login-screen');
  }

  function handleNavClick() {
    onMobileClose?.();
  }

  return (
    <aside
      id="app-sidebar"
      className={`sidebar-drawer flex flex-col bg-card border-r border-border
        fixed inset-y-0 left-0 z-50 w-60 min-w-60
        md:relative md:z-20 md:translate-x-0
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        ${collapsed ? 'md:w-16 md:min-w-16' : 'md:w-60 md:min-w-60'}
      `}
    >
      {/* Logo */}
      <div
        className={`flex items-center h-16 px-4 border-b border-border ${
          collapsed ? 'md:justify-center gap-3' : 'gap-3'
        }`}
      >
        <AppLogo size={32} />
        <span
          className={`font-bold text-base text-foreground tracking-tight ${
            collapsed ? 'md:hidden' : ''
          }`}
        >
          SmartCricket
        </span>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        <div className={`mb-2 ${collapsed ? 'md:hidden' : 'block'}`}>
          <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground px-3">
            Navigation
          </span>
        </div>
        {navItems.map((item) => {
          const isActive =
            activePath === item.href || activePath.startsWith(item.href.split('#')[0]);
          return (
            <div
              key={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
              className="relative group"
            >
              <Link
                href={item.href}
                onClick={handleNavClick}
                className={`flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                  isActive ? 'nav-item-active' : 'nav-item-inactive'
                } ${collapsed ? 'md:justify-center gap-3' : 'gap-3'}`}
              >
                <span className={`flex-shrink-0 ${isActive ? 'text-accent' : ''}`}>
                  {item.icon}
                </span>
                <span className={`flex-1 truncate ${collapsed ? 'md:hidden' : ''}`}>
                  {item.label}
                </span>
                {item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`text-xs font-semibold bg-primary text-primary-foreground rounded-full w-5 h-5 flex items-center justify-center ${
                      collapsed ? 'md:hidden' : ''
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
              {collapsed && (
                <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150 hidden md:block">
                  <div className="bg-card border border-border text-foreground text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-card whitespace-nowrap">
                    {item.label}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Theme switcher */}
      {onThemeChange && (
        <div className={`px-2 pb-2 ${collapsed ? 'md:hidden' : 'block'}`}>
          <p className="text-xs font-semibold tracking-widest uppercase text-muted-foreground px-3 mb-2">
            Theme
          </p>
          <div className="flex gap-2 px-1">
            <button
              onClick={() => onThemeChange('violet')}
              title="Violet theme"
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition-all duration-150 border ${
                theme === 'violet'
                  ? 'bg-violet-500/20 border-violet-500/40 text-violet-300'
                  : 'border-border text-muted-foreground hover:text-foreground hover:border-violet-500/30'
              }`}
            >
              <span className="w-3 h-3 rounded-full bg-violet-500 flex-shrink-0" />
              Violet
            </button>
            <button
              onClick={() => onThemeChange('cyber')}
              title="Cyber theme"
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition-all duration-150 border ${
                theme === 'cyber'
                  ? 'bg-cyan-500/20 border-cyan-400/40 text-cyan-300'
                  : 'border-border text-muted-foreground hover:text-foreground hover:border-cyan-400/30'
              }`}
            >
              <span
                className="w-3 h-3 rounded-full bg-cyan-400 flex-shrink-0"
                style={{ boxShadow: '0 0 6px #00FFEE' }}
              />
              Cyber
            </button>
          </div>
        </div>
      )}

      {/* User + Collapse */}
      <div className="border-t border-border p-2 space-y-1">
        {/* User profile */}
        <div
          className={`flex items-center rounded-lg px-3 py-2.5 nav-item-inactive cursor-pointer ${
            collapsed ? 'md:justify-center gap-3' : 'gap-3'
          }`}
        >
          <div className="w-7 h-7 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
            <User size={14} className="text-accent" />
          </div>
          <div className={`flex-1 min-w-0 ${collapsed ? 'md:hidden' : ''}`}>
            <p className="text-sm font-semibold text-foreground truncate">{displayName}</p>
            <p className="text-xs text-muted-foreground truncate">Player</p>
          </div>
        </div>

        {/* Logout */}
        <div className="relative group">
          <button
            type="button"
            onClick={() => void handleSignOut()}
            className={`flex items-center rounded-lg px-3 py-2.5 nav-item-inactive text-sm font-medium transition-all duration-150 ${
              collapsed ? 'md:justify-center gap-3' : 'gap-3'
            }`}
          >
            <LogOut size={18} />
            <span className={collapsed ? 'md:hidden' : ''}>Sign Out</span>
          </button>
          {collapsed && (
            <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150 hidden md:block">
              <div className="bg-card border border-border text-foreground text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-card whitespace-nowrap">
                Sign Out
              </div>
            </div>
          )}
        </div>

        {/* Collapse toggle — desktop only */}
        <button
          onClick={onToggle}
          className={`hidden md:flex w-full items-center rounded-lg px-3 py-2.5 nav-item-inactive text-sm font-medium transition-all duration-150 ${
            collapsed ? 'justify-center' : 'gap-3'
          }`}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
