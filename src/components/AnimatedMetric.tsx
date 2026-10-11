import { useEffect, useState } from "react";

const CYCLE_MS = 4000; // total loop duration
const COUNT_MS = 1500; // number counting duration
const PAUSE_MS = 2000; // pause at full value before reset

function useCountUp(target: number, duration: number, running: boolean) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!running) {
      setValue(0);
      return;
    }
    let raf: number;
    const start = performance.now();
    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(eased * target);
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, running]);

  return value;
}

function formatB(val: number, decimals: number): string {
  return `$${val.toFixed(decimals)}B`;
}

export default function AnimatedMetric() {
  const [cycleKey, setCycleKey] = useState(0);
  const [running, setRunning] = useState(false);

  // restart loop
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const loop = () => {
      setRunning(true);
      timer = setTimeout(() => {
        setRunning(false);
        // brief pause then restart
        timer = setTimeout(() => {
          setCycleKey((k) => k + 1);
        }, 500);
      }, COUNT_MS + PAUSE_MS);
    };
    loop();
    return () => clearTimeout(timer);
  }, [cycleKey]);

  const ocf = useCountUp(125.4, COUNT_MS, running);
  const capex = useCountUp(16.6, COUNT_MS, running);
  const fcf = useCountUp(108.8, COUNT_MS, running);

  return (
    <div className="border border-ink/20 bg-paper p-6 sm:p-8">
      <div className="font-mono text-[10px] tracking-[0.2em] text-ink-3 uppercase">
        Metric: Free Cash Flow · Apple Inc. · FY2025
      </div>

      <div className="mt-6 flex flex-col gap-4 font-mono text-sm">
        {/* Operating Cash Flow */}
        <div className="relative overflow-hidden border-b border-dashed border-ink/30 pb-3">
          <div className="flex items-center justify-between">
            <span className="text-ink-2">Operating Cash Flow</span>
            <span className="font-bold text-ink tabular-nums">
              {formatB(ocf, 1)}
            </span>
          </div>
          {/* sketch underline */}
          <div
            key={`ocf-${cycleKey}`}
            className="absolute bottom-0 left-0 h-[1px] bg-ink/30 sketch-line"
            style={{ width: running ? undefined : "100%" }}
          />
        </div>

        {/* Capital Expenditure */}
        <div className="relative overflow-hidden border-b border-dashed border-ink/30 pb-3">
          <div className="flex items-center justify-between">
            <span className="text-ink-2">− Capital Expenditure</span>
            <span className="font-bold text-ink tabular-nums">
              {formatB(capex, 1)}
            </span>
          </div>
          <div
            key={`capex-${cycleKey}`}
            className="absolute bottom-0 left-0 h-[1px] bg-ink/30 sketch-line"
            style={{ width: running ? undefined : "100%" }}
          />
        </div>

        {/* = Free Cash Flow */}
        <div className="relative pt-1">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-ink">= Free Cash Flow</span>
            <span className="relative inline-block font-mono text-lg font-bold text-ink tabular-nums">
              {/* yellow highlighter strip behind text */}
              <span
                key={`hl-strip-${cycleKey}`}
                className="hl-strip absolute -inset-x-2 inset-y-[-2px] -z-10 -rotate-[0.5deg] bg-highlight"
              />
              {/* text with left-to-right reveal */}
              <span
                key={`hl-reveal-${cycleKey}`}
                className="hl-reveal relative"
              >
                {formatB(fcf, 1)}
              </span>
            </span>
          </div>
        </div>
      </div>

      {/* Source row */}
      <div className="mt-8 flex flex-wrap gap-6 border-t border-ink/15 pt-6">
        <div>
          <div className="font-mono text-[9px] tracking-[0.2em] text-ink-3 uppercase">Source</div>
          <div className="mt-1 font-mono text-xs text-ink">SEC 10-K, FY2025</div>
        </div>
        <div className="max-w-[220px]">
          <div className="font-mono text-[9px] tracking-[0.2em] text-ink-3 uppercase">XBRL Concept</div>
          <div className="mt-1 font-mono text-xs text-ink break-all leading-snug">
            NetCashProvidedByUsedInOperatingActivities
          </div>
        </div>
      </div>
    </div>
  );
}
