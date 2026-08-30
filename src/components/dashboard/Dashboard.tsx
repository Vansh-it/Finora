import { useEffect, useState, useCallback } from 'react';
import KpiCard from './KpiCard';
import { BarChart, LineChart } from './charts';
import DashboardChat from './DashboardChat';
import { fetchDashboardData, adaptKpi, adaptChart, adaptSource } from '../../lib/dashboardAdapter';
import type { DashboardData, ExecutiveSummary, KpiData, SeriesPoint, ValuationMetric } from '../../lib/dashboardAdapter';

type TabId = 'overview' | 'income' | 'balance' | 'cashflow' | 'growth' | 'profitability' | 'valuation' | 'sources';

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'income', label: 'Income Statement' },
  { id: 'balance', label: 'Balance Sheet' },
  { id: 'cashflow', label: 'Cash Flow' },
  { id: 'growth', label: 'Growth' },
  { id: 'profitability', label: 'Profitability' },
  { id: 'valuation', label: 'Valuation' },
  { id: 'sources', label: 'Sources' },
];

const fmt = (v: number) => `$${v.toFixed(1)}B`;

interface FinTableProps {
  columns: string[];
  rows: { label: string; values: string[]; strong?: boolean }[];
}

function FinTable({ columns, rows }: FinTableProps) {
  if (!rows || rows.length === 0) {
    return <p className="text-caption text-mute">No data available for this statement.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[480px] border-collapse text-left">
        <thead>
          <tr className="border-b border-hairline">
            <th scope="col" className="py-3 pr-4 font-mono text-caption-mono uppercase tracking-wide text-mute">
              {columns[0]}
            </th>
            {columns.slice(1).map((c) => (
              <th key={c} scope="col" className="px-4 py-3 text-right font-mono text-caption-mono uppercase tracking-wide text-mute tabular-nums">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-hairline">
          {rows.map((r) => (
            <tr key={r.label} className={r.strong ? 'bg-canvas-soft/60' : ''}>
              <th scope="row" className={'py-3 pr-4 text-body-sm ' + (r.strong ? 'text-ink' : 'text-body')}>
                {r.label}
              </th>
              {r.values.map((v, i) => (
                <td
                  key={i}
                  className={
                    'px-4 py-3 text-right font-mono text-body-sm tabular-nums ' +
                    (v.startsWith('(') ? 'text-down' : r.strong ? 'text-ink' : 'text-body')
                  }
                >
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Card({ title, subtitle, meta, children }: { title: string; subtitle?: string; meta?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-canvas p-6 shadow-l2">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-display-sm text-ink">{title}</h3>
          {subtitle && <p className="mt-1 text-caption text-mute">{subtitle}</p>}
        </div>
        {meta && <span className="shrink-0 font-mono text-caption-mono text-mute">{meta}</span>}
      </div>
      <div className="mt-5">{children}</div>
    </div>
  );
}

function MetricGrid({ items }: { items: { metric: string; value: string; note: string }[] }) {
  if (!items || items.length === 0) {
    return <p className="text-caption text-mute">No data available.</p>;
  }
  return (
    <div className="grid content-start gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((p) => (
        <div key={p.metric} className="rounded-lg bg-canvas p-5 shadow-l2">
          <p className="text-caption text-mute">{p.metric}</p>
          <p className="mt-2 text-display-sm text-ink tabular-nums">{p.value}</p>
        </div>
      ))}
    </div>
  );
}

function ExecutiveAnalysis({ summary }: { summary: ExecutiveSummary | null }) {
  if (!summary || summary._metadata?.error) {
    return (
      <Card title="Executive Analysis">
        <p className="text-caption text-mute">AI analysis unavailable for this research session.</p>
      </Card>
    );
  }

  const severityColor: Record<string, string> = {
    high: 'bg-down/10 text-down',
    medium: 'bg-accent-soft text-accent',
    low: 'bg-canvas-soft-2 text-mute',
  };

  return (
    <div className="space-y-6">
      {summary.executive_overview && (
        <Card title="Executive Analysis" subtitle="AI-generated financial research briefing">
          <p className="text-body-sm text-body leading-relaxed">{summary.executive_overview}</p>
        </Card>
      )}

      {summary.highlights && summary.highlights.length > 0 && (
        <Card title="Key Highlights">
          <div className="space-y-3">
            {summary.highlights.map((h, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-caption font-medium ${severityColor[h.importance] || 'bg-canvas-soft-2 text-mute'}`}>
                  {h.importance}
                </span>
                <div>
                  <p className="text-body-sm-strong text-ink">{h.title}</p>
                  <p className="mt-0.5 text-body-sm text-body">{h.text}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {summary.growth_analysis && (
          <Card title="Growth & Operating Performance">
            <p className="text-body-sm text-body leading-relaxed">{summary.growth_analysis}</p>
          </Card>
        )}
        {summary.profitability_analysis && (
          <Card title="Profitability & Returns">
            <p className="text-body-sm text-body leading-relaxed">{summary.profitability_analysis}</p>
          </Card>
        )}
        {summary.cash_flow_analysis && (
          <Card title="Cash Flow & Capital Allocation">
            <p className="text-body-sm text-body leading-relaxed">{summary.cash_flow_analysis}</p>
          </Card>
        )}
        {summary.balance_sheet_analysis && (
          <Card title="Balance Sheet & Financial Risk">
            <p className="text-body-sm text-body leading-relaxed">{summary.balance_sheet_analysis}</p>
          </Card>
        )}
      </div>

      {summary.watch_items && summary.watch_items.length > 0 && (
        <Card title="Key Watch Items" subtitle="Areas for further investigation">
          <div className="space-y-3">
            {summary.watch_items.map((w, i) => (
              <div key={i} className="flex items-start gap-3 rounded-sm border border-hairline bg-canvas-soft p-3">
                <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-caption font-medium ${severityColor[w.severity] || 'bg-canvas-soft-2 text-mute'}`}>
                  {w.severity}
                </span>
                <div>
                  <p className="text-body-sm-strong text-ink">{w.title}</p>
                  <p className="mt-0.5 text-body-sm text-body">{w.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {summary.management_commentary_summary && (
        <Card title="Management Commentary Summary">
          <p className="text-body-sm text-body leading-relaxed">{summary.management_commentary_summary}</p>
        </Card>
      )}

      {summary.data_quality_note && (
        <div className="rounded-lg bg-canvas-soft p-4 text-caption text-mute">
          <span className="font-mono uppercase tracking-wide">Data quality: </span>
          {summary.data_quality_note}
        </div>
      )}
    </div>
  );
}

function DuPontSection({ dupont }: { dupont: DashboardData['dupont'] }) {
  if (!dupont) return null;
  return (
    <Card title="DuPont Analysis" subtitle="ROE decomposition">
      <div className="flex flex-wrap items-center gap-3 text-2xl font-semibold text-ink">
        <span>{dupont.roe}</span>
        <span className="text-mute">=</span>
        <span>{dupont.net_margin}</span>
        <span className="text-mute">&times;</span>
        <span>{dupont.asset_turnover}</span>
        <span className="text-mute">&times;</span>
        <span>{dupont.equity_multiplier}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-caption text-mute">
        <span>Net Margin</span>
        <span>Asset Turnover</span>
        <span>Equity Multiplier</span>
      </div>
      {dupont.methodology && (
        <p className="mt-4 text-caption text-mute">{dupont.methodology}</p>
      )}
    </Card>
  );
}

function ManagementCommentary({ commentary }: { commentary: DashboardData['management_commentary'] }) {
  if (!commentary || commentary.length === 0) return null;

  const topicLabels: Record<string, string> = {
    revenue_drivers: 'Revenue Drivers',
    margin_commentary: 'Margin Commentary',
    segment_performance: 'Segment Performance',
    guidance: 'Guidance',
    outlook: 'Outlook',
    risks: 'Risks',
    strategic_investment: 'Strategic Investments',
    cost_structure: 'Cost Structure',
    market_conditions: 'Market Conditions',
  };

  return (
    <Card title="Management Commentary" subtitle="Sourced from official company materials">
      <div className="space-y-4">
        {commentary.map((c, i) => (
          <div key={i} className="rounded-sm border border-hairline bg-canvas-soft p-4">
            <div className="flex items-center gap-2">
              <span className="font-mono text-caption-mono uppercase tracking-wide text-accent">
                {topicLabels[c.topic] || c.topic}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-caption ${
                c.sentiment === 'positive' ? 'bg-up/10 text-up' :
                c.sentiment === 'negative' ? 'bg-down/10 text-down' :
                'bg-canvas-soft-2 text-mute'
              }`}>
                {c.sentiment}
              </span>
              {c.importance === 'high' && (
                <span className="rounded-full bg-accent-soft px-2 py-0.5 text-caption text-accent">high</span>
              )}
            </div>
            <p className="mt-2 text-body-sm text-body">{c.summary}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function DataQualityBar({ quality }: { quality: DashboardData['data_quality'] }) {
  if (!quality) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 sm:gap-4 rounded-lg bg-canvas p-4 shadow-l1 text-caption text-mute">
      <span className="font-mono text-caption-mono uppercase tracking-wide">Primary: </span>
      <span><strong className="text-body">{quality.primary_source}</strong></span>
      <span>·</span>
      <span><strong className="text-body">{quality.metrics_calculated}</strong> calculated metrics</span>
      {quality.cross_verified > 0 && (
        <><span>·</span><span className="text-up">{quality.cross_verified} cross-verified</span></>
      )}
      {quality.mismatches > 0 && (
        <><span>·</span><span className="text-down">{quality.mismatches} material mismatches</span></>
      )}
      <span>·</span>
      <span>{quality.sources_count} sources</span>
    </div>
  );
}

function ValuationSection({ valuation }: { valuation: DashboardData['valuation'] }) {
  if (!valuation) {
    return (
      <Card title="Valuation" subtitle="Market-based multiples">
        <p className="text-caption text-mute">Market valuation data not available for this research session.</p>
      </Card>
    );
  }

  const { market_data, metrics, period_alignment, is_financial_institution } = valuation;

  // Headline cards: share price, market cap, EV
  const headline = metrics.filter(m =>
    ['share_price', 'market_cap', 'enterprise_value'].includes(m.metric_id)
  );
  const multiples = metrics.filter(m =>
    !['share_price', 'market_cap', 'enterprise_value'].includes(m.metric_id)
  );

  return (
    <div className="space-y-6">
      {/* Market Data Header */}
      {market_data.price && (
        <div className="rounded-lg bg-canvas p-6 shadow-l2">
          <div className="flex flex-wrap items-baseline gap-6">
            <div>
              <p className="text-caption text-mute">
                {valuation.is_historical ? 'Historical Share Price' : 'Share Price'}
              </p>
              <p className="mt-1 text-display-lg text-ink tabular-nums">${market_data.price.toFixed(2)}</p>
            </div>
            {!valuation.is_historical && market_data.percent_change !== null && market_data.percent_change !== undefined && (
              <span className={`rounded-full px-3 py-1 text-body-sm-strong ${
                market_data.percent_change >= 0 ? 'bg-up/10 text-up' : 'bg-down/10 text-down'
              }`}>
                {market_data.percent_change >= 0 ? '+' : ''}{market_data.percent_change.toFixed(2)}%
              </span>
            )}
            {valuation.is_historical && (
              <span className="rounded-full bg-accent-soft px-3 py-1 text-body-sm-strong text-accent">
                Historical
              </span>
            )}
            {!valuation.is_historical && market_data.previous_close && (
              <span className="text-caption text-mute">
                Prev close: ${market_data.previous_close.toFixed(2)}
              </span>
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-caption text-mute">
            <span>Source: <strong className="text-body">{market_data.source || 'Twelve Data'}</strong></span>
            {market_data.price_date && <span>
              {valuation.is_historical ? `Price date: ${market_data.price_date}` : `Date: ${market_data.price_date}`}
            </span>}
            {valuation.is_historical && market_data.target_date && market_data.price_date !== market_data.target_date && (
              <span className="text-accent">Nearest trading day to {market_data.target_date}</span>
            )}
            {market_data.exchange && <span>{market_data.exchange}</span>}
            {period_alignment.note && <span>{period_alignment.note}</span>}
          </div>
        </div>
      )}

      {/* Financial institution note */}
      {is_financial_institution && (
        <div className="rounded-lg bg-accent-soft p-4 text-caption text-accent">
          Financial institution detected — enterprise-value metrics may be suppressed.
        </div>
      )}

      {/* Headline Cards */}
      {headline.length > 0 && (
        <Card title="Valuation Overview" subtitle={period_alignment.note || ''}>
          <div className="grid gap-4 sm:grid-cols-3">
            {headline.map((m) => (
              <ValuationCard key={m.metric_id} metric={m} />
            ))}
          </div>
        </Card>
      )}

      {/* Multiples Grid */}
      {multiples.length > 0 && (
        <Card title="Valuation Multiples" subtitle="Based on SEC financials and market data">
          <div className="grid content-start gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {multiples.map((m) => (
              <ValuationCard key={m.metric_id} metric={m} />
            ))}
          </div>
        </Card>
      )}

      {metrics.length === 0 && (
        <Card title="Valuation" subtitle="Market-based multiples">
          <p className="text-caption text-mute">Valuation metrics could not be calculated. Market data may be unavailable.</p>
        </Card>
      )}
    </div>
  );
}

function ValuationCard({ metric }: { metric: ValuationMetric }) {
  const isNM = metric.display_value === 'NM';
  const isNA = metric.status === 'unavailable' || metric.display_value === 'N/A';
  const isSuppressed = metric.applicability === 'suppressed_for_financial';

  return (
    <div className={`rounded-lg p-5 shadow-l2 ${isNA ? 'bg-canvas-soft' : 'bg-canvas'}`}>
      <p className="text-caption text-mute">{metric.name}</p>
      <p className={`mt-2 text-display-sm tabular-nums ${
        isNM ? 'text-down' : isNA ? 'text-mute' : 'text-ink'
      }`}>
        {metric.display_value}
      </p>
      {metric.formula && !isNA && (
        <p className="mt-2 text-caption-mono text-mute truncate" title={metric.formula}>
          {metric.formula}
        </p>
      )}
      {isNM && metric.reason && (
        <p className="mt-1 text-caption text-down">{metric.reason}</p>
      )}
      {isSuppressed && (
        <p className="mt-1 text-caption text-mute">Suppressed for financial institutions</p>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-canvas-soft-2 text-mute">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 17H7A5 5 0 0 1 7 7h2" />
          <path d="M15 7h2a5 5 0 1 1 0 10h-2" />
          <line x1="8" y1="12" x2="16" y2="12" />
        </svg>
      </div>
      <h2 className="mt-4 text-display-sm text-ink">No research result available</h2>
      <p className="mt-2 max-w-sm text-body-sm text-mute">
        Start a company research session to see real financial data, verified metrics, and source documents.
      </p>
      <a
        href="/"
        className="btn-press mt-6 inline-flex h-11 items-center rounded-pill bg-ink px-6 text-button-md text-canvas hover:opacity-90"
      >
        Start Research
      </a>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-down/10 text-down">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      </div>
      <h2 className="mt-4 text-display-sm text-ink">Research session unavailable</h2>
      <p className="mt-2 max-w-sm text-body-sm text-mute">{message}</p>
      <a
        href="/"
        className="btn-press mt-6 inline-flex h-11 items-center rounded-pill bg-ink px-6 text-button-md text-canvas hover:opacity-90"
      >
        Start New Research
      </a>
    </div>
  );
}

function Skeleton() {
  return (
    <div aria-hidden="true">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-lg bg-canvas p-5 shadow-l2">
            <div className="flex items-center justify-between">
              <div className="h-3 w-24 animate-pulse rounded-full bg-canvas-soft-2" />
              <div className="h-5 w-5 animate-pulse rounded-sm bg-canvas-soft-2" />
            </div>
            <div className="mt-4 flex items-end justify-between">
              <div>
                <div className="h-7 w-28 animate-pulse rounded-md bg-canvas-soft-2" />
                <div className="mt-2 h-3 w-16 animate-pulse rounded-full bg-canvas-soft-2" />
              </div>
              <div className="h-8 w-24 animate-pulse rounded-md bg-canvas-soft-2" />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-8 flex gap-2">
        {TABS.map((t) => (
          <div key={t.id} className="h-9 w-28 animate-pulse rounded-full bg-canvas-soft-2" />
        ))}
      </div>
      <div className="mt-6 h-80 animate-pulse rounded-lg bg-canvas shadow-l2" />
    </div>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState<TabId>('overview');
  const [ready, setReady] = useState(false);
  const [realData, setRealData] = useState<DashboardData | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);

  const toggleChat = useCallback(() => {
    setChatOpen((prev) => !prev);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');

    if (!sessionId) {
      setLoading(false);
      setReady(true);
      return;
    }

    fetchDashboardData(sessionId)
      .then((data) => {
        setRealData(data);
        setLoading(false);
        setReady(true);
      })
      .catch((err) => {
        setError(err.message || 'This research session could not be loaded.');
        setLoading(false);
        setReady(true);
      });
  }, []);

  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get('tab');
    if (initial && TABS.some((t) => t.id === initial)) setTab(initial as TabId);
  }, []);

  const selectTab = (id: TabId) => {
    setTab(id);
    const url = new URL(window.location.href);
    url.searchParams.set('tab', id);
    history.replaceState(null, '', url.pathname + url.search + url.hash);
  };

  useEffect(() => {
    const goto = (e: Event) => {
      const id = (e as CustomEvent<string>).detail;
      if (id && TABS.some((t) => t.id === id)) selectTab(id as TabId);
    };
    window.addEventListener('finora:goto-tab', goto);
    return () => window.removeEventListener('finora:goto-tab', goto);
  }, []);

  if (!ready) return <Skeleton />;
  if (loading) return <Skeleton />;

  const params = new URLSearchParams(window.location.search);
  const hasSession = !!params.get('session_id');

  if (!hasSession) {
    return (
      <div>
        <EmptyState />
      </div>
    );
  }

  if (error || !realData) {
    return (
      <div>
        <ErrorState message={error || 'This research session could not be loaded.'} />
      </div>
    );
  }

  const d = realData;
  const company = d.company;
  const kpis = d.kpis.map(adaptKpi);
  const periods = d.periods;
  const incomeStatement = d.income_statement;
  const balanceSheet = d.balance_sheet;
  const cashFlow = d.cash_flow;
  const growthRows = d.growth;
  const profitability = d.profitability;
  const liquidity = d.liquidity;
  const leverage = d.leverage;
  const efficiency = d.efficiency;
  const capitalAlloc = d.capital_allocation;
  const dupont = d.dupont;
  const commentary = d.management_commentary;
  const execSummary = d.executive_summary;
  const valuation = d.valuation;
  const sources = d.sources.map(adaptSource);
  const revChart: SeriesPoint[] = adaptChart(d.charts.revenue);
  const oiChart: SeriesPoint[] = adaptChart(d.charts.operating_income);

  return (
    <div className="animate-fade-up">
      {d.data_quality && <DataQualityBar quality={d.data_quality} />}

      {/* KPI row */}
      <div className="mt-6 grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3">
        {kpis.map((k: KpiData) => (
          <KpiCard key={k.id} kpi={k} />
        ))}
      </div>

      {/* Tabs */}
      <div className="mt-8 flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Dashboard sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            id={`dash-tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`dash-panel-${t.id}`}
            onClick={() => selectTab(t.id)}
            className={
              'shrink-0 rounded-full border px-4 py-2 text-button-md transition-colors ' +
              (tab === t.id
                ? 'border-ink bg-ink text-canvas'
                : 'border-hairline bg-canvas text-body hover:border-hairline-strong hover:text-ink')
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {/* Overview */}
        {tab === 'overview' && (
          <div className="space-y-6" id="dash-panel-overview" role="tabpanel" aria-labelledby="dash-tab-overview">
            <ExecutiveAnalysis summary={execSummary} />
            <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
              <Card title="Revenue trend" subtitle={`${periods.join(', ')}, $ billions`}>
                <LineChart data={revChart} formatValue={fmt} />
              </Card>
              <Card title="Operating income trend" subtitle={`${periods.join(', ')}, $ billions`}>
                <BarChart data={oiChart} formatValue={fmt} />
              </Card>
            </div>
            <DuPontSection dupont={dupont} />
            {commentary.length > 0 && <ManagementCommentary commentary={commentary} />}
          </div>
        )}

        {/* Income statement */}
        {tab === 'income' && (
          <div className="space-y-6" id="dash-panel-income" role="tabpanel" aria-labelledby="dash-tab-income">
            <Card title="Income statement" subtitle="Annual, $ billions" meta={company.period}>
              <FinTable columns={incomeStatement.columns} rows={incomeStatement.rows} />
            </Card>
          </div>
        )}

        {/* Balance sheet */}
        {tab === 'balance' && (
          <div className="space-y-6" id="dash-panel-balance" role="tabpanel" aria-labelledby="dash-tab-balance">
            <Card title="Balance sheet" subtitle="As of period end, $ billions">
              <FinTable columns={balanceSheet.columns} rows={balanceSheet.rows} />
            </Card>
          </div>
        )}

        {/* Cash flow */}
        {tab === 'cashflow' && (
          <div className="space-y-6" id="dash-panel-cashflow" role="tabpanel" aria-labelledby="dash-tab-cashflow">
            <Card title="Cash flow statement" subtitle="Annual, $ billions">
              <FinTable columns={cashFlow.columns} rows={cashFlow.rows} />
            </Card>
          </div>
        )}

        {/* Growth */}
        {tab === 'growth' && (
          <div className="space-y-6" id="dash-panel-growth" role="tabpanel" aria-labelledby="dash-tab-growth">
            <Card title="Year-over-year growth" subtitle="Annual % change">
              <FinTable columns={growthRows.columns} rows={growthRows.rows} />
            </Card>
          </div>
        )}

        {/* Profitability */}
        {tab === 'profitability' && (
          <div className="space-y-6" id="dash-panel-profitability" role="tabpanel" aria-labelledby="dash-tab-profitability">
            <Card title="Profitability & Returns">
              <MetricGrid items={profitability} />
            </Card>
            {liquidity.length > 0 && (
              <Card title="Liquidity">
                <MetricGrid items={liquidity} />
              </Card>
            )}
            {leverage.length > 0 && (
              <Card title="Leverage & Credit">
                <MetricGrid items={leverage} />
              </Card>
            )}
            {efficiency.length > 0 && (
              <Card title="Operating Efficiency">
                <MetricGrid items={efficiency} />
              </Card>
            )}
            {capitalAlloc.length > 0 && (
              <Card title="Capital Allocation">
                <MetricGrid items={capitalAlloc} />
              </Card>
            )}
          </div>
        )}

        {/* Valuation */}
        {tab === 'valuation' && (
          <div className="space-y-6" id="dash-panel-valuation" role="tabpanel" aria-labelledby="dash-tab-valuation">
            <ValuationSection valuation={valuation} />
          </div>
        )}

        {/* Sources */}
        {tab === 'sources' && (
          <div className="space-y-6" id="dash-panel-sources" role="tabpanel" aria-labelledby="dash-tab-sources">
            <Card title="Source documents" subtitle="Every figure traces to these authoritative sources">
              {sources.length === 0 ? (
                <p className="text-caption text-mute">No external sources discovered for this research.</p>
              ) : (
                <ul className="divide-y divide-hairline">
                  {sources.map((s) => (
                    <li key={s.id} className="flex items-start justify-between gap-4 py-4">
                      <div className="min-w-0">
                        <p className="text-body-sm-strong text-ink">{s.name}</p>
                        <p className="mt-1 font-mono text-caption-mono text-mute">{s.meta}</p>
                        <p className="mt-1 text-caption text-body truncate">{s.pages}</p>
                      </div>
                      <span className="shrink-0 rounded-full bg-up/10 px-3 py-1 text-caption font-medium text-up">
                        {s.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        )}
      </div>

      {/* Ask Finora button — fixed bottom-right */}
      <button
        type="button"
        onClick={toggleChat}
        className="btn-press fixed bottom-6 right-6 z-[60] flex h-12 items-center gap-2 rounded-full bg-ink px-5 text-button-md text-canvas shadow-l4 hover:opacity-90 md:bottom-8 md:right-8"
        aria-label="Ask Finora about this company"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        Ask Finora
      </button>

      {/* Dashboard Chat panel */}
      <DashboardChat
        sessionId={new URLSearchParams(window.location.search).get('session_id') || ''}
        companyName={company.name}
        ticker={company.ticker}
        isOpen={chatOpen}
        onClose={toggleChat}
      />
    </div>
  );
}
