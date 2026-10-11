import { useState } from "react";
import { Download, Loader2 } from "lucide-react";

export default function ExportExcelButton({ onExport }: { onExport: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);

  async function handle() {
    if (busy) return;
    setBusy(true);
    try {
      await onExport();
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={handle}
      disabled={busy}
      title="Download full dashboard as Excel workbook (.xlsx)"
      className="inline-flex items-center gap-2 border-2 border-ink bg-paper px-5 py-2.5 font-mono text-[11px] font-bold tracking-[0.15em] text-ink uppercase shadow-[3px_3px_0_0_#111111] transition-all hover:bg-ink hover:text-paper disabled:opacity-60 disabled:hover:bg-paper disabled:hover:text-ink"
    >
      {busy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
      {busy ? "Building…" : "Export Excel"}
    </button>
  );
}
