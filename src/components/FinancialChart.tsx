import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Dot } from "recharts";

interface ChartPoint {
  year: string;
  revenue: number;
  netIncome: number;
}

export default function FinancialChart({ data }: { data: ChartPoint[] }) {
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
        <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid stroke="#11111115" vertical={false} />
          <XAxis
            dataKey="year"
            tick={{ fontFamily: "IBM Plex Mono", fontSize: 11, fill: "#6b6558" }}
            axisLine={{ stroke: "#11111130" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontFamily: "IBM Plex Mono", fontSize: 11, fill: "#6b6558" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "#F2EFE7",
              border: "1px solid #111111",
              borderRadius: 0,
              fontFamily: "IBM Plex Mono",
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="revenue"
            stroke="#111111"
            strokeWidth={2}
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
            dot={{ r: 2.5, fill: "#3978FF" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
