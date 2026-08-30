import { Search } from 'lucide-react';
import { cn } from '../../lib/utils';

interface KpiCardProps {
  label: string;
  value: string;
  delta?: string;
  deltaTone?: 'pos' | 'neg' | 'neutral';
  highlighted?: boolean;
  unavailable?: boolean;
  onInspect?: () => void;
}

export default function KpiCard({ label, value, delta, deltaTone, highlighted, unavailable, onInspect }: KpiCardProps) {
  return (
    <div
      className={cn(
        'group relative border border-ink/20 bg-paper p-5 transition-colors',
        highlighted && 'border-ink'
      )}
    >
      <div className="flex items-start justify-between">
        <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{label}</span>
        {onInspect && !unavailable && (
          <button
            onClick={onInspect}
            aria-label={`How Finora calculated ${label}`}
            title={`How Finora calculated ${label}`}
            className="text-ink-3 opacity-0 transition-opacity group-hover:opacity-100 hover:text-annotate-blue"
          >
            <Search size={13} />
          </button>
        )}
      </div>

      {unavailable ? (
        <div className="mt-3 text-center">
          <div className="font-mono text-lg font-bold text-ink-3">&mdash;</div>
          <div className="mt-1 font-mono text-sm text-ink-3 uppercase">Data Unavailable</div>
        </div>
      ) : (
        <div className="mt-3 flex items-baseline gap-2">
          <span
            className={cn(
              'font-mono text-2xl font-bold text-ink tabular sm:text-3xl',
              highlighted && 'mark-highlight'
            )}
          >
            {value}
          </span>
          {delta && (
            <span
              className={cn(
                'font-mono text-xs font-semibold',
                deltaTone === 'pos' && 'text-annotate-green',
                deltaTone === 'neg' && 'text-annotate-red',
                deltaTone === 'neutral' && 'text-ink-3'
              )}
            >
              {delta}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
