import type { CompanyData } from "../data/companies";

export default function ResearchQualityBar({ quality }: { quality: CompanyData["quality"] }) {
  const items = [
    { label: "Primary Source", value: quality.sourceType, isText: true },
    { label: "Metrics", value: String(quality.metrics) },
    { label: "Sources", value: String(quality.sources) },
    { label: "Cross-Verified", value: String(quality.crossVerified) },
    { label: "Material Mismatches", value: String(quality.mismatches) },
  ];
  return (
    <div className="grid grid-cols-2 divide-x divide-ink/15 border-y border-ink/15 sm:grid-cols-5">
      {items.map((item) => (
        <div key={item.label} className="px-4 py-3 first:pl-0">
          <div className={item.isText ? "font-mono text-sm font-bold text-ink" : "font-mono text-xl font-bold text-ink tabular"}>
            {item.value}
          </div>
          <div className="mt-0.5 font-mono text-[10px] font-semibold tracking-[0.12em] text-ink-3 uppercase">
            {item.label}
          </div>
        </div>
      ))}
    </div>
  );
}
