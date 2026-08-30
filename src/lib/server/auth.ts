/**
 * Server-side auth for Astro — uses Vercel-compatible storage.
 * Upstash Redis in production, JSON files locally.
 */
import crypto from 'node:crypto';
import {
  getItem, setItem, deleteItem,
  NS_USERS, NS_AUTH_SESSIONS, NS_EMAIL_INDEX,
} from './storage';

// ── Password hashing (PBKDF2 SHA-256, Werkzeug-compatible) ──────────────────
function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString('hex');
  const derived = crypto.pbkdf2Sync(password, salt, 600_000, 32, 'sha256');
  return `pbkdf2:sha256:600000$${salt}$${derived.toString('hex')}`;
}

function verifyPassword(password: string, stored: string): boolean {
  try {
    const match = stored.match(/^pbkdf2:sha256:(\d+)\$([0-9a-f]+)\$([0-9a-f]+)$/);
    if (!match) return false;
    const iterations = parseInt(match[1], 10);
    const salt = match[2];
    const expectedHash = match[3];
    const derived = crypto.pbkdf2Sync(password, salt, iterations, 32, 'sha256');
    return crypto.timingSafeEqual(Buffer.from(derived.toString('hex'), 'hex'), Buffer.from(expectedHash, 'hex'));
  } catch {
    return false;
  }
}

// ── Token / ID generation ────────────────────────────────────────────────────
function generateToken(): string {
  return crypto.randomBytes(32).toString('hex');
}

function generateUserId(): string {
  return crypto.randomBytes(16).toString('hex');
}

// ── Types ───────────────────────────────────────────────────────────────────
interface StoredUser {
  user_id: string;
  email: string;
  name: string;
  password_hash: string;
  created_at: number;
  research_runs_used: number;
  research_runs_limit: number;
}

interface StoredSession {
  token: string;
  user_id: string;
  created_at: number;
  expires_at: number;
}

// ── Public API ──────────────────────────────────────────────────────────────

export async function signUp(email: string, password: string, name: string = '') {
  email = email.trim().toLowerCase();
  if (!email || !password) throw new Error('Email and password are required');
  if (password.length < 8) throw new Error('Password must be at least 8 characters');

  const existingEmail = await getItem(NS_EMAIL_INDEX, email);
  if (existingEmail && existingEmail.user_id) throw new Error('An account with this email already exists');

  const userId = generateUserId();
  const user: StoredUser = {
    user_id: userId,
    email,
    name: name.trim(),
    password_hash: hashPassword(password),
    created_at: Date.now() / 1000,
    research_runs_used: 0,
    research_runs_limit: 5,
  };

  await setItem(NS_USERS, userId, user as unknown as Record<string, any>);
  await setItem(NS_EMAIL_INDEX, email, { user_id: userId } as unknown as Record<string, any>);

  const token = generateToken();
  const session: StoredSession = {
    token,
    user_id: userId,
    created_at: Date.now() / 1000,
    expires_at: Date.now() / 1000 + 7 * 24 * 3600,
  };
  await setItem(NS_AUTH_SESSIONS, token, session as unknown as Record<string, any>);

  return { user: toPublic(user), token };
}

export async function signIn(email: string, password: string) {
  email = email.trim().toLowerCase();
  if (!email || !password) throw new Error('Email and password are required');

  const emailRecord = await getItem(NS_EMAIL_INDEX, email);
  const userId = emailRecord?.user_id;
  if (!userId) throw new Error('No account found with this email');

  const user = await getItem(NS_USERS, userId) as unknown as StoredUser | null;
  if (!user) throw new Error('No account found with this email');

  if (!verifyPassword(password, user.password_hash)) {
    throw new Error('Incorrect password');
  }

  const token = generateToken();
  const session: StoredSession = {
    token,
    user_id: userId,
    created_at: Date.now() / 1000,
    expires_at: Date.now() / 1000 + 7 * 24 * 3600,
  };
  await setItem(NS_AUTH_SESSIONS, token, session as unknown as Record<string, any>);

  return { user: toPublic(user), token };
}

export async function signOut(token: string): Promise<boolean> {
  const session = await getItem(NS_AUTH_SESSIONS, token) as unknown as StoredSession | null;
  if (session) {
    await deleteItem(NS_AUTH_SESSIONS, token);
    return true;
  }
  return false;
}

export async function getUserFromToken(token: string): Promise<StoredUser | null> {
  if (!token) return null;
  const session = await getItem(NS_AUTH_SESSIONS, token) as unknown as StoredSession | null;
  if (!session) return null;
  if (Date.now() / 1000 > session.expires_at) {
    await deleteItem(NS_AUTH_SESSIONS, token);
    return null;
  }
  const user = await getItem(NS_USERS, session.user_id) as unknown as StoredUser | null;
  return user || null;
}

function toPublic(user: StoredUser) {
  return {
    user_id: user.user_id,
    email: user.email,
    name: user.name,
    research_runs_used: user.research_runs_used,
    research_runs_limit: user.research_runs_limit,
  };
}
