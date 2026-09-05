import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "../utils/cn";
import WatchlistButton from "./WatchlistButton";

interface CompanyHeaderProps {
  ticker: string;
  name: string;
  exchange: string;
  sector: string;
  fiscalYear: string;
  price: number;
  priceChange: number;
  sessionId?: string;
  description?: string;
  industry?: string;
}

/** Build a clean 2-line summary from industry + description */
function buildSummary(industry?: string, description?: string): string {
  if (!industry && !description) return "";

  // Take the first sentence of the description
  let sentence = "";
  if (description) {
    // Find the first full sentence (ends with .)
    const firstPeriod = description.indexOf(".");
    sentence = firstPeriod > 0 ? description.slice(0, firstPeriod + 1) : description.slice(0, 120);
  }

  if (industry && sentence) {
    return `${industry} — ${sentence}`;
  }
  if (industry) return `${industry}.`;
  return sentence;
}

export default function CompanyHeader({ company }: { company: CompanyHeaderProps }) {
  const positive = company.priceChange >= 0;

  const summary = buildSummary(company.industry, company.description);

  return (
    <div className="border-b border-ink/15 pb-6">
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_auto_auto_auto] lg:items-start">
        {/* Left — Company Identity */}
        <div>
          <p className="font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">
            {company.sector}
          </p>
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
          </div>

          {/* Company context — 2 lines max */}
          {summary && (
            <p className="mt-3 max-w-xl font-sans text-sm leading-relaxed text-ink-2 line-clamp-2">
              {summary}
            </p>
          )}
        </div>

        {/* Center — Share Price */}
        <div className="flex flex-col items-start border-l border-ink/15 pl-8 lg:items-center lg:border-l lg:pl-8">
          <span className="font-mono text-[10px] font-semibold tracking-[0.25em] text-ink-3 uppercase">
            Share Price
          </span>
          <div className="mt-1 font-mono text-4xl font-bold text-ink tabular">
            ${company.price.toFixed(2)}
          </div>
          <div
            className={cn(
              "mt-1 flex items-center gap-1 font-mono text-sm font-semibold",
              positive ? "text-annotate-green" : "text-annotate-red"
            )}
          >
            {positive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {positive ? "+" : ""}
            {company.priceChange}%
          </div>
        </div>

        {/* Right — Primary Source + Watchlist */}
        <div className="flex items-start gap-6 border-l border-ink/15 pl-8">
          <div className="flex flex-col">
            <span className="font-mono text-[10px] font-semibold tracking-[0.25em] text-ink-3 uppercase">
              Primary Source
            </span>
            <div className="mt-1 flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-annotate-green" />
              <span className="font-mono text-sm font-bold tracking-wider text-ink uppercase">
                SEC XBRL
              </span>
            </div>
            <span className="mt-0.5 font-mono text-[10px] tracking-wider text-ink-3">
              Verified Financial Data
            </span>
          </div>
          <WatchlistButton
            ticker={company.ticker}
            name={company.name}
            sessionId={company.sessionId}
          />
        </div>
      </div>
    </div>
  );
}
