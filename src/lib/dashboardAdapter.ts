/**
 * Dashboard data adapter.
 *
 * Transforms the universal backend dashboard payload into the format
 * consumed by existing React dashboard components. Handles the mapping
 * from backend camelCase/snake_case to frontend types.
 */

const BACKEND_URL = '';

// ── Types ────────────────────────────────────────────────────────────────────
export interface ExecutiveSummary {
  executive_overview: string;
  highlights: { title: string; text: string; importance: string }[];
  growth_analysis: string;
  profitability_analysis: string;
  cash_flow_analysis: string;
  balance_sheet_analysis: string;
  watch_items: { title: string; reason: string; severity: string }[];
  management_commentary_summary: string;
  data_quality_note: string;
  _metadata?: Record<string, unknown>;
}

export interface ValuationMetric {
  metric_id: string;
  name: string;
  display_value: string;
  value: number | null;
  status: string;
  applicability: string;
  formula: string;
  inputs: { name: string; value: number; source?: string }[];
  calculation: string;
  market_data_date: string;
  reason: string;
}

export interface ValuationSection {
  market_data: {
    price: number | null;
    price_date: string;
    previous_close: number | null;
    percent_change: number | null;
    exchange: string;
    currency: string;
    source: string;
    is_historical?: boolean;
    alignment_status?: string;
    target_date?: string;
  };
  metrics: ValuationMetric[];
  period_alignment: {
    financial_period: string;
    market_data_date: string;
    is_current_valuation: boolean;
    note: string;
    financial_period_end?: string;
    alignment_status?: string;
  };
  is_financial_institution: boolean;
  is_historical?: boolean;
}

export interface DashboardData {
  company: {
    name: string;
    ticker: string;
    exchange: string;
    period: string;
    period_mode: string;
    currency: string;
    cik: string;
    logoInitials: string;
  };
  periods: string[];
  kpis: KpiData[];
  income_statement: TableData;
  balance_sheet: TableData;
  cash_flow: TableData;
  growth: TableData;
  profitability: { metric: string; value: string; note: string }[];
  liquidity: { metric: string; value: string; note: string }[];
  leverage: { metric: string; value: string; note: string }[];
  efficiency: { metric: string; value: string; note: string }[];
  capital_allocation: { metric: string; value: string; note: string }[];
  dupont: {
    roe: string;
    net_margin: string;
    asset_turnover: string;
    equity_multiplier: string;
    calculation: string;
    methodology: string;
  } | null;
  charts: {
    revenue: { label: string; value: number }[];
    operating_income: { label: string; value: number }[];
    net_income: { label: string; value: number }[];
    free_cash_flow: { label: string; value: number }[];
  };
  sources: SourceData[];
  management_commentary: CommentaryItem[];
  executive_summary: ExecutiveSummary | null;
  valuation: ValuationSection | null;
  data_quality: {
    primary_source: string;
    metrics_calculated: number;
    cross_verified: number;
    mismatches: number;
    sources_count: number;
  };
}

export interface KpiData {
  id: string;
  label: string;
  value: string;
  change: { value: string; direction: 'up' | 'down' | 'flat' };
  spark: number[];
  verification: {
    formula: string;
    values: { label: string; value: string }[];
    source: { doc: string; page: string };
    explanation: string;
    verification_status?: string;
  };
}

export interface TableData {
  columns: string[];
  rows: { label: string; values: string[]; strong?: boolean }[];
}

export interface SourceData {
  id: string;
  name: string;
  meta: string;
  pages: string;
  status: string;
  url?: string;
  trust_tier?: number;
  period?: string;
}

export interface CommentaryItem {
  topic: string;
  summary: string;
  sentiment: string;
  importance: string;
}

export interface SeriesPoint {
  label: string;
  value: number;
}

// ── Fetcher ──────────────────────────────────────────────────────────────────
export async function fetchDashboardData(sessionId: string): Promise<DashboardData> {
  const res = await fetch(`${BACKEND_URL}/api/research/result/${sessionId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Adapters ─────────────────────────────────────────────────────────────────

/** Convert backend KPI to frontend Kpi type for KpiCard/VerificationModal */
export function adaptKpi(kpi: KpiData) {
  return {
    id: kpi.id,
    label: kpi.label,
    value: kpi.value,
    change: kpi.change,
    spark: kpi.spark.length > 0 ? kpi.spark : [0],
    verification: kpi.verification,
  };
}

/** Convert backend table to chart SeriesPoint[] */
export function adaptChart(chartData: { label: string; value: number }[]): SeriesPoint[] {
  return chartData.map((d) => ({ label: d.label, value: d.value }));
}

/** Convert backend source to frontend Source type */
export function adaptSource(src: SourceData) {
  return {
    id: src.id,
    name: src.name,
    meta: src.meta,
    pages: src.pages,
    status: src.status,
  };
}
