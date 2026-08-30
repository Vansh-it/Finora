import { useEffect, useState, useCallback } from 'react';
import KpiCard from './KpiCard';
import { MultiSeriesLineChart } from './charts';
import type { SeriesPoint } from './charts';
import DashboardChat from './DashboardChat';
import VerificationModal from './VerificationModal';
import { fetchDashboardData, adaptKpi } from '../../lib/dashboardAdapter';
import type { DashboardData, ExecutiveSummary, KpiData } from '../../lib/dashboardAdapter';
import { cn } from '../../lib/utils';

type TabId = 'overview' | 'income' | 'balance' | 'cashflow' | 'growth' | 'profitability' | 'valuation' | 'sources';

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'OVERVIEW' },
  { id: 'income', label: 'INCOME STATEMENT' },
  { id: 'balance', label: 'BALANCE SHEET' },
  { id: 'cashflow', label: 'CASH FLOW' },
  { id: 'growth', label: 'GROWTH' },
  { id: 'profitability', label: 'PROFITABILITY' },
  { id: 'valuation', label: 'VALUATION' },
  { id: 'sources', label: 'SOURCES' },
];

function safeArray<T>(v: T[] | undefined | null): T[] { return Array.isArray(v) ? v : []; }
function safeObj(v: any): Record<string, any> { return (v && typeof v === 'object' && !Array.isArray(v)) ? v : {}; }
function safeRows(table: any): { label: string; values: string[]; strong?: boolean }[] {
  if (!table) return [];
  if (Array.isArray(table.rows)) return table.rows;
  return [];
}

/* ── Formatters ──────────────────────────────────────────────────────────── */
function fmtBillions(v: number): string {
  if (Math.abs(v) >= 1000) return `$${(v / 1000).toFixed(1)}T`;
  if (Math.abs(v) >= 1) return `$${v.toFixed(0)}B`;
  return `$${v.toFixed(1)}B`;
}

/* ── Financial Table ─────────────────────────────────────────────────────── */
function FinTable({ title, unitLabel, columns, rows }: { title: string; unitLabel: string; columns: string[]; rows: { label: string; values: string[]; strong?: boolean }[] }) {
  if (!rows.length) return <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">No data available.</p>;
  return (
    <div>
      <div className="mb-4 flex items-baseline justify-between">
        <h3 className="font-serif text-2xl font-semibold text-ink">{title}</h3>
        <span className="font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">{unitLabel}</span>
      </div>
      <div className="thin-scroll overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-ink">
              <th className="sticky left-0 bg-paper py-2 pr-4 text-left font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">Line Item</th>
              {columns.map((c) => (
                <th key={c} className="py-2 pl-4 text-right font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, ri) => (
              <tr key={ri} className={cn('group border-b border-ink/12 hover:bg-paper-2/60', r.strong && 'border-b border-ink/40 font-semibold')}>
                <td className={cn('sticky left-0 bg-paper py-3 pr-4 group-hover:bg-paper-2/60', r.strong ? 'text-ink font-semibold' : 'text-ink-2')}>{r.label}</td>
                {safeArray(r.values).map((v, i) => (
                  <td key={i} className={cn('py-3 pl-4 text-right font-mono tabular-nums text-ink', r.strong && 'font-bold', String(v).startsWith('(') && 'text-annotate-red')}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Metric Grid ─────────────────────────────────────────────────────────── */
function MetricGrid({ items }: { items: { metric: string; value: string; note: string }[] }) {
  const safe = safeArray(items);
  if (!safe.length) return <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">No data available.</p>;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {safe.map((p, i) => (
        <div key={i} className="border border-ink/20 bg-paper p-4 flex flex-col sm:flex-row items-start justify-between">
          <span className="font-mono text-[9px] font-semibold tracking-[0.1em] text-ink-3 uppercase pr-2">{p.metric}</span>
          <div className="mt-2 sm:mt-0 sm:ml-auto font-mono text-xl font-bold text-ink tabular-nums">{p.value}</div>
          {p.note && <div className="mt-2 sm:mt-0 text-[10px] text-ink-3 uppercase">{p.note}</div>}
        </div>
      ))}
    </div>
  );
}

/* ── Full Executive Analysis ─────────────────────────────────────────────── */
function ExecutiveAnalysisSection({ summary }: { summary: ExecutiveSummary | null }) {
  if (!summary || summary._metadata?.error) {
    return (
      <div className="border border-ink/20 bg-paper p-6 sm:p-8">
        <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Executive Analysis</p>
        <h3 className="mt-2 font-serif text-2xl font-semibold text-ink">The Read.</h3>
        <p className="mt-4 font-mono text-[10px] tracking-widest text-ink-3 uppercase">Executive analysis unavailable for this research session. Core verified financial research remains available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {summary.executive_overview && (
        <div className="border border-ink/20 bg-paper p-6 sm:p-8">
          <p className="mb-2 font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Executive Analysis</p>
          <h3 className="mb-6 font-serif text-3xl font-semibold text-ink">The Read.</h3>
          <div className="max-w-3xl space-y-4 font-serif text-[1.05rem] leading-relaxed text-ink-2">
            {summary.executive_overview.split('\n').filter(Boolean).map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </div>
      )}

      {safeArray(summary.highlights).length > 0 && (
        <div className="border border-ink/20 bg-paper p-6 sm:p-8">
          <p className="mb-4 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Key Highlights</p>
          <div className="space-y-3">
            {safeArray(summary.highlights).map((h: any, i: number) => (
              <div key={i} className="flex items-start gap-3 border-t border-ink/12 pt-3 first:border-t-0 first:pt-0">
                <span className={cn(
                  'shrink-0 rounded-[2px] border px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-widest uppercase',
                  h.importance === 'high' && 'border-annotate-red text-annotate-red',
                  h.importance === 'medium' && 'border-annotate-blue text-annotate-blue',
                  h.importance === 'low' && 'border-ink/30 text-ink-3'
                )}>{h.importance === 'high' ? 'WATCH' : h.importance === 'medium' ? 'NOTE' : 'INFO'}</span>
                <div>
                  <p className="font-mono text-xs font-bold text-ink">{h.title}</p>
                  <p className="mt-1 text-sm text-ink-2">{h.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {summary.growth_analysis && (
          <div className="border border-ink/20 bg-paper p-6">
            <p className="mb-3 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Growth &amp; Operating Performance</p>
            <p className="text-sm leading-relaxed text-ink-2">{summary.growth_analysis}</p>
          </div>
        )}
        {summary.profitability_analysis && (
          <div className="border border-ink/20 bg-paper p-6">
            <p className="mb-3 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Profitability Analysis</p>
            <p className="text-sm leading-relaxed text-ink-2">{summary.profitability_analysis}</p>
          </div>
        )}
        {summary.cash_flow_analysis && (
          <div className="border border-ink/20 bg-paper p-6">
            <p className="mb-3 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Cash Flow Analysis</p>
            <p className="text-sm leading-relaxed text-ink-2">{summary.cash_flow_analysis}</p>
          </div>
        )}
        {summary.balance_sheet_analysis && (
          <div className="border border-ink/20 bg-paper p-6">
            <p className="mb-3 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Balance Sheet Analysis</p>
            <p className="text-sm leading-relaxed text-ink-2">{summary.balance_sheet_analysis}</p>
          </div>
        )}
      </div>

      {safeArray(summary.watch_items).length > 0 && (
        <div className="border border-ink/20 bg-paper p-6">
          <p className="mb-4 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Watch Items</p>
          <div className="space-y-2">
            {safeArray(summary.watch_items).map((w: any, i: number) => (
              <div key={i} className="flex items-start gap-3 border-t border-ink/12 py-2 first:border-t-0">
                <span className={cn(
                  'shrink-0 rounded-[2px] border px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-widest uppercase',
                  w.severity === 'high' && 'border-annotate-red text-annotate-red',
                  w.severity === 'medium' && 'border-annotate-blue text-annotate-blue',
                  w.severity === 'low' && 'border-annotate-green text-annotate-green'
                )}>{w.severity || 'NOTE'}</span>
                <span className="text-sm text-ink-2">{w.item || w.text || ''}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {summary.management_commentary_summary && (
        <div className="border border-ink/20 bg-paper p-6">
          <p className="mb-3 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Management Commentary</p>
          <p className="text-sm leading-relaxed text-ink-2">{summary.management_commentary_summary}</p>
        </div>
      )}

      {summary.data_quality_note && (
        <div className="border border-dashed border-ink/25 bg-paper-2/30 p-4">
          <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">{summary.data_quality_note}</p>
        </div>
      )}
    </div>
  );
}

/* ── Source Ledger ────────────────────────────────────────────────────────── */
function SourceLedger({ sources }: { sources: any[] }) {
  const safe = safeArray(sources);
  if (!safe.length) return <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">No sources found.</p>;
  return (
    <div className="divide-y divide-ink/12 border-y border-ink/20">
      {safe.map((s: any, i: number) => (
        <div key={i} className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-4">
            <span className="font-mono text-sm font-bold text-ink-3">{String(i + 1).padStart(2, '0')}</span>
            <div>
              <div className="font-serif text-lg font-semibold text-ink">{s.name || s.title || 'Source'}</div>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <span className={cn('inline-flex -rotate-2 items-center gap-1 rounded-[2px] border-2 px-2 py-0.5 font-mono text-[10px] font-bold tracking-[0.15em] uppercase',
                  (s.trust_tier ?? 3) <= 1 ? 'border-ink text-ink' : (s.trust_tier ?? 3) <= 2 ? 'border-annotate-blue text-annotate-blue' : 'border-annotate-green text-annotate-green'
                )}>{(s.trust_tier ?? 3) <= 1 ? 'PRIMARY' : (s.trust_tier ?? 3) <= 2 ? 'OFFICIAL' : 'CORROBORATING'}</span>
                {s.period && <span className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">{s.period}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 pl-9 sm:pl-0">
            <span className="font-mono text-[10px] font-bold tracking-widest text-annotate-green uppercase">{s.status || 'VERIFIED'}</span>
            {s.url && <a href={s.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 border border-ink/40 px-2.5 py-1.5 font-mono text-[10px] font-semibold tracking-widest text-ink uppercase transition-colors hover:border-ink">Open &nearr;</a>}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Valuation Section ───────────────────────────────────────────────────── */
function ValuationSection({ valuation }: { valuation: any }) {
  const marketData = safeObj(valuation.market_data);
  const metrics = safeArray(valuation.metrics);
  const isFinancial = valuation.is_financial_institution;

  const headlineMetrics = metrics.filter((m: any) => ['share_price', 'market_cap', 'enterprise_value'].includes(m.metric_id));
  const multipleMetrics = metrics.filter((m: any) => !['share_price', 'market_cap', 'enterprise_value'].includes(m.metric_id));

  return (
    <div className="space-y-8">
      {/* Market data header */}
      {marketData.price && (
        <div className="border border-ink/20 bg-paper p-6">
          <div className="flex items-baseline gap-4">
            <span className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Share Price</span>
            {marketData.percent_change !== null && marketData.percent_change !== undefined && (
              <span className={cn('font-mono text-xs font-semibold', marketData.percent_change >= 0 ? 'text-annotate-green' : 'text-annotate-red')}>
                {marketData.percent_change >= 0 ? '+' : ''}{marketData.percent_change.toFixed(2)}%
              </span>
            )}
          </div>
          <div className="mt-2 font-serif text-5xl font-semibold text-ink tabular-nums">
            ${typeof marketData.price === 'number' ? marketData.price.toFixed(2) : '—'}
          </div>
          {marketData.price_date && (
            <p className="mt-2 font-mono text-[10px] tracking-widest text-ink-3 uppercase">
              As of {marketData.price_date} · {marketData.source || 'Twelve Data'}
            </p>
          )}
        </div>
      )}

      {/* Headline metrics: Market Cap, Enterprise Value */}
      {headlineMetrics.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {headlineMetrics.map((m: any, i: number) => {
            const isNA = m.status === 'unavailable' || m.applicability === 'not_applicable';
            return (
              <div key={i} className={cn('border bg-paper p-5', isNA ? 'border-dashed border-ink/30' : 'border-ink/20')}>
                <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{m.name}</span>
                <div className={cn('mt-2 font-mono text-2xl font-bold tabular-nums', isNA ? 'text-ink-3' : 'text-ink')}>
                  {isNA ? '—' : (m.display_value || '—')}
                </div>
                {isNA && m.reason && (
                  <div className="mt-1 font-mono text-[10px] tracking-widest text-ink-3 uppercase">{m.reason}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Multiples */}
      {multipleMetrics.length > 0 && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {multipleMetrics.map((m: any, i: number) => {
            const isNA = m.status === 'unavailable' || m.applicability === 'not_applicable';
            return (
              <div key={i} className={cn('border bg-paper p-5', isNA ? 'border-dashed border-ink/30' : 'border-ink/20')}>
                <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{m.name}</span>
                <div className={cn('mt-2 font-mono text-xl font-bold tabular-nums', isNA ? 'text-ink-3' : 'text-ink')}>
                  {isNA ? '—' : (m.display_value || '—')}
                </div>
                {isNA && (
                  <div className="mt-1 font-mono text-[10px] tracking-widest text-ink-3 uppercase">
                    {m.applicability === 'not_applicable' ? 'Not Applicable' : 'Data Unavailable'}
                  </div>
                )}
                {!isNA && m.formula && (
                  <div className="mt-2 font-mono text-[9px] text-ink-3 leading-tight">{m.formula}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Financial institution note */}
      {isFinancial && (
        <div className="border border-dashed border-ink/25 bg-paper-2/30 p-4">
          <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">
            Note: Finora applies adjusted methodology for financial institutions. Conventional industrial metrics such as EBITDA and EV/EBITDA may not be shown where economically inappropriate.
          </p>
        </div>
      )}

      {!metrics.length && !marketData.price && (
        <div className="border border-dashed border-ink/25 bg-paper-2/30 p-6 text-center">
          <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">Valuation data unavailable for this research session.</p>
        </div>
      )}
    </div>
  );
}

/* ── Main Dashboard ──────────────────────────────────────────────────────── */
export default function Dashboard({ sessionId }: { sessionId?: string }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<TabId>('overview');
  const [verifyMetric, setVerifyMetric] = useState<KpiData | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const toggleChat = useCallback(() => setChatOpen((o) => !o), []);

  useEffect(() => {
    const sid = sessionId || new URLSearchParams(window.location.search).get('session_id') || '';
    if (!sid) { setLoading(false); setError('No research session found.'); return; }
    fetchDashboardData(sid).then((d) => { setData(d); setLoading(false); }).catch((e: any) => { setError(e.message || 'Failed to load'); setLoading(false); });
  }, [sessionId]);

  if (loading) return (
    <div className="mx-auto max-w-md px-6 py-24 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center border-2 border-dashed border-ink/30 mx-auto animate-pulse"><span className="font-mono text-2xl text-ink-3">&hellip;</span></div>
      <h2 className="font-serif text-3xl font-semibold text-ink">Loading research&hellip;</h2>
    </div>
  );

  if (error || !data) return (
    <div className="mx-auto max-w-md px-6 py-24 text-center">
      <span className="mb-4 inline-block -rotate-2 border-2 border-annotate-red px-2 py-0.5 font-mono text-[10px] font-bold tracking-widest text-annotate-red uppercase">Error</span>
      <h2 className="font-serif text-3xl font-semibold text-ink">{error || 'No data'}</h2>
      <a href="/" className="mt-8 inline-block bg-ink px-6 py-3 font-mono text-xs font-bold tracking-widest text-paper uppercase transition-colors hover:bg-ink-2">Return to Finora</a>
    </div>
  );

  const kpis = safeArray(data.kpis);
  const adaptedKpis = kpis.map(adaptKpi);
  const company = safeObj(data.company);
  const periods = safeArray(data.periods);
  const latest = periods[periods.length - 1] || '';
  const dq = safeObj(data.data_quality);
  const incStmt = safeObj(data.income_statement);
  const balSheet = safeObj(data.balance_sheet);
  const cashFlow = safeObj(data.cash_flow);
  const growth = safeObj(data.growth);
  const valuation = safeObj(data.valuation);
  const sources = safeArray(data.sources);

  // Build chart data for Revenue vs Net Income
  const revenueChart: SeriesPoint[] = safeArray(safeObj(data.charts).revenue).map((d: any) => ({ label: d.label, value: d.value }));
  const netIncomeChart: SeriesPoint[] = safeArray(safeObj(data.charts).net_income).map((d: any) => ({ label: d.label, value: d.value }));

  const chartSeries = [
    { name: 'Revenue', data: revenueChart, color: '#111111' },
    { name: 'Net Income', data: netIncomeChart, color: '#3978ff' },
  ].filter((s) => s.data.length > 0);

  return (
    <div className="mx-auto max-w-[1440px] px-4 py-10 sm:px-6 lg:px-10">
      {/* Header */}
      <div className="border-b border-ink/15 pb-6">
        <p className="font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Public Company</p>
        <h1 className="mt-2 font-serif text-4xl font-semibold tracking-tight text-ink uppercase sm:text-5xl">{company.name || 'Company'}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2">
          <span className="font-mono text-sm font-bold tracking-wider text-ink">{company.ticker || ''} <span className="text-ink-3">&middot; {company.exchange || ''}</span></span>
          {latest && <span className="font-mono text-xs font-semibold tracking-widest text-ink-3 uppercase">{latest} Research</span>}
          <span className="font-mono text-[10px] leading-tight tracking-[0.18em] uppercase">
            <span className="font-semibold text-annotate-blue">Primary Source</span>
            <span className="mt-0.5 block text-ink-3">SEC XBRL</span>
          </span>
        </div>
      </div>

      {/* Quality Bar */}
      <div className="my-8 grid grid-cols-2 divide-x divide-ink/15 border-y border-ink/15 sm:grid-cols-5">
        {[
          { label: 'Primary Source', value: dq.primary_source || 'SEC XBRL', isText: true },
          { label: 'Metrics', value: String(dq.metrics_calculated ?? kpis.length) },
          { label: 'Sources', value: String(dq.sources_count ?? sources.length) },
          { label: 'Cross-Verified', value: String(dq.cross_verified ?? 0) },
          { label: 'Mismatches', value: String(dq.mismatches ?? 0) },
        ].map((item) => (
          <div key={item.label} className="px-4 py-3 first:pl-0">
            <div className={cn('font-mono font-bold', item.isText ? 'text-sm' : 'text-xl')}>{item.value}</div>
            <div className="mt-0.5 font-mono text-[10px] font-semibold tracking-[0.12em] text-ink-3 uppercase">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="thin-scroll -mx-4 flex gap-1 overflow-x-auto border-b border-ink/15 px-4 sm:mx-0 sm:px-0">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={cn('relative shrink-0 px-4 py-3 font-mono text-xs font-semibold tracking-[0.1em] whitespace-nowrap uppercase transition-colors hover:text-ink', tab === t.id ? 'text-ink' : 'text-ink-2')}>
            {t.label}
            {tab === t.id && <span className="absolute right-2 bottom-0 left-2 h-[3px] bg-highlight" />}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="pt-10 pb-24">
        {tab === 'overview' && (
          <div className="space-y-14">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {adaptedKpis.filter(Boolean).map((kpi: any, i: number) => (
                <KpiCard key={kpi.id || i} label={kpi.label} value={kpi.value} delta={kpi.change?.value} deltaTone={kpi.change?.direction === 'up' ? 'pos' : kpi.change?.direction === 'down' ? 'neg' : 'neutral'} onInspect={() => setVerifyMetric(kpis.find((k: KpiData) => k.id === kpi.id) || null)} />
              ))}
            </div>

            {/* Revenue vs Net Income Chart */}
            {chartSeries.length > 0 && (
              <div className="border border-ink/20 bg-paper p-5">
                <h3 className="mb-4 font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase">Revenue vs. Net Income ($B)</h3>
                <MultiSeriesLineChart series={chartSeries} formatValue={fmtBillions} />
              </div>
            )}

            {/* Executive Analysis */}
            <ExecutiveAnalysisSection summary={data.executive_summary || null} />
          </div>
        )}

        {tab === 'income' && <FinTable title="Income Statement" unitLabel="USD (Billions)" columns={['Line Item', ...periods]} rows={safeRows(incStmt)} />}
        {tab === 'balance' && <FinTable title="Balance Sheet" unitLabel="USD (Billions)" columns={['Line Item', ...periods]} rows={safeRows(balSheet)} />}
        {tab === 'cashflow' && <FinTable title="Cash Flow Statement" unitLabel="USD (Billions)" columns={['Line Item', ...periods]} rows={safeRows(cashFlow)} />}
        {tab === 'growth' && <MetricGrid items={safeRows(growth).map((r) => ({ metric: r.label, value: r.values?.[0] || '—', note: '' }))} />}
        {tab === 'profitability' && <MetricGrid items={[...(safeArray(data.profitability)), ...(safeArray(data.liquidity)), ...(safeArray(data.leverage)), ...(safeArray(data.efficiency)), ...(safeArray(data.capital_allocation))]} />}
        {tab === 'valuation' && <ValuationSection valuation={valuation} />}
        {tab === 'sources' && <SourceLedger sources={sources} />}
      </div>

      {/* Evidence Drawer */}
      {verifyMetric && <VerificationModal kpi={verifyMetric} onClose={() => setVerifyMetric(null)} />}

      {/* Dashboard Chat */}
      <DashboardChat sessionId={sessionId || new URLSearchParams(window.location.search).get('session_id') || ''} open={chatOpen} onToggle={toggleChat} />
    </div>
  );
}
