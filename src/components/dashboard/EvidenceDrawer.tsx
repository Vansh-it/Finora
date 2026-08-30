import { X, ExternalLink } from 'lucide-react';
import type { KpiData } from '../../lib/dashboardAdapter';

const BEGINNER_EXPLANATIONS: Record<string, string> = {
  revenue: 'The total amount of money a company earns from selling its products or services before any expenses are deducted.',
  'net-income': 'The bottom line — profit after all expenses, interest, and taxes are paid.',
  'op-income': 'Profit from core business operations before interest and taxes.',
  eps: 'Earnings per share — the portion of profit allocated to each outstanding share of stock.',
  fcf: 'Cash generated from operations minus capital expenditures — money available for dividends, buybacks, or reinvestment.',
  'gross-margin': 'Gross profit as a percentage of revenue — measures production efficiency.',
};

export default function EvidenceDrawer({ kpi, onClose }: { kpi: KpiData | null; onClose: () => void }) {
  if (!kpi) return null;

  const label = kpi.label || 'Metric';
  const value = kpi.value || '—';
  const ver = kpi.verification;
  const beginner = BEGINNER_EXPLANATIONS[kpi.id] || 'This metric measures a specific aspect of the company\'s financial performance.';

  return (
    <div className="fixed inset-0 z-[60] flex justify-end">
      <button aria-label="Close evidence drawer" className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l-2 border-ink bg-paper p-6 shadow-2xl sm:p-8">
        {/* Header */}
        <div className="flex items-start justify-between">
          <p className="font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Evidence Panel</p>
          <button onClick={onClose} aria-label="Close" className="text-ink-2 hover:text-ink">
            <X size={20} />
          </button>
        </div>

        <h2 className="mt-4 font-serif text-3xl font-semibold text-ink">{label}</h2>
        <div className="mt-2 font-mono text-3xl font-bold text-ink tabular-nums">{value}</div>

        {/* Formula & Calculation */}
        {ver && (
          <div className="mt-8 border-t border-ink/15 pt-6">
            <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">How Finora Calculated This</p>
            {ver.formula && <p className="mt-3 font-mono text-sm text-ink-2">{ver.formula}</p>}

            {ver.values && ver.values.length > 0 && (
              <div className="relative mt-5 border border-ink/25 bg-paper-2/50 p-5">
                {ver.values.map((v, i) => (
                  <div key={i}>
                    <div className="flex items-center justify-between font-mono text-sm">
                      <span className="text-ink-2">{v.label}</span>
                      <span className="font-bold text-ink">{v.value}</span>
                    </div>
                    {i < ver.values.length - 1 && <div className="my-2 h-px bg-ink/30" />}
                  </div>
                ))}
                <div className="mt-4 flex items-center justify-end gap-2 border-t border-dashed border-ink/30 pt-3">
                  <span className="font-mono text-xs text-ink-2">=</span>
                  <span className="mark-highlight font-mono text-lg font-bold">{value}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Source Evidence */}
        <div className="mt-8 border-t border-ink/15 pt-6">
          <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Source Evidence</p>
          <div className="mt-4 flex flex-wrap gap-6">
            {ver?.source && (
              <>
                <div className="font-mono text-[10px] leading-tight tracking-[0.18em] uppercase">
                  <div className="font-semibold text-ink-2">Filing</div>
                  <div className="mt-0.5 text-ink-3">{ver.source.doc || 'SEC 10-K'}</div>
                </div>
                <div className="font-mono text-[10px] leading-tight tracking-[0.18em] uppercase">
                  <div className="font-semibold text-ink-2">Page</div>
                  <div className="mt-0.5 text-ink-3">{ver.source.page || '—'}</div>
                </div>
              </>
            )}
          </div>
          {ver?.verification_status && (
            <div className="mt-3">
              <span className="inline-flex -rotate-2 items-center gap-1 rounded-[2px] border-2 border-annotate-green px-2 py-0.5 font-mono text-[10px] font-bold tracking-[0.15em] uppercase text-annotate-green">
                {ver.verification_status === 'verified' ? 'CROSS-VERIFIED' : 'SEC PRIMARY'}
              </span>
            </div>
          )}
        </div>

        {/* What This Means */}
        <div className="mt-8 border-t border-ink/15 pt-6 pb-4">
          <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">What This Means</p>
          <p className="mt-3 text-sm leading-relaxed text-ink-2">{ver?.explanation || beginner}</p>
        </div>
      </div>
    </div>
  );
}
