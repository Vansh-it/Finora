import type { CompanyData } from "../data/companies";

export default function ResearchQualityBar({ quality }: { quality: CompanyData["quality"] }) {
  const items = [
    { label: "Metrics", value: String(quality.metrics) },
    { label: "Sources", value: String(quality.sources) },
    { label: "Cross-Verified", value: String(quality.crossVerified) },
    { label: "Material Mismatches", value: String(quality.mismatches) },
  ];

  return (
    <div className="flex items-stretch justify-between border-y border-ink/15 py-4">
      {items.map((item) => (
        <div key={item.label} className="flex-1 text-center">
          <div className="font-mono text-xl font-bold text-ink tabular">
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
