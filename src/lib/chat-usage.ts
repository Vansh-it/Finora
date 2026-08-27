/**
 * Chat usage limit service — 15 messages per user per rolling 24-hour period.
 * Uses globalThis to survive Astro HMR module re-initialization.
 */

const CHAT_LIMIT = 15;
const ROLLING_WINDOW_SECONDS = 24 * 3600;

// Use globalThis to survive HMR
const g = globalThis as any;
if (!g.__finora_message_log) g.__finora_message_log = new Map<string, number[]>();
const messageLog: Map<string, number[]> = g.__finora_message_log;

function pruneOld(userId: string) {
  const cutoff = Date.now() / 1000 - ROLLING_WINDOW_SECONDS;
  const msgs = messageLog.get(userId);
  if (msgs) {
    const filtered = msgs.filter((ts) => ts > cutoff);
    if (filtered.length === 0) messageLog.delete(userId);
    else messageLog.set(userId, filtered);
  }
}

export function canSendMessage(userId: string): boolean {
  pruneOld(userId);
  const msgs = messageLog.get(userId) ?? [];
  return msgs.length < CHAT_LIMIT;
}

export function recordMessage(userId: string) {
  pruneOld(userId);
  const msgs = messageLog.get(userId) ?? [];
  const used = msgs.length;

  if (used >= CHAT_LIMIT) {
    const resetIn = Math.max(0, Math.round(msgs[0] + ROLLING_WINDOW_SECONDS - Date.now() / 1000));
    return { allowed: false, used, limit: CHAT_LIMIT, remaining: 0, reset_in_seconds: resetIn };
  }

  msgs.push(Date.now() / 1000);
  messageLog.set(userId, msgs);

  const newUsed = msgs.length;
  const newRemaining = Math.max(0, CHAT_LIMIT - newUsed);
  const resetIn = msgs.length > 0
    ? Math.max(0, Math.round(msgs[0] + ROLLING_WINDOW_SECONDS - Date.now() / 1000))
    : 0;

  return { allowed: true, used: newUsed, limit: CHAT_LIMIT, remaining: newRemaining, reset_in_seconds: resetIn };
}

export function getUsage(userId: string) {
  pruneOld(userId);
  const msgs = messageLog.get(userId) ?? [];
  const used = msgs.length;
  const remaining = Math.max(0, CHAT_LIMIT - used);
  const resetIn = msgs.length > 0
    ? Math.max(0, Math.round(msgs[0] + ROLLING_WINDOW_SECONDS - Date.now() / 1000))
    : 0;

  return { used, limit: CHAT_LIMIT, remaining, reset_in_seconds: resetIn };
}
