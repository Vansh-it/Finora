import { Search } from "lucide-react";
import type { StatementRow } from "../data/companies";
import { cn } from "../utils/cn";

function formatValue(v: number | null, unit?: string) {
  if (v === null) return "—";
  if (unit === "number") return v.toFixed(2);
  const negative = v < 0;
  const abs = Math.abs(v);
  const formatted = abs.toLocaleString("en-US");
  return negative ? `(${formatted})` : formatted;
}

export default function StatementTable({
  title,
  unitLabel,
  years,
  rows,
  onInspect,
}: {
  title: string;
  unitLabel: string;
  years: string[];
  rows: StatementRow[];
  onInspect?: (label: string) => void;
}) {
  return (
    <div>
      <div className="mb-4 flex items-baseline justify-between">
        <h3 className="font-serif text-2xl font-semibold text-ink">{title}</h3>
        <span className="font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">{unitLabel}</span>
      </div>
      <div className="thin-scroll overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-ink">
              <th className="sticky left-0 bg-paper py-2 pr-4 text-left font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">
                Line Item
              </th>
              {years.map((y) => (
                <th key={y} className="py-2 pl-4 text-right font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">
                  {y}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.label}
                className={cn(
                  "group border-b border-ink/12 hover:bg-paper-2/60",
                  row.isTotal && "border-b border-ink/40 font-semibold"
                )}
              >
                <td className="sticky left-0 bg-paper py-3 pr-4 text-ink-2 group-hover:bg-paper-2/60">
                  <div className="flex items-center gap-1.5">
                    {row.label}
                    {onInspect && (
                      <button
                        onClick={() => onInspect(row.label)}
                        aria-label={`How Finora calculated ${row.label}`}
                        title={`How Finora calculated ${row.label}`}
                        className="text-ink-3 opacity-0 transition-opacity group-hover:opacity-100 hover:text-annotate-blue"
                      >
                        <Search size={11} />
                      </button>
                    )}
                  </div>
                </td>
                {row.values.map((v, i) => (
                  <td
                    key={i}
                    className={cn(
                      "py-3 pl-4 text-right font-mono tabular text-ink",
                      row.isTotal && "font-bold",
                      v !== null && v < 0 && "text-annotate-red"
                    )}
                  >
                    {formatValue(v, row.unit)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
