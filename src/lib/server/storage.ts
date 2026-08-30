/**
 * Unified storage abstraction for Finora server-side state.
 *
 * - Production (Vercel): Upstash Redis via @upstash/redis
 * - Local development: JSON files on disk (existing behavior)
 *
 * This replaces direct fs usage in auth.ts and research-sessions.ts.
 */

import { Redis } from '@upstash/redis';

// ── Detection ────────────────────────────────────────────────────────────────
const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL || '';
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN || '';
const USE_REDIS = Boolean(UPSTASH_URL && UPSTASH_TOKEN);

let redis: Redis | null = null;
if (USE_REDIS) {
  redis = new Redis({ url: UPSTASH_URL, token: UPSTASH_TOKEN });
}

// ── Filesystem fallback ──────────────────────────────────────────────────────
import fs from 'node:fs';
import path from 'node:path';

const DATA_DIR = path.resolve(process.cwd(), 'backend', 'data');

function ensureDir() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
}

function readJSONFile(name: string): Record<string, any> {
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

function writeJSONFile(name: string, data: Record<string, any>) {
  ensureDir();
  const p = path.join(DATA_DIR, name);
  fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf-8');
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Get a JSON object by key. Returns empty object if not found.
 * In Redis, the entire object is stored as a JSON string under one key.
 */
export async function getItem(namespace: string, key: string): Promise<Record<string, any>> {
  if (USE_REDIS && redis) {
    try {
      const raw = await redis.get<string>(`${namespace}:${key}`);
      if (!raw) return {};
      if (typeof raw === 'object') return raw;
      const parsed = JSON.parse(raw);
      return typeof parsed === 'object' && parsed !== null ? parsed : {};
    } catch {
      return {};
    }
  }
  // Filesystem: namespace IS the filename
  return readJSONFile(`${namespace}.json`)[key] || {};
}

/**
 * Set a JSON object by key.
 */
export async function setItem(namespace: string, key: string, value: Record<string, any>): Promise<void> {
  if (USE_REDIS && redis) {
    try {
      await redis.set(`${namespace}:${key}`, JSON.stringify(value));
    } catch (err) {
      console.error(`Redis setItem failed for ${namespace}:${key}:`, err);
    }
    return;
  }
  // Filesystem: read entire namespace file, update key, write back
  const file = `${namespace}.json`;
  const all = readJSONFile(file);
  all[key] = value;
  writeJSONFile(file, all);
}

/**
 * Delete a key from a namespace.
 */
export async function deleteItem(namespace: string, key: string): Promise<void> {
  if (USE_REDIS && redis) {
    try {
      await redis.del(`${namespace}:${key}`);
    } catch (err) {
      console.error(`Redis deleteItem failed for ${namespace}:${key}:`, err);
    }
    return;
  }
  const file = `${namespace}.json`;
  const all = readJSONFile(file);
  delete all[key];
  writeJSONFile(file, all);
}

/**
 * Get all items in a namespace as a Record<string, any>.
 */
export async function getAll(namespace: string): Promise<Record<string, any>> {
  if (USE_REDIS && redis) {
    try {
      // Use keys command to find all keys in this namespace
      const pattern = `${namespace}:*`;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const keys: string[] = await (redis as any).keys(pattern);
      if (!keys || keys.length === 0) return {};

      const values = await redis.mget(...keys) as (string | null)[];
      const result: Record<string, any> = {};
      for (let i = 0; i < keys.length; i++) {
        const fullKey = keys[i];
        const shortKey = fullKey.replace(`${namespace}:`, '');
        const raw = values[i];
        if (raw) {
          try {
            result[shortKey] = typeof raw === 'object' ? raw : JSON.parse(raw);
          } catch {
            result[shortKey] = raw;
          }
        }
      }
      return result;
    } catch (err) {
      console.error(`Redis getAll failed for ${namespace}:`, err);
      return {};
    }
  }
  return readJSONFile(`${namespace}.json`);
}

/**
 * Set all items in a namespace (bulk write).
 */
export async function setAll(namespace: string, data: Record<string, any>): Promise<void> {
  if (USE_REDIS && redis) {
    try {
      // Pipeline the writes
      const pipeline = redis.pipeline();
      for (const [key, value] of Object.entries(data)) {
        pipeline.set(`${namespace}:${key}`, JSON.stringify(value));
      }
      await pipeline.exec();
    } catch (err) {
      console.error(`Redis setAll failed for ${namespace}:`, err);
    }
    return;
  }
  writeJSONFile(`${namespace}.json`, data);
}

/**
 * Check if running with Redis (production) or filesystem (local dev).
 */
export function isRedisStorage(): boolean {
  return USE_REDIS;
}

// ── Namespace constants ──────────────────────────────────────────────────────
export const NS_USERS = 'users';
export const NS_AUTH_SESSIONS = 'auth_sessions';
export const NS_RESEARCH_SESSIONS = 'research_sessions';
export const NS_CHAT_USAGE = 'chat_usage';
export const NS_EMAIL_INDEX = 'email_index';
