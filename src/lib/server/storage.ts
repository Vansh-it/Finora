/**
 * Unified storage abstraction for Finora server-side state.
 *
 * Priority order:
 *   1. Upstash Redis  (production with UPSTASH env vars)
 *   2. JSON files     (local development)
 *   3. In-memory Map  (Vercel without Redis — graceful degradation)
 *
 * This replaces direct fs usage in auth.ts and research-sessions.ts.
 */

// ── Detection ────────────────────────────────────────────────────────────────
const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL || '';
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN || '';
const USE_REDIS = Boolean(UPSTASH_URL && UPSTASH_TOKEN);

let redis: any = null;
if (USE_REDIS) {
  try {
    const { Redis } = await import('@upstash/redis');
    redis = new Redis({ url: UPSTASH_URL, token: UPSTASH_TOKEN });
  } catch {
    // Redis module not available — fall through to filesystem/memory
  }
}

// ── Filesystem fallback ──────────────────────────────────────────────────────
let USE_FS = false;
let fs: typeof import('node:fs') | null = null;
let path: typeof import('node:path') | null = null;
let DATA_DIR = '';

try {
  fs = await import('node:fs');
  path = await import('node:path');
  DATA_DIR = path.resolve(process.cwd(), 'backend', 'data');

  // Test if we can actually write here (will fail on Vercel)
  if (fs.existsSync(DATA_DIR) || (() => {
    try {
      fs.mkdirSync(DATA_DIR, { recursive: true });
      return true;
    } catch {
      return false;
    }
  })()) {
    USE_FS = true;
  }
} catch {
  // node:fs not available (edge runtime) — use in-memory
}

// ── In-memory fallback (last resort for Vercel without Redis) ────────────────
const memStore: Map<string, Map<string, Record<string, any>>> = new Map();

function memGet(namespace: string): Map<string, Record<string, any>> {
  if (!memStore.has(namespace)) memStore.set(namespace, new Map());
  return memStore.get(namespace)!;
}

// ── Filesystem helpers ───────────────────────────────────────────────────────
function ensureDir() {
  if (!fs || !DATA_DIR) return;
  try {
    if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  } catch {
    // Vercel read-only — silently fail
  }
}

function readJSONFile(name: string): Record<string, any> {
  if (!fs || !DATA_DIR) return {};
  const p = path!.join(DATA_DIR, name);
  try {
    if (!fs.existsSync(p)) return {};
    const raw = fs.readFileSync(p, 'utf-8');
    const data = JSON.parse(raw);
    return typeof data === 'object' && data !== null ? data : {};
  } catch {
    return {};
  }
}

function writeJSONFile(name: string, data: Record<string, any>) {
  if (!fs || !DATA_DIR) return;
  try {
    ensureDir();
    const p = path!.join(DATA_DIR, name);
    fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf-8');
  } catch {
    // Vercel read-only — silently fail
  }
}

// ── Storage backend selector ─────────────────────────────────────────────────
function getBackend(): 'redis' | 'fs' | 'memory' {
  if (USE_REDIS && redis) return 'redis';
  if (USE_FS) return 'fs';
  return 'memory';
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Get a JSON object by key. Returns empty object if not found.
 */
export async function getItem(namespace: string, key: string): Promise<Record<string, any>> {
  const backend = getBackend();

  if (backend === 'redis') {
    try {
      const raw = await redis.get(`${namespace}:${key}`);
      if (!raw) return {};
      if (typeof raw === 'object') return raw;
      const parsed = JSON.parse(raw);
      return typeof parsed === 'object' && parsed !== null ? parsed : {};
    } catch {
      return {};
    }
  }

  if (backend === 'fs') {
    return readJSONFile(`${namespace}.json`)[key] || {};
  }

  // In-memory
  return memGet(namespace).get(key) || {};
}

/**
 * Set a JSON object by key.
 */
export async function setItem(namespace: string, key: string, value: Record<string, any>): Promise<void> {
  const backend = getBackend();

  if (backend === 'redis') {
    try {
      await redis.set(`${namespace}:${key}`, JSON.stringify(value));
    } catch (err) {
      console.error(`Redis setItem failed for ${namespace}:${key}:`, err);
    }
    return;
  }

  if (backend === 'fs') {
    const file = `${namespace}.json`;
    const all = readJSONFile(file);
    all[key] = value;
    writeJSONFile(file, all);
    return;
  }

  // In-memory
  memGet(namespace).set(key, value);
}

/**
 * Delete a key from a namespace.
 */
export async function deleteItem(namespace: string, key: string): Promise<void> {
  const backend = getBackend();

  if (backend === 'redis') {
    try {
      await redis.del(`${namespace}:${key}`);
    } catch (err) {
      console.error(`Redis deleteItem failed for ${namespace}:${key}:`, err);
    }
    return;
  }

  if (backend === 'fs') {
    const file = `${namespace}.json`;
    const all = readJSONFile(file);
    delete all[key];
    writeJSONFile(file, all);
    return;
  }

  // In-memory
  memGet(namespace).delete(key);
}

/**
 * Get all items in a namespace as a Record<string, any>.
 */
export async function getAll(namespace: string): Promise<Record<string, any>> {
  const backend = getBackend();

  if (backend === 'redis') {
    try {
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

  if (backend === 'fs') {
    return readJSONFile(`${namespace}.json`);
  }

  // In-memory
  const ns = memGet(namespace);
  const result: Record<string, any> = {};
  ns.forEach((v, k) => { result[k] = v; });
  return result;
}

/**
 * Set all items in a namespace (bulk write).
 */
export async function setAll(namespace: string, data: Record<string, any>): Promise<void> {
  const backend = getBackend();

  if (backend === 'redis') {
    try {
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

  if (backend === 'fs') {
    writeJSONFile(`${namespace}.json`, data);
    return;
  }

  // In-memory
  const ns = memGet(namespace);
  for (const [key, value] of Object.entries(data)) {
    ns.set(key, value);
  }
}

/**
 * Check which storage backend is in use.
 */
export function getStorageBackend(): string {
  return getBackend();
}

/** @deprecated Use getStorageBackend() */
export function isRedisStorage(): boolean {
  return getBackend() === 'redis';
}

// ── Namespace constants ──────────────────────────────────────────────────────
export const NS_USERS = 'users';
export const NS_AUTH_SESSIONS = 'auth_sessions';
export const NS_RESEARCH_SESSIONS = 'research_sessions';
export const NS_CHAT_USAGE = 'chat_usage';
export const NS_EMAIL_INDEX = 'email_index';
