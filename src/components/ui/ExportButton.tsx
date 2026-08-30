import { useState } from 'react';

export default function ExportButton({ label = 'Export PDF' }: { label?: string }) {
  const [state, setState] = useState<'idle' | 'working' | 'done'>('idle');

  const run = () => {
    if (state !== 'idle') return;
    setState('working');
    window.setTimeout(() => {
      setState('done');
      window.setTimeout(() => setState('idle'), 2600);
    }, 1400);
  };

  return (
    <>
      <button
        type="button"
        onClick={run}
        className={
          'inline-flex h-9 items-center gap-2 rounded-sm border px-3.5 text-button-md transition-colors ' +
          (state === 'done'
            ? 'border-up/40 bg-up/10 text-up'
            : 'border-hairline bg-canvas text-ink hover:border-hairline-strong')
        }
      >
        {state === 'working' ? (
          <svg className="animate-spin" width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <circle cx="8" cy="8" r="6" stroke="#a1a1a1" strokeWidth="2" />
            <path d="M14 8a6 6 0 0 0-6-6" stroke="#3978ff" strokeWidth="2" strokeLinecap="round" />
          </svg>
        ) : state === 'done' ? (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M8 11V3M5 7.5L8 11l3-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M3 12.5v0.5a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-0.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        )}
        {state === 'working' ? 'Preparing PDF…' : state === 'done' ? 'Dashboard exported' : label}
      </button>

      <div aria-live="polite" className="sr-only">
        {state === 'done' ? 'Dashboard exported as PDF' : ''}
      </div>
    </>
  );
}
