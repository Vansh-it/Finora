/**
 * Auth service — file-backed users + sessions.
 * Survives Astro HMR module re-initialization.
 */

import { createHash, randomBytes } from 'crypto';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

// ── Persistent storage via JSON file ──────────────────────────────────────
const DATA_DIR = join(process.cwd(), '.finora-data');
const USERS_FILE = join(DATA_DIR, 'users.json');
const SESSIONS_FILE = join(DATA_DIR, 'sessions.json');
const EMAIL_INDEX_FILE = join(DATA_DIR, 'email-index.json');

interface UserRecord {
  userId: string;
  email: string;
  name: string;
  passwordHash: string;
  createdAt: number;
  researchRunsUsed: number;
  researchRunsLimit: number;
}

interface Session {
  token: string;
  userId: string;
  createdAt: number;
  expiresAt: number;
}

function ensureDir() {
  if (!existsSync(DATA_DIR)) {
    mkdirSync(DATA_DIR, { recursive: true });
  }
}

function loadJson<T>(file: string, fallback: T): T {
  try {
    if (existsSync(file)) return JSON.parse(readFileSync(file, 'utf-8'));
  } catch { /* ignore */ }
  return fallback;
}

function saveJson(file: string, data: any) {
  ensureDir();
  writeFileSync(file, JSON.stringify(data, null, 2));
}

const users: Map<string, UserRecord> = new Map(Object.entries(loadJson<Record<string, UserRecord>>(USERS_FILE, {})));
const sessions: Map<string, Session> = new Map(Object.entries(loadJson<Record<string, Session>>(SESSIONS_FILE, {})));
const emailIndex: Map<string, string> = new Map(Object.entries(loadJson<Record<string, string>>(EMAIL_INDEX_FILE, {})));

function persist() {
  saveJson(USERS_FILE, Object.fromEntries(users));
  saveJson(SESSIONS_FILE, Object.fromEntries(sessions));
  saveJson(EMAIL_INDEX_FILE, Object.fromEntries(emailIndex));
}

// ── Password hashing ──────────────────────────────────────────────────────
function hashPassword(password: string): string {
  const salt = randomBytes(16).toString('hex');
  const hash = createHash('sha256').update(`${salt}:${password}`).digest('hex');
  return `${salt}:${hash}`;
}

function verifyPassword(password: string, stored: string): boolean {
  const [salt, hash] = stored.split(':');
  const computed = createHash('sha256').update(`${salt}:${password}`).digest('hex');
  return computed === hash;
}

// ── User operations ───────────────────────────────────────────────────────
function userToDict(u: UserRecord) {
  return {
    user_id: u.userId,
    email: u.email,
    name: u.name,
    research_runs_used: u.researchRunsUsed,
    research_runs_limit: u.researchRunsLimit,
  };
}

export function signUp(email: string, password: string, name = '') {
  email = email.trim().toLowerCase();
  if (!email || !password) throw new Error('Email and password are required');
  if (emailIndex.has(email)) throw new Error('An account with this email already exists');
  if (password.length < 8) throw new Error('Password must be at least 8 characters');

  const userId = randomBytes(16).toString('hex');
  const user: UserRecord = {
    userId,
    email,
    name: name.trim(),
    passwordHash: hashPassword(password),
    createdAt: Date.now(),
    researchRunsUsed: 0,
    researchRunsLimit: 5,
  };
  users.set(userId, user);
  emailIndex.set(email, userId);

  const session = createSession(userId);
  persist();
  return { user: userToDict(user), token: session.token };
}

export function signIn(email: string, password: string) {
  email = email.trim().toLowerCase();
  const userId = emailIndex.get(email);
  if (!userId) throw new Error('No account found with this email');

  const user = users.get(userId)!;
  if (!verifyPassword(password, user.passwordHash)) throw new Error('Incorrect password');

  const session = createSession(userId);
  persist();
  return { user: userToDict(user), token: session.token };
}

export function getUserFromToken(token: string): UserRecord | null {
  const session = sessions.get(token);
  if (!session || session.expiresAt < Date.now() / 1000) return null;
  return users.get(session.userId) ?? null;
}

export function signOut(token: string): boolean {
  const result = sessions.delete(token);
  persist();
  return result;
}

export function clearAll() {
  users.clear();
  sessions.clear();
  emailIndex.clear();
  persist();
}

function createSession(userId: string): Session {
  const token = randomBytes(32).toString('hex');
  const session: Session = {
    token,
    userId,
    createdAt: Date.now() / 1000,
    expiresAt: Date.now() / 1000 + 7 * 24 * 3600,
  };
  sessions.set(token, session);
  return session;
}
