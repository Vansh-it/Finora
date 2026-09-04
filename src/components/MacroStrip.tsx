interface MacroItem {
  label: string;
  value: string;
  series_id?: string;
  date?: string;
}

interface MacroContext {
  available: boolean;
  strip: MacroItem[];
  attribution?: string;
}

export default function MacroStrip({ macro }: { macro?: MacroContext | null }) {
  if (!macro || !macro.available || !macro.strip || macro.strip.length === 0) {
    return null;
  }

  return (
    <div className="border border-ink/15 bg-paper p-5">
      <p className="mb-3 font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">
        Market Context
      </p>
      <div className="grid grid-cols-3 gap-4">
        {macro.strip.map((item) => (
          <div key={item.label}>
            <span className="font-mono text-[10px] tracking-wider text-ink-3 uppercase">
              {item.label}
            </span>
            <div className="mt-1 font-mono text-sm font-bold tabular text-ink">
              {item.value}
            </div>
          </div>
        ))}
      </div>
      {macro.attribution && (
        <p className="mt-3 font-mono text-[9px] text-ink-3">
          {macro.attribution}
        </p>
      )}
    </div>
  );
}
