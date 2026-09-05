// 100% FREE client-side Excel export — no API, no server, no key.
// Uses `exceljs` (MIT) loaded via dynamic import so the main bundle stays small.
import { Buffer } from "buffer";

// exceljs expects Node's Buffer at runtime. Vite browsers don't provide it,
// so `writeBuffer()` throws "Buffer is not defined" and the button appears dead.
// Polyfill it once before exceljs is ever imported.
if (!(globalThis as any).Buffer) {
  (globalThis as any).Buffer = Buffer;
}
if (!(globalThis as any).process) {
  (globalThis as any).process = { nextTick: (fn: (...a: any[]) => void, ...a: any[]) => setTimeout(() => fn(...a), 0), env: {} };
}

type RawNum = number | null | undefined;

interface DashboardLike {
  company: { name: string; ticker: string; exchange: string; period: string; currency: string; cik: string };
  periods: string[];
  kpis: Array<{ id: string; label: string; value: string; change?: { value: string; direction: string } }>;
  income_statement: { columns: string[]; rows: Array<{ label: string; values: string[]; strong?: boolean }> };
  balance_sheet: { columns: string[]; rows: Array<{ label: string; values: string[]; strong?: boolean }> };
  cash_flow: { columns: string[]; rows: Array<{ label: string; values: string[]; strong?: boolean }> };
  growth: { columns: string[]; rows: Array<{ label: string; values: string[]; strong?: boolean }> };
  profitability: Array<{ metric: string; value: string; note: string }>;
  liquidity: Array<{ metric: string; value: string; note: string }>;
  leverage: Array<{ metric: string; value: string; note: string }>;
  efficiency: Array<{ metric: string; value: string; note: string }>;
  capital_allocation: Array<{ metric: string; value: string; note: string }>;
  dupont?: { roe: string; net_margin: string; asset_turnover: string; equity_multiplier: string; calculation: string } | null;
  valuation: {
    market_data: { price: number | null; price_date: string; exchange: string; currency: string; source: string; is_historical: boolean; alignment_status: string; target_date: string; percent_change?: number | null };
    metrics: Array<{ metric_id: string; name: string; display_value: string; value: number | null; status: string; formula: string; calculation: string; reason: string }>;
    period_alignment: Record<string, unknown>;
    is_financial_institution: boolean;
  };
  forensic_scores?: {
    piotroski?: { score: number; status: string; signals: Array<{ label: string; value: number; max: number }>; interpretation: string } | null;
    altman?: { score: number; status: string; zone: string; applicable: boolean; reason: string; factors: Array<{ name: string; value: number }>; variant: string } | null;
    beneish?: { score: number; status: string; applicable: boolean; reason: string; indices: Array<{ name: string; value: number }> } | null;
  };
  watch_items?: Array<{ id: string; title: string; headline: string; reason: string; severity: string; tag: string }>;
  macro_context?: { available: boolean; strip: Array<{ label: string; value: string }>; attribution: string };
  sources: Array<{ id: string; name: string; meta: string; pages: string; status: string; url: string; trust_tier: number; period: string }>;
  data_quality: { primary_source: string; metrics_calculated: number; cross_verified: number; mismatches: number; sources_count: number };
  executive_summary?: { executive_overview: string; highlights: Array<{ title: string; text: string }>; growth_analysis: string; profitability_analysis: string; cash_flow_analysis: string; balance_sheet_analysis: string; watch_items: Array<{ tag: string; text: string }>; management_commentary_summary: string; data_quality_note: string } | null;
  raw_export?: {
    periods: string[];
    kpis: Array<{ id: string; label: string; value: RawNum; kind: string }>;
    income: Array<{ label: string; values: RawNum[] }>;
    balance: Array<{ label: string; values: RawNum[] }>;
    cashflow: Array<{ label: string; values: RawNum[] }>;
    growth_raw: Record<string, Record<string, RawNum>>;
    profitability_raw: Record<string, RawNum>;
    liquidity_raw: Record<string, RawNum>;
    leverage_raw: Record<string, RawNum>;
    efficiency_raw: Record<string, RawNum>;
    capital_raw: Record<string, RawNum>;
  };
}

const INK = "FF111111";
const PAPER = "FFFFFFFF";
const MUTED = "FFF5F1E8";
const BLUE = "FF3978FF";

function styleHeader(row: any) {
  row.eachCell((cell: any) => {
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: INK } };
    cell.font = { color: { argb: PAPER }, bold: true, size: 10, name: "Consolas" };
    cell.alignment = { vertical: "middle", horizontal: "center", wrapText: true };
  });
  row.height = 22;
}

function styleTitle(cell: any) {
  cell.font = { bold: true, size: 14, name: "Georgia", color: { argb: INK } };
}

function addSheetTitle(ws: any, title: string, subtitle: string) {
  ws.getCell("A1").value = title;
  styleTitle(ws.getCell("A1"));
  ws.getCell("A2").value = subtitle;
  ws.getCell("A2").font = { size: 9, name: "Consolas", color: { argb: "FF666666" } };
}

function freezeAndFilter(ws: any, ref: string) {
  (ws.views as any) = [{ state: "frozen", ySplit: 3 }];
  try {
    ws.autoFilter = ref;
  } catch { /* older exceljs */ }
}

function numOrNa(v: RawNum) {
  return typeof v === "number" && isFinite(v) ? v : null;
}

export async function exportDashboardToExcel(data: DashboardLike): Promise<void> {
  if (!data || !data.company || !data.periods?.length) {
    throw new Error("No dashboard data to export yet. Wait for research to load.");
  }
  let mod: any;
  try {
    mod = await import("exceljs");
  } catch (e) {
    console.error("[ExportExcel] exceljs import failed:", e);
    throw new Error("Excel engine failed to load. Check connection and retry.");
  }
  const ExcelJS = mod.Workbook ? mod : (mod.default ?? mod);
  if (!ExcelJS?.Workbook) {
    throw new Error("Excel engine failed to initialise. Please retry.");
  }
  const wb = new ExcelJS.Workbook();
  wb.creator = "Finora";
  wb.created = new Date();
  wb.company = "Finora";

  const periods: string[] = data.raw_export?.periods?.length ? data.raw_export.periods : data.periods;
  const fileTicker = (data.company.ticker || "research").replace(/[^A-Z0-9.-]/gi, "");
  const safePeriod = (periods[periods.length - 1] || data.company.period || "latest").replace(/[^A-Za-z0-9-]/g, "");

  // ── COVER ──
  {
    const ws = wb.addWorksheet("Cover");
    ws.columns = [{ width: 28 }, { width: 70 }];
    addSheetTitle(ws, `${data.company.name} (${data.company.ticker})`, `Finora research export · ${data.company.period} · ${new Date().toLocaleDateString()}`);
    const rows: Array<[string, string | number]> = [
      ["Company", data.company.name],
      ["Ticker", data.company.ticker],
      ["Exchange", data.company.exchange],
      ["CIK", data.company.cik],
      ["Period", periods.join(", ")],
      ["Currency", data.company.currency || "USD"],
      ["Share price", data.valuation.market_data.price ?? "N/A"],
      ["Price date", data.valuation.market_data.price_date || ""],
      ["Price source", data.valuation.market_data.source || ""],
      ["Primary source", data.data_quality.primary_source],
      ["Metrics calculated", data.data_quality.metrics_calculated],
      ["Cross-verified", data.data_quality.cross_verified],
      ["Mismatches", data.data_quality.mismatches],
      ["Sources", data.data_quality.sources_count],
    ];
    rows.forEach(([k, v], i) => {
      const r = ws.getRow(4 + i);
      r.getCell(1).value = k;
      r.getCell(1).font = { bold: true, size: 10, name: "Consolas" };
      r.getCell(2).value = v as any;
      r.getCell(2).font = { size: 10, name: "Consolas" };
      if (k === "Share price" && typeof v === "number") r.getCell(2).numFmt = '"$"#,##0.00';
    });
    if (data.executive_summary?.executive_overview) {
      const r = ws.getRow(4 + rows.length + 1);
      r.getCell(1).value = "Executive overview";
      r.getCell(1).font = { bold: true, size: 10, name: "Consolas" };
      ws.mergeCells(`B${4 + rows.length + 1}:B${4 + rows.length + 4}`);
      const c = ws.getCell(`B${4 + rows.length + 1}`);
      c.value = data.executive_summary.executive_overview;
      c.alignment = { wrapText: true, vertical: "top" };
    }
  }

  // ── KPIs ──
  {
    const ws = wb.addWorksheet("KPIs");
    ws.columns = [{ width: 26 }, { width: 24 }, { width: 18 }];
    addSheetTitle(ws, "Key figures", "Raw numbers — fully calculable in Excel (USD unless noted)");
    ws.getRow(3).values = ["Metric", "Value (raw)", "Display"];
    styleHeader(ws.getRow(3));
    const raw = data.raw_export?.kpis;
    data.kpis.forEach((kpi, i) => {
      const r = ws.getRow(4 + i);
      const rawVal = raw?.find((x) => x.label.toLowerCase().includes(kpi.label.toLowerCase().split(" ")[0]))?.value ?? null;
      const v = numOrNa(rawVal);
      r.getCell(1).value = kpi.label;
      r.getCell(2).value = v;
      r.getCell(3).value = kpi.value;
      [1, 2, 3].forEach((c) => { r.getCell(c).font = { size: 10, name: "Consolas" }; });
      if (v !== null) {
        if (kpi.label.toLowerCase().includes("margin")) { r.getCell(2).value = v / 100; r.getCell(2).numFmt = "0.0%"; }
        else if (kpi.label.toLowerCase().includes("eps")) r.getCell(2).numFmt = '"$"#,##0.00';
        else r.getCell(2).numFmt = '"$"#,##0';
      }
    });
    freezeAndFilter(ws, `A3:C${3 + data.kpis.length}`);
  }

  // ── Generic statement writer (raw numbers = interactive) ──
  function writeStatement(sheetName: string, title: string, rawRows: Array<{ label: string; values: RawNum[] }> | undefined, dispRows: Array<{ label: string; values: string[] }>, isEpsSheet = false) {
    const ws = wb.addWorksheet(sheetName);
    const widths = [{ width: 32 }, ...periods.map(() => ({ width: 20 }))];
    ws.columns = widths as any;
    addSheetTitle(ws, title, "All values in USD (raw) — use SUM / AVERAGE / charts freely. EPS rows in $/share.");
    ws.getRow(3).values = ["Line item", ...periods];
    styleHeader(ws.getRow(3));
    const rows = (rawRows?.length ? rawRows : dispRows.map((d) => ({ label: d.label, values: d.values.map(() => null) })));
    rows.forEach((row, i) => {
      const r = ws.getRow(4 + i);
      r.getCell(1).value = row.label;
      r.getCell(1).font = { size: 10, name: "Consolas", bold: /revenue|assets|liabilities|equity|operating cash/i.test(row.label) };
      row.values.forEach((v, j) => {
        const c = r.getCell(2 + j);
        const n = numOrNa(v as any);
        if (n !== null) {
          c.value = n;
          c.numFmt = /eps/i.test(row.label) ? '"$"#,##0.00' : '"$"#,##0';
        } else {
          const disp = (dispRows[i]?.values?.[j] ?? "") as string;
          c.value = disp === "—" ? null : disp;
        }
        c.font = { size: 10, name: "Consolas" };
      });
    });
    freezeAndFilter(ws, `A3:${String.fromCharCode(65 + periods.length)}${3 + rows.length}`);
    void isEpsSheet;
  }

  writeStatement("Income Statement", "Income Statement (USD)", data.raw_export?.income, data.income_statement.rows);
  writeStatement("Balance Sheet", "Balance Sheet (USD)", data.raw_export?.balance, data.balance_sheet.rows);
  writeStatement("Cash Flow", "Cash Flow (USD)", data.raw_export?.cashflow, data.cash_flow.rows);

  // ── RATIOS (growth + profitability + liquidity + leverage + efficiency) ──
  {
    const ws = wb.addWorksheet("Ratios");
    ws.columns = [{ width: 30 }, { width: 20 }, { width: 24 }];
    addSheetTitle(ws, "Growth & Ratios", "Margins/growth stored as real % numbers (0.12 = 12%). Ratios as numbers.");
    ws.getRow(3).values = ["Metric", "Value (raw)", "Display"];
    styleHeader(ws.getRow(3));
    let rIdx = 4;
    const pushSection = (name: string) => {
      const r = ws.getRow(rIdx++);
      r.getCell(1).value = name;
      r.getCell(1).font = { bold: true, size: 10, name: "Consolas", color: { argb: BLUE } };
    };
    const pushNum = (label: string, raw: RawNum, disp: string, kind: "pct" | "ratio" | "currency" | "days" | "raw") => {
      const r = ws.getRow(rIdx++);
      r.getCell(1).value = label;
      const n = numOrNa(raw);
      if (n !== null) {
        if (kind === "pct") { r.getCell(2).value = n / 100; r.getCell(2).numFmt = "0.0%"; }
        else if (kind === "currency") { r.getCell(2).value = n; r.getCell(2).numFmt = '"$"#,##0'; }
        else if (kind === "ratio") { r.getCell(2).value = n; r.getCell(2).numFmt = '0.00"x"'; }
        else if (kind === "days") { r.getCell(2).value = n; r.getCell(2).numFmt = '0" days"'; }
        else { r.getCell(2).value = n; r.getCell(2).numFmt = "0.00"; }
      } else {
        r.getCell(2).value = disp === "—" ? null : disp;
      }
      r.getCell(3).value = disp;
      [1, 2, 3].forEach((c) => { r.getCell(c).font = { size: 10, name: "Consolas" }; });
    };

    const raw = data.raw_export;
    pushSection("GROWTH (%) — latest vs prior");
    data.growth.rows.forEach((g) => {
      const keys = Object.keys(raw?.growth_raw ?? {});
      const lastKey = keys[keys.length - 1];
      const guessId = g.label.toLowerCase().includes("revenue") ? "revenue_growth"
        : g.label.toLowerCase().includes("operating") ? "operating_income_growth"
        : g.label.toLowerCase().includes("eps") ? "eps_growth" : "net_income_growth";
      const rv = lastKey ? raw?.growth_raw?.[lastKey]?.[guessId] : null;
      pushNum(g.label, rv ?? null, g.values[g.values.length - 1] ?? "—", "pct");
    });
    const pctSet = new Set(["gross_margin","operating_margin","pretax_margin","net_margin","ebitda_margin","fcf_margin","ocf_margin","roa","roe","roic","roce","nwc_to_revenue","capex_intensity","buyback_to_fcf","cash_conversion","ocf_to_net_income"]);
    const ratioGroups: Array<[string, Array<{ metric: string; value: string }>]> = [
      ["PROFITABILITY & RETURNS", data.profitability],
      ["LIQUIDITY", data.liquidity],
      ["LEVERAGE", data.leverage],
      ["EFFICIENCY", data.efficiency],
      ["CAPITAL ALLOCATION", data.capital_allocation],
    ];
    const rawMaps = [raw?.profitability_raw, raw?.liquidity_raw, raw?.leverage_raw, raw?.efficiency_raw, raw?.capital_raw];
    ratioGroups.forEach(([name, arr], gi) => {
      pushSection(name);
      arr.forEach((m) => {
        const id = m.metric.toLowerCase().replace(/ /g, "_").replace(/'/g, "");
        const rv = (rawMaps[gi] as any)?.[id] ?? null;
        let kind: "pct" | "ratio" | "currency" | "days" | "raw" = "ratio";
        if (pctSet.has(id)) kind = "pct";
        else if (/net_working_capital|net_debt/.test(id) && !/to_|ratio/.test(id)) kind = "currency";
        else if (/days|cycle/.test(id)) kind = "days";
        pushNum(m.metric, rv, m.value, kind);
      });
    });
    if (data.dupont) {
      pushSection("DUPONT");
      const r = ws.getRow(rIdx++);
      r.getCell(1).value = `ROE ${data.dupont.roe} = ${data.dupont.calculation}`;
      r.getCell(1).font = { size: 9, name: "Consolas" };
    }
    freezeAndFilter(ws, `A3:C${rIdx}`);
  }

  // ── VALUATION ──
  {
    const ws = wb.addWorksheet("Valuation");
    ws.columns = [{ width: 24 }, { width: 20 }, { width: 34 }, { width: 44 }];
    addSheetTitle(ws, "Valuation", `Price ${data.valuation.market_data.price ?? "N/A"} on ${data.valuation.market_data.price_date || ""} · ${data.valuation.market_data.source} · ${data.valuation.market_data.alignment_status}`);
    ws.getRow(3).values = ["Multiple", "Value (raw)", "Display", "Formula / reason"];
    styleHeader(ws.getRow(3));
    data.valuation.metrics.forEach((m, i) => {
      const r = ws.getRow(4 + i);
      r.getCell(1).value = m.name;
      r.getCell(2).value = numOrNa(m.value);
      r.getCell(3).value = m.display_value;
      r.getCell(4).value = m.status === "calculated" ? `${m.formula} | ${m.calculation}` : m.reason;
      [1, 2, 3, 4].forEach((c) => { r.getCell(c).font = { size: 10, name: "Consolas" }; r.getCell(c).alignment = { wrapText: true, vertical: "middle" }; });
      if (typeof m.value === "number") {
        if (/price|cap|value/i.test(m.name)) r.getCell(2).numFmt = '"$"#,##0.00';
        else if (/yield/i.test(m.name)) { r.getCell(2).value = m.value / 100; r.getCell(2).numFmt = "0.00%"; }
        else r.getCell(2).numFmt = '0.00"x"';
      }
      r.height = 26;
    });
    freezeAndFilter(ws, `A3:D${3 + data.valuation.metrics.length}`);
  }

  // ── FORENSICS — every score + every indicator as a table ──
  {
    const ws = wb.addWorksheet("Forensics");
    ws.columns = [{ width: 34 }, { width: 20 }, { width: 22 }, { width: 50 }];
    addSheetTitle(ws, "Forensics — full evidence", "Piotroski 9 signals + Altman factors + Beneish 8 indices. 1 = pass.");
    ws.getRow(3).values = ["Indicator", "Score / value", "Status", "Note"];
    styleHeader(ws.getRow(3));
    let rIdx = 4;
    const fs = data.forensic_scores;
    const section = (t: string) => { const r = ws.getRow(rIdx++); r.getCell(1).value = t; r.getCell(1).font = { bold: true, size: 11, name: "Consolas", color: { argb: BLUE } }; };
    const line = (a: string, b: number | string | null, c: string, d: string) => {
      const r = ws.getRow(rIdx++);
      r.getCell(1).value = a;
      r.getCell(2).value = b as any;
      r.getCell(3).value = c;
      r.getCell(4).value = d;
      [1, 2, 3, 4].forEach((col) => { r.getCell(col).font = { size: 10, name: "Consolas" }; r.getCell(col).alignment = { wrapText: true, vertical: "middle" }; });
    };
    section("PIOTROSKI F-SCORE");
    if (fs?.piotroski && typeof fs.piotroski.score === "number") {
      line("Piotroski total", fs.piotroski.score, `${fs.piotroski.status} (0-3 WEAK, 4-6 MIXED, 7-9 STRONG)`, fs.piotroski.interpretation || "");
      (fs.piotroski.signals ?? []).forEach((s) => line(`  ${s.label}`, s.value, s.value === 1 ? "PASS +1" : "FAIL +0", `max ${s.max}`));
    } else line("Piotroski", "N/A", "insufficient data", "");
    section("ALTMAN Z-SCORE");
    if (fs?.altman && fs.altman.applicable !== false && typeof fs.altman.score === "number") {
      line("Altman Z total", Math.round(fs.altman.score * 100) / 100, `${fs.altman.zone || fs.altman.status} (${fs.altman.variant || ""})`, "Safe >2.99, Grey 1.81-2.99, Distress <1.81");
      (fs.altman.factors ?? []).forEach((f) => line(`  ${f.name}`, Math.round(f.value * 10000) / 10000, "", ""));
    } else line("Altman Z", "N/A", "not applicable", fs?.altman?.reason || "");
    section("BENEISH M-SCORE");
    if (fs?.beneish && fs.beneish.applicable !== false && typeof fs.beneish.score === "number") {
      line("Beneish M total", Math.round(fs.beneish.score * 100) / 100, `${fs.beneish.status}`, "Flag if > -1.78 (elevated manipulation signal)");
      (fs.beneish.indices ?? []).forEach((ix) => line(`  ${ix.name}`, Math.round(ix.value * 10000) / 10000, "", ""));
    } else line("Beneish M", "N/A", "needs 2 periods", fs?.beneish?.reason || "");
    freezeAndFilter(ws, `A3:D${rIdx}`);
  }

  // ── RISKS ──
  if (data.watch_items?.length || data.executive_summary?.watch_items?.length) {
    const ws = wb.addWorksheet("Risks");
    ws.columns = [{ width: 10 }, { width: 34 }, { width: 14 }, { width: 70 }];
    addSheetTitle(ws, "Watch items & red flags", "Every flagged item with severity + reason");
    ws.getRow(3).values = ["#", "Headline", "Severity", "Reason"];
    styleHeader(ws.getRow(3));
    const all = [
      ...(data.watch_items ?? []).map((w) => ({ h: w.headline || w.title, s: w.severity, r: w.reason })),
      ...(data.executive_summary?.watch_items ?? []).map((w) => ({ h: w.tag, s: w.tag, r: w.text })),
    ];
    all.forEach((w, i) => {
      const r = ws.getRow(4 + i);
      r.getCell(1).value = i + 1;
      r.getCell(2).value = w.h;
      r.getCell(3).value = String(w.s).toUpperCase();
      r.getCell(4).value = w.r;
      [1, 2, 3, 4].forEach((c) => { r.getCell(c).font = { size: 10, name: "Consolas" }; r.getCell(c).alignment = { wrapText: true, vertical: "top" }; });
      r.height = 30;
    });
    freezeAndFilter(ws, `A3:D${3 + all.length}`);
  }

  // ── MACRO + SOURCES ──
  if (data.macro_context?.available) {
    const ws = wb.addWorksheet("Macro");
    ws.columns = [{ width: 30 }, { width: 24 }, { width: 30 }];
    addSheetTitle(ws, "Macro context (FRED)", data.macro_context.attribution || "");
    ws.getRow(3).values = ["Indicator", "Value", "Date"];
    styleHeader(ws.getRow(3));
    data.macro_context.strip.forEach((m, i) => {
      const r = ws.getRow(4 + i);
      r.getCell(1).value = m.label; r.getCell(2).value = m.value; r.getCell(3).value = (m as any).date || "";
      [1, 2, 3].forEach((c) => { r.getCell(c).font = { size: 10, name: "Consolas" }; });
    });
  }
  {
    const ws = wb.addWorksheet("Sources");
    ws.columns = [{ width: 44 }, { width: 18 }, { width: 16 }, { width: 50 }];
    addSheetTitle(ws, "Source ledger", "Every figure traces to a source — click URL to open filing");
    ws.getRow(3).values = ["Source", "Trust tier", "Status", "URL"];
    styleHeader(ws.getRow(3));
    data.sources.forEach((s, i) => {
      const r = ws.getRow(4 + i);
      r.getCell(1).value = s.name;
      r.getCell(2).value = s.trust_tier === 1 ? "PRIMARY" : s.trust_tier === 2 ? "OFFICIAL" : "CORROBORATING";
      r.getCell(3).value = s.status;
      if (s.url) {
        r.getCell(4).value = { text: s.url.slice(0, 80), hyperlink: s.url } as any;
        r.getCell(4).font = { color: { argb: BLUE }, underline: true, size: 9, name: "Consolas" };
      }
      r.getCell(1).font = { size: 10, name: "Consolas" };
      r.getCell(2).font = { size: 10, name: "Consolas" };
      r.getCell(3).font = { size: 10, name: "Consolas" };
      r.getCell(4).alignment = { wrapText: true };
    });
    freezeAndFilter(ws, `A3:D${3 + data.sources.length}`);
  }

  // Print + style polish
  wb.eachSheet((ws: any) => {
    ws.sheetProperties.pageSetUpPr = { fitToPage: true };
    ws.pageSetup = { fitToWidth: 1, fitToHeight: 0, orientation: "landscape" };
  });

  const buf = await wb.xlsx.writeBuffer();
  const blob = new Blob([buf as any], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `Finora-${fileTicker}-${safePeriod}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}
