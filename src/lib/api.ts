const API_BASE = import.meta.env.VITE_API_URL || "";

const MAX_RETRIES = 2;
const INITIAL_RETRY_DELAY = 1000;

export class ApiError extends Error {
  status: number;
  payload: Record<string, unknown> | null;

  constructor(message: string, status: number, payload: Record<string, unknown> | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retries = MAX_RETRIES
): Promise<T> {
  const url = `${API_BASE}${path}`;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      // Set a generous timeout: 180s for chat, 120s for research endpoints, 30s default
      const isChat = path.includes("/chat");
      const isResearch = path.includes("/research/");
      const timeoutMs = isChat ? 45000 : isResearch ? 120000 : 30000;
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      const res = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      const contentType = res.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        const text = await res.text();
        throw new Error(
          text.includes("<!doctype")
            ? `Server returned HTML instead of JSON. Make sure the backend is running on port 8000.`
            : `API error (${res.status}): ${text.slice(0, 200)}`
        );
      }

      const data = await res.json();

      if (!res.ok) {
        const errorMsg = data?.error || `Request failed (${res.status})`;
        throw new ApiError(errorMsg, res.status, data);
      }

      return data as T;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));

      // Don't retry on 4xx client errors (quota 429, conflict 409, etc.)
      if (
        (err instanceof ApiError && err.status >= 400 && err.status < 500) ||
        lastError.message.includes("(4") ||
        lastError.message.includes("company_limit_reached")
      ) {
        throw lastError;
      }

      // Don't retry if this was the last attempt
      if (attempt >= retries) break;

      // Retry with exponential backoff
      const delay = INITIAL_RETRY_DELAY * Math.pow(2, attempt);
      await sleep(delay);
    }
  }

  // All retries failed — provide a clear, actionable error message
  const msg = lastError?.message || "Unknown error";
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
    throw new Error(
      "Could not reach the Finora backend. Make sure the server is running (npm run dev:all) and try again."
    );
  }
  if (msg.includes("abort")) {
    throw new Error(
      "The request timed out. The AI is still thinking — please try again."
    );
  }
  throw lastError || new Error("Request failed after multiple attempts.");
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthUser {
  user_id: string;
  email: string;
  name: string;
}

export async function signUp(
  email: string,
  password: string,
  name: string
): Promise<{ token: string; user: AuthUser }> {
  return apiFetch("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export async function signIn(
  email: string,
  password: string
): Promise<{ token: string; user: AuthUser }> {
  return apiFetch("/api/auth/signin", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getProfile(
  token: string
): Promise<{ user: AuthUser }> {
  return apiFetch("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatResponse {
  response: string;
  model_used: string;
  status: string;
  elapsed_ms: number;
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export async function sendChatMessage(
  message: string,
  history: ChatHistoryMessage[] = [],
  token?: string
): Promise<ChatResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, history }),
    headers,
  });
}

export async function sendDashboardChatMessage(
  message: string,
  sessionId: string,
  history: ChatHistoryMessage[] = [],
  token?: string
): Promise<ChatResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/chat/dashboard", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId, history }),
    headers,
  });
}

// ── Chat research streaming + usage quota ───────────────────────────────────

export interface ChatUsage {
  messages_used: number;
  messages_limit: number;
  messages_remaining: number;
  words_used: number;
  words_limit: number;
  words_remaining: number;
  reset_at: string;
}

export async function getChatUsage(token?: string): Promise<ChatUsage> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return apiFetch("/api/chat/usage", { headers });
}

export interface ChatSource {
  title: string;
  url: string;
  publisher: string;
  published_at?: string;
  tier?: string;
}

export interface ChatResearchInfo {
  mode: string;
  performed: boolean;
  num_queries: number;
  num_sources_found: number;
  num_sources_used: number;
  search_ms: number;
  fetch_ms: number;
  llm_ms: number;
  total_ms: number;
  degraded: boolean;
}

export interface ChatUsageInline extends Partial<ChatUsage> {
  remaining?: number;
  limit?: number;
}

export interface ChatAnswerPayload {
  response: string;
  status: string;
  elapsed_ms: number;
  word_count?: number;
  response_compressed?: boolean;
  sources?: ChatSource[];
  research?: ChatResearchInfo;
  usage?: ChatUsageInline;
}

export type ChatStage =
  | "understanding"
  | "internal"
  | "searching"
  | "comparing"
  | "synthesizing";

export interface ChatStreamHandlers {
  onStatus?: (stage: ChatStage) => void;
  onAnswer?: (payload: ChatAnswerPayload) => void;
  onError?: (message: string) => void;
}

/**
 * POST /api/chat/stream — reads an SSE-style stream of JSON frames:
 *   {"event":"status","stage":...} | {"event":"answer",...} | {"event":"error",...}
 * Research statuses are emitted only when the backend actually runs that stage.
 */
export async function streamChatMessage(opts: {
  message: string;
  history?: ChatHistoryMessage[];
  sessionId?: string | null;
  previousMode?: string | null;
  token?: string;
  handlers: ChatStreamHandlers;
}): Promise<void> {
  const { message, history = [], sessionId, previousMode, token, handlers } = opts;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120000);

  try {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        message,
        history,
        session_id: sessionId || "",
        previous_mode: previousMode || null,
      }),
      signal: controller.signal,
    });

    if (!res.ok) {
      let msg = `Request failed (${res.status})`;
      try {
        const data = await res.json();
        if (data?.error) msg = data.error;
      } catch {
        /* keep generic message */
      }
      const err = new Error(msg) as Error & { status?: number };
      err.status = res.status;
      throw err;
    }

    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("text/event-stream")) {
      const data = await res.json();
      if (data?.event === "error" || data?.error) {
        handlers.onError?.(data.error || "Request failed");
      } else if (data?.response) {
        handlers.onAnswer?.(data as ChatAnswerPayload);
      }
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      throw new Error("Streaming is not supported by this browser.");
    }
    const decoder = new TextDecoder();
    let buffer = "";

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const line = frame.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        let parsed: Record<string, unknown> & { event?: string };
        try {
          parsed = JSON.parse(line.slice(6));
        } catch {
          continue;
        }
        if (parsed.event === "status") {
          handlers.onStatus?.(parsed.stage as ChatStage);
        } else if (parsed.event === "answer") {
          handlers.onAnswer?.(parsed as unknown as ChatAnswerPayload);
        } else if (parsed.event === "error") {
          handlers.onError?.(
            (parsed.error as string) || "Finora is temporarily unable to respond."
          );
        }
      }
    }
  } finally {
    clearTimeout(timeoutId);
  }
}

// ── Intent Classification ─────────────────────────────────────────────────────

export interface IntentResult {
  intent: "chat" | "research";
  confidence: number;
  reasoning?: string;
}

export async function classifyIntent(
  prompt: string
): Promise<IntentResult> {
  return apiFetch("/api/classify-intent", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

// ── Research Pipeline ─────────────────────────────────────────────────────────

export interface GrantPermissionResponse {
  session_id: string;
  company: string;
  status: string;
  period_mode: string;
}

export async function grantPermission(
  company: string,
  periodMode: string = "latest",
  startYear?: number,
  endYear?: number,
  token?: string
): Promise<GrantPermissionResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/grant-permission", {
    method: "POST",
    body: JSON.stringify({
      company,
      period_mode: periodMode,
      start_year: startYear,
      end_year: endYear,
    }),
    headers,
  });
}

export interface FetchFilingsResponse {
  status: string;
  company: { name: string; ticker: string; cik: string; exchange: string };
  period: { mode: string; start_year: number; end_year: number; label: string };
  documents: Array<{
    document_id: string;
    form: string;
    filing_date: string;
    period_of_report: string;
    source_url: string;
    primary_document: string;
  }>;
  document_count: number;
}

export async function fetchFilings(
  sessionId: string,
  token?: string
): Promise<FetchFilingsResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/research/fetch-filings", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
    headers,
  });
}

export interface ExtractFinancialsResponse {
  status: string;
  company: { name: string; ticker: string; cik: string };
  periods: string[];
  income_statement: Record<string, unknown>;
  balance_sheet: Record<string, unknown>;
  cash_flow: Record<string, unknown>;
  additional: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export async function extractFinancials(
  sessionId: string,
  token?: string
): Promise<ExtractFinancialsResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/research/extract-financials", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
    headers,
  });
}

export interface CalculateMetricsResponse {
  status: string;
  company: { name: string; ticker: string };
  periods: string[];
  annual_metrics: Record<string, unknown>;
  growth_metrics: Record<string, unknown>;
  cagr_metrics: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export async function calculateMetrics(
  sessionId: string,
  token?: string
): Promise<CalculateMetricsResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/research/calculate-metrics", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
    headers,
  });
}

export interface DiscoverSourcesResponse {
  status: string;
  sources: Array<{
    source_id: string;
    source_type: string;
    authority: string;
    provider: string;
    url: string;
    title: string;
    period: string;
    trust_tier: number;
    status: string;
  }>;
  metadata: Record<string, unknown>;
}

export async function discoverSources(
  sessionId: string,
  token?: string
): Promise<DiscoverSourcesResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/research/discover-sources", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
    headers,
  });
}

export interface ReadVerifySourcesResponse {
  status: string;
  sources_read: number;
  metrics_verified: number;
  mismatches: number;
  verifications: Array<Record<string, unknown>>;
  commentary: Array<Record<string, unknown>>;
  summary: {
    total_compared: number;
    exact_matches: number;
    within_tolerance: number;
    mismatches: number;
    not_comparable: number;
    missing_external: number;
    missing_sec: number;
  };
}

export async function readVerifySources(
  sessionId: string,
  token?: string
): Promise<ReadVerifySourcesResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/research/read-verify-sources", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
    headers,
  });
}

export interface GenerateSummaryResponse {
  status: string;
  executive_summary: {
    executive_overview: string;
    highlights: Array<{ title: string; text: string }>;
    growth_analysis: string;
    profitability_analysis: string;
    cash_flow_analysis: string;
    balance_sheet_analysis: string;
    watch_items: Array<{ tag: string; text: string }>;
    management_commentary_summary: string;
    data_quality_note: string;
  };
  warning?: string;
}

export async function generateSummary(
  sessionId: string,
  token?: string
): Promise<GenerateSummaryResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/research/generate-summary", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
    headers,
  });
}

export interface CalculateValuationResponse {
  status: string;
  market_data: {
    ticker: string;
    name: string;
    exchange: string;
    currency: string;
    price: number | null;
    price_date: string;
    previous_close: number | null;
    percent_change: number | null;
    shares_outstanding: number | null;
    market_cap: number | null;
    source: string;
    error?: string;
    fallback?: boolean;
    historical?: boolean;
  };
  valuation_metrics: Record<string, unknown>;
  period_alignment: Record<string, unknown>;
  is_financial_institution: boolean;
}

export async function calculateValuation(
  sessionId: string,
  token?: string
): Promise<CalculateValuationResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/research/calculate-valuation", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
    headers,
  });
}

// ── Dashboard Payload ─────────────────────────────────────────────────────────

export interface DashboardPayload {
  company: {
    ticker: string;
    name: string;
    exchange: string;
    sector: string;
  };
  periods: string[];
  income_statement: Record<string, unknown>;
  balance_sheet: Record<string, unknown>;
  cash_flow: Record<string, unknown>;
  annual_metrics: Record<string, unknown>;
  growth_metrics: Record<string, unknown>;
  cagr_metrics: Record<string, unknown>;
  market_data: Record<string, unknown>;
  valuation_metrics: Record<string, unknown>;
  executive_summary: Record<string, unknown>;
  verification_results: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export async function getResearchResult(
  sessionId: string,
  token?: string
): Promise<DashboardPayload> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch(`/api/research/result/${sessionId}`, {
    headers,
  });
}

// ── Session ───────────────────────────────────────────────────────────────────

export async function getSession(
  sessionId: string
): Promise<Record<string, unknown>> {
  return apiFetch(`/api/session/${sessionId}`);
}

export async function cancelSession(
  sessionId: string
): Promise<{ session_id: string; status: string }> {
  return apiFetch("/api/cancel-session", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

// ── Research Quota ────────────────────────────────────────────────────────────

export async function getResearchQuota(
  token: string
): Promise<{
  allowed: boolean;
  used: number;
  limit: number;
  remaining: number;
  resets_at: number;
}> {
  return apiFetch("/api/research/quota", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ── Single Pipeline Call ─────────────────────────────────────────────────────

export interface RunResearchResponse {
  status: string;
  session_id: string;
  dashboard?: DashboardPayload;
  error?: string;
}

export async function runResearch(
  company: string,
  periodMode: string = "latest",
  token?: string
): Promise<RunResearchResponse> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return apiFetch("/api/research/run", {
    method: "POST",
    body: JSON.stringify({ company, period_mode: periodMode }),
    headers,
  });
}

// ── Research History ──────────────────────────────────────────────────────

export interface HistoryEntry {
  session_id: string;
  company: string;
  ticker: string;
  period: string;
  created_at: string;
  headline: string;
  metric_count: number;
  source_count: number;
  status: string;
}

export interface HistoryResponse {
  researches: HistoryEntry[];
  usage: {
    used: number;
    limit: number;
    remaining: number;
    resets_at?: number;
    exhausted?: boolean;
  };
}

export async function getResearchHistory(
  token: string
): Promise<HistoryResponse> {
  return apiFetch("/api/research/history", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ── Profile ────────────────────────────────────────────────────────────────

export interface ProfileData {
  user: {
    user_id: string;
    email: string;
    name: string;
    company?: string;
    research_runs_used: number;
    research_runs_limit: number;
  };
  completed_researches: number;
  usage: {
    used: number;
    limit: number;
    remaining: number;
    resets_at?: number;
  };
}

export async function getFullProfile(token: string): Promise<ProfileData> {
  return apiFetch("/api/auth/profile", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateProfile(
  token: string,
  data: { name?: string; company?: string }
): Promise<{ user: ProfileData["user"] }> {
  return apiFetch("/api/auth/update-profile", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

// ── Health Check ──────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{
  status: string;
  active_provider: string;
  providers_available: number;
}> {
  return apiFetch("/api/health");
}

// ── Reviews ──────────────────────────────────────────────────────────────────

export interface Review {
  timestamp: string;
  name: string;
  company: string;
  rating: number;
  review: string;
}

export interface ReviewsResponse {
  reviews: Review[];
  configured?: boolean;
  error?: string | null;
}

export async function getReviews(limit = 12): Promise<ReviewsResponse> {
  return apiFetch(`/api/reviews?limit=${limit}`);
}

export async function submitReview(data: {
  name: string;
  company: string;
  rating: number;
  review: string;
  website?: string;
}): Promise<{ status: string; message: string; review: Review }> {
  return apiFetch("/api/reviews", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
