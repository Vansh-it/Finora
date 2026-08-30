/**
 * Server-side chat usage tracker — Vercel-compatible storage.
 * Upstash Redis in production, JSON files locally.
 */
import {
  getItem, setItem,
  NS_CHAT_USAGE,
} from './storage';

const CHAT_LIMIT = 15;
const ROLLING_WINDOW_SECONDS = 24 * 3600; // 24 hours

function pruneOld(timestamps: number[]): number[] {
  const cutoff = Date.now() / 1000 - ROLLING_WINDOW_SECONDS;
  return timestamps.filter((ts) => ts > cutoff);
}

export async function getChatUsage(userId: string) {
  const raw = await getItem(NS_CHAT_USAGE, userId);
  const messages: number[] = pruneOld(raw?.timestamps || []);
  const used = messages.length;
  const remaining = Math.max(0, CHAT_LIMIT - used);
  let resetInSeconds = 0;
  if (messages.length > 0) {
    resetInSeconds = Math.max(0, Math.round(messages[0] + ROLLING_WINDOW_SECONDS - Date.now() / 1000));
  }
  return { used, limit: CHAT_LIMIT, remaining, reset_in_seconds: resetInSeconds };
}

export async function recordChatMessage(userId: string) {
  const raw = await getItem(NS_CHAT_USAGE, userId);
  const messages: number[] = pruneOld(raw?.timestamps || []);

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
  await setItem(NS_CHAT_USAGE, userId, { timestamps: messages } as unknown as Record<string, any>);

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
