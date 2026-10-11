import { useState } from "react";
import WatchItem from "./WatchItem";
import HighlightText from "./HighlightText";

interface Annotation {
  tag: string;
  text: string;
}

interface ExecutiveAnalysisProps {
  analysis: {
    paragraphs: string[];
    highlights: string[];
    watch: Array<{ tag: "WATCH" | "STRENGTH" | "RISK"; text: string }>;
    the_read?: string;
    annotations?: Annotation[];
    generating?: boolean;
  };
  onAskFollowUp?: () => void;
}

export default function ExecutiveAnalysis({ analysis, onAskFollowUp }: ExecutiveAnalysisProps) {
  const theRead = analysis.the_read || analysis.paragraphs.join(" ");
  const annotations = analysis.annotations || analysis.watch || [];
  const generating = analysis.generating || false;

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[1fr_320px]">
      <div>
        <p className="mb-2 font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Executive Analysis</p>
        <h3 className="mb-6 font-serif text-3xl font-semibold text-ink">The Read.</h3>

        {generating ? (
          <div className="max-w-2xl space-y-4">
            <div className="relative overflow-hidden border border-ink/15 bg-paper-2/50 p-6">
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-highlight/20 to-transparent animate-[marker-sweep_2s_ease-in-out_infinite]" />
              <p className="relative font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">
                Finora is reading the numbers...
              </p>
              <div className="relative mt-4 space-y-2">
                <div className="h-3 w-3/4 bg-ink/5" />
                <div className="h-3 w-1/2 bg-ink/5" />
                <div className="h-3 w-2/3 bg-ink/5" />
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-2xl space-y-5 font-serif text-[1.05rem] leading-relaxed text-ink-2">
            {theRead.split("\n").filter(Boolean).map((p, i) => {
              // Highlight any highlighted terms
              let content = <>{p}</>;
              if (analysis.highlights && analysis.highlights.length > 0) {
                for (const h of analysis.highlights) {
                  if (p.includes(h)) {
                    const parts = p.split(h);
                    content = (
                      <>
                        {parts[0]}
                        <HighlightText>{h}</HighlightText>
                        {parts[1]}
                      </>
                    );
                    break;
                  }
                }
              }
              return <p key={i}>{content}</p>;
            })}
          </div>
        )}
      </div>

      <div className="border-t border-ink/15 pt-4 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-8">
        <p className="mb-1 font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Annotations</p>
        <div>
          {annotations.map((w, i) => {
            const tag = (w.tag || "WATCH") as "WATCH" | "STRENGTH" | "RISK";
            const text = w.text || "";
            const mappedTag: "WATCH" | "STRENGTH" | "RISK" =
              tag === "STRENGTH" ? "STRENGTH" : tag === "RISK" ? "RISK" : "WATCH";
            return <WatchItem key={i} tag={mappedTag} text={text} />;
          })}
        </div>

        {onAskFollowUp && !generating && (
          <button
            onClick={onAskFollowUp}
            className="mt-6 w-full border border-ink/25 px-4 py-3 text-left font-mono text-xs font-semibold tracking-wider text-ink-2 uppercase transition-colors hover:border-ink hover:text-ink"
          >
            Ask Follow-Up →
          </button>
        )}
      </div>
    </div>
  );
}
