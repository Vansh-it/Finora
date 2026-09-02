import { useEffect, useMemo, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import CompanyHeader from "../components/CompanyHeader";
import ResearchQualityBar from "../components/ResearchQualityBar";
import KPICard from "../components/KPICard";
import DashboardTabs, { type DashboardTab } from "../components/DashboardTabs";
import StatementTable from "../components/StatementTable";
import FinancialChart from "../components/FinancialChart";
import ExecutiveAnalysis from "../components/ExecutiveAnalysis";
import ValuationGrid from "../components/ValuationGrid";
import SourceLedger from "../components/SourceLedger";
import EvidenceDrawer from "../components/EvidenceDrawer";
import AskFinoraDrawer from "../components/AskFinoraDrawer";

import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import { getResearchResult } from "../lib/api";
import { getToken, removeToken } from "../lib/auth";

// Types matching the backend dashboard payload
interface DashboardData {
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
  kpis: Array<{
    id: string;
    label: string;
    value: string;
    change?: { value: string; direction: string };
    spark?: number[];
    verification?: Record<string, unknown>;
  }>;
  income_statement: { columns: string[]; rows: Array<{ label: string; values: string[]; strong?: boolean }> };
  balance_sheet: { columns: string[]; rows: Array<{ label: string; values: string[]; strong?: boolean }> };
  cash_flow: { columns: string[]; rows: Array<{ label: string; values: string[]; strong?: boolean }> };
  growth: { columns: string[]; rows: Array<{ label: string; values: string[]; strong?: boolean }> };
  profitability: Array<{ metric: string; value: string; note: string }>;
  liquidity: Array<{ metric: string; value: string; note: string }>;
  leverage: Array<{ metric: string; value: string; note: string }>;
  efficiency: Array<{ metric: string; value: string; note: string }>;
  capital_allocation: Array<{ metric: string; value: string; note: string }>;
  dupont?: { roe: string; net_margin: string; asset_turnover: string; equity_multiplier: string; calculation: string; methodology: string } | null;
  charts: {
    revenue: Array<{ label: string; value: number }>;
    operating_income: Array<{ label: string; value: number }>;
    net_income: Array<{ label: string; value: number }>;
    free_cash_flow: Array<{ label: string; value: number }>;
  };
  sources: Array<{
    id: string;
    name: string;
    meta: string;
    pages: string;
    status: string;
    url: string;
    trust_tier: number;
    period: string;
  }>;
  management_commentary: Array<Record<string, unknown>>;
  data_quality: {
    primary_source: string;
    metrics_calculated: number;
    cross_verified: number;
    mismatches: number;
    sources_count: number;
  };
  executive_summary?: {
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
  valuation: {
    market_data: {
      price: number | null;
      price_date: string;
      previous_close: number | null;
      percent_change: number | null;
      exchange: string;
      currency: string;
      source: string;
      is_historical: boolean;
      alignment_status: string;
      target_date: string;
    };
    metrics: Array<{
      metric_id: string;
      name: string;
      display_value: string;
      value: number | null;
      status: string;
      applicability: string;
      formula: string;
      inputs: string[];
      calculation: string;
      market_data_date: string;
      price_type: string;
      reason: string;
    }>;
    period_alignment: Record<string, unknown>;
    is_financial_institution: boolean;
    is_historical: boolean;
  };
}



export default function DashboardPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const sessionId = params.get("session_id");
  const ticker = (params.get("ticker") || "").toUpperCase();
  const initialTab = (params.get("tab") as DashboardTab) || "OVERVIEW";
  const [tab, setTab] = useState<DashboardTab>(initialTab);
  const [evidenceMetric, setEvidenceMetric] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch real data from backend
  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchData() {
      const token = getToken();
      if (!token) {
        navigate("/auth", { state: { from: `/dashboard?session_id=${sessionId}` } });
        return;
      }

      try {
        const result = await getResearchResult(sessionId!, token);
        if (!cancelled) {
          setData(result as unknown as DashboardData);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : "Failed to load research data";
          if (msg.includes("401") || msg.includes("Invalid") || msg.includes("expired")) {
            removeToken();
            navigate("/auth", { state: { from: `/dashboard?session_id=${sessionId}` } });
          } else {
            setError(msg);
            setLoading(false);
          }
        }
      }
    }

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  function selectTicker(t: string) {
    setParams({ ticker: t });
  }

  const tabContent = useMemo(() => {
    if (!data) return null;

    switch (tab) {
      case "OVERVIEW":
        return (
          <div className="space-y-14">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {data.kpis.map((kpi) => (
                <KPICard
                  key={kpi.id}
                  label={kpi.label}
                  value={kpi.value}
                  delta={kpi.change?.value}
                  deltaTone={kpi.change?.direction === "up" ? "pos" : kpi.change?.direction === "down" ? "neg" : "neutral"}
                  highlighted={kpi.id === "fcf"}
                  onInspect={() => setEvidenceMetric(kpi.label)}
                />
              ))}
            </div>

            <FinancialChart data={data.charts.revenue.map((d) => ({ year: d.label, revenue: d.value, netIncome: data.charts.net_income.find((n) => n.label === d.label)?.value || 0 }))} />

            {data.executive_summary && (
              <ExecutiveAnalysis
                analysis={{
                  paragraphs: [data.executive_summary.executive_overview],
                  highlights: data.executive_summary.highlights.map((h) => h.title),
                  watch: data.executive_summary.watch_items.map((w) => ({
                    tag: (w.tag as "WATCH" | "STRENGTH" | "RISK") || "WATCH",
                    text: w.text,
                  })),
                  the_read: (data.executive_summary as Record<string, unknown>).the_read as string || undefined,
                  annotations: (data.executive_summary as Record<string, unknown>).annotations as Array<{tag: string; text: string}> || undefined,
                }}
                onAskFollowUp={() => setEvidenceMetric("ask_finora")}
              />
            )}
          </div>
        );
      case "INCOME STATEMENT":
        return (
          <StatementTable
            title="Income Statement"
            unitLabel="USD, except per-share"
            years={data.periods}
            rows={data.income_statement.rows.map((r) => ({
              label: r.label,
              values: r.values.map((v) => {
                const num = parseFloat(v.replace(/[$,BMT%—]/g, ""));
                return isNaN(num) ? null : num;
              }),
              isTotal: r.strong,
            }))}
            onInspect={setEvidenceMetric}
          />
        );
      case "BALANCE SHEET":
        return (
          <StatementTable
            title="Balance Sheet"
            unitLabel="USD"
            years={data.periods}
            rows={data.balance_sheet.rows.map((r) => ({
              label: r.label,
              values: r.values.map((v) => {
                const num = parseFloat(v.replace(/[$,BMT%—]/g, ""));
                return isNaN(num) ? null : num;
              }),
              isTotal: r.strong,
            }))}
            onInspect={setEvidenceMetric}
          />
        );
      case "CASH FLOW":
        return (
          <StatementTable
            title="Cash Flow Statement"
            unitLabel="USD"
            years={data.periods}
            rows={data.cash_flow.rows.map((r) => ({
              label: r.label,
              values: r.values.map((v) => {
                const num = parseFloat(v.replace(/[$,BMT%—]/g, ""));
                return isNaN(num) ? null : num;
              }),
              isTotal: r.strong,
            }))}
            onInspect={setEvidenceMetric}
          />
        );
      case "GROWTH":
        return (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {data.growth.rows.map((g) => (
              <div key={g.label} className="border border-ink/20 bg-paper p-5">
                <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{g.label}</span>
                <div className="mt-2 font-mono text-2xl font-bold tabular">
                  {g.values[g.values.length - 1] || "—"}
                </div>
              </div>
            ))}
          </div>
        );
      case "PROFITABILITY":
        return (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {data.profitability.map((p) => (
              <div key={p.metric} className="border border-ink/20 bg-paper p-5">
                <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{p.metric}</span>
                <div className="mt-2 font-mono text-2xl font-bold text-ink tabular">{p.value}</div>
              </div>
            ))}
          </div>
        );
      case "VALUATION":
        return <ValuationGrid valuation={{
          price: `$${data.valuation.market_data.price?.toFixed(2) || "—"}`,
          marketCap: "—",
          enterpriseValue: "—",
          multiples: data.valuation.metrics.map((m) => ({
            label: m.name,
            value: m.display_value,
            unavailable: m.status === "unavailable",
            note: m.reason,
          })),
        }} />;
      case "SOURCES":
        return <SourceLedger sources={data.sources.map((s) => ({
          id: s.id,
          name: s.name,
          trust: s.trust_tier === 1 ? "PRIMARY" : s.trust_tier === 2 ? "OFFICIAL" : "CORROBORATING",
          period: s.period,
          usedFor: s.meta,
          status: s.status.toUpperCase() as "VERIFIED" | "CROSS-VERIFIED",
        }))} />;
      default:
        return null;
    }
  }, [tab, data]);

  // Loading state
  if (loading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-3xl items-center justify-center px-4">
        <div className="text-center">
          <Loader2 size={32} className="mx-auto animate-spin text-ink-3" />
          <p className="mt-4 font-mono text-sm text-ink-3">Loading research data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <EditorialHeading size="md">
          <HighlightText>Something went wrong.</HighlightText>
        </EditorialHeading>
        <p className="mt-4 text-sm text-ink-2">{error}</p>
        <button
          onClick={() => navigate("/research")}
          className="mt-6 border-2 border-ink bg-paper px-6 py-3 font-mono text-xs font-bold tracking-wider uppercase transition-colors hover:bg-ink hover:text-paper"
        >
          Start New Research
        </button>
      </div>
    );
  }

  // No session — direct to research
  if (!sessionId || !data) {
    return (
      <div className="mx-auto max-w-[1440px] px-4 py-10 sm:px-6 lg:px-10">
        <div className="border-2 border-ink/20 bg-paper p-8 text-center">
          <p className="text-ink-2">Run a research analysis to see the full dashboard.</p>
          <button
            onClick={() => navigate("/research")}
            className="mt-4 border-2 border-ink bg-paper px-6 py-3 font-mono text-xs font-bold tracking-wider uppercase transition-colors hover:bg-ink hover:text-paper"
          >
            Start Research
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1440px] px-4 py-10 sm:px-6 lg:px-10">
      <CompanyHeader company={{
        ticker: data.company.ticker,
        name: data.company.name,
        exchange: data.company.exchange,
        sector: data.company.period,
        fiscalYear: data.company.period,
        price: data.valuation.market_data.price || 0,
        priceChange: data.valuation.market_data.percent_change || 0,
      }} />

      <div className="my-8">
        <ResearchQualityBar quality={{
          sourceType: data.data_quality.primary_source,
          metrics: data.data_quality.metrics_calculated,
          sources: data.data_quality.sources_count,
          crossVerified: data.data_quality.cross_verified,
          mismatches: data.data_quality.mismatches,
        }} />
      </div>

      <DashboardTabs active={tab} onChange={setTab} />

      <div className="pt-10 pb-24">{tabContent}</div>

      <EvidenceDrawer metric={evidenceMetric} data={data} onClose={() => setEvidenceMetric(null)} />
      <AskFinoraDrawer sessionId={sessionId} />
    </div>
  );
}
