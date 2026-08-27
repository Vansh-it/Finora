import { useEffect, useRef, useState } from 'react';
import type { Kpi } from '../../data/microsoft';
import { Sparkline } from './charts';

interface ParsedValue {
  prefix: string;
  num: number;
  suffix: string;
  decimals: number;
}

function parseValue(value: string): ParsedValue {
  const m = value.match(/^([^\d]*)([\d,]+(?:\.\d+)?)(.*)$/);
  if (!m) return { prefix: '', num: 0, suffix: value, decimals: 0 };
  const [, prefix, numStr, suffix] = m;
  const decimals = numStr.includes('.') ? numStr.split('.')[1].length : 0;
  return { prefix, num: parseFloat(numStr.replace(/,/g, '')), suffix, decimals };
}

export default function KpiCard({ kpi }: { kpi: Kpi }) {
  const ref = useRef<HTMLElement>(null);
  const [inView, setInView] = useState(false);
  const { prefix, num, suffix, decimals } = parseValue(kpi.value);
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!inView) return;
    let raf = 0;
    const t0 = performance.now();
    const duration = 950;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = p === 1 ? 1 : 1 - Math.pow(2, -10 * p);
      setDisplay(num * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, num]);

  const formatted =
    prefix +
    display.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }) +
    suffix;

  return (
    <article
      ref={ref}
      className="rounded-lg bg-canvas p-5 shadow-l2 transition-[box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:shadow-l4"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-caption text-mute">{kpi.label}</p>
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent('finora:verify', { detail: kpi }))}
          aria-label={`Verify ${kpi.label}`}
          title="Verify this number"
          className="btn-press flex h-6 w-6 items-center justify-center rounded-sm text-mute hover:bg-accent-soft hover:text-accent"
        >
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path
              d="M8 1.8l5.2 2v4.1c0 3.2-2.2 5.3-5.2 6.3-3-1-5.2-3.1-5.2-6.3V3.8L8 1.8z"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinejoin="round"
            />
            <path d="M5.8 8l1.6 1.6 2.8-3.2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
      <div className="mt-3 flex items-end justify-between gap-4">
        <div>
          <p className="text-display-md text-ink tabular-nums">{formatted}</p>
          <p
            className={
              'mt-1 font-mono text-caption-mono tabular-nums ' +
              (kpi.change.direction === 'up'
                ? 'text-up'
                : kpi.change.direction === 'down'
                  ? 'text-down'
                  : 'text-mute')
            }
          >
            {kpi.change.value} YoY
          </p>
        </div>
        <div className="h-8 w-24 shrink-0">
          <Sparkline data={kpi.spark} />
        </div>
      </div>
    </article>
  );
}
