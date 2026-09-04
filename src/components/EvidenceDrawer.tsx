import { X, ExternalLink } from "lucide-react";
import { getEvidence } from "../data/evidence";
import Annotation from "./Annotation";
import HighlightText from "./HighlightText";

/* Accept optional `data` prop so evidence comes from real dashboard payload */
interface EvidenceDrawerProps {
  metric: string | null;
  data?: unknown | null;
  onClose: () => void;
}

/* ── Type helpers for dashboard data ────────────────────────────────────── */
interface DashboardLike {
  company?: { ticker: string; name: string; period: string };
  forensic_scores?: {
    piotroski?: { score: number; status: string; signals: Array<{ label: string; value: number; max: number }>; interpretation: string } | null;
    altman?: { score: number; status: string; zone: string; applicable: boolean; reason: string; factors: Array<{ name: string; value: number }>; variant: string } | null;
    beneish?: { score: number; status: string; applicable: boolean; reason: string; indices: Array<{ name: string; value: number }> } | null;
  };
  watch_items?: Array<{ id: string; headline: string; reason: string; severity: string; evidence: Record<string, unknown> }>;
  macro_context?: { available: boolean; strip: Array<{ label: string; value: string; series_id?: string; date?: string }>; attribution: string };
  valuation?: { market_data: { source: string; price_date: string }; metrics: Array<{ metric_id: string; name: string; formula: string; inputs: string[]; calculation: string; reason: string; status: string }> };
  sources?: Array<{ id: string; name: string; url: string; trust_tier: number; period: string }>;
}

/* ── Special metric renderers ────────────────────────────────────────────── */

function PiotroskiEvidence({ data }: { data: DashboardLike }) {
  const p = data.forensic_scores?.piotroski;
  if (!p) return <p className="text-sm text-ink-2">Piotroski F-Score data is not available for this company.</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-3xl font-bold tabular">{p.score}/9</span>
        <span className="font-mono text-sm font-bold text-ink-3 uppercase">{p.status}</span>
      </div>

      {p.interpretation && (
        <p className="text-sm leading-relaxed text-ink-2">{p.interpretation}</p>
      )}

      <div className="border-t border-ink/15 pt-4">
        <p className="font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase mb-3">9 Component Signals</p>
        {p.signals && p.signals.map((s, i) => (
          <div key={i} className="flex items-center justify-between py-1.5 font-mono text-sm border-b border-ink/5 last:border-0">
            <span className="text-ink-2 pr-2">{s.label}</span>
            <span className={s.value === 1 ? "text-annotate-green font-bold" : "text-ink-3"}>
              {s.value === 1 ? "✓ +1" : "✕ +0"}
            </span>
          </div>
        ))}
      </div>

      <p className="text-xs text-ink-3 italic">This is a financial health signal, not an investment recommendation.</p>
    </div>
  );
}

function AltmanEvidence({ data }: { data: DashboardLike }) {
  const a = data.forensic_scores?.altman;
  if (!a) return <p className="text-sm text-ink-2">Altman Z-Score data is not available.</p>;

  if (a.applicable === false) {
    return (
      <div className="space-y-3">
        <div className="font-mono text-lg font-bold text-ink-3">NOT APPLICABLE</div>
        <p className="text-sm text-ink-2">{a.reason || "The Altman Z-Score is designed for industrial/manufacturing companies and is not appropriate for financial institutions."}</p>
        <p className="text-xs text-ink-3 italic">Alternative analysis methods are used for financial institutions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-3xl font-bold tabular">{a.score?.toFixed(2)}</span>
        <span className="font-mono text-sm text-ink-3 uppercase">{a.zone}</span>
      </div>

      {a.variant && (
        <p className="font-mono text-xs text-ink-3">Variant: {a.variant}</p>
      )}

      {a.factors && a.factors.length > 0 && (
        <div className="border-t border-ink/15 pt-4">
          <p className="font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase mb-3">Formula Factors</p>
          {a.factors.map((f, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 font-mono text-sm border-b border-ink/5 last:border-0">
              <span className="text-ink-2 pr-2">{f.name}</span>
              <span className="font-bold tabular">{f.value.toFixed(4)}</span>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-ink-3 italic">Z &gt; 2.99 = Safe | 1.81–2.99 = Grey Zone | Z &lt; 1.81 = Distress</p>
    </div>
  );
}

function BeneishEvidence({ data }: { data: DashboardLike }) {
  const b = data.forensic_scores?.beneish;
  if (!b || b.applicable === false) {
    return <p className="text-sm text-ink-2">{b?.reason || "Beneish M-Score requires two comparable periods of data. Insufficient data is available."}</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-3xl font-bold tabular">{b.score?.toFixed(2)}</span>
        <span className="font-mono text-sm text-ink-3 uppercase">{b.status}</span>
      </div>

      {b.indices && b.indices.length > 0 && (
        <div className="border-t border-ink/15 pt-4">
          <p className="font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase mb-3">8 Component Indices</p>
          {b.indices.map((idx, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 font-mono text-sm border-b border-ink/5 last:border-0">
              <span className="text-ink-2 pr-2">{idx.name}</span>
              <span className="font-bold tabular">{idx.value.toFixed(4)}</span>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-ink-3 italic">
        M &gt; -1.78 suggests elevated manipulation-risk screening signal.
        This is a statistical indicator, not proof of accounting misconduct.
      </p>
    </div>
  );
}

function MacroEvidence({ data }: { data: DashboardLike }) {
  const m = data.macro_context;
  if (!m || !m.available || !m.strip?.length) {
    return <p className="text-sm text-ink-2">Macro context is not available. FRED API key may be missing or data could not be retrieved.</p>;
  }

  return (
    <div className="space-y-4">
      {m.strip.map((item) => (
        <div key={item.label} className="border-b border-ink/5 pb-3 last:border-0">
          <p className="font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">{item.label}</p>
          <div className="mt-1 font-mono text-lg font-bold tabular">{item.value}</div>
          <div className="mt-1 flex gap-4 font-mono text-[10px] text-ink-3">
            <span>Provider: FRED</span>
            {item.series_id && <span>Series: {item.series_id}</span>}
            {item.date && <span>Observed: {item.date}</span>}
          </div>
        </div>
      ))}
      {m.attribution && (
        <p className="mt-2 text-[10px] text-ink-3 italic">{m.attribution}</p>
      )}
    </div>
  );
}

function GenericMetricEvidence({ metric, data }: { metric: string; data?: DashboardLike }) {
  // For unknown metrics, use the existing getEvidence function
  const evidence = getEvidence(metric, data as any);

  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Formula</p>
        <p className="mt-2 font-mono text-sm text-ink-2">{evidence.formulaLabel}</p>
      </div>

      <div className="border border-ink/25 bg-paper-2/50 p-5">
        <div className="flex items-center justify-between font-mono text-sm">
          <span className="text-ink-2">{evidence.numerator.label}</span>
          <span className="font-bold text-ink">{evidence.numerator.value}</span>
        </div>
        <div className="my-2 h-px bg-ink" />
        <div className="flex items-center justify-between font-mono text-sm">
          <span className="text-ink-2">{evidence.denominator.label}</span>
          <span className="font-bold text-ink">{evidence.denominator.value}</span>
        </div>
        <div className="mt-4 flex items-center justify-end gap-2 border-t border-dashed border-ink/30 pt-3">
          <span className="font-mono text-xs text-ink-2">=</span>
          <HighlightText className="font-mono text-lg font-bold">{evidence.value}</HighlightText>
        </div>
      </div>

      <div>
        <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Source Evidence</p>
        <div className="mt-3 flex flex-wrap gap-4">
          <Annotation label="Filing" value={evidence.source} />
          <Annotation label="Period" value={evidence.period} />
        </div>
        <div className="mt-3">
          <Annotation label="US-GAAP Concept" value={evidence.concept} tone="blue" />
        </div>
        <div className="mt-3">
          <Annotation label="Accession" value={evidence.accession} />
        </div>
      </div>

      {/* Multi-source cross-check */}
      {data?.valuation?.metrics && (() => {
        const valMetric = data.valuation.metrics.find((m) => m.name === metric);
        if (!valMetric) return null;
        return (
          <div className="border-t border-ink/15 pt-4">
            <p className="font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">Cross-Check</p>
            <div className="mt-2 space-y-2 font-mono text-sm">
              <div className="flex justify-between">
                <span className="text-ink-2">Finora Calculation</span>
                <span className="font-bold">{evidence.value}</span>
              </div>
              {valMetric.calculation && valMetric.calculation !== evidence.value && (
                <div className="flex justify-between">
                  <span className="text-ink-2">External Value</span>
                  <span className="font-bold">{valMetric.calculation}</span>
                </div>
              )}
              {valMetric.reason && (
                <div className="flex justify-between">
                  <span className="text-ink-2">Status</span>
                  <span className="font-bold text-ink-2">{valMetric.reason}</span>
                </div>
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
}

/* ── Main Drawer ──────────────────────────────────────────────────────────── */

export default function EvidenceDrawer({ metric, data, onClose }: EvidenceDrawerProps) {
  if (!metric) return null;

  const dash = data as DashboardLike | undefined;
  const latestPeriod = dash?.company?.period || "";

  // Determine which special renderer to use
  const isPiotroski = metric === "Piotroski F-Score";
  const isAltman = metric === "Altman Z-Score";
  const isBeneish = metric === "Beneish M-Score";
  const isMacro = metric.toLowerCase().includes("macro") || metric.toLowerCase().includes("treasury") || metric.toLowerCase().includes("fed funds") || metric.toLowerCase().includes("cpi");

  let title = metric;
  let value = "";
  let classification = "";
  let content: React.ReactNode;

  if (isPiotroski) {
    const p = dash?.forensic_scores?.piotroski;
    title = "Piotroski F-Score";
    value = p ? `${p.score}/9` : "—";
    classification = "Financial Health Signal";
    content = <PiotroskiEvidence data={dash!} />;
  } else if (isAltman) {
    const a = dash?.forensic_scores?.altman;
    title = "Altman Z-Score";
    value = a ? a.score?.toFixed(2) ?? "—" : "—";
    classification = a?.applicable === false ? "Not Applicable" : "Distress Screening";
    content = <AltmanEvidence data={dash!} />;
  } else if (isBeneish) {
    const b = dash?.forensic_scores?.beneish;
    title = "Beneish M-Score";
    value = b ? b.score?.toFixed(2) ?? "—" : "—";
    classification = "Manipulation Risk Screening";
    content = <BeneishEvidence data={dash!} />;
  } else if (isMacro) {
    title = metric;
    value = dash?.macro_context?.strip?.find(s => s.label.toLowerCase().includes(metric.toLowerCase().split(" ")[0]))?.value || "—";
    classification = "Macro Context (FRED)";
    content = <MacroEvidence data={dash!} />;
  } else {
    // Standard metric evidence
    const evidence = getEvidence(metric, dash as any);
    title = evidence.metric;
    value = evidence.value;
    classification = "SEC XBRL";
    content = <GenericMetricEvidence metric={metric} data={dash} />;
  }

  return (
    <div className="fixed inset-0 z-[60] flex justify-end">
      <button aria-label="Close evidence drawer" className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l-2 border-ink bg-paper p-6 shadow-2xl sm:p-8">
        <div className="flex items-start justify-between">
          <p className="font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Evidence Panel</p>
          <button onClick={onClose} aria-label="Close" className="text-ink-2 hover:text-ink">
            <X size={20} />
          </button>
        </div>

        <h2 className="mt-4 font-serif text-3xl font-semibold text-ink">{title}</h2>
        <div className="mt-2 font-mono text-3xl font-bold text-ink tabular">{value}</div>
        {classification && (
          <div className="mt-1 font-mono text-[10px] font-bold tracking-wider text-ink-3 uppercase">{classification}</div>
        )}

        <div className="mt-8 border-t border-ink/15 pt-6">
          {content}
        </div>

        {latestPeriod && (
          <div className="mt-8 border-t border-ink/15 pt-4 pb-4">
            <p className="font-mono text-[10px] text-ink-3">
              Period: {latestPeriod} · Source: {isMacro ? "FRED" : "SEC XBRL"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
