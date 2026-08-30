/**
 * Server-side auth for Astro — proxies all auth operations to Flask backend.
 *
 * This eliminates the split-brain issue where Astro had its own auth store
 * separate from Flask's. All user data lives in one place (Flask).
 */
import { Redis } from '@upstash/redis';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// ── Types ───────────────────────────────────────────────────────────────────
export interface AuthUser {
  user_id: string;
  email: string;
  name: string;
  research_runs_used: number;
  research_runs_limit: number;
}

export interface StoredSession {
  token: string;
  user_id: string;
  created_at: number;
  expires_at: number;
}

// ── Backend proxy helper ────────────────────────────────────────────────────
async function flaskRequest(
  method: string,
  path: string,
  body?: Record<string, any>,
  token?: string,
): Promise<{ ok: boolean; status: number; data: any }> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    // Backend unreachable
    return { ok: false, status: 502, data: { error: 'Backend unavailable' } };
  }
}

// ── Public API ──────────────────────────────────────────────────────────────

export async function signUp(
  email: string,
  password: string,
  name: string = '',
): Promise<{ user: AuthUser; token: string }> {
  const result = await flaskRequest('POST', '/api/auth/signup', {
    email,
    password,
    name,
  });

  if (!result.ok) {
    throw new Error(result.data?.error || 'Sign up failed');
  }

  return {
    user: result.data.user as AuthUser,
    token: result.data.token as string,
  };
}

export async function signIn(
  email: string,
  password: string,
): Promise<{ user: AuthUser; token: string }> {
  const result = await flaskRequest('POST', '/api/auth/signin', {
    email,
    password,
  });

  if (!result.ok) {
    throw new Error(result.data?.error || 'Sign in failed');
  }

  return {
    user: result.data.user as AuthUser,
    token: result.data.token as string,
  };
}

export async function signOut(token: string): Promise<boolean> {
  const result = await flaskRequest('POST', '/api/auth/signout', {}, token);
  return result.ok;
}

export async function getUserFromToken(token: string): Promise<AuthUser | null> {
  if (!token) return null;

  const result = await flaskRequest('GET', '/api/auth/me', undefined, token);
  if (!result.ok) return null;

  return {
    user_id: result.data.user_id,
    email: result.data.email,
    name: result.data.name || '',
    research_runs_used: result.data.research_runs_used ?? 0,
    research_runs_limit: result.data.research_runs_limit ?? 5,
  };
}
