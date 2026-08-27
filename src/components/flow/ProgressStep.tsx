export type StepState = 'pending' | 'active' | 'done';

interface Props {
  index: number;
  label: string;
  detail: string;
  state: StepState;
  progress?: number; // 0..1 — for the active step only
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
          className="absolute top-9 left-4 h-[calc(100%+14px)] w-px -translate-x-1/2 rounded-full bg-canvas-soft-2"
          aria-hidden="true"
        >
          <span
            className={
              'block h-full w-full origin-top rounded-full bg-accent transition-transform duration-500 ease-out ' +
              (lineState === 'fill' ? 'scale-y-100' : 'scale-y-0')
            }
          />
        </span>
      )}

      <div className="relative flex h-8 w-8 shrink-0 items-center justify-center">
        {state === 'done' ? (
          <span className="animate-pop flex h-8 w-8 items-center justify-center rounded-full bg-up/15 text-up">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
        ) : state === 'active' ? (
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-soft text-accent ring-4 ring-accent/10">
            <svg className="animate-spin" width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="6" stroke="var(--ds-accent)" strokeWidth="2" opacity="0.25" />
              <path d="M14 8a6 6 0 0 0-6-6" stroke="var(--ds-accent)" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </span>
        ) : (
          <span className="flex h-8 w-8 items-center justify-center rounded-full border border-hairline bg-canvas font-mono text-caption-mono text-mute">
            {String(index + 1).padStart(2, '0')}
          </span>
        )}
      </div>

      <div className="min-w-0 flex-1 pt-1">
        <div className="flex items-center justify-between gap-3">
          <p className={'text-body-sm-strong transition-colors duration-300 ' + (state === 'pending' ? 'text-mute' : 'text-ink')}>
            {label}
          </p>
          {state === 'active' && (
            <span className="shrink-0 font-mono text-caption-mono text-accent tabular-nums">
              {Math.max(0, Math.round(progress * 100))}%
            </span>
          )}
        </div>
        <p className={'mt-0.5 truncate font-mono text-caption-mono transition-colors duration-300 ' + (state === 'pending' ? 'text-mute/70' : 'text-mute')}>
          {detail}
        </p>
        {state === 'active' && (
          <div className="mt-2.5 h-1 w-full overflow-hidden rounded-full bg-canvas-soft-2">
            <div
              className="h-full origin-left rounded-full bg-accent transition-transform duration-200 ease-linear"
              style={{ transform: `scaleX(${Math.max(0.05, progress)})` }}
            />
          </div>
        )}
        {state === 'done' && (
          <div className="mt-2.5 h-1 w-full overflow-hidden rounded-full bg-canvas-soft-2">
            <div className="h-full w-full rounded-full bg-up/40" />
          </div>
        )}
      </div>
    </li>
  );
}
