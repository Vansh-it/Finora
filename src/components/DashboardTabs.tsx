import { cn } from "../utils/cn";

export const TABS = [
  "OVERVIEW",
  "INCOME STATEMENT",
  "BALANCE SHEET",
  "CASH FLOW",
  "GROWTH",
  "PROFITABILITY",
  "VALUATION",
  "SOURCES",
] as const;

export type DashboardTab = (typeof TABS)[number];

export default function DashboardTabs({
  active,
  onChange,
}: {
  active: DashboardTab;
  onChange: (t: DashboardTab) => void;
}) {
  return (
    <div className="flex justify-center">
      <div className="thin-scroll -mx-4 flex gap-1 overflow-x-auto border-b border-ink/15 px-4 sm:mx-0 sm:px-0">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className={cn(
              "relative shrink-0 px-4 py-3 font-mono text-xs font-semibold tracking-[0.1em] whitespace-nowrap text-ink-2 uppercase transition-colors hover:text-ink",
              active === tab && "text-ink"
            )}
          >
            {tab}
            {active === tab && <span className="absolute right-2 bottom-0 left-2 h-[3px] bg-highlight" />}
          </button>
        ))}
      </div>
    </div>
  );
}
