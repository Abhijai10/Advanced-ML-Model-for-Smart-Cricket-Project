'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '@/lib/supabase';

interface SignupFormData {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
}

interface SignupFormProps {
  onSwitchMode: () => void;
}

export default function SignupForm({ onSwitchMode }: SignupFormProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<SignupFormData>();

  const passwordValue = watch('password');

  const onSubmit = async (data: SignupFormData) => {
    setIsLoading(true);
    if (!supabase) {
      toast.error('Authentication is not configured for this environment.');
    } else {
      const { data: result, error } = await supabase.auth.signUp({
        email: data.email,
        password: data.password,
        options: { data: { full_name: data.fullName, display_name: data.fullName } },
      });
      if (error) {
        toast.error(error.message);
      } else if (result.session) {
        toast.success(`Account created. Welcome, ${data.fullName.split(' ')[0]}!`);
        router.push('/home-screen');
      } else {
        toast.success('Check your email to confirm your account, then sign in.');
        onSwitchMode();
      }
    }
    setIsLoading(false);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <h2 className="text-xl font-bold text-foreground mb-1">Create your account</h2>
      <p className="text-sm text-muted-foreground mb-6">
        Start tracking your batting sessions today
      </p>

      {/* Full Name */}
      <div className="mb-4">
        <label className="block text-sm font-semibold text-foreground mb-1.5">Full name</label>
        <input
          type="text"
          className="input-field"
          placeholder="Arjun Mehta"
          autoComplete="name"
          {...register('fullName', {
            required: 'Full name is required',
            minLength: { value: 2, message: 'Name must be at least 2 characters' },
          })}
        />
        {errors.fullName && (
          <p className="text-xs text-red-400 mt-1.5">{errors.fullName.message}</p>
        )}
      </div>

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
        <p className="text-xs text-muted-foreground mb-1.5">
          At least 8 characters with a number and a symbol
        </p>
        <div className="relative">
          <input
            type={showPassword ? 'text' : 'password'}
            className="input-field pr-10"
            placeholder="Create a strong password"
            autoComplete="new-password"
            {...register('password', {
              required: 'Password is required',
              minLength: { value: 8, message: 'Minimum 8 characters' },
              pattern: {
                value: /^(?=.*[0-9])(?=.*[!@#$%^&*])/,
                message: 'Must include at least one number and one symbol',
              },
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

      {/* Confirm Password */}
      <div className="mb-6">
        <label className="block text-sm font-semibold text-foreground mb-1.5">
          Confirm password
        </label>
        <div className="relative">
          <input
            type={showConfirm ? 'text' : 'password'}
            className="input-field pr-10"
            placeholder="Re-enter your password"
            autoComplete="new-password"
            {...register('confirmPassword', {
              required: 'Please confirm your password',
              validate: (val) => val === passwordValue || 'Passwords do not match',
            })}
          />
          <button
            type="button"
            onClick={() => setShowConfirm((p) => !p)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            aria-label={showConfirm ? 'Hide' : 'Show'}
          >
            {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        {errors.confirmPassword && (
          <p className="text-xs text-red-400 mt-1.5">{errors.confirmPassword.message}</p>
        )}
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
            Creating account…
          </>
        ) : (
          'Create Account'
        )}
      </button>

      <p className="text-center text-xs text-muted-foreground mt-4 leading-relaxed">
        By creating an account you agree to our{' '}
        <span className="text-accent hover:underline cursor-pointer">Terms of Service</span> and{' '}
        <span className="text-accent hover:underline cursor-pointer">Privacy Policy</span>
      </p>

      <p className="text-center text-sm text-muted-foreground mt-4">
        Already have an account?{' '}
        <button
          type="button"
          onClick={onSwitchMode}
          className="text-accent font-semibold hover:underline"
        >
          Sign in
        </button>
      </p>
    </form>
  );
}
