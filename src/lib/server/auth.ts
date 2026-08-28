/**
 * Server-side auth for Astro — no Flask dependency.
 * Uses JSON-file persistence (same format as the Flask backend).
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

// ── Data paths ──────────────────────────────────────────────────────────────
const DATA_DIR = path.resolve(process.cwd(), 'backend', 'data');

function ensureDir() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
}

function readJSON(name: string): Record<string, any> {
  const p = path.join(DATA_DIR, name);
  if (!fs.existsSync(p)) return {};
  try {
    const raw = fs.readFileSync(p, 'utf-8');
    const data = JSON.parse(raw);
    return typeof data === 'object' && data !== null ? data : {};
  } catch {
    return {};
  }
}

function writeJSON(name: string, data: Record<string, any>) {
  ensureDir();
  const p = path.join(DATA_DIR, name);
  fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf-8');
}

// ── Password hashing (PBKDF2 SHA-256, Werkzeug-compatible) ──────────────────
// Werkzeug format: pbkdf2:sha256:iterations$salt_hex$hash_hex
function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString('hex');
  const derived = crypto.pbkdf2Sync(password, salt, 600_000, 32, 'sha256');
  return `pbkdf2:sha256:600000$${salt}$${derived.toString('hex')}`;
}

function verifyPassword(password: string, stored: string): boolean {
  try {
    // Werkzeug format: pbkdf2:sha256:iterations$salt_hex$hash_hex
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

// ── Token generation ────────────────────────────────────────────────────────
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

export function signUp(email: string, password: string, name: string = '') {
  email = email.trim().toLowerCase();
  if (!email || !password) throw new Error('Email and password are required');
  if (password.length < 8) throw new Error('Password must be at least 8 characters');

  const emailIndex = readJSON('email_index.json');
  if (emailIndex[email]) throw new Error('An account with this email already exists');

  const users = readJSON('users.json');
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

  users[userId] = user;
  emailIndex[email] = userId;

  const token = generateToken();
  const sessions = readJSON('auth_sessions.json');
  sessions[token] = {
    token,
    user_id: userId,
    created_at: Date.now() / 1000,
    expires_at: Date.now() / 1000 + 7 * 24 * 3600,
  };

  writeJSON('users.json', users);
  writeJSON('email_index.json', emailIndex);
  writeJSON('auth_sessions.json', sessions);

  return { user: toPublic(user), token };
}

export function signIn(email: string, password: string) {
  email = email.trim().toLowerCase();
  if (!email || !password) throw new Error('Email and password are required');

  const emailIndex = readJSON('email_index.json');
  const userId = emailIndex[email];
  if (!userId) throw new Error('No account found with this email');

  const users = readJSON('users.json');
  const user = users[userId] as StoredUser | undefined;
  if (!user) throw new Error('No account found with this email');

  if (!verifyPassword(password, user.password_hash)) {
    throw new Error('Incorrect password');
  }

  const token = generateToken();
  const sessions = readJSON('auth_sessions.json');
  sessions[token] = {
    token,
    user_id: userId,
    created_at: Date.now() / 1000,
    expires_at: Date.now() / 1000 + 7 * 24 * 3600,
  };
  writeJSON('auth_sessions.json', sessions);

  return { user: toPublic(user), token };
}

export function signOut(token: string): boolean {
  const sessions = readJSON('auth_sessions.json');
  if (sessions[token]) {
    delete sessions[token];
    writeJSON('auth_sessions.json', sessions);
    return true;
  }
  return false;
}

export function getUserFromToken(token: string): StoredUser | null {
  if (!token) return null;
  const sessions = readJSON('auth_sessions.json');
  const session: StoredSession | undefined = sessions[token];
  if (!session) return null;
  if (Date.now() / 1000 > session.expires_at) {
    // Expired
    delete sessions[token];
    writeJSON('auth_sessions.json', sessions);
    return null;
  }
  const users = readJSON('users.json');
  return (users[session.user_id] as StoredUser) || null;
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
