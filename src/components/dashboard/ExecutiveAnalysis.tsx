import type { ExecutiveSummary } from '../../lib/dashboardAdapter';
import { cn } from '../../lib/utils';

interface WatchItem {
  title?: string;
  text?: string;
  item?: string;
  reason?: string;
  severity?: string;
}

const TONE_MAP: Record<string, string> = {
  high: 'border-annotate-red text-annotate-red',
  medium: 'border-annotate-blue text-annotate-blue',
  low: 'border-annotate-green text-annotate-green',
};

function WatchItemRow({ w }: { w: WatchItem }) {
  const tag = w.severity || 'NOTE';
  const label = tag === 'high' ? 'WATCH' : tag === 'medium' ? 'NOTE' : tag === 'low' ? 'STRENGTH' : tag.toUpperCase();
  const text = w.item || w.text || w.title || '';
  const tone = TONE_MAP[tag] || 'border-ink/30 text-ink-3';

  return (
    <div className="flex items-start gap-3 border-t border-ink/12 py-3 first:border-t-0">
      <span className={cn('shrink-0 rounded-[2px] border px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-widest uppercase', tone)}>
        {label}
      </span>
      <span className="text-sm text-ink-2">{text}</span>
    </div>
  );
}

export default function ExecutiveAnalysis({ summary }: { summary: ExecutiveSummary | null }) {
  if (!summary || summary._metadata?.error) {
    return (
      <div className="border border-ink/20 bg-paper p-6 sm:p-8">
        <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Executive Analysis</p>
        <h3 className="mt-2 font-serif text-2xl font-semibold text-ink">The Read.</h3>
        <p className="mt-4 font-mono text-[10px] tracking-widest text-ink-3 uppercase">
          Executive analysis unavailable for this research session. Core verified financial research remains available.
        </p>
      </div>
    );
  }

  const paragraphs = (summary.executive_overview || '').split('\n').filter(Boolean);
  const highlights = summary.highlights || [];
  const watchItems = summary.watch_items || [];

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[1fr_320px]">
      <div>
        <p className="mb-2 font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Executive Analysis</p>
        <h3 className="mb-6 font-serif text-3xl font-semibold text-ink">The Read.</h3>
        <div className="max-w-2xl space-y-5 font-serif text-[1.05rem] leading-relaxed text-ink-2">
          {paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>

        {/* Sub-analyses */}
        <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2">
          {summary.growth_analysis && (
            <div className="border border-ink/20 bg-paper p-5">
              <p className="mb-2 font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">Growth & Performance</p>
              <p className="text-sm leading-relaxed text-ink-2">{summary.growth_analysis}</p>
            </div>
          )}
          {summary.profitability_analysis && (
            <div className="border border-ink/20 bg-paper p-5">
              <p className="mb-2 font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">Profitability</p>
              <p className="text-sm leading-relaxed text-ink-2">{summary.profitability_analysis}</p>
            </div>
          )}
          {summary.cash_flow_analysis && (
            <div className="border border-ink/20 bg-paper p-5">
              <p className="mb-2 font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">Cash Flow</p>
              <p className="text-sm leading-relaxed text-ink-2">{summary.cash_flow_analysis}</p>
            </div>
          )}
          {summary.balance_sheet_analysis && (
            <div className="border border-ink/20 bg-paper p-5">
              <p className="mb-2 font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">Balance Sheet</p>
              <p className="text-sm leading-relaxed text-ink-2">{summary.balance_sheet_analysis}</p>
            </div>
          )}
        </div>
      </div>

      {/* Annotation sidebar */}
      <div className="border-t border-ink/15 pt-4 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-8">
        <p className="mb-1 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Annotations</p>
        <div>
          {/* Highlights */}
          {highlights.map((h: any, i: number) => (
            <div key={`h-${i}`} className="flex items-start gap-3 border-t border-ink/12 py-3 first:border-t-0">
              <span className={cn(
                'shrink-0 rounded-[2px] border px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-widest uppercase',
                h.importance === 'high' ? 'border-annotate-red text-annotate-red' :
                h.importance === 'medium' ? 'border-annotate-blue text-annotate-blue' :
                'border-ink/30 text-ink-3'
              )}>
                {h.importance === 'high' ? 'WATCH' : h.importance === 'medium' ? 'NOTE' : 'INFO'}
              </span>
              <div>
                <p className="font-mono text-xs font-bold text-ink">{h.title}</p>
                <p className="mt-1 text-xs text-ink-2">{h.text}</p>
              </div>
            </div>
          ))}

          {/* Watch items */}
          {watchItems.map((w: WatchItem, i: number) => (
            <WatchItemRow key={`w-${i}`} w={w} />
          ))}
        </div>

        {/* Management commentary */}
        {summary.management_commentary_summary && (
          <div className="mt-6 border-t border-ink/15 pt-4">
            <p className="mb-2 font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">Management Commentary</p>
            <p className="text-xs leading-relaxed text-ink-2">{summary.management_commentary_summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}
