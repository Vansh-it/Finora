/* Dummy financial data for Microsoft (FY2024, fiscal year ending June 30).
   Realistic magnitudes for frontend demonstration only — not investment advice. */

export interface SourceRef {
  doc: string;
  page: string;
}

export interface Verification {
  formula: string;
  values: { label: string; value: string }[];
  source: SourceRef;
  explanation: string;
}

export interface Kpi {
  id: string;
  label: string;
  value: string;
  change: { value: string; direction: 'up' | 'down' | 'flat' };
  spark: number[];
  verification: Verification;
}

export interface SeriesPoint {
  label: string;
  value: number;
}

export interface FinancialRow {
  label: string;
  y2022?: string;
  y2023: string;
  y2024: string;
}

export const company = {
  name: 'Microsoft Corporation',
  ticker: 'MSFT',
  exchange: 'NASDAQ',
  fiscalYear: 'FY2024',
  fiscalPeriod: 'Jul 2023 – Jun 2024',
  industry: 'Software & Cloud Infrastructure',
  sector: 'Information Technology',
  headquarters: 'Redmond, Washington, USA',
  cik: '0000789019',
  logoInitials: 'MS',
};

export const kpis: Kpi[] = [
  {
    id: 'revenue',
    label: 'Revenue',
    value: '$245.1B',
    change: { value: '+15.7%', direction: 'up' },
    spark: [56.5, 62.0, 61.9, 64.7, 65.6, 69.6, 70.0, 76.6],
    verification: {
      formula: 'Σ segment revenues (PBP + IC + MPC)',
      values: [
        { label: 'Productivity & Business Processes', value: '$77.7B' },
        { label: 'Intelligent Cloud', value: '$105.4B' },
        { label: 'More Personal Computing', value: '$62.0B' },
      ],
      source: { doc: 'Form 10-K FY2024 · Income Statement', page: 'p. 38' },
      explanation:
        'Revenue equals the sum of Microsoft’s three reportable segments as disclosed in the segment note. No adjustments are applied.',
    },
  },
  {
    id: 'net-income',
    label: 'Net Income',
    value: '$88.1B',
    change: { value: '+21.7%', direction: 'up' },
    spark: [16.4, 18.8, 21.9, 22.0, 24.7, 24.1, 23.5, 25.0],
    verification: {
      formula: 'Pre-tax income − income tax expense',
      values: [
        { label: 'Pre-tax income', value: '$116.4B' },
        { label: 'Income tax expense', value: '$28.3B' },
      ],
      source: { doc: 'Form 10-K FY2024 · Income Statement', page: 'p. 44' },
      explanation:
        'Net income is pre-tax income of $116.4B less income tax expense of $28.3B. The effective tax rate of 24.3% is within management’s guided range.',
    },
  },
  {
    id: 'op-income',
    label: 'Operating Income',
    value: '$109.4B',
    change: { value: '+23.6%', direction: 'up' },
    spark: [24.1, 27.0, 26.9, 28.0, 30.6, 31.7, 30.8, 32.7],
    verification: {
      formula: 'Gross profit − operating expenses',
      values: [
        { label: 'Gross profit', value: '$169.5B' },
        { label: 'Operating expenses', value: '$60.2B' },
      ],
      source: { doc: 'Form 10-K FY2024 · Income Statement', page: 'p. 43' },
      explanation:
        'Operating income is gross profit of $169.5B minus total operating expenses of $60.2B (R&D $29.5B, S&M $24.4B, G&A $6.3B).',
    },
  },
  {
    id: 'eps',
    label: 'Diluted EPS',
    value: '$11.80',
    change: { value: '+21.9%', direction: 'up' },
    spark: [2.17, 2.51, 2.94, 2.97, 3.32, 3.23, 3.16, 3.38],
    verification: {
      formula: 'Net income ÷ diluted weighted-average shares',
      values: [
        { label: 'Net income', value: '$88.1B' },
        { label: 'Diluted shares outstanding', value: '7,434M' },
      ],
      source: { doc: 'Form 10-K FY2024 · Income Statement', page: 'p. 44' },
      explanation:
        'Diluted EPS of $11.80 = $88.1B net income divided by 7,434 million diluted weighted-average shares.',
    },
  },
  {
    id: 'fcf',
    label: 'Free Cash Flow',
    value: '$74.2B',
    change: { value: '+20.3%', direction: 'up' },
    spark: [20.8, 21.1, 17.9, 21.4, 19.5, 19.8, 18.3, 18.9],
    verification: {
      formula: 'Operating cash flow − capital expenditures',
      values: [
        { label: 'Cash from operations', value: '$118.5B' },
        { label: 'Capital expenditures', value: '$44.3B' },
      ],
      source: { doc: 'Form 10-K FY2024 · Cash Flow Statement', page: 'p. 49' },
      explanation:
        'Free cash flow is cash from operations of $118.5B less purchases of property and equipment of $44.3B, matching management’s definition.',
    },
  },
  {
    id: 'gross-margin',
    label: 'Gross Margin',
    value: '69.2%',
    change: { value: '+0.9 pts', direction: 'up' },
    spark: [68.6, 68.4, 69.4, 69.9, 69.6, 69.5, 69.4, 70.0],
    verification: {
      formula: '(Revenue − cost of revenue) ÷ revenue',
      values: [
        { label: 'Revenue', value: '$245.1B' },
        { label: 'Cost of revenue', value: '$75.6B' },
      ],
      source: { doc: 'Form 10-K FY2024 · Income Statement', page: 'p. 42' },
      explanation:
        'Gross margin of 69.2% = ($245.1B − $75.6B) ÷ $245.1B. Expansion reflects the growing mix of high-margin cloud services.',
    },
  },
];

export const quarterlyRevenue: SeriesPoint[] = [
  { label: 'Q1 FY24', value: 56.5 },
  { label: 'Q2 FY24', value: 62.0 },
  { label: 'Q3 FY24', value: 61.9 },
  { label: 'Q4 FY24', value: 64.7 },
  { label: 'Q1 FY25', value: 65.6 },
  { label: 'Q2 FY25', value: 69.6 },
  { label: 'Q3 FY25', value: 70.0 },
  { label: 'Q4 FY25', value: 76.6 },
];

export const quarterlyOperatingIncome: SeriesPoint[] = [
  { label: 'Q1 FY24', value: 26.9 },
  { label: 'Q2 FY24', value: 27.0 },
  { label: 'Q3 FY24', value: 27.6 },
  { label: 'Q4 FY24', value: 27.9 },
  { label: 'Q1 FY25', value: 30.6 },
  { label: 'Q2 FY25', value: 31.7 },
  { label: 'Q3 FY25', value: 30.8 },
  { label: 'Q4 FY25', value: 32.7 },
];

export const revenueMix = [
  { label: 'Intelligent Cloud', value: 105.4 },
  { label: 'Productivity & Business', value: 77.7 },
  { label: 'More Personal Computing', value: 62.0 },
];

export const marginsByYear: SeriesPoint[] = [
  { label: 'FY21', value: 69.6 },
  { label: 'FY22', value: 68.4 },
  { label: 'FY23', value: 68.9 },
  { label: 'FY24', value: 69.2 },
];

export const incomeStatement: FinancialRow[] = [
  { label: 'Revenue', y2022: '198.3', y2023: '211.9', y2024: '245.1' },
  { label: 'Cost of revenue', y2022: '(62.7)', y2023: '(65.9)', y2024: '(75.6)' },
  { label: 'Gross profit', y2022: '135.6', y2023: '146.0', y2024: '169.5' },
  { label: 'Research & development', y2022: '(24.5)', y2023: '(27.2)', y2024: '(29.5)' },
  { label: 'Sales & marketing', y2022: '(21.8)', y2023: '(22.5)', y2024: '(24.4)' },
  { label: 'General & administrative', y2022: '(5.9)', y2023: '(7.8)', y2024: '(6.3)' },
  { label: 'Operating income', y2022: '83.4', y2023: '88.5', y2024: '109.4' },
  { label: 'Other income (expense), net', y2022: '1.2', y2023: '2.7', y2024: '7.0' },
  { label: 'Income before income taxes', y2022: '84.6', y2023: '91.2', y2024: '116.4' },
  { label: 'Income tax expense', y2022: '(11.9)', y2023: '(18.8)', y2024: '(28.3)' },
  { label: 'Net income', y2022: '72.7', y2023: '72.4', y2024: '88.1' },
  { label: 'Diluted EPS ($)', y2022: '9.65', y2023: '9.68', y2024: '11.80' },
];

export const balanceSheet: FinancialRow[] = [
  { label: 'Cash & cash equivalents', y2023: '34.7', y2024: '18.3' },
  { label: 'Short-term investments', y2023: '76.6', y2024: '57.2' },
  { label: 'Accounts receivable, net', y2023: '48.7', y2024: '57.0' },
  { label: 'Property & equipment, net', y2023: '95.5', y2024: '102.9' },
  { label: 'Goodwill', y2023: '63.2', y2024: '67.5' },
  { label: 'Total assets', y2023: '411.9', y2024: '512.1' },
  { label: 'Total liabilities', y2023: '205.8', y2024: '243.6' },
  { label: 'Long-term debt', y2023: '41.9', y2024: '44.1' },
  { label: 'Stockholders’ equity', y2023: '206.2', y2024: '268.5' },
];

export const cashFlow: FinancialRow[] = [
  { label: 'Cash from operations', y2023: '87.6', y2024: '118.5' },
  { label: 'Purchases of property & equipment', y2023: '(28.1)', y2024: '(44.5)' },
  { label: 'Free cash flow', y2023: '61.7', y2024: '74.2' },
  { label: 'Dividends paid', y2023: '(19.8)', y2024: '(22.3)' },
  { label: 'Common stock repurchases', y2023: '(19.4)', y2024: '(25.6)' },
  { label: 'Net cash from financing', y2023: '(57.7)', y2024: '(68.4)' },
  { label: 'Effect of FX on cash', y2023: '(0.3)', y2024: '(0.4)' },
];

export const growthByYear = [
  { metric: 'Revenue', y2022: '18.0%', y2023: '6.9%', y2024: '15.7%' },
  { metric: 'Operating income', y2022: '19.3%', y2023: '6.1%', y2024: '23.6%' },
  { metric: 'Net income', y2022: '18.6%', y2023: '-0.4%', y2024: '21.7%' },
  { metric: 'Diluted EPS', y2022: '19.9%', y2023: '0.3%', y2024: '21.9%' },
  { metric: 'Free cash flow', y2022: '10.9%', y2023: '-1.4%', y2024: '20.3%' },
  { metric: 'Gross margin (pts)', y2022: '-0.7', y2023: '+0.5', y2024: '+0.3' },
];

export const profitability = [
  { metric: 'Gross margin', value: '69.2%', note: 'Cloud mix shift' },
  { metric: 'Operating margin', value: '44.6%', note: 'OpEx leverage' },
  { metric: 'Net margin', value: '35.9%', note: 'Record high' },
  { metric: 'Return on equity (ROE)', value: '35.4%', note: 'Buybacks + income' },
  { metric: 'Return on invested capital (ROIC)', value: '31.2%', note: 'After-tax basis' },
  { metric: 'Return on assets (ROA)', value: '17.2%', note: 'Asset base growth' },
];

export const sources = [
  {
    id: 's1',
    name: 'Annual Report (Form 10-K) · FY2024',
    meta: 'SEC EDGAR · filed Jul 30, 2024 · 112 pages',
    pages: 'Income statement p.42–45 · Balance sheet p.46–47 · Cash flow p.48–50',
    status: 'Parsed & verified',
  },
  {
    id: 's2',
    name: 'Q4 FY2025 Earnings Press Release',
    meta: 'Investor Relations · Jul 2025',
    pages: 'Segment revenue table · Guidance commentary',
    status: 'Parsed & verified',
  },
  {
    id: 's3',
    name: '10-K MD&A — Segment Discussion',
    meta: 'Form 10-K FY2024 · p.30–40',
    pages: 'Segment revenue · Gross margin drivers',
    status: 'Parsed & verified',
  },
  {
    id: 's4',
    name: 'Statement of Stockholders’ Equity',
    meta: 'Form 10-K FY2024 · p.51–52',
    pages: 'Dividends · Share repurchases · Retained earnings',
    status: 'Parsed & verified',
  },
];

export const execSummary = {
  headline:
    'Microsoft delivered a record fiscal 2024, driven by double-digit growth across every segment and accelerating cloud momentum.',
  body: 'Revenue grew 15.7% to $245.1B with operating income up 23.6% to $109.4B — margin expansion outpacing top-line growth for the third consecutive year. Intelligent Cloud remains the growth engine, contributing $105.4B of revenue. The balance sheet remains fortress-grade: $75.5B of cash and short-term investments against $46.6B of total debt, while free cash flow reached $74.2B.',
  keyFindings: [
    {
      title: 'Cloud acceleration',
      body: 'Intelligent Cloud grew 20% to $105.4B; Azure and other cloud services grew 24% in constant currency, re-accelerating through the year.',
    },
    {
      title: 'Margin expansion',
      body: 'Operating margin expanded 280 bps to 44.6% on disciplined hiring and cloud efficiency gains; gross margin held above 69%.',
    },
    {
      title: 'AI monetization',
      body: 'AI services contributed over 12 points of Azure growth, with Copilot adoption broadening across M365 and GitHub.',
    },
    {
      title: 'Shareholder returns',
      body: '$47.9B returned via dividends and buybacks — the 19th consecutive year of dividend increases.',
    },
  ],
  growthDrivers: [
    'Azure & AI services demand (AI services >12 pts of Azure growth)',
    'Commercial cloud backlog growing double-digits, securing forward revenue',
    'Operating leverage from cloud efficiency and AI infrastructure utilization',
    'Office 365 commercial seats + M365 Copilot attach driving ARPU expansion',
  ],
  risks: [
    'Capital intensity of AI datacenter buildout pressures near-term FCF conversion',
    'Macro-softening in enterprise IT budgets could temper seat and workload growth',
    'Regulatory scrutiny of cloud bundling and AI partnerships across the EU and US',
  ],
};

export const ratioExplanations: Record<string, string> = {
  'Gross margin': 'Revenue minus cost of revenue, divided by revenue.',
  'Operating margin': 'Operating income divided by revenue.',
  'Net margin': 'Net income divided by revenue.',
  'Return on equity (ROE)': 'Net income divided by average stockholders’ equity.',
  'Return on invested capital (ROIC)': 'After-tax operating income divided by average invested capital (debt + equity).',
  'Return on assets (ROA)': 'Net income divided by average total assets.',
};

export const chatThread = [
  {
    role: 'user' as const,
    text: 'What drove the acceleration in Azure growth this year?',
  },
  {
    role: 'assistant' as const,
    text: 'Azure and other cloud services grew 24% in constant currency in FY2025, with AI services contributing more than 12 points of that growth. Management credited expanded AI capacity, Copilot adoption, and enterprise migration workloads. Source: Q4 FY2025 press release, segment discussion.',
    cites: ['Q4 FY2025 Press Release'],
  },
  {
    role: 'user' as const,
    text: 'How does free cash flow conversion look versus last year?',
  },
  {
    role: 'assistant' as const,
    text: 'FCF improved 20.3% to $74.2B, though cash conversion (FCF ÷ net income) eased to ~84% from ~85% last year as capex stepped up to $44.5B for AI infrastructure. Operating cash flow grew 35.3% to $118.5B. Source: 10-K FY2024, cash flow statement p.49.',
    cites: ['10-K FY2024 · p.49'],
  },
];
