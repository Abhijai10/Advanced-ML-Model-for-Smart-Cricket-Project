/**
 * Validates email addresses using a practical pattern that accepts common formats
 * (e.g. user.name@gmail.com, abc123@yahoo.com) without being overly strict.
 */
export function isValidEmail(email: string): boolean {
  const trimmed = email.trim();
  if (!trimmed || trimmed.length > 254) return false;

  const emailPattern =
    /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

  return emailPattern.test(trimmed);
}

/** User-facing message for react-hook-form email validation. */
export const EMAIL_VALIDATION_MESSAGE = 'Please enter a valid email address.';

export function validateEmailField(value: string): true | string {
  if (!value.trim()) return 'Email is required';
  if (!isValidEmail(value)) return EMAIL_VALIDATION_MESSAGE;
  return true;
}

/** Maps raw Supabase auth errors to friendly user-facing messages. */
export function mapAuthError(message: string): string {
  const normalized = message.toLowerCase().trim();

  if (normalized.includes('invalid email')) {
    return 'Please enter a valid email address.';
  }
  if (
    normalized.includes('email rate limit exceeded') ||
    normalized.includes('rate limit exceeded')
  ) {
    return 'Too many attempts. Please wait a few minutes and try again.';
  }
  if (normalized.includes('email limit exceeded')) {
    return 'Too many signup attempts. Please wait before trying again.';
  }
  if (
    normalized.includes('invalid login credentials') ||
    normalized.includes('invalid credentials')
  ) {
    return 'Incorrect email or password. Please try again.';
  }
  if (normalized.includes('email not confirmed')) {
    return 'Please confirm your email before signing in.';
  }
  if (
    normalized.includes('user already registered') ||
    normalized.includes('already registered') ||
    normalized.includes('already been registered')
  ) {
    return 'An account with this email already exists. Try signing in instead.';
  }
  if (normalized.includes('weak password') || normalized.includes('password is too weak')) {
    return 'Please choose a stronger password.';
  }
  if (normalized.includes('signup is disabled')) {
    return 'Sign up is currently unavailable. Please try again later.';
  }
  if (normalized.includes('network') || normalized.includes('fetch')) {
    return 'Connection error. Check your internet and try again.';
  }

  return 'Something went wrong. Please try again.';
}

export const SIGNUP_COOLDOWN_SECONDS = 30;

export function isRateLimitAuthError(message: string): boolean {
  const normalized = message.toLowerCase();
  return (
    normalized.includes('rate limit exceeded') ||
    normalized.includes('email limit exceeded') ||
    normalized.includes('too many requests')
  );
}
