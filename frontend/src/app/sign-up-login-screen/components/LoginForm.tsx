'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '@/lib/supabase';

interface LoginFormData {
  email: string;
  password: string;
  rememberMe: boolean;
}

interface LoginFormProps {
  onSwitchMode: () => void;
}

export default function LoginForm({ onSwitchMode }: LoginFormProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<LoginFormData>({
    defaultValues: { email: '', password: '', rememberMe: false },
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);
    if (!supabase) {
      setError('email', { message: 'Authentication is not configured for this environment.' });
    } else {
      const { error } = await supabase.auth.signInWithPassword({
        email: data.email,
        password: data.password,
      });
      if (error) {
        setError('email', { message: error.message });
      } else {
        toast.success('Welcome back.');
        router.push('/home-screen');
      }
    }
    setIsLoading(false);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <h2 className="text-xl font-bold text-foreground mb-1">Welcome back</h2>
      <p className="text-sm text-muted-foreground mb-6">Sign in to your SmartCricket account</p>

      {/* Email */}
      <div className="mb-4">
        <label className="block text-sm font-semibold text-foreground mb-1.5">Email address</label>
        <input
          type="email"
          className="input-field"
          placeholder="you@example.com"
          autoComplete="email"
          {...register('email', {
            required: 'Email is required',
            pattern: {
              value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
              message: 'Enter a valid email address',
            },
          })}
        />
        {errors.email && <p className="text-xs text-red-400 mt-1.5">{errors.email.message}</p>}
      </div>

      {/* Password */}
      <div className="mb-4">
        <label className="block text-sm font-semibold text-foreground mb-1.5">Password</label>
        <div className="relative">
          <input
            type={showPassword ? 'text' : 'password'}
            className="input-field pr-10"
            placeholder="Enter your password"
            autoComplete="current-password"
            {...register('password', {
              required: 'Password is required',
              minLength: { value: 6, message: 'Minimum 6 characters' },
            })}
          />
          <button
            type="button"
            onClick={() => setShowPassword((p) => !p)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        {errors.password && (
          <p className="text-xs text-red-400 mt-1.5">{errors.password.message}</p>
        )}
      </div>

      {/* Remember me */}
      <div className="flex items-center gap-2 mb-6">
        <input
          type="checkbox"
          id="rememberMe"
          className="w-4 h-4 rounded border-border bg-input accent-primary cursor-pointer"
          {...register('rememberMe')}
        />
        <label
          htmlFor="rememberMe"
          className="text-sm text-muted-foreground cursor-pointer select-none"
        >
          Remember me for 30 days
        </label>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isLoading}
        className="btn-primary w-full py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
        style={{ minHeight: '44px' }}
      >
        {isLoading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Signing in…
          </>
        ) : (
          'Sign In'
        )}
      </button>

      <p className="text-center text-sm text-muted-foreground mt-5">
        No account yet?{' '}
        <button
          type="button"
          onClick={onSwitchMode}
          className="text-accent font-semibold hover:underline"
        >
          Create one
        </button>
      </p>
    </form>
  );
}
