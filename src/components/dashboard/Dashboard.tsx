import { useEffect, useState, useCallback } from 'react';
import KpiCard from './KpiCard';
import { LineChart } from './charts';
import DashboardChat from './DashboardChat';
import VerificationModal from './VerificationModal';
import { fetchDashboardData, adaptKpi, adaptChart } from '../../lib/dashboardAdapter';
import type { DashboardData, ExecutiveSummary, KpiData, SourceData } from '../../lib/dashboardAdapter';
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

/* ── Editorial Table ─────────────────────────────────────────────────────── */
function FinTable({ title, unitLabel, columns, rows }: { title: string; unitLabel: string; columns: string[]; rows: { label: string; values: string[]; strong?: boolean }[] }) {
  if (!rows || rows.length === 0) {
    return <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">No data available.</p>;
  }
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
            {rows.map((r) => (
              <tr key={r.label} className={cn('group border-b border-ink/12 hover:bg-paper-2/60', r.strong && 'border-b border-ink/40 font-semibold')}>
                <td className={cn('sticky left-0 bg-paper py-3 pr-4 group-hover:bg-paper-2/60', r.strong ? 'text-ink font-semibold' : 'text-ink-2')}>{r.label}</td>
                {r.values.map((v, i) => (
                  <td key={i} className={cn('py-3 pl-4 text-right font-mono tabular text-ink', r.strong && 'font-bold', v.startsWith('(') && 'text-annotate-red')}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Editorial Card ──────────────────────────────────────────────────────── */
function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="border border-ink/20 bg-paper p-6 sm:p-8">
      <h3 className="font-serif text-2xl font-semibold text-ink">{title}</h3>
      {subtitle && <p className="mt-1 font-mono text-[10px] tracking-widest text-ink-3 uppercase">{subtitle}</p>}
      <div className="mt-5">{children}</div>
    </div>
  );
}

/* ── Metric Grid ─────────────────────────────────────────────────────────── */
function MetricGrid({ items }: { items: { metric: string; value: string; note: string }[] }) {
  if (!items || items.length === 0) return <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">No data available.</p>;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {items.map((p) => (
        <div key={p.metric} className="border border-ink/20 bg-paper p-5">
          <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{p.metric}</span>
          <div className="mt-2 font-mono text-2xl font-bold text-ink tabular">{p.value}</div>
        </div>
      ))}
    </div>
  );
}

/* ── Executive Analysis ──────────────────────────────────────────────────── */
function ExecutiveAnalysisSection({ summary }: { summary: ExecutiveSummary | null }) {
  if (!summary || summary._metadata?.error) {
    return <Card title="Executive Analysis"><p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">AI analysis unavailable.</p></Card>;
  }
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[1fr_320px]">
      <div>
        <p className="mb-2 font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Executive Analysis</p>
        <h3 className="mb-6 font-serif text-3xl font-semibold text-ink">The Read.</h3>
        <div className="max-w-2xl space-y-5 font-serif text-[1.05rem] leading-relaxed text-ink-2">
          {summary.executive_overview && <p>{summary.executive_overview}</p>}
        </div>
      </div>
      <div className="border-t border-ink/15 pt-4 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-8">
        <p className="mb-1 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Annotations</p>
        {summary.highlights?.map((h, i) => (
          <div key={i} className="flex items-start gap-3 border-t border-ink/12 py-3 first:border-t-0">
            <span className={cn('shrink-0 rounded-[2px] border px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-widest uppercase',
              h.importance === 'high' && 'border-annotate-red text-annotate-red',
              h.importance === 'medium' && 'border-annotate-blue text-annotate-blue',
              h.importance === 'low' && 'border-ink/30 text-ink-3'
            )}>{h.importance === 'high' ? 'WATCH' : h.importance === 'medium' ? 'NOTE' : 'INFO'}</span>
            <span className="text-sm text-ink-2">{h.title}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Source Ledger ────────────────────────────────────────────────────────── */
function SourceLedger({ sources }: { sources: any[] }) {
  if (!sources || sources.length === 0) return <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">No sources found.</p>;
  return (
    <div className="divide-y divide-ink/12 border-y border-ink/20">
      {sources.map((s: any, i: number) => (
        <div key={i} className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-4">
            <span className="font-mono text-sm font-bold text-ink-3">{String(i + 1).padStart(2, '0')}</span>
            <div>
              <div className="font-serif text-lg font-semibold text-ink">{s.name}</div>
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
      <div className="mb-6 flex h-16 w-16 items-center justify-center border-2 border-dashed border-ink/30 mx-auto"><span className="font-mono text-2xl text-ink-3">&hellip;</span></div>
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

  const adaptedKpis = data.kpis.map(adaptKpi);
  const chartData = adaptChart(data.charts.revenue);
  const { company, periods } = data;
  const latest = periods[periods.length - 1] || '';

  return (
    <div className="mx-auto max-w-[1440px] px-4 py-10 sm:px-6 lg:px-10">
      {/* Header */}
      <div className="border-b border-ink/15 pb-6">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <p className="font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Public Company</p>
            <h1 className="mt-2 font-serif text-4xl font-semibold tracking-tight text-ink uppercase sm:text-5xl">{company.name}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2">
              <span className="font-mono text-sm font-bold tracking-wider text-ink">{company.ticker} <span className="text-ink-3">&middot; {company.exchange}</span></span>
              <span className="font-mono text-xs font-semibold tracking-widest text-ink-3 uppercase">{latest} Research</span>
              <span className="font-mono text-[10px] leading-tight tracking-[0.18em] uppercase">
                <span className="font-semibold text-annotate-blue">Primary Source</span>
                <span className="mt-0.5 block text-ink-3">SEC XBRL</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quality Bar */}
      <div className="my-8 grid grid-cols-2 divide-x divide-ink/15 border-y border-ink/15 sm:grid-cols-5">
        {[{ label: 'Primary Source', value: data.data_quality.primary_source, isText: true }, { label: 'Metrics', value: String(data.data_quality.metrics_calculated) }, { label: 'Sources', value: String(data.data_quality.sources_count) }, { label: 'Cross-Verified', value: String(data.data_quality.cross_verified) }, { label: 'Mismatches', value: String(data.data_quality.mismatches) }].map((item) => (
          <div key={item.label} className="px-4 py-3 first:pl-0">
            <div className={item.isText ? 'font-mono text-sm font-bold text-ink' : 'font-mono text-xl font-bold text-ink tabular'}>{item.value}</div>
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
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {adaptedKpis.map((kpi: any) => (
                <KpiCard key={kpi.id} label={kpi.label} value={kpi.value} delta={kpi.change?.value} deltaTone={kpi.change?.direction === 'up' ? 'pos' : kpi.change?.direction === 'down' ? 'neg' : 'neutral'} onInspect={() => setVerifyMetric(data.kpis.find((k: KpiData) => k.id === kpi.id) || null)} />
              ))}
            </div>
            {chartData.length > 0 && (
              <div className="border border-ink/20 bg-paper p-5">
                <h3 className="mb-4 font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase">Revenue vs. Net Income ($B)</h3>
                <LineChart data={chartData} />
              </div>
            )}
            <ExecutiveAnalysisSection summary={data.executive_summary} />
          </div>
        )}
        {tab === 'income' && <FinTable title="Income Statement" unitLabel="USD Millions" columns={['Line Item', ...periods]} rows={data.income_statement.rows} />}
        {tab === 'balance' && <FinTable title="Balance Sheet" unitLabel="USD Millions" columns={['Line Item', ...periods]} rows={data.balance_sheet.rows} />}
        {tab === 'cashflow' && <FinTable title="Cash Flow Statement" unitLabel="USD Millions" columns={['Line Item', ...periods]} rows={data.cash_flow.rows} />}
        {tab === 'growth' && <MetricGrid items={data.growth?.rows?.map((r: any) => ({ metric: r.label, value: r.values[0] || '—', note: '' })) || []} />}
        {tab === 'profitability' && <MetricGrid items={[...(data.profitability || []), ...(data.liquidity || []), ...(data.leverage || []), ...(data.efficiency || [])]} />}
        {tab === 'valuation' && data.valuation && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {data.valuation.metrics.filter((m: any) => ['Share Price', 'Market Cap', 'Enterprise Value'].includes(m.label)).map((m: any) => (
                <div key={m.label} className="border border-ink/20 bg-paper p-5">
                  <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{m.label}</span>
                  <div className="mt-2 font-mono text-2xl font-bold text-ink tabular">{m.value}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {data.valuation.metrics.filter((m: any) => !['Share Price', 'Market Cap', 'Enterprise Value'].includes(m.label)).map((m: any) => (
                <div key={m.label} className={cn('border bg-paper p-5', m.unavailable ? 'border-dashed border-ink/30' : 'border-ink/20')}>
                  <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{m.label}</span>
                  <div className={cn('mt-2 font-mono text-xl font-bold tabular', m.unavailable ? 'text-ink-3' : 'text-ink')}>{m.unavailable ? '—' : m.value}</div>
                  {m.unavailable && <div className="mt-1 font-mono text-[10px] tracking-widest text-ink-3 uppercase">Data Unavailable</div>}
                </div>
              ))}
            </div>
          </div>
        )}
        {tab === 'sources' && <SourceLedger sources={data.sources} />}
      </div>

      {verifyMetric && <VerificationModal kpi={verifyMetric} onClose={() => setVerifyMetric(null)} />}
      <DashboardChat sessionId={sessionId || new URLSearchParams(window.location.search).get('session_id') || ''} open={chatOpen} onToggle={toggleChat} />
    </div>
  );
}
