/**
 * Server-side research session management — Vercel-compatible storage.
 * Upstash Redis in production, JSON files locally.
 */
import crypto from 'node:crypto';
import {
  getItem, setItem, deleteItem, getAll,
  NS_RESEARCH_SESSIONS, NS_USERS,
} from './storage';

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

export async function createSession(
  userId: string,
  company: string,
  opts: {
    period_mode?: string;
    start_year?: number | null;
    end_year?: number | null;
    objective?: string;
  } = {},
): Promise<ResearchSession> {
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

  await setItem(NS_RESEARCH_SESSIONS, sessionId, toDict(session));
  return session;
}

export async function getSession(sessionId: string): Promise<ResearchSession | null> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (!raw || !raw.session_id) return null;
  return raw as unknown as ResearchSession;
}

export async function updateSession(sessionId: string, updates: Partial<ResearchSession>): Promise<ResearchSession | null> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (!raw || !raw.session_id) return null;
  Object.assign(raw, updates);
  await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  return raw as unknown as ResearchSession;
}

export async function updateSessionStatus(sessionId: string, status: string): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.status = status;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionCompanyMeta(sessionId: string, meta: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.company_meta = meta;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionDocumentRegistry(sessionId: string, registry: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.document_registry = registry;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionFinancialStatements(sessionId: string, statements: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.financial_statements = statements;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionCalculatedMetrics(sessionId: string, metrics: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.calculated_metrics = metrics;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionSourceRegistry(sessionId: string, registry: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.source_registry = registry;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionVerificationResults(sessionId: string, results: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.verification_results = results;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionExecutiveSummary(sessionId: string, summary: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.executive_summary = summary;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionMarketData(sessionId: string, data: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.market_data = data;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionValuationMetrics(sessionId: string, metrics: Record<string, any>): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.valuation_metrics = metrics;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function setSessionError(sessionId: string, error: string): Promise<void> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (raw && raw.session_id) {
    raw.status = 'error';
    raw.error = error;
    await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  }
}

export async function cancelSession(sessionId: string): Promise<boolean> {
  const raw = await getItem(NS_RESEARCH_SESSIONS, sessionId);
  if (!raw || !raw.session_id) return false;
  raw.status = 'cancelled';
  await setItem(NS_RESEARCH_SESSIONS, sessionId, raw);
  return true;
}

export async function incrementResearchRuns(userId: string): Promise<boolean> {
  const user = await getItem(NS_USERS, userId);
  if (!user || !user.user_id) return false;
  if ((user.research_runs_used ?? 0) >= (user.research_runs_limit ?? 5)) return false;
  user.research_runs_used = (user.research_runs_used ?? 0) + 1;
  await setItem(NS_USERS, userId, user);
  return true;
}

export async function canUseResearch(userId: string) {
  const user = await getItem(NS_USERS, userId);
  if (!user || !user.user_id) {
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
