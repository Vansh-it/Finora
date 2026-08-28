/**
 * Server-side research session management — no Flask dependency.
 * Stores research sessions in JSON files on disk.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

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

export interface ResearchSession {
  session_id: string;
  user_id: string;
  company: string;
  status: string;
  period_mode: string;
  start_year: number | null;
  end_year: number | null;
  objective: string;
  created_at: number;
  error: string | null;
  company_meta: Record<string, any> | null;
  document_registry: Record<string, any> | null;
  financial_statements: Record<string, any> | null;
  calculated_metrics: Record<string, any> | null;
  source_registry: Record<string, any> | null;
  verification_results: Record<string, any> | null;
  executive_summary: Record<string, any> | null;
  market_data: Record<string, any> | null;
  valuation_metrics: Record<string, any> | null;
}

function toDict(session: ResearchSession): Record<string, any> {
  return { ...session };
}

export function createSession(
  userId: string,
  company: string,
  opts: {
    period_mode?: string;
    start_year?: number | null;
    end_year?: number | null;
    objective?: string;
  } = {},
): ResearchSession {
  const sessionId = crypto.randomBytes(32).toString('hex');
  const session: ResearchSession = {
    session_id: sessionId,
    user_id: userId,
    company,
    status: 'researching',
    period_mode: opts.period_mode ?? 'latest',
    start_year: opts.start_year ?? null,
    end_year: opts.end_year ?? null,
    objective: opts.objective ?? '',
    created_at: Date.now() / 1000,
    error: null,
    company_meta: null,
    document_registry: null,
    financial_statements: null,
    calculated_metrics: null,
    source_registry: null,
    verification_results: null,
    executive_summary: null,
    market_data: null,
    valuation_metrics: null,
  };

  const sessions = readJSON('research_sessions.json');
  sessions[sessionId] = toDict(session);
  writeJSON('research_sessions.json', sessions);

  return session;
}

export function getSession(sessionId: string): ResearchSession | null {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (!raw) return null;
  return raw as ResearchSession;
}

export function updateSession(sessionId: string, updates: Partial<ResearchSession>): ResearchSession | null {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (!raw) return null;
  Object.assign(raw, updates);
  writeJSON('research_sessions.json', sessions);
  return raw as ResearchSession;
}

export function updateSessionStatus(sessionId: string, status: string): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.status = status;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionCompanyMeta(sessionId: string, meta: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.company_meta = meta;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionDocumentRegistry(sessionId: string, registry: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.document_registry = registry;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionFinancialStatements(sessionId: string, statements: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.financial_statements = statements;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionCalculatedMetrics(sessionId: string, metrics: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.calculated_metrics = metrics;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionSourceRegistry(sessionId: string, registry: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.source_registry = registry;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionVerificationResults(sessionId: string, results: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.verification_results = results;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionExecutiveSummary(sessionId: string, summary: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.executive_summary = summary;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionMarketData(sessionId: string, data: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.market_data = data;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionValuationMetrics(sessionId: string, metrics: Record<string, any>): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.valuation_metrics = metrics;
    writeJSON('research_sessions.json', sessions);
  }
}

export function setSessionError(sessionId: string, error: string): void {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (raw) {
    raw.status = 'error';
    raw.error = error;
    writeJSON('research_sessions.json', sessions);
  }
}

export function cancelSession(sessionId: string): boolean {
  const sessions = readJSON('research_sessions.json');
  const raw = sessions[sessionId];
  if (!raw) return false;
  raw.status = 'cancelled';
  writeJSON('research_sessions.json', sessions);
  return true;
}

export function incrementResearchRuns(userId: string): boolean {
  const users = readJSON('users.json');
  const user = users[userId];
  if (!user) return false;
  if (user.research_runs_used >= user.research_runs_limit) return false;
  user.research_runs_used += 1;
  writeJSON('users.json', users);
  return true;
}

export function canUseResearch(userId: string) {
  const users = readJSON('users.json');
  const user = users[userId];
  if (!user) {
    return { allowed: false, remaining: 0, limit: 5, used: 0, reason: 'User not found' };
  }
  const remaining = Math.max(0, (user.research_runs_limit ?? 5) - (user.research_runs_used ?? 0));
  return {
    allowed: remaining > 0,
    remaining,
    limit: user.research_runs_limit ?? 5,
    used: user.research_runs_used ?? 0,
  };
}

export { toDict };
