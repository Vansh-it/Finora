import { X, ExternalLink } from "lucide-react";
import { getEvidence } from "../data/evidence";
import Annotation from "./Annotation";
import HighlightText from "./HighlightText";

export default function EvidenceDrawer({ metric, onClose }: { metric: string | null; onClose: () => void }) {
  if (!metric) return null;
  const evidence = getEvidence(metric);

  return (
    <div className="fixed inset-0 z-[60] flex justify-end">
      <button aria-label="Close evidence drawer" className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l-2 border-ink bg-paper p-6 shadow-2xl sm:p-8">
        <div className="flex items-start justify-between">
          <p className="font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">Evidence Panel</p>
          <button onClick={onClose} aria-label="Close" className="text-ink-2 hover:text-ink">
            <X size={20} />
          </button>
        </div>

        <h2 className="mt-4 font-serif text-3xl font-semibold text-ink">{evidence.metric}</h2>
        <div className="mt-2 font-mono text-3xl font-bold text-ink tabular">{evidence.value}</div>

        <div className="mt-8 border-t border-ink/15 pt-6">
          <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">
            How Finora Calculated This
          </p>
          <p className="mt-3 font-mono text-sm text-ink-2">{evidence.formulaLabel}</p>

          <div className="relative mt-5 border border-ink/25 bg-paper-2/50 p-5">
            <div className="flex items-center justify-between font-mono text-sm">
              <span className="text-ink-2">{evidence.numerator.label}</span>
              <span className="font-bold text-ink">{evidence.numerator.value}</span>
            </div>
            <div className="my-2 h-px bg-ink" />
            <div className="flex items-center justify-between font-mono text-sm">
              <span className="text-ink-2">{evidence.denominator.label}</span>
              <span className="font-bold text-ink">{evidence.denominator.value}</span>
            </div>
            <div className="mt-4 flex items-center justify-end gap-2 border-t border-dashed border-ink/30 pt-3">
              <span className="font-mono text-xs text-ink-2">=</span>
              <HighlightText className="font-mono text-lg font-bold">{evidence.value}</HighlightText>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-ink/15 pt-6">
          <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Source Evidence</p>
          <div className="mt-4 flex flex-wrap gap-6">
            <Annotation label="Filing" value={evidence.source} />
            <Annotation label="Period" value={evidence.period} />
          </div>
          <div className="mt-4">
            <Annotation label="US-GAAP Concept" value={evidence.concept} tone="blue" />
          </div>
          <div className="mt-4">
            <Annotation label="Accession" value={evidence.accession} />
          </div>
          <button className="mt-5 flex items-center gap-2 border border-ink px-4 py-2 font-mono text-xs font-bold tracking-widest text-ink uppercase transition-colors hover:bg-ink hover:text-paper">
            Open Filing <ExternalLink size={13} />
          </button>
        </div>

        <div className="mt-8 border-t border-ink/15 pt-6 pb-4">
          <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">What This Means</p>
          <p className="mt-3 text-sm leading-relaxed text-ink-2">{evidence.meaning}</p>
        </div>
      </div>
    </div>
  );
}
