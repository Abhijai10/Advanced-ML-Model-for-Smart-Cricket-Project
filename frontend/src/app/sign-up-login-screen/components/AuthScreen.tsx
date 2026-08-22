'use client';

import React, { useState } from 'react';
import LoginForm from './LoginForm';
import SignupForm from './SignupForm';
import AppLogo from '@/components/ui/AppLogo';
import { Activity, Shield, TrendingUp, Zap } from 'lucide-react';

const BRAND_FEATURES = [
  {
    icon: <Zap size={16} />,
    text: 'Real-time ML shot classification',
  },
  {
    icon: <TrendingUp size={16} />,
    text: 'Per-session accuracy tracking',
  },
  {
    icon: <Activity size={16} />,
    text: 'Cover drive, pull, sweep, defensive',
  },
  {
    icon: <Shield size={16} />,
    text: 'Independent player accounts',
  },
];

export default function AuthScreen() {
  const [mode, setMode] = useState<'login' | 'signup'>('login');

  return (
    <div className="min-h-screen bg-background flex overflow-hidden">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-[55%] flex-col relative overflow-hidden bg-cricket-pattern">
        {/* Background layers */}
        <div className="absolute inset-0 bg-grid-pattern" />
        <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-gradient-to-t from-background/80 to-transparent" />
        <div className="absolute top-0 right-0 w-96 h-96 rounded-full bg-primary/8 blur-3xl" />
        <div className="absolute bottom-20 left-20 w-64 h-64 rounded-full bg-accent/5 blur-3xl" />

        {/* Content */}
        <div className="relative z-10 flex flex-col h-full px-12 py-10">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <AppLogo size={40} />
            <span className="font-bold text-xl text-foreground tracking-tight">
              SmartCricket
            </span>
          </div>

          {/* Hero text */}
          <div className="flex-1 flex flex-col justify-center max-w-md">
            <div className="mb-3">
              <span className="text-xs font-semibold tracking-widest uppercase text-accent bg-primary/10 border border-primary/20 px-3 py-1 rounded-full">
                ML-Powered Analysis
              </span>
            </div>
            <h1 className="text-4xl xl:text-5xl font-bold text-foreground leading-tight mb-4">
              Know every shot.{' '}
              <span className="text-gradient-violet">Improve every session.</span>
            </h1>
            <p className="text-base text-muted-foreground leading-relaxed mb-8">
              SmartCricket classifies your batting shots in real-time using machine learning — giving you instant feedback and session-by-session accuracy trends.
            </p>

            {/* Feature list */}
            <ul className="space-y-3">
              {BRAND_FEATURES.map((feat, i) => (
                <li
                  key={`feat-${i}`}
                  className="flex items-center gap-3 text-sm text-muted-foreground"
                >
                  <span className="w-7 h-7 rounded-lg bg-primary/15 border border-primary/25 flex items-center justify-center text-accent flex-shrink-0">
                    {feat.icon}
                  </span>
                  {feat.text}
                </li>
              ))}
            </ul>
          </div>

          {/* Bottom watermark */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground/50">
            <span>© 2026 SmartCricket</span>
            <span>·</span>
            <span>Powered by ML</span>
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center px-6 py-10 relative">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-primary/5" />

        <div className="relative z-10 w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex lg:hidden items-center gap-2 mb-8 justify-center">
            <AppLogo size={36} />
            <span className="font-bold text-lg text-foreground">SmartCricket</span>
          </div>

          {/* Tab toggle */}
          <div className="glass-card rounded-2xl p-1 flex mb-6">
            <button
              onClick={() => setMode('login')}
              className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition-all duration-200 ${
                mode === 'login' ?'bg-primary text-primary-foreground shadow-violet-sm' :'text-muted-foreground hover:text-foreground'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setMode('signup')}
              className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition-all duration-200 ${
                mode === 'signup' ?'bg-primary text-primary-foreground shadow-violet-sm' :'text-muted-foreground hover:text-foreground'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Form card */}
          <div className="glass-card rounded-2xl p-7 violet-glow">
            {mode === 'login' ? (
              <LoginForm onSwitchMode={() => setMode('signup')} />
            ) : (
              <SignupForm onSwitchMode={() => setMode('login')} />
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
