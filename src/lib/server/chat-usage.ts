/**
 * Server-side chat usage tracker — no Flask dependency.
 * Tracks per-user message counts with JSON-file persistence.
 */
import fs from 'node:fs';
import path from 'node:path';

const DATA_DIR = path.resolve(process.cwd(), 'backend', 'data');
const CHAT_LIMIT = 15;
const ROLLING_WINDOW_SECONDS = 24 * 3600; // 24 hours

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

function pruneOld(timestamps: number[]): number[] {
  const cutoff = Date.now() / 1000 - ROLLING_WINDOW_SECONDS;
  return timestamps.filter((ts) => ts > cutoff);
}

export function getChatUsage(userId: string) {
  const log = readJSON('chat_usage.json');
  const messages: number[] = pruneOld(log[userId] || []);
  const used = messages.length;
  const remaining = Math.max(0, CHAT_LIMIT - used);
  let resetInSeconds = 0;
  if (messages.length > 0) {
    resetInSeconds = Math.max(0, Math.round(messages[0] + ROLLING_WINDOW_SECONDS - Date.now() / 1000));
  }
  return { used, limit: CHAT_LIMIT, remaining, reset_in_seconds: resetInSeconds };
}

export function recordChatMessage(userId: string) {
  const log = readJSON('chat_usage.json');
  const messages: number[] = pruneOld(log[userId] || []);

  if (messages.length >= CHAT_LIMIT) {
    const resetIn = Math.max(0, Math.round(messages[0] + ROLLING_WINDOW_SECONDS - Date.now() / 1000));
    return {
      allowed: false,
      used: messages.length,
      limit: CHAT_LIMIT,
      remaining: 0,
      reset_in_seconds: resetIn,
    };
  }

  messages.push(Date.now() / 1000);
  log[userId] = messages;
  writeJSON('chat_usage.json', log);

  const remaining = Math.max(0, CHAT_LIMIT - messages.length);
  let resetIn = 0;
  if (messages.length > 0) {
    resetIn = Math.max(0, Math.round(messages[0] + ROLLING_WINDOW_SECONDS - Date.now() / 1000));
  }

  return {
    allowed: true,
    used: messages.length,
    limit: CHAT_LIMIT,
    remaining,
    reset_in_seconds: resetIn,
  };
}
