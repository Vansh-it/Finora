import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Dot } from 'recharts';
import type { SeriesPoint } from './charts';

interface FinancialChartProps {
  revenue: SeriesPoint[];
  netIncome: SeriesPoint[];
}

function fmtBillions(v: number): string {
  if (Math.abs(v) >= 1000) return `$${(v / 1000).toFixed(0)}T`;
  if (Math.abs(v) >= 1) return `$${v.toFixed(0)}B`;
  return `$${v.toFixed(1)}B`;
}

export default function FinancialChart({ revenue, netIncome }: FinancialChartProps) {
  // Merge into recharts format
  const allLabels = [...new Set([...revenue.map((d) => d.label), ...netIncome.map((d) => d.label)])].sort();
  const revMap = new Map(revenue.map((d) => [d.label, d.value]));
  const niMap = new Map(netIncome.map((d) => [d.label, d.value]));

  const data = allLabels.map((label) => ({
    year: label,
    revenue: revMap.get(label) ?? null,
    netIncome: niMap.get(label) ?? null,
  }));

  if (data.length < 1) {
    return (
      <div className="border border-ink/20 bg-paper p-5">
        <h3 className="mb-4 font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase">Revenue vs. Net Income ($B)</h3>
        <div className="flex h-[260px] items-center justify-center border border-dashed border-ink/20">
          <span className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">Insufficient data for chart</span>
        </div>
      </div>
    );
  }

  const lastIndex = data.length - 1;

  return (
    <div className="border border-ink/20 bg-paper p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase">Revenue vs. Net Income ($B)</h3>
        <div className="flex items-center gap-4 font-mono text-[10px] tracking-widest text-ink-3 uppercase">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-3 bg-ink" /> Revenue
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-3 bg-annotate-blue" /> Net Income
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <CartesianGrid stroke="#11111115" vertical={false} />
          <XAxis
            dataKey="year"
            tick={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, fill: '#6b6558' }}
            axisLine={{ stroke: '#11111130' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, fill: '#6b6558' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={fmtBillions}
            width={60}
          />
          <Tooltip
            formatter={(value: any, name: any) => [fmtBillions(Number(value)), name === 'revenue' ? 'Revenue' : 'Net Income']}
            contentStyle={{
              background: '#F2EFE7',
              border: '1px solid #111111',
              borderRadius: 0,
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="revenue"
            stroke="#111111"
            strokeWidth={2}
            connectNulls
            dot={(props) => {
              const { cx, cy, index } = props;
              if (index === lastIndex) {
                return <Dot key={`d-${index}`} cx={cx} cy={cy} r={5} fill="#E9FF32" stroke="#111111" strokeWidth={1.5} />;
              }
              return <Dot key={`d-${index}`} cx={cx} cy={cy} r={2.5} fill="#111111" />;
            }}
          />
          <Line
            type="monotone"
            dataKey="netIncome"
            stroke="#3978FF"
            strokeWidth={2}
            connectNulls
            dot={{ r: 2.5, fill: '#3978FF' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
