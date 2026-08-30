import { useEffect, useRef, useState } from 'react';
import type { Kpi } from '../../data/microsoft';

const BEGINNER_EXPLANATIONS: Record<string, string> = {
  'revenue': 'Revenue is the total amount of money a company earns from selling its products or services. It\'s the "top line" — the starting point for measuring business performance.',
  'net-income': 'Net income is the company\'s bottom-line profit — what\'s left after subtracting ALL expenses, taxes, and costs from revenue. This is the money that belongs to shareholders.',
  'op-income': 'Operating income shows how much profit the company makes from its core business operations, before accounting for interest, taxes, and one-time items.',
  'eps': 'Earnings Per Share (EPS) shows how much profit is attributed to each share of stock. It\'s one of the most important metrics investors track.',
  'fcf': 'Free cash flow is the cash the company generates after spending on equipment and buildings. This is real money available for dividends, debt repayment, or growth investments.',
  'gross-margin': 'Gross margin shows what percentage of revenue remains after subtracting the direct cost of making products. A higher margin means more efficient production.',
  'operating-margin': 'Operating margin shows what percentage of revenue remains after paying all operating costs — salaries, rent, marketing, R&D, and other expenses to run the business.',
  'net-margin': 'Net margin (profit margin) shows what percentage of each dollar of revenue becomes actual profit after ALL expenses. This is the bottom line per dollar earned.',
  'roa': 'Return on Assets (ROA) measures how efficiently a company uses its assets to generate profit. Think of it as: for every dollar of assets, how much profit did the company make?',
  'roe': 'Return on Equity (ROE) measures how efficiently a company generates profit from shareholders\' capital. A higher ROE can indicate stronger capital efficiency, but should be interpreted alongside leverage and industry characteristics.',
  'roic': 'Return on Invested Capital (ROIC) measures how well a company uses all its capital — both debt and equity — to generate profits. It\'s considered one of the most important metrics for evaluating a company\'s true economic performance.',
  'current-ratio': 'The current ratio measures whether a company has enough short-term assets to cover its short-term bills. A ratio above 1.0 means it can pay its near-term obligations.',
  'quick-ratio': 'The quick ratio is a stricter version of the current ratio — it excludes inventory, which might be hard to sell quickly. It tests whether a company can pay bills without selling inventory.',
  'debt-to-equity': 'Debt-to-equity shows how much the company relies on borrowed money versus shareholder money. Higher ratios mean more financial leverage and potentially more risk.',
  'ebitda': 'EBITDA is a measure of operating profitability that removes the effects of financing decisions (interest), government take (taxes), and accounting choices (depreciation/amortization).',
};

function getBeginnerExplanation(kpiId: string): string {
  return BEGINNER_EXPLANATIONS[kpiId] || '';
}

export default function VerificationModal() {
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const open = (e: Event) => {
      const detail = (e as CustomEvent).detail as Kpi;
      setKpi(detail);
    };
    window.addEventListener('finora:verify', open);
    return () => window.removeEventListener('finora:verify', open);
  }, []);

  useEffect(() => {
    if (kpi) closeRef.current?.focus();
  }, [kpi]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setKpi(null);
    };
    if (kpi) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [kpi]);

  useEffect(() => {
    if (!kpi) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [kpi]);

  if (!kpi) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-end justify-center p-4 overscroll-contain sm:items-center sm:p-6">
      <button
        type="button"
        aria-label="Close verification"
        onClick={() => setKpi(null)}
        className="animate-fade-in absolute inset-0 cursor-default bg-black/50 backdrop-blur-sm"
        tabIndex={-1}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="verify-title"
        className="animate-panel-in relative flex max-h-[88vh] w-full max-w-lg flex-col rounded-lg bg-canvas shadow-l5 sm:max-h-[86vh]"
      >
        <div className="overflow-y-auto p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-caption text-mute">
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path
                  d="M8 1.8l5.2 2v4.1c0 3.2-2.2 5.3-5.2 6.3-3-1-5.2-3.1-5.2-6.3V3.8L8 1.8z"
                  stroke="var(--ds-accent)"
                  strokeWidth="1.4"
                  strokeLinejoin="round"
                />
                <path d="M5.8 8l1.6 1.6 2.8-3.2" stroke="var(--ds-accent)" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Verified calculation
            </p>
            <h3 id="verify-title" className="mt-1 text-display-sm text-ink">
              {kpi.label}
            </h3>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="hidden items-center gap-1 rounded-full bg-up/10 px-2.5 py-0.5 font-mono text-caption-mono text-up sm:inline-flex">
              <svg width="10" height="10" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Verified
            </span>
            <button
              ref={closeRef}
              type="button"
              onClick={() => setKpi(null)}
              aria-label="Close"
              className="btn-press flex h-7 w-7 items-center justify-center rounded-sm border border-hairline bg-canvas text-body hover:text-ink"
            >
              <svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>

        <p className="mt-5 text-display-md text-ink tabular-nums">{kpi.value}</p>

        <div className="mt-6 space-y-6">
          <div>
            <p className="font-mono text-caption-mono uppercase tracking-wide text-mute">Formula</p>
            <p className="mt-1.5 rounded-sm bg-canvas-soft p-3 font-mono text-code text-ink">{kpi.verification.formula}</p>
          </div>

          <div>
            <p className="font-mono text-caption-mono uppercase tracking-wide text-mute">Raw values</p>
            <dl className="mt-2 divide-y divide-hairline border-y border-hairline">
              {kpi.verification.values.map((v) => (
                <div key={v.label} className="flex items-center justify-between gap-4 py-2.5">
                  <dt className="text-body-sm text-body">{v.label}</dt>
                  <dd className="font-mono text-body-sm-strong text-ink tabular-nums">{v.value}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="flex items-start gap-3 rounded-sm border border-hairline bg-canvas-soft p-3">
            <svg className="mt-0.5 shrink-0 text-accent" width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M2.5 13.5V5L8 2l5.5 3v8.5" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
              <path d="M5.5 13.5V8h5v5.5" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
            </svg>
            <div>
              <p className="text-body-sm-strong text-ink">{kpi.verification.source.doc}</p>
              <p className="mt-0.5 font-mono text-caption-mono text-mute">{kpi.verification.source.page}</p>
            </div>
          </div>

          <div>
            <p className="font-mono text-caption-mono uppercase tracking-wide text-mute">How it’s calculated</p>
            <p className="mt-1.5 text-body-sm text-body">{kpi.verification.explanation}</p>
          </div>

          {getBeginnerExplanation(kpi.id) && (
            <div className="rounded-sm border border-accent/20 bg-accent-soft p-4">
              <p className="font-mono text-caption-mono uppercase tracking-wide text-accent">What does this mean?</p>
              <p className="mt-2 text-body-sm text-body leading-relaxed">{getBeginnerExplanation(kpi.id)}</p>
            </div>
          )}
        </div>

        <div className="mt-6 flex items-center gap-2 border-t border-hairline pt-4">
          <svg className="shrink-0 text-up" width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M8 1.8l5.2 2v4.1c0 3.2-2.2 5.3-5.2 6.3-3-1-5.2-3.1-5.2-6.3V3.8L8 1.8z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
            <path d="M5.8 8l1.6 1.6 2.8-3.2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <p className="font-mono text-caption-mono text-mute">
            Recomputed from raw statement values — not estimated.
          </p>
        </div>
        </div>
      </div>
    </div>
  );
}
