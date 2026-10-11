import { cn } from "../utils/cn";

interface AnnotationProps {
  label: string;
  value?: string;
  tone?: "blue" | "red" | "ink";
  className?: string;
}

/** Small handwritten-style editorial annotation label, e.g. "SOURCE 01 / SEC EDGAR" */
export default function Annotation({ label, value, tone = "ink", className }: AnnotationProps) {
  const toneClasses = {
    blue: "text-annotate-blue",
    red: "text-annotate-red",
    ink: "text-ink-2",
  };
  return (
    <div className={cn("font-mono text-[10px] leading-tight tracking-[0.18em] uppercase", className)}>
      <div className={cn("font-semibold", toneClasses[tone])}>{label}</div>
      {value && <div className="mt-0.5 text-ink-3">{value}</div>}
    </div>
  );
}
