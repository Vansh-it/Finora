import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { SeriesPoint } from '../../data/microsoft';

/* Theme-aware SVG charts — no chart library, crisp at any DPI.
   All charts animate in on mount: lines draw, bars grow, donuts sweep. */

function useMounted() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(raf);
  }, []);
  return mounted;
}

function usePathLength(ref: RefObject<SVGPathElement | null>, ready: boolean) {
  const [len, setLen] = useState(0);
  useEffect(() => {
    if (!ready || !ref.current) return;
    setLen(ref.current.getTotalLength());
  }, [ready, ref]);
  return len;
}

const EASE = 'cubic-bezier(0.16, 1, 0.3, 1)';

interface LineChartProps {
  data: SeriesPoint[];
  height?: number;
  color?: string;
  formatValue?: (v: number) => string;
}

export function LineChart({ data, height = 240, color = 'var(--ds-accent)', formatValue }: LineChartProps) {
  const W = 600;
  const H = height;
  const PAD = { top: 16, right: 12, bottom: 30, left: 40 };
  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const mounted = useMounted();
  const lineRef = useRef<SVGPathElement>(null);
  const len = usePathLength(lineRef, mounted);
  const dash = len || 1200;

  const x = (i: number) => PAD.left + (i / (data.length - 1)) * innerW;
  const y = (v: number) => PAD.top + innerH - ((v - min) / span) * innerH;

  const line = data.map((d, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(d.value).toFixed(1)}`).join(' ');
  const area = `${line} L${x(data.length - 1).toFixed(1)},${(PAD.top + innerH).toFixed(1)} L${x(0).toFixed(1)},${(PAD.top + innerH).toFixed(1)} Z`;

  const ticks = 4;
  const gridVals = Array.from({ length: ticks + 1 }, (_, i) => min + (span * i) / ticks);
  const showXEvery = Math.ceil(data.length / 6);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Line chart">
      {gridVals.map((v, i) => (
        <g key={i}>
          <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} stroke="var(--ds-hairline)" strokeWidth="1" />
          <text x={PAD.left - 8} y={y(v) + 3.5} textAnchor="end" fontSize="10" fill="var(--ds-mute)">
            {formatValue ? formatValue(v) : v}
          </text>
        </g>
      ))}
      <path
        d={area}
        fill={color}
        style={{ opacity: mounted ? 0.08 : 0, transition: `opacity 700ms ease ${200}ms` }}
      />
      <path
        ref={lineRef}
        d={line}
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        style={{
          strokeDasharray: dash,
          strokeDashoffset: mounted ? 0 : dash,
          transition: `stroke-dashoffset 1100ms ${EASE} 150ms`,
        }}
      />
      {data.map((d, i) =>
        i % showXEvery === 0 || i === data.length - 1 ? (
          <g key={i}>
            <circle
              cx={x(i)}
              cy={y(d.value)}
              r="3.5"
              fill="var(--ds-canvas)"
              stroke={color}
              strokeWidth="2"
              style={{
                opacity: mounted ? 1 : 0,
                transform: mounted ? 'scale(1)' : 'scale(0)',
                transformBox: 'fill-box',
                transformOrigin: 'center',
                transition: `opacity 300ms ease ${350 + i * 70}ms, transform 300ms ease ${350 + i * 70}ms`,
              }}
            >
              <title>{`${d.label}: ${formatValue ? formatValue(d.value) : d.value}`}</title>
            </circle>
            <text
              x={x(i)}
              y={H - 10}
              textAnchor="middle"
              fontSize="10"
              fill="var(--ds-mute)"
              style={{ opacity: mounted ? 1 : 0, transition: `opacity 300ms ease ${350 + i * 70}ms` }}
            >
              {d.label}
            </text>
          </g>
        ) : null,
      )}
    </svg>
  );
}

interface BarChartProps {
  data: SeriesPoint[];
  height?: number;
  color?: string;
  formatValue?: (v: number) => string;
}

export function BarChart({ data, height = 220, color = 'var(--ds-accent)', formatValue }: BarChartProps) {
  const W = 600;
  const H = height;
  const PAD = { top: 16, right: 12, bottom: 30, left: 40 };
  const values = data.map((d) => d.value);
  const max = Math.max(...values);
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const slot = innerW / data.length;
  const barW = Math.min(38, slot * 0.55);

  const mounted = useMounted();
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Bar chart">
      <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + innerH} y2={PAD.top + innerH} stroke="var(--ds-hairline)" strokeWidth="1" />
      {data.map((d, i) => {
        const cx = PAD.left + slot * i + slot / 2;
        return (
          <g key={i}>
            <rect
              x={cx - barW / 2}
              y={y(d.value)}
              width={barW}
              height={PAD.top + innerH - y(d.value)}
              rx="4"
              fill={color}
              opacity={0.92}
              style={{
                transform: mounted ? 'scaleY(1)' : 'scaleY(0)',
                transformBox: 'fill-box',
                transformOrigin: 'bottom',
                transition: `transform 700ms ${EASE} ${i * 70}ms`,
              }}
            >
              <title>{`${d.label}: ${formatValue ? formatValue(d.value) : d.value}`}</title>
            </rect>
            <text
              x={cx}
              y={H - 10}
              textAnchor="middle"
              fontSize="10"
              fill="var(--ds-mute)"
              style={{ opacity: mounted ? 1 : 0, transition: `opacity 300ms ease ${i * 70 + 400}ms` }}
            >
              {d.label}
            </text>
            <text
              x={cx}
              y={y(d.value) - 7}
              textAnchor="middle"
              fontSize="10"
              fontWeight={500}
              fill="var(--ds-body)"
              style={{ opacity: mounted ? 1 : 0, transition: `opacity 300ms ease ${i * 70 + 520}ms` }}
            >
              {formatValue ? formatValue(d.value) : d.value}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export function Sparkline({ data, width = 96, height = 32, color = 'var(--ds-accent)' }: SparklineProps) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const x = (i: number) => (i / (data.length - 1)) * (width - 4) + 2;
  const y = (v: number) => 2 + (height - 4) * (1 - (v - min) / span);
  const line = data.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');

  const mounted = useMounted();
  const pathRef = useRef<SVGPathElement>(null);
  const len = usePathLength(pathRef, mounted);
  const dash = len || 200;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full" aria-hidden="true">
      <path
        ref={pathRef}
        d={line}
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{
          strokeDasharray: dash,
          strokeDashoffset: mounted ? 0 : dash,
          transition: `stroke-dashoffset 900ms ${EASE} 250ms`,
        }}
      />
    </svg>
  );
}

interface DonutProps {
  data: { label: string; value: number }[];
  formatValue?: (v: number) => string;
}

const DONUT_COLORS = ['var(--ds-accent)', 'var(--ds-violet)', 'var(--ds-cyan)'];

export function Donut({ data, formatValue }: DonutProps) {
  const mounted = useMounted();
  const total = data.reduce((s, d) => s + d.value, 0);
  const R = 60;
  const C = 2 * Math.PI * R;
  const starts: number[] = [];
  data.forEach((d, i) => {
    starts[i] = (starts[i - 1] ?? 0) + (d.value / total) * C;
  });

  return (
    <div className="flex flex-col items-center gap-6 sm:flex-row sm:gap-8">
      <svg viewBox="0 0 160 160" className="h-40 w-40 shrink-0" role="img" aria-label="Donut chart of revenue mix">
        <g transform="rotate(-90 80 80)">
          {data.map((d, i) => {
            const frac = d.value / total;
            const start = starts[i - 1] ?? 0;
            return (
              <circle
                key={d.label}
                cx="80"
                cy="80"
                r={R}
                fill="none"
                stroke={DONUT_COLORS[i % DONUT_COLORS.length]}
                strokeWidth="22"
                strokeDasharray={`${mounted ? frac * C : 0} ${C}`}
                strokeDashoffset={mounted ? -start : 0}
                style={{
                  transition: `stroke-dasharray 850ms ${EASE} ${i * 120}ms, stroke-dashoffset 850ms ${EASE} ${i * 120}ms`,
                }}
              >
                <title>{`${d.label}: ${formatValue ? formatValue(d.value) : d.value}`}</title>
              </circle>
            );
          })}
        </g>
        <g style={{ opacity: mounted ? 1 : 0, transition: `opacity 500ms ease ${600}ms` }}>
          <text x="80" y="76" textAnchor="middle" fontSize="13" fontWeight={600} fill="var(--ds-ink)">
            {formatValue ? formatValue(total) : total}
          </text>
          <text x="80" y="92" textAnchor="middle" fontSize="10" fill="var(--ds-mute)">
            Total
          </text>
        </g>
      </svg>
      <ul className="space-y-3" style={{ opacity: mounted ? 1 : 0, transition: `opacity 500ms ease ${350}ms` }}>
        {data.map((d, i) => (
          <li key={d.label} className="flex items-center gap-3">
            <svg className="h-2.5 w-2.5 shrink-0" viewBox="0 0 10 10" aria-hidden="true">
              <circle cx="5" cy="5" r="5" fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
            </svg>
            <div>
              <p className="text-body-sm-strong text-ink">{d.label}</p>
              <p className="font-mono text-caption-mono text-mute tabular-nums">
                {formatValue ? formatValue(d.value) : d.value} · {Math.round((d.value / total) * 100)}%
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
