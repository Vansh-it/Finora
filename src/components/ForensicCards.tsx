import { useState } from "react";
import { cn } from "../utils/cn";

interface ForensicSignal {
  label: string;
  value: number;
  max: number;
}

interface ForensicScores {
  piotroski?: {
    score?: number;
    status?: string;
    signals?: ForensicSignal[];
    interpretation?: string;
    applicable?: boolean;
    reason?: string;
  } | null;
  altman?: {
    score?: number;
    status?: string;
    zone?: string;
    applicable?: boolean;
    reason?: string;
    factors?: Array<{ name: string; value: number }>;
    variant?: string;
  } | null;
  beneish?: {
    score?: number;
    status?: string;
    applicable?: boolean;
    reason?: string;
    indices?: Array<{ name: string; value: number }>;
  } | null;
}

function ScoreBar({
  value,
  max,
  thresholds,
}: {
  value: number;
  max: number;
  thresholds?: { good: number; warn: number };
}) {
  const pct = Math.min((value / max) * 100, 100);
  const good = thresholds?.good ?? max * 0.7;
  const warn = thresholds?.warn ?? max * 0.4;
  const color =
    value >= good
      ? "bg-annotate-green"
      : value >= warn
        ? "bg-annotate-blue"
        : "bg-annotate-red";

  return (
    <div className="h-1.5 w-full bg-ink/10">
      <div className={cn("h-full transition-all", color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function ForensicCards({
  scores,
  onInspect,
}: {
  scores: ForensicScores;
  onInspect?: (metric: string) => void;
}) {
  const { piotroski, altman, beneish } = scores;

  // Don't render if all are null/undefined
  if (!piotroski && !altman && !beneish) return null;

  return (
    <div className="space-y-6">
      <p className="font-mono text-xs font-semibold tracking-[0.25em] text-ink-3 uppercase">
        Financial Health &amp; Forensics
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Piotroski F-Score */}
        <PiotroskiCard data={piotroski} onInspect={onInspect} />

        {/* Altman Z-Score */}
        <AltmanCard data={altman} onInspect={onInspect} />

        {/* Beneish M-Score */}
        <BeneishCard data={beneish} onInspect={onInspect} />
      </div>
    </div>
  );
}

function PiotroskiCard({
  data,
  onInspect,
}: {
  data?: ForensicScores["piotroski"];
  onInspect?: (metric: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!data || !data.score) {
    return (
      <div className="border border-dashed border-ink/25 bg-paper p-5">
        <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">
          Piotroski F-Score
        </span>
        <div className="mt-3 font-mono text-lg font-bold text-ink-3">
          —
        </div>
        <p className="mt-1 font-mono text-[10px] text-ink-3">
          Insufficient data for calculation
        </p>
      </div>
    );
  }

  return (
    <div className="border border-ink/20 bg-paper p-5">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">
          Piotroski F-Score
        </span>
        {onInspect && (
          <button
            onClick={() => onInspect("Piotroski F-Score")}
            className="font-mono text-[10px] text-ink-3 underline hover:text-ink"
          >
            Evidence →
          </button>
        )}
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <span className="font-mono text-2xl font-bold tabular">{data.score}</span>
        <span className="font-mono text-sm text-ink-3">/ 9</span>
      </div>

      <div className="mt-2">
        <ScoreBar value={data.score} max={9} thresholds={{ good: 7, warn: 4 }} />
      </div>

      <div className="mt-2">
        <span
          className={cn(
            "font-mono text-[10px] font-bold tracking-wider uppercase",
            data.score >= 7
              ? "text-annotate-green"
              : data.score >= 4
                ? "text-annotate-blue"
                : "text-annotate-red"
          )}
        >
          {data.status || (data.score >= 7 ? "STRONG" : data.score >= 4 ? "MIXED" : "WEAK")}
        </span>
      </div>

      {/* Expandable signals */}
      {data.signals && data.signals.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="font-mono text-[10px] text-ink-3 underline hover:text-ink"
          >
            {expanded ? "Hide signals" : "Show 9 signals"}
          </button>

          {expanded && (
            <div className="mt-2 space-y-1">
              {data.signals.map((s) => (
                <div key={s.label} className="flex items-center justify-between font-mono text-[10px]">
                  <span className="text-ink-2 truncate pr-2">{s.label}</span>
                  <span className={cn("shrink-0 font-bold", s.value === 1 ? "text-annotate-green" : "text-ink-3")}>
                    {s.value === 1 ? "✓ +1" : "✕ +0"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AltmanCard({
  data,
  onInspect,
}: {
  data?: ForensicScores["altman"];
  onInspect?: (metric: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!data) {
    return (
      <div className="border border-dashed border-ink/25 bg-paper p-5">
        <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">
          Altman Z-Score
        </span>
        <div className="mt-3 font-mono text-lg font-bold text-ink-3">—</div>
        <p className="mt-1 font-mono text-[10px] text-ink-3">
          Insufficient data for calculation
        </p>
      </div>
    );
  }

  if (data.applicable === false) {
    return (
      <div className="border border-dashed border-ink/25 bg-paper p-5">
        <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">
          Altman Z-Score
        </span>
        <div className="mt-3 font-mono text-sm font-bold text-ink-3">
          NOT APPLICABLE
        </div>
        <p className="mt-1 font-mono text-[10px] leading-relaxed text-ink-3">
          {data.reason || "Not applicable for financial institutions."}
        </p>
      </div>
    );
  }

  const zoneColor =
    data.zone === "Safe"
      ? "text-annotate-green"
      : data.zone === "Grey"
        ? "text-annotate-blue"
        : "text-annotate-red";

  return (
    <div className="border border-ink/20 bg-paper p-5">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">
          Altman Z-Score
        </span>
        {onInspect && (
          <button
            onClick={() => onInspect("Altman Z-Score")}
            className="font-mono text-[10px] text-ink-3 underline hover:text-ink"
          >
            Evidence →
          </button>
        )}
      </div>

      <div className="mt-2 font-mono text-2xl font-bold tabular">
        {data.score?.toFixed(2) ?? "—"}
      </div>

      <div className="mt-1">
        <span className={cn("font-mono text-[10px] font-bold tracking-wider uppercase", zoneColor)}>
          {data.zone || data.status || "Unknown"}
        </span>
        {data.variant && (
          <span className="ml-2 font-mono text-[10px] text-ink-3">
            ({data.variant})
          </span>
        )}
      </div>

      {data.factors && data.factors.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="font-mono text-[10px] text-ink-3 underline hover:text-ink"
          >
            {expanded ? "Hide factors" : "Show factors"}
          </button>
          {expanded && (
            <div className="mt-2 space-y-1">
              {data.factors.map((f) => (
                <div key={f.name} className="flex items-center justify-between font-mono text-[10px]">
                  <span className="text-ink-2 truncate pr-2">{f.name}</span>
                  <span className="shrink-0 font-bold tabular">{f.value.toFixed(4)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BeneishCard({
  data,
  onInspect,
}: {
  data?: ForensicScores["beneish"];
  onInspect?: (metric: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!data || data.applicable === false) {
    return (
      <div className="border border-dashed border-ink/25 bg-paper p-5">
        <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">
          Beneish M-Score
        </span>
        <div className="mt-3 font-mono text-lg font-bold text-ink-3">—</div>
        <p className="mt-1 font-mono text-[10px] text-ink-3">
          {data?.reason || "Requires two comparable periods of data."}
        </p>
      </div>
    );
  }

  return (
    <div className="border border-ink/20 bg-paper p-5">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">
          Beneish M-Score
        </span>
        {onInspect && (
          <button
            onClick={() => onInspect("Beneish M-Score")}
            className="font-mono text-[10px] text-ink-3 underline hover:text-ink"
          >
            Evidence →
          </button>
        )}
      </div>

      <div className="mt-2 font-mono text-2xl font-bold tabular">
        {data.score?.toFixed(2) ?? "—"}
      </div>

      <div className="mt-1">
        <span
          className={cn(
            "font-mono text-[10px] font-bold tracking-wider uppercase",
            data.score && data.score > -1.78 ? "text-annotate-red" : "text-annotate-green"
          )}
        >
          {data.status || (data.score && data.score > -1.78 ? "ELEVATED SIGNAL" : "LOW RISK")}
        </span>
      </div>

      <p className="mt-2 font-mono text-[9px] leading-relaxed text-ink-3">
        Screening indicator, not proof of misconduct.
      </p>

      {data.indices && data.indices.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="font-mono text-[10px] text-ink-3 underline hover:text-ink"
          >
            {expanded ? "Hide indices" : "Show 8 indices"}
          </button>
          {expanded && (
            <div className="mt-2 space-y-1">
              {data.indices.map((idx) => (
                <div key={idx.name} className="flex items-center justify-between font-mono text-[10px]">
                  <span className="text-ink-2 truncate pr-2">{idx.name}</span>
                  <span className="shrink-0 font-bold tabular">{idx.value.toFixed(4)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
