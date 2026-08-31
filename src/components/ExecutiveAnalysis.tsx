import type { CompanyData } from "../data/companies";
import WatchItem from "./WatchItem";
import HighlightText from "./HighlightText";

export default function ExecutiveAnalysis({ analysis }: { analysis: CompanyData["executiveAnalysis"] }) {
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[1fr_320px]">
      <div>
        <p className="mb-2 font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Executive Analysis</p>
        <h3 className="mb-6 font-serif text-3xl font-semibold text-ink">The Read.</h3>
        <div className="max-w-2xl space-y-5 font-serif text-[1.05rem] leading-relaxed text-ink-2">
          {analysis.paragraphs.map((p, i) => {
            const highlighted = analysis.highlights.find((h) => p.includes(h));
            if (highlighted) {
              const parts = p.split(highlighted);
              return (
                <p key={i}>
                  {parts[0]}
                  <HighlightText>{highlighted}</HighlightText>
                  {parts[1]}
                </p>
              );
            }
            return <p key={i}>{p}</p>;
          })}
        </div>
      </div>

      <div className="border-t border-ink/15 pt-4 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-8">
        <p className="mb-1 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Annotations</p>
        <div>
          {analysis.watch.map((w, i) => (
            <WatchItem key={i} tag={w.tag} text={w.text} />
          ))}
        </div>
      </div>
    </div>
  );
}
