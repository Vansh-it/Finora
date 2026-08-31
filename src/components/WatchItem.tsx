import { cn } from "../utils/cn";

const TONE_MAP = {
  WATCH: "border-annotate-blue text-annotate-blue",
  STRENGTH: "border-annotate-green text-annotate-green",
  RISK: "border-annotate-red text-annotate-red",
};

export default function WatchItem({ tag, text }: { tag: "WATCH" | "STRENGTH" | "RISK"; text: string }) {
  return (
    <div className="flex items-start gap-3 border-t border-ink/12 py-3 first:border-t-0">
      <span
        className={cn(
          "shrink-0 rounded-[2px] border px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-widest uppercase",
          TONE_MAP[tag]
        )}
      >
        {tag}
      </span>
      <span className="text-sm text-ink-2">{text}</span>
    </div>
  );
}
