import { useEffect, useState, useCallback } from 'react';
import KpiCard from './KpiCard';
import FinancialChart from './FinancialChart';
import ValuationGrid from './ValuationGrid';
import ExecutiveAnalysis from './ExecutiveAnalysis';
import EvidenceDrawer from './EvidenceDrawer';
import DashboardChat from './DashboardChat';
import { fetchDashboardData, adaptKpi } from '../../lib/dashboardAdapter';
import type { DashboardData, KpiData } from '../../lib/dashboardAdapter';
import { ExternalLink } from 'lucide-react';
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

/* ── Financial Table (ZIP style) ──────────────────────────────────────── */
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

/* ── Metric Grid (ZIP style) ──────────────────────────────────────────── */
function MetricGrid({ items }: { items: { metric: string; value: string; note: string }[] }) {
  const safe = safeArray(items);
  if (!safe.length) return <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">No data available.</p>;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {safe.map((p, i) => (
        <div key={i} className="border border-ink/20 bg-paper p-5">
          <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{p.metric}</span>
          <div className="mt-2 font-mono text-2xl font-bold text-ink tabular-nums">{p.value}</div>
          {p.note && <div className="mt-1 font-mono text-[10px] text-ink-3 uppercase">{p.note}</div>}
        </div>
      ))}
    </div>
  );
}

/* ── Source Ledger (ZIP style) ────────────────────────────────────────── */
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
              {s.meta && <p className="mt-1.5 max-w-md text-sm text-ink-2">{s.meta}</p>}
            </div>
          </div>
          <div className="flex items-center gap-3 pl-9 sm:pl-0">
            <span className="font-mono text-[10px] font-bold tracking-widest text-annotate-green uppercase">{s.status || 'VERIFIED'}</span>
            {s.url && <a href={s.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 border border-ink/40 px-2.5 py-1.5 font-mono text-[10px] font-semibold tracking-widest text-ink uppercase transition-colors hover:border-ink">Open <ExternalLink size={11} /></a>}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Research Quality Bar (ZIP style) ─────────────────────────────────── */
function ResearchQualityBar({ dq, kpiCount, sourceCount }: { dq: any; kpiCount: number; sourceCount: number }) {
  const items = [
    { label: 'Primary Source', value: dq.primary_source || 'SEC XBRL', isText: true },
    { label: 'Metrics', value: String(dq.metrics_calculated ?? kpiCount) },
    { label: 'Sources', value: String(dq.sources_count ?? sourceCount) },
    { label: 'Cross-Verified', value: String(dq.cross_verified ?? 0) },
    { label: 'Mismatches', value: String(dq.mismatches ?? 0) },
  ];
  return (
    <div className="grid grid-cols-2 divide-x divide-ink/15 border-y border-ink/15 sm:grid-cols-5">
      {items.map((item) => (
        <div key={item.label} className="px-4 py-3 first:pl-0">
          <div className={item.isText ? 'font-mono text-sm font-bold text-ink' : 'font-mono text-xl font-bold text-ink tabular-nums'}>{item.value}</div>
          <div className="mt-0.5 font-mono text-[10px] font-semibold tracking-[0.12em] text-ink-3 uppercase">{item.label}</div>
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
  const [evidenceKpi, setEvidenceKpi] = useState<KpiData | null>(null);
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

  // Chart data
  const revenueData = safeArray(safeObj(data.charts).revenue).map((d: any) => ({ label: d.label, value: d.value }));
  const netIncomeData = safeArray(safeObj(data.charts).net_income).map((d: any) => ({ label: d.label, value: d.value }));

  return (
    <div className="mx-auto max-w-[1440px] px-4 py-10 sm:px-6 lg:px-10">
      {/* Company Header (ZIP style) */}
      <div className="border-b border-ink/15 pb-6">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
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
        </div>
      </div>

      {/* Quality Bar */}
      <div className="my-8">
        <ResearchQualityBar dq={dq} kpiCount={kpis.length} sourceCount={sources.length} />
      </div>

      {/* Tabs (ZIP style) */}
      <div className="thin-scroll -mx-4 flex gap-1 overflow-x-auto border-b border-ink/15 px-4 sm:mx-0 sm:px-0">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={cn('relative shrink-0 px-4 py-3 font-mono text-xs font-semibold tracking-[0.1em] whitespace-nowrap text-ink-2 uppercase transition-colors hover:text-ink', tab === t.id && 'text-ink')}>
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
                <KpiCard key={kpi.id || i} label={kpi.label} value={kpi.value} delta={kpi.change?.value} deltaTone={kpi.change?.direction === 'up' ? 'pos' : kpi.change?.direction === 'down' ? 'neg' : 'neutral'} onInspect={() => setEvidenceKpi(kpis.find((k: KpiData) => k.id === kpi.id) || null)} />
              ))}
            </div>

            {/* Revenue vs Net Income Chart (ZIP FinancialChart) */}
            {(revenueData.length > 0 || netIncomeData.length > 0) && (
              <FinancialChart revenue={revenueData} netIncome={netIncomeData} />
            )}

            {/* Executive Analysis (ZIP style) */}
            <ExecutiveAnalysis summary={data.executive_summary || null} />
          </div>
        )}

        {tab === 'income' && <FinTable title="Income Statement" unitLabel="USD (Billions)" columns={['Line Item', ...periods]} rows={safeRows(incStmt)} />}
        {tab === 'balance' && <FinTable title="Balance Sheet" unitLabel="USD (Billions)" columns={['Line Item', ...periods]} rows={safeRows(balSheet)} />}
        {tab === 'cashflow' && <FinTable title="Cash Flow Statement" unitLabel="USD (Billions)" columns={['Line Item', ...periods]} rows={safeRows(cashFlow)} />}
        {tab === 'growth' && <MetricGrid items={safeRows(growth).map((r) => ({ metric: r.label, value: r.values?.[0] || '—', note: '' }))} />}
        {tab === 'profitability' && <MetricGrid items={[...(safeArray(data.profitability)), ...(safeArray(data.liquidity)), ...(safeArray(data.leverage)), ...(safeArray(data.efficiency)), ...(safeArray(data.capital_allocation))]} />}
        {tab === 'valuation' && <ValuationGrid metrics={safeArray(valuation.metrics)} marketData={valuation.market_data} isFinancial={valuation.is_financial_institution} />}
        {tab === 'sources' && <SourceLedger sources={sources} />}
      </div>

      {/* Evidence Drawer (ZIP style, real data) */}
      <EvidenceDrawer kpi={evidenceKpi} onClose={() => setEvidenceKpi(null)} />

      {/* Dashboard Chat (connected to real backend) */}
      <DashboardChat sessionId={sessionId || new URLSearchParams(window.location.search).get('session_id') || ''} open={chatOpen} onToggle={toggleChat} />
    </div>
  );
}
