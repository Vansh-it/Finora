import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

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

export interface SeriesPoint {
  label: string;
  value: number;
}

interface MultiSeriesLineChartProps {
  series: { name: string; data: SeriesPoint[]; color: string }[];
  height?: number;
  formatValue?: (v: number) => string;
  unitLabel?: string;
}

export function MultiSeriesLineChart({ series, height = 280, formatValue, unitLabel = '$B' }: MultiSeriesLineChartProps) {
  const allData = series.flatMap((s) => s.data);
  if (!allData.length) {
    return (
      <div className="flex h-[240px] items-center justify-center border border-dashed border-ink/20">
        <span className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">Insufficient data for chart</span>
      </div>
    );
  }

  const W = 640;
  const H = height;
  const PAD = { top: 20, right: 16, bottom: 36, left: 56 };

  // Collect all unique periods across series, sorted
  const allLabels = [...new Set(allData.map((d) => d.label))].sort();
  const xMap = new Map(allLabels.map((l, i) => [l, i]));

  // Find global min/max across all series
  const allValues = allData.map((d) => d.value);
  let min = Math.min(...allValues);
  let max = Math.max(...allValues);
  // Add some padding
  const padding = (max - min) * 0.08 || max * 0.1;
  min = Math.max(0, min - padding);
  max = max + padding;

  const span = max - min || 1;
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const mounted = useMounted();

  const x = (label: string) => PAD.left + ((xMap.get(label) ?? 0) / Math.max(allLabels.length - 1, 1)) * innerW;
  const y = (v: number) => PAD.top + innerH - ((v - min) / span) * innerH;

  const defaultFmt = (v: number) => {
    if (Math.abs(v) >= 1000) return `$${(v / 1000).toFixed(0)}T`;
    if (Math.abs(v) >= 1) return `$${v.toFixed(0)}B`;
    return `$${v.toFixed(2)}B`;
  };
  const fmt = formatValue || defaultFmt;

  // Y-axis ticks (4-5 nice ticks)
  const tickCount = 5;
  const rawStep = span / tickCount;
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep || 1)));
  const niceStep = Math.ceil(rawStep / mag) * mag || 1;
  const gridStart = Math.ceil(min / niceStep) * niceStep;
  const gridVals: number[] = [];
  for (let v = gridStart; v <= max + niceStep * 0.01; v += niceStep) {
    gridVals.push(v);
  }

  // Period labels — show every Nth to avoid crowding
  const showEvery = Math.max(1, Math.ceil(allLabels.length / 8));

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Multi-series line chart">
        {/* Grid lines & Y-axis labels */}
        {gridVals.map((v, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(v)}
              y2={y(v)}
              stroke="rgba(17,17,17,0.1)"
              strokeWidth="1"
            />
            <text
              x={PAD.left - 10}
              y={y(v) + 4}
              textAnchor="end"
              fontSize="11"
              fontFamily="IBM Plex Mono, monospace"
              fill="#6b6558"
            >
              {fmt(v)}
            </text>
          </g>
        ))}

        {/* Bottom axis */}
        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={PAD.top + innerH}
          y2={PAD.top + innerH}
          stroke="rgba(17,17,17,0.25)"
          strokeWidth="1"
        />

        {/* X-axis period labels */}
        {allLabels.map((label, i) =>
          i % showEvery === 0 || i === allLabels.length - 1 ? (
            <text
              key={label}
              x={x(label)}
              y={H - 10}
              textAnchor="middle"
              fontSize="11"
              fontFamily="IBM Plex Mono, monospace"
              fill="#6b6558"
              style={{ opacity: mounted ? 1 : 0, transition: `opacity 300ms ease ${200 + i * 50}ms` }}
            >
              {label}
            </text>
          ) : null,
        )}

        {/* Lines */}
        {series.map((s, si) => {
          const points = s.data.map((d) => `${x(d.label).toFixed(1)},${y(d.value).toFixed(1)}`).join(' ');
          if (!points) return null;
          const pathD = points.split(' ').map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');

          return (
            <g key={s.name}>
              <path
                d={pathD}
                fill="none"
                stroke={s.color}
                strokeWidth="2.5"
                strokeLinejoin="round"
                strokeLinecap="round"
                style={{
                  strokeDasharray: 2000,
                  strokeDashoffset: mounted ? 0 : 2000,
                  transition: `stroke-dashoffset 1200ms ${EASE} ${si * 200}ms`,
                }}
              />
              {/* Data points */}
              {s.data.map((d, i) => (
                <circle
                  key={i}
                  cx={x(d.label)}
                  cy={y(d.value)}
                  r="4"
                  fill="#f2efe7"
                  stroke={s.color}
                  strokeWidth="2"
                  style={{
                    opacity: mounted ? 1 : 0,
                    transition: `opacity 300ms ease ${400 + i * 80}ms`,
                  }}
                >
                  <title>{`${d.label}\n${s.name}: ${fmt(d.value)}`}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="mt-3 flex items-center justify-center gap-6">
        {series.map((s) => (
          <div key={s.name} className="flex items-center gap-2">
            <span className="block h-[3px] w-5" style={{ backgroundColor: s.color }} />
            <span className="font-mono text-[10px] font-semibold tracking-widest text-ink-2 uppercase">{s.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Legacy single-series LineChart ──────────────────────────────────────── */

interface LineChartProps {
  data: SeriesPoint[];
  height?: number;
  color?: string;
  formatValue?: (v: number) => string;
}

export function LineChart({ data, height = 240, color = '#3978ff', formatValue }: LineChartProps) {
  return (
    <MultiSeriesLineChart
      series={[{ name: 'Value', data, color }]}
      height={height}
      formatValue={formatValue}
    />
  );
}

/* ── BarChart ────────────────────────────────────────────────────────────── */

interface BarChartProps {
  data: SeriesPoint[];
  height?: number;
  color?: string;
  formatValue?: (v: number) => string;
}

export function BarChart({ data, height = 220, color = '#3978ff', formatValue }: BarChartProps) {
  if (!data || data.length < 1) {
    return (
      <div className="flex h-[220px] items-center justify-center border border-dashed border-ink/20">
        <span className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">No data</span>
      </div>
    );
  }

  const W = 600;
  const H = height;
  const PAD = { top: 16, right: 12, bottom: 30, left: 40 };
  const values = data.map((d) => d.value);
  const max = Math.max(...values) || 1;
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const slot = innerW / data.length;
  const barW = Math.min(38, slot * 0.55);

  const mounted = useMounted();
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Bar chart">
      <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + innerH} y2={PAD.top + innerH} stroke="rgba(17,17,17,0.15)" strokeWidth="1" />
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
              fill="#6b6558"
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
              fill="#353535"
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

/* ── Sparkline ───────────────────────────────────────────────────────────── */

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export function Sparkline({ data, width = 96, height = 32, color = '#3978ff' }: SparklineProps) {
  if (!data || data.length < 2) return null;
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

/* ── Donut ───────────────────────────────────────────────────────────────── */

interface DonutProps {
  data: { label: string; value: number }[];
  formatValue?: (v: number) => string;
}

const DONUT_COLORS = ['#3978ff', '#7928ca', '#50e3c2'];

export function Donut({ data, formatValue }: DonutProps) {
  const mounted = useMounted();
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;
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
          <text x="80" y="76" textAnchor="middle" fontSize="13" fontWeight={600} fill="#111111">
            {formatValue ? formatValue(total) : total}
          </text>
          <text x="80" y="92" textAnchor="middle" fontSize="10" fill="#6b6558">
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
              <p className="text-sm font-semibold text-ink">{d.label}</p>
              <p className="font-mono text-xs text-ink-3 tabular-nums">
                {formatValue ? formatValue(d.value) : d.value} · {Math.round((d.value / total) * 100)}%
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
