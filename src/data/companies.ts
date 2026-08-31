export interface StatementRow {
  label: string;
  values: (number | null)[];
  isTotal?: boolean;
  unit?: "currency" | "percent" | "number";
}

export interface CompanyData {
  ticker: string;
  name: string;
  exchange: string;
  sector: string;
  fiscalYear: string;
  price: number;
  priceChange: number;
  marketCap: string;
  enterpriseValue: string;
  years: string[];
  kpis: {
    label: string;
    value: string;
    delta?: string;
    deltaTone?: "pos" | "neg" | "neutral";
    highlighted?: boolean;
    unavailable?: boolean;
  }[];
  quality: {
    sourceType: string;
    metrics: number;
    sources: number;
    crossVerified: number;
    mismatches: number;
  };
  incomeStatement: StatementRow[];
  balanceSheet: StatementRow[];
  cashFlow: StatementRow[];
  growth: { label: string; value: string; tone: "pos" | "neg" }[];
  profitability: { label: string; value: string }[];
  valuation: {
    price: string;
    marketCap: string;
    enterpriseValue: string;
    multiples: { label: string; value: string; unavailable?: boolean; note?: string }[];
  };
  executiveAnalysis: {
    paragraphs: string[];
    highlights: string[];
    watch: { tag: "WATCH" | "STRENGTH" | "RISK"; text: string }[];
  };
  sources: {
    id: string;
    name: string;
    trust: "PRIMARY" | "OFFICIAL" | "CORROBORATING";
    period: string;
    usedFor: string;
    status: "VERIFIED" | "CROSS-VERIFIED";
  }[];
  fcfBridge: { operatingCF: string; capex: string; fcf: string };
  chartData: { year: string; revenue: number; netIncome: number }[];
}
