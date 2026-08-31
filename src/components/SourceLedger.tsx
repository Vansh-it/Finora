import { ExternalLink } from "lucide-react";
import type { CompanyData } from "../data/companies";
import SourceStamp from "./SourceStamp";

export default function SourceLedger({ sources }: { sources: CompanyData["sources"] }) {
  return (
    <div className="divide-y divide-ink/12 border-y border-ink/20">
      {sources.map((s) => (
        <div key={s.id} className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-4">
            <span className="font-mono text-sm font-bold text-ink-3">{s.id}</span>
            <div>
              <div className="font-serif text-lg font-semibold text-ink">{s.name}</div>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <SourceStamp tone={s.trust === "PRIMARY" ? "ink" : s.trust === "OFFICIAL" ? "blue" : "green"}>
                  {s.trust}
                </SourceStamp>
                <span className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">{s.period}</span>
              </div>
              <p className="mt-1.5 max-w-md text-sm text-ink-2">{s.usedFor}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 pl-9 sm:pl-0">
            <span className="font-mono text-[10px] font-bold tracking-widest text-annotate-green uppercase">
              {s.status}
            </span>
            <button
              className="flex items-center gap-1 border border-ink/40 px-2.5 py-1.5 font-mono text-[10px] font-semibold tracking-widest text-ink uppercase transition-colors hover:border-ink"
              aria-label={`Open ${s.name}`}
            >
              Open <ExternalLink size={11} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
