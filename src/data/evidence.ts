/**
 * Dynamic evidence builder.
 *
 * Instead of returning hardcoded Apple demo data, this module constructs
 * evidence entries from the live DashboardData payload so the Evidence
 * Drawer always shows real company metrics, formulas, and SEC sources.
 */

export interface EvidenceEntry {
  metric: string;
  value: string;
  formulaLabel: string;
  numerator: { label: string; value: string };
  denominator: { label: string; value: string };
  source: string;
  period: string;
  concept: string;
  accession: string;
  meaning: string;
}

/* ── Minimal type subset so we avoid importing the full DashboardData type ── */
interface DashboardDataLike {
  company: { ticker: string; name: string; period: string; cik: string };
  periods: string[];
  kpis: Array<{ id: string; label: string; value: string }>;
  income_statement: {
    columns: string[];
    rows: Array<{ label: string; values: string[]; strong?: boolean }>;
  };
  balance_sheet: {
    columns: string[];
    rows: Array<{ label: string; values: string[]; strong?: boolean }>;
  };
  cash_flow: {
    columns: string[];
    rows: Array<{ label: string; values: string[]; strong?: boolean }>;
  };
  growth: {
    columns: string[];
    rows: Array<{ label: string; values: string[]; strong?: boolean }>;
  };
  profitability: Array<{ metric: string; value: string; note: string }>;
  liquidity: Array<{ metric: string; value: string; note: string }>;
  leverage: Array<{ metric: string; value: string; note: string }>;
  efficiency: Array<{ metric: string; value: string; note: string }>;
  capital_allocation: Array<{ metric: string; value: string; note: string }>;
  valuation: {
    metrics: Array<{
      metric_id: string;
      name: string;
      display_value: string;
      formula: string;
      inputs: string[];
      calculation: string;
      reason: string;
    }>;
  };
  sources: Array<{
    id: string;
    name: string;
    url: string;
    trust_tier: number;
    period: string;
  }>;
}

/* ── Formula / concept / meaning metadata for well-known metrics ────────── */
const METRIC_META: Record<
  string,
  {
    formulaLabel: string;
    numeratorLabel: string;
    denominatorLabel: string;
    concept: string;
    meaning: string;
  }
> = {
  /* KPI card metrics */
  Revenue: {
    formulaLabel: "Sum of reported net sales across all reportable segments",
    numeratorLabel: "Product Revenue",
    denominatorLabel: "Services Revenue",
    concept: "RevenueFromContractWithCustomerExcludingAssessedTax",
    meaning: "Total revenue recognized across product and services segments for the fiscal year.",
  },
  "Net Income": {
    formulaLabel: "Pretax Income − Income Tax Expense",
    numeratorLabel: "Pretax Income",
    denominatorLabel: "Income Tax Expense",
    concept: "NetIncomeLoss",
    meaning: "The company's bottom-line profit after all operating costs, interest and taxes.",
  },
  "Operating Income": {
    formulaLabel: "Revenue − Cost of Revenue − Operating Expenses",
    numeratorLabel: "Gross Profit",
    denominatorLabel: "Operating Expenses",
    concept: "OperatingIncomeLoss",
    meaning: "Profit from core business operations before interest and taxes.",
  },
  "EPS (Diluted)": {
    formulaLabel: "Net Income / Diluted Weighted Avg. Shares Outstanding",
    numeratorLabel: "Net Income",
    denominatorLabel: "Diluted Shares Outstanding",
    concept: "EarningsPerShareDiluted",
    meaning: "Each diluted share represents the company's annual net income on a per-share basis.",
  },
  "Free Cash Flow": {
    formulaLabel: "Operating Cash Flow − Capital Expenditures",
    numeratorLabel: "Operating Cash Flow",
    denominatorLabel: "Capital Expenditures",
    concept: "NetCashProvidedByUsedInOperatingActivities",
    meaning: "Cash generated from operations after funding the capital investments needed to sustain the business.",
  },
  "Gross Margin": {
    formulaLabel: "Gross Profit / Revenue × 100",
    numeratorLabel: "Gross Profit",
    denominatorLabel: "Revenue",
    concept: "GrossProfitLoss",
    meaning: "The percentage of revenue left after subtracting the direct cost of producing goods or services.",
  },
  /* Income statement rows */
  "Cost of Revenue": {
    formulaLabel: "Direct costs attributable to the production of goods/services",
    numeratorLabel: "Direct Materials",
    denominatorLabel: "Direct Labor & Overhead",
    concept: "CostOfGoodsAndServicesSold",
    meaning: "All direct costs associated with producing the company's products or delivering services.",
  },
  "Gross Profit": {
    formulaLabel: "Revenue − Cost of Revenue",
    numeratorLabel: "Revenue",
    denominatorLabel: "Cost of Revenue",
    concept: "GrossProfitLoss",
    meaning: "Revenue remaining after covering the direct costs of producing goods or services.",
  },
  "Pretax Income": {
    formulaLabel: "Operating Income − Interest Expense ± Other Income",
    numeratorLabel: "Operating Income",
    denominatorLabel: "Interest & Other",
    concept: "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    meaning: "Profit before the company pays income taxes.",
  },
  "Basic EPS": {
    formulaLabel: "Net Income / Basic Weighted Avg. Shares Outstanding",
    numeratorLabel: "Net Income",
    denominatorLabel: "Basic Shares Outstanding",
    concept: "EarningsPerShareBasic",
    meaning: "Earnings per share calculated using basic (non-diluted) share count.",
  },
  "Diluted EPS": {
    formulaLabel: "Net Income / Diluted Weighted Avg. Shares Outstanding",
    numeratorLabel: "Net Income",
    denominatorLabel: "Diluted Shares Outstanding",
    concept: "EarningsPerShareDiluted",
    meaning: "Earnings per share adjusted for potential dilution from stock options, convertible securities, etc.",
  },
  /* Balance sheet rows */
  "Cash & Equivalents": {
    formulaLabel: "Cash on hand plus highly liquid short-term investments",
    numeratorLabel: "Cash on Hand",
    denominatorLabel: "Money Market Funds",
    concept: "CashAndCashEquivalentsAtCarryingValue",
    meaning: "The most liquid assets the company holds, readily available for operations.",
  },
  "Short-term Investments": {
    formulaLabel: "Marketable securities maturing within 12 months",
    numeratorLabel: "Treasury Securities",
    denominatorLabel: "Corporate Bonds",
    concept: "ShortTermInvestments",
    meaning: "Investments the company expects to convert to cash within one year.",
  },
  "Accounts Receivable": {
    formulaLabel: "Amounts owed by customers for goods/services delivered",
    numeratorLabel: "Trade Receivables",
    denominatorLabel: "Allowance for Doubtful Accounts",
    concept: "AccountsReceivableNetCurrent",
    meaning: "Money customers owe the company for products or services already delivered.",
  },
  "Current Assets": {
    formulaLabel: "Cash + Short-term Investments + Receivables + Inventory + Other",
    numeratorLabel: "Liquid Assets",
    denominatorLabel: "Other Current Assets",
    concept: "AssetsCurrent",
    meaning: "All assets expected to be converted to cash or used within one year.",
  },
  "Total Assets": {
    formulaLabel: "Current Assets + Non-current Assets",
    numeratorLabel: "Current Assets",
    denominatorLabel: "Property, Plant & Equipment + Other",
    concept: "Assets",
    meaning: "Everything the company owns that has value — the complete asset base.",
  },
  "Current Liabilities": {
    formulaLabel: "Debts and obligations due within 12 months",
    numeratorLabel: "Accounts Payable",
    denominatorLabel: "Short-term Debt & Other",
    concept: "LiabilitiesCurrent",
    meaning: "Financial obligations the company must settle within the next year.",
  },
  "Total Liabilities": {
    formulaLabel: "Current Liabilities + Non-current Liabilities",
    numeratorLabel: "Current Liabilities",
    denominatorLabel: "Long-term Debt & Other",
    concept: "Liabilities",
    meaning: "Everything the company owes — the total of all debts and obligations.",
  },
  "Long-term Debt": {
    formulaLabel: "Borrowings due after 12 months",
    numeratorLabel: "Corporate Bonds",
    denominatorLabel: "Term Loans",
    concept: "LongTermDebtNoncurrent",
    meaning: "Debt obligations that mature beyond one year.",
  },
  "Short-term Debt": {
    formulaLabel: "Borrowings due within 12 months",
    numeratorLabel: "Commercial Paper",
    denominatorLabel: "Current Portion of Long-term Debt",
    concept: "ShortTermBorrowings",
    meaning: "Debt obligations that must be repaid within the next year.",
  },
  "Shareholders' Equity": {
    formulaLabel: "Total Assets − Total Liabilities",
    numeratorLabel: "Total Assets",
    denominatorLabel: "Total Liabilities",
    concept: "StockholdersEquity",
    meaning: "The net value belonging to shareholders — assets minus all debts.",
  },
  /* Cash flow rows */
  "Operating Cash Flow": {
    formulaLabel: "Cash generated from core business operations",
    numeratorLabel: "Net Income",
    denominatorLabel: "Adjustments (D&A, Working Capital, etc.)",
    concept: "NetCashProvidedByUsedInOperatingActivities",
    meaning: "Cash the company generated (or used) in its day-to-day business operations.",
  },
  "Capital Expenditures": {
    formulaLabel: "Cash spent on property, plant, and equipment",
    numeratorLabel: "PP&E Purchases",
    denominatorLabel: "Other CapEx",
    concept: "PaymentsToAcquirePropertyPlantAndEquipment",
    meaning: "Cash invested in long-term assets to maintain or grow the business.",
  },
  "Investing Cash Flow": {
    formulaLabel: "Cash flows from investment activities",
    numeratorLabel: "CapEx",
    denominatorLabel: "Acquisitions & Investments",
    concept: "NetCashProvidedByUsedInInvestingActivities",
    meaning: "Net cash used for or generated from investment activities like buying/selling assets.",
  },
  "Financing Cash Flow": {
    formulaLabel: "Cash flows from financing activities",
    numeratorLabel: "Debt Issuance/Repayment",
    denominatorLabel: "Equity Issuance/Buybacks & Dividends",
    concept: "NetCashProvidedByUsedInFinancingActivities",
    meaning: "Net cash from debt and equity transactions — borrowing, repaying, issuing stock, paying dividends.",
  },
};

/* ── Growth metric labels ── */
const GROWTH_META: Record<string, { concept: string; meaning: string }> = {
  "Revenue Growth": {
    concept: "RevenueFromContractWithCustomerExcludingAssessedTax (YoY)",
    meaning: "Year-over-year percentage change in total revenue.",
  },
  "Operating Income Growth": {
    concept: "OperatingIncomeLoss (YoY)",
    meaning: "Year-over-year percentage change in operating income.",
  },
  "Net Income Growth": {
    concept: "NetIncomeLoss (YoY)",
    meaning: "Year-over-year percentage change in net income.",
  },
  "EPS Growth": {
    concept: "EarningsPerShareDiluted (YoY)",
    meaning: "Year-over-year percentage change in diluted earnings per share.",
  },
};

/* ── Lookup helpers ──────────────────────────────────────────────────────── */

/** Find the primary SEC source from the sources array. */
function primarySource(data: DashboardDataLike): {
  name: string;
  period: string;
  accession: string;
} {
  const sec = data.sources.find(
    (s) =>
      s.name.toLowerCase().includes("sec") ||
      s.name.toLowerCase().includes("10-k") ||
      s.name.toLowerCase().includes("10-q") ||
      s.trust_tier === 1
  );
  if (sec) {
    // Extract accession from URL if available
    const accMatch = sec.url.match(/\/(\d{10,}-\d{2}-\d{6})\//);
    return {
      name: sec.name,
      period: sec.period || data.company.period,
      accession: accMatch ? accMatch[1] : data.company.cik,
    };
  }
  return {
    name: "SEC XBRL",
    period: data.company.period,
    accession: data.company.cik || "N/A",
  };
}

/** Find a row value from a statement by label. */
function statementValue(
  stmt: { rows: Array<{ label: string; values: string[] }> },
  columns: string[],
  label: string,
  latestIdx: number
): string {
  const row = stmt.rows.find((r) => r.label === label);
  if (!row) return "—";
  return row.values[latestIdx] || "—";
}

/* ── Main public function ────────────────────────────────────────────────── */

export function getEvidence(
  metric: string,
  data?: DashboardDataLike | null
): EvidenceEntry {
  // Fallback for when data isn't loaded yet
  if (!data) {
    return {
      metric,
      value: "—",
      formulaLabel: "Data not yet loaded",
      numerator: { label: "—", value: "—" },
      denominator: { label: "—", value: "—" },
      source: "SEC XBRL",
      period: "—",
      concept: "—",
      accession: "—",
      meaning: "Load a research analysis to see real evidence for this metric.",
    };
  }

  const src = primarySource(data);
  const latestIdx = Math.max(0, data.periods.length - 1);
  const latestPeriod = data.periods[latestIdx] || data.company.period;

  // Try to find value from KPIs first (labels match exactly)
  const kpi = data.kpis.find((k) => k.label === metric);

  // Try to find from statement rows
  const stmtRows = [
    ...data.income_statement.rows,
    ...data.balance_sheet.rows,
    ...data.cash_flow.rows,
  ];
  const stmtRow = stmtRows.find((r) => r.label === metric);

  // Try to find from analytics sections
  const analyticsMetric =
    data.profitability.find((p) => p.metric === metric) ||
    data.liquidity.find((l) => l.metric === metric) ||
    data.leverage.find((l) => l.metric === metric) ||
    data.efficiency.find((e) => e.metric === metric) ||
    data.capital_allocation.find((c) => c.metric === metric);

  // Try to find from growth rows
  const growthRow = data.growth.rows.find((r) => r.label === metric);

  // Try valuation metrics (by name)
  const valMetric = data.valuation.metrics.find((m) => m.name === metric);

  // Resolve the displayed value
  let value = "—";
  if (kpi) {
    value = kpi.value;
  } else if (stmtRow) {
    value = stmtRow.values[latestIdx] || "—";
  } else if (analyticsMetric) {
    value = analyticsMetric.value;
  } else if (growthRow) {
    value = growthRow.values[growthRow.values.length - 1] || "—";
  } else if (valMetric) {
    value = valMetric.display_value;
  }

  // Resolve formula metadata
  const meta = METRIC_META[metric];
  const growthMeta = GROWTH_META[metric];

  let formulaLabel: string;
  let numeratorLabel: string;
  let numeratorValue: string;
  let denominatorLabel: string;
  let denominatorValue: string;
  let concept: string;
  let meaning: string;

  if (valMetric) {
    // Valuation metric — use its rich formula data
    formulaLabel = valMetric.formula || `${metric} calculation`;
    const inputs = valMetric.inputs || [];
    numeratorLabel = inputs[0] || "Numerator";
    numeratorValue = inputs[0] ? value : "—";
    denominatorLabel = inputs[1] || "Denominator";
    denominatorValue = inputs[1] ? valMetric.calculation : "—";
    concept = valMetric.metric_id;
    meaning =
      valMetric.reason ||
      `${metric} calculated from the company's financial data and current market price.`;
  } else if (meta) {
    // Known metric — use the curated metadata
    formulaLabel = meta.formulaLabel;
    numeratorLabel = meta.numeratorLabel;
    denominatorLabel = meta.denominatorLabel;
    concept = meta.concept;
    meaning = meta.meaning;

    // Resolve numerator/denominator values from statement data
    const numRow = stmtRows.find((r) => r.label === meta.numeratorLabel);
    const denRow = stmtRows.find((r) => r.label === meta.denominatorLabel);
    numeratorValue = numRow
      ? numRow.values[latestIdx] || value
      : value;
    denominatorValue = denRow
      ? denRow.values[latestIdx] || "—"
      : "—";
  } else if (growthMeta) {
    // Growth metric
    formulaLabel = `Year-over-year percentage change`;
    numeratorLabel = "Current Period";
    numeratorValue = value;
    denominatorLabel = "Previous Period";
    denominatorValue = "—";
    concept = growthMeta.concept;
    meaning = growthMeta.meaning;
  } else {
    // Generic fallback — try to construct something useful
    formulaLabel = `${metric}`;
    numeratorLabel = "—";
    numeratorValue = "—";
    denominatorLabel = "—";
    denominatorValue = "—";
    concept = metric.toLowerCase().replace(/\s+/g, "_");
    meaning = `${metric} for ${data.company.name} (${data.company.ticker}). Value sourced from the company's SEC filings.`;
  }

  return {
    metric,
    value,
    formulaLabel,
    numerator: { label: numeratorLabel, value: numeratorValue },
    denominator: { label: denominatorLabel, value: denominatorValue },
    source: src.name,
    period: src.period || latestPeriod,
    concept,
    accession: src.accession,
    meaning,
  };
}
