import { cn } from '../../lib/utils';

export type StepState = 'pending' | 'active' | 'done';

interface Props {
  index: number;
  label: string;
  detail: string;
  state: StepState;
  progress?: number;
  isLast?: boolean;
  lineState?: 'idle' | 'fill';
}

export default function ProgressStep({
  index,
  label,
  detail,
  state,
  progress = 0,
  isLast = false,
  lineState = 'idle',
}: Props) {
  return (
    <li className="relative flex items-start gap-4">
      {!isLast && (
        <span
          className="absolute top-9 left-4 h-[calc(100%+14px)] w-px -translate-x-1/2 bg-paper-3"
          aria-hidden="true"
        >
          <span
            className={cn(
              'block h-full w-full origin-top bg-ink transition-transform duration-500 ease-out',
              lineState === 'fill' ? 'scale-y-100' : 'scale-y-0'
            )}
          />
        </span>
      )}

      <div className="relative flex h-8 w-8 shrink-0 items-center justify-center">
        {state === 'done' ? (
          <span className="flex h-8 w-8 items-center justify-center border-2 border-annotate-green text-annotate-green transition-all duration-300">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
        ) : state === 'active' ? (
          <span className="flex h-8 w-8 items-center justify-center border-2 border-annotate-blue text-annotate-blue transition-all duration-300">
            <svg className="animate-spin" width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" opacity="0.25" />
              <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </span>
        ) : (
          <span className="flex h-8 w-8 items-center justify-center border border-ink/25 bg-paper font-mono text-[10px] font-bold text-ink-3">
            {String(index + 1).padStart(2, '0')}
          </span>
        )}
      </div>

      <div className="min-w-0 flex-1 pt-1">
        <div className="flex items-center justify-between gap-3">
          <p className={cn(
            'font-mono text-xs font-semibold tracking-wider transition-colors duration-300',
            state === 'pending' ? 'text-ink-3' : 'text-ink'
          )}>
            {label}
          </p>
          {state === 'active' && (
            <span className="shrink-0 font-mono text-[10px] font-bold text-annotate-blue tabular-nums">
              {Math.max(0, Math.round(progress * 100))}%
            </span>
          )}
        </div>
        <p className={cn(
          'mt-0.5 truncate font-mono text-[10px] tracking-wider transition-colors duration-300',
          state === 'pending' ? 'text-ink-3/70' : 'text-ink-3'
        )}>
          {detail}
        </p>
        {state === 'active' && (
          <div className="mt-2.5 h-1 w-full overflow-hidden bg-paper-3">
            <div
              className="h-full origin-left bg-annotate-blue transition-transform duration-200 ease-linear"
              style={{ transform: `scaleX(${Math.max(0.05, progress)})` }}
            />
          </div>
        )}
        {state === 'done' && (
          <div className="mt-2.5 h-1 w-full overflow-hidden bg-paper-3">
            <div className="h-full w-full bg-annotate-green/40" />
          </div>
        )}
      </div>
    </li>
  );
}
