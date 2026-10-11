export default function SourceCitation({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1 border border-ink/30 bg-paper-2/60 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wide text-ink-2 uppercase">
      {label}
    </span>
  );
}
