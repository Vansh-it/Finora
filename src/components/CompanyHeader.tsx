import { TrendingUp, TrendingDown } from "lucide-react";
import Annotation from "./Annotation";
import { cn } from "../utils/cn";

interface CompanyHeaderProps {
  ticker: string;
  name: string;
  exchange: string;
  sector: string;
  fiscalYear: string;
  price: number;
  priceChange: number;
}

export default function CompanyHeader({ company }: { company: CompanyHeaderProps }) {
  const positive = company.priceChange >= 0;
  return (
    <div className="border-b border-ink/15 pb-6">
      <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
        <div>
          <p className="font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">{company.sector}</p>
          <h1 className="mt-2 font-serif text-4xl font-semibold tracking-tight text-ink uppercase sm:text-5xl">
            {company.name}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2">
            <span className="font-mono text-sm font-bold tracking-wider text-ink">
              {company.ticker} <span className="text-ink-3">· {company.exchange}</span>
            </span>
            <span className="font-mono text-xs font-semibold tracking-widest text-ink-3 uppercase">
              {company.fiscalYear} Research
            </span>
            <Annotation label="Primary Source" value="SEC XBRL" tone="blue" />
          </div>
        </div>

        <div className="text-left lg:text-right">
          <div className="font-mono text-4xl font-bold text-ink tabular">${company.price.toFixed(2)}</div>
          <div
            className={cn(
              "mt-1 flex items-center gap-1 font-mono text-sm font-semibold lg:justify-end",
              positive ? "text-annotate-green" : "text-annotate-red"
            )}
          >
            {positive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {positive ? "+" : ""}
            {company.priceChange}%
          </div>
        </div>
      </div>
    </div>
  );
}
