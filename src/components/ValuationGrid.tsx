import type { CompanyData } from "../data/companies";
import UnavailableMetric from "./UnavailableMetric";

export default function ValuationGrid({ valuation }: { valuation: CompanyData["valuation"] }) {
  return (
    <div>
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { label: "Share Price", value: valuation.price },
          { label: "Market Cap", value: valuation.marketCap },
          { label: "Enterprise Value", value: valuation.enterpriseValue },
        ].map((v) => (
          <div key={v.label} className="border border-ink/20 bg-paper p-5">
            <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{v.label}</span>
            <div className="mt-2 font-mono text-2xl font-bold text-ink tabular">{v.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {valuation.multiples.map((m) =>
          m.unavailable ? (
            <UnavailableMetric key={m.label} label={m.label} reason={m.note ?? ""} notApplicable />
          ) : (
            <div key={m.label} className="border border-ink/20 bg-paper p-5">
              <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{m.label}</span>
              <div className="mt-2 font-mono text-xl font-bold text-ink tabular">{m.value}</div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
