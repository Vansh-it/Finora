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

const DEFAULT: EvidenceEntry = {
  metric: "Return on Equity",
  value: "31.4%",
  formulaLabel: "Net Income / Average Shareholders' Equity",
  numerator: { label: "Net Income", value: "$93.7B" },
  denominator: { label: "Avg. Shareholders' Equity", value: "$298.4B" },
  source: "SEC 10-K",
  period: "FY2025",
  concept: "NetIncomeLoss",
  accession: "0000320193-25-000073",
  meaning: "For every $1 of average shareholder equity, the company generated approximately $0.31 of profit.",
};

const OVERRIDES: Record<string, Partial<EvidenceEntry>> = {
  Revenue: {
    metric: "Revenue",
    value: "$391.0B",
    formulaLabel: "Sum of reported net sales across all reportable segments",
    numerator: { label: "Products Revenue", value: "$300.2B" },
    denominator: { label: "Services Revenue", value: "$90.8B" },
    concept: "RevenueFromContractWithCustomerExcludingAssessedTax",
    meaning: "Total revenue recognized across product and services segments for the fiscal year.",
  },
  "Net Income": {
    metric: "Net Income",
    value: "$93.7B",
    formulaLabel: "Pretax Income − Income Tax Expense",
    numerator: { label: "Pretax Income", value: "$123.5B" },
    denominator: { label: "Income Tax Expense", value: "$29.7B" },
    concept: "NetIncomeLoss",
    meaning: "The company's bottom-line profit after all operating costs, interest and taxes.",
  },
  "Free Cash Flow": {
    metric: "Free Cash Flow",
    value: "$108.8B",
    formulaLabel: "Operating Cash Flow − Capital Expenditures",
    numerator: { label: "Operating Cash Flow", value: "$125.4B" },
    denominator: { label: "Capital Expenditures", value: "$16.6B" },
    concept: "NetCashProvidedByUsedInOperatingActivities",
    meaning: "Cash generated from operations after funding the capital investments needed to sustain the business.",
  },
  "Operating Margin": {
    metric: "Operating Margin",
    value: "31.5%",
    formulaLabel: "Operating Income / Revenue",
    numerator: { label: "Operating Income", value: "$123.2B" },
    denominator: { label: "Revenue", value: "$391.0B" },
    concept: "OperatingIncomeLoss",
    meaning: "For every $1 of revenue, approximately $0.315 remained as operating profit before interest and tax.",
  },
  ROIC: {
    metric: "ROIC",
    value: "56.2%",
    formulaLabel: "NOPAT / Invested Capital",
    numerator: { label: "NOPAT", value: "$96.4B" },
    denominator: { label: "Invested Capital", value: "$171.6B" },
    concept: "OperatingIncomeLoss (tax-adjusted)",
    meaning: "The company generates roughly $0.56 of after-tax operating profit for every $1 of invested capital.",
  },
  "Diluted EPS": {
    metric: "Diluted EPS",
    value: "$6.11",
    formulaLabel: "Net Income / Diluted Weighted Avg. Shares Outstanding",
    numerator: { label: "Net Income", value: "$93.7B" },
    denominator: { label: "Diluted Shares Outstanding", value: "15.34B" },
    concept: "EarningsPerShareDiluted",
    meaning: "Each diluted share represents approximately $6.11 of the company's annual net income.",
  },
};

export function getEvidence(metric: string): EvidenceEntry {
  const override = OVERRIDES[metric];
  if (!override) return { ...DEFAULT, metric };
  return { ...DEFAULT, ...override };
}
