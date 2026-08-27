import { useState, useEffect, useCallback } from 'react';

const BACKEND_URL = '';

export interface AuthUser {
  user_id: string;
  email: string;
  name: string;
  research_runs_used: number;
  research_runs_limit: number;
}

// ── Global singleton state ──────────────────────────────────────────────────
// This avoids needing a React context provider (which can't wrap Astro components).
// Each component that calls useAuth() will re-render when state changes via the hook.

type Listener = () => void;
const listeners: Set<Listener> = new Set();

let _token: string | null = null;
let _user: AuthUser | null = null;
let _loading = true;
let _initialized = false;

function emitChange() {
  listeners.forEach((fn) => fn());
}

/** Initialize auth from localStorage (call once from any component) */
export function initAuth() {
  if (_initialized) return;
  _initialized = true;
  const stored = localStorage.getItem('finora_token');
  if (stored) {
    _token = stored;
    fetch(`${BACKEND_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${stored}` },
    })
      .then((r) => {
        if (r.ok) return r.json();
        throw new Error('Session expired');
      })
      .then((data) => {
        _user = data;
        emitChange();
      })
      .catch(() => {
        localStorage.removeItem('finora_token');
        _token = null;
        _user = null;
        emitChange();
      })
      .finally(() => {
        _loading = false;
        emitChange();
      });
  } else {
    _loading = false;
    emitChange();
  }
}

export function useAuth() {
  const [, setTick] = useState(0);

  useEffect(() => {
    initAuth();
    const listener = () => setTick((t) => t + 1);
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, []);

  // If backend is unreachable, resolve loading immediately
  useEffect(() => {
    if (_loading) {
      const t = setTimeout(() => {
        if (_loading) {
          _loading = false;
          emitChange();
        }
      }, 500);
      return () => clearTimeout(t);
    }
  }, []);

  const signUp = useCallback(async (email: string, password: string, name?: string) => {
    let res: Response;
    try {
      res = await fetch(`${BACKEND_URL}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      });
    } catch {
      throw new Error('Unable to connect to the server. Please make sure the backend is running on port 8000.');
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Sign up failed');
    localStorage.setItem('finora_token', data.token);
    _token = data.token;
    _user = data.user;
    emitChange();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    let res: Response;
    try {
      res = await fetch(`${BACKEND_URL}/api/auth/signin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
    } catch {
      throw new Error('Unable to connect to the server. Please make sure the backend is running on port 8000.');
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Sign in failed');
    localStorage.setItem('finora_token', data.token);
    _token = data.token;
    _user = data.user;
    emitChange();
  }, [])

  const signOut = useCallback(async () => {
    if (_token) {
      await fetch(`${BACKEND_URL}/api/auth/signout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${_token}` },
      }).catch(() => {});
    }
    localStorage.removeItem('finora_token');
    _token = null;
    _user = null;
    emitChange();
  }, []);

  return {
    user: _user,
    token: _token,
    loading: _loading,
    signUp,
    signIn,
    signOut,
  };
}

/** Get the current token (non-reactive, for use in callbacks) */
export function getToken(): string | null {
  return _token;
}
