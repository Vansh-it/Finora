import { useState } from "react";
import { cn } from "../utils/cn";

export default function UnavailableMetric({
  label,
  reason,
  notApplicable,
}: {
  label: string;
  reason: string;
  notApplicable?: boolean;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative border border-dashed border-ink/30 bg-paper p-5">
      <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{label}</span>
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow((s) => !s)}
        className="mt-3 block text-left font-mono text-lg font-bold text-ink-3"
      >
        {notApplicable ? "NOT APPLICABLE" : "—"}
      </button>
      {!notApplicable && (
        <div className="mt-1 font-mono text-[10px] tracking-widest text-ink-3 uppercase">Data Unavailable</div>
      )}
      {show && (
        <div
          className={cn(
            "absolute top-full left-0 z-20 mt-2 w-64 border border-ink bg-paper p-3 text-xs leading-relaxed text-ink shadow-[3px_3px_0_0_#111111]"
          )}
        >
          {reason}
        </div>
      )}
    </div>
  );
}
