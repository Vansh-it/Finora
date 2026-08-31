import { cn } from "../utils/cn";

interface SourceStampProps {
  children: React.ReactNode;
  tone?: "ink" | "blue" | "red" | "green";
  className?: string;
}

export default function SourceStamp({ children, tone = "ink", className }: SourceStampProps) {
  const toneClasses: Record<string, string> = {
    ink: "border-ink text-ink",
    blue: "border-annotate-blue text-annotate-blue",
    red: "border-annotate-red text-annotate-red",
    green: "border-annotate-green text-annotate-green",
  };
  return (
    <span
      className={cn(
        "inline-flex -rotate-2 items-center gap-1 rounded-[2px] border-2 px-2 py-0.5 font-mono text-[10px] font-bold tracking-[0.15em] uppercase",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
