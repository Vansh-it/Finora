import { X } from 'lucide-react';
import type { KpiData } from '../../lib/dashboardAdapter';

const BEGINNER_EXPLANATIONS: Record<string, string> = {
  'revenue': 'The total amount of money a company earns from selling its products or services before any expenses are deducted.',
  'gross_profit': 'Revenue minus the direct cost of producing goods sold. It shows how efficiently a company produces its products.',
  'operating_income': 'Profit from core business operations before interest and taxes. It reveals the profitability of the main business.',
  'net_income': 'The bottom line — profit after all expenses, interest, and taxes are paid.',
  'operating_margin': 'What percentage of revenue becomes operating income. Higher = more efficient operations.',
  'net_margin': 'What percentage of revenue becomes net profit. Shows overall profitability.',
  'roe': 'Return on equity — how efficiently a company generates profit from shareholders\' capital.',
  'roa': 'Return on assets — how efficiently a company uses its assets to generate profit.',
  'roic': 'Return on invested capital — the return generated on all capital invested in the business.',
  'current_ratio': 'Current assets divided by current liabilities. Measures ability to pay short-term obligations.',
  'debt_to_equity': 'Total debt relative to shareholders\' equity. Shows financial leverage and risk.',
  'free_cash_flow': 'Cash generated from operations minus capital expenditures. The cash available for dividends, buybacks, or growth.',
  'gross_margin': 'Gross profit as a percentage of revenue. Shows production efficiency.',
  'fcf_margin': 'Free cash flow as a percentage of revenue. Shows cash generation efficiency.',
  'ebitda': 'Earnings before interest, taxes, depreciation, and amortization. A proxy for operating cash generation.',
};

export default function VerificationModal({ kpi, onClose }: { kpi: KpiData; onClose: () => void }) {
  const beginner = BEGINNER_EXPLANATIONS[kpi.id] || 'This metric measures a specific aspect of the company\'s financial performance.';

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

        <h2 className="mt-4 font-serif text-3xl font-semibold text-ink">{kpi.label}</h2>
        <div className="mt-2 font-mono text-3xl font-bold text-ink tabular">{kpi.value}</div>

        {kpi.verification && (
          <div className="mt-8 border-t border-ink/15 pt-6">
            <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">How Finora Calculated This</p>
            <p className="mt-3 font-mono text-sm text-ink-2">{kpi.verification.formula}</p>

            <div className="relative mt-5 border border-ink/25 bg-paper-2/50 p-5">
              {kpi.verification.values.map((v, i) => (
                <div key={i} className="flex items-center justify-between font-mono text-sm">
                  <span className="text-ink-2">{v.label}</span>
                  <span className="font-bold text-ink">{v.value}</span>
                </div>
              ))}
              <div className="mt-4 flex items-center justify-end gap-2 border-t border-dashed border-ink/30 pt-3">
                <span className="font-mono text-xs text-ink-2">=</span>
                <span className="mark-highlight font-mono text-lg font-bold">{kpi.value}</span>
              </div>
            </div>
          </div>
        )}

        <div className="mt-8 border-t border-ink/15 pt-6">
          <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Source Evidence</p>
          <div className="mt-4 flex flex-wrap gap-6">
            {kpi.verification?.source && (
              <>
                <div className="font-mono text-[10px] leading-tight tracking-[0.18em] uppercase">
                  <div className="font-semibold text-ink-2">Filing</div>
                  <div className="mt-0.5 text-ink-3">{kpi.verification.source.doc}</div>
                </div>
                <div className="font-mono text-[10px] leading-tight tracking-[0.18em] uppercase">
                  <div className="font-semibold text-ink-2">Page</div>
                  <div className="mt-0.5 text-ink-3">{kpi.verification.source.page}</div>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="mt-8 border-t border-ink/15 pt-6 pb-4">
          <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">What This Means</p>
          <p className="mt-3 text-sm leading-relaxed text-ink-2">{kpi.verification?.explanation || beginner}</p>
        </div>
      </div>
    </div>
  );
}
