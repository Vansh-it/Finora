export const navLinks = [
  { label: 'Product', href: '/#features' },
  { label: 'How it works', href: '/#how-it-works' },
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Chat', href: '/chat' },
];

export interface HeroExample {
  label: string;
  company: string;
  from: string;
  to: string;
  objective: string;
}

export const heroExamples: HeroExample[] = [
  {
    label: 'Research any company',
    company: 'Microsoft',
    from: '',
    to: '',
    objective: 'Calculate key financial metrics and summarize performance.',
  },
  {
    label: 'Analyze NVIDIA',
    company: 'Nvidia',
    from: '',
    to: '',
    objective: 'Analyze NVIDIA revenue and margin trends.',
  },
  {
    label: 'Apple financial dashboard',
    company: 'Apple',
    from: '',
    to: '',
    objective: 'Generate a comprehensive financial dashboard for Apple.',
  },
];

export type FeatureIcon = 'calc' | 'shield' | 'doc' | 'grid' | 'export' | 'chat';

export const features: { title: string; body: string; icon: FeatureIcon }[] = [
  {
    title: 'Institutional-grade metrics',
    body: 'ROE, ROIC, FCF conversion, margins, and growth — computed from raw filings with standard definitions, not estimates.',
    icon: 'calc',
  },
  {
    title: 'Every number verified',
    body: 'Each metric links back to the exact source document, page, and raw values used in the calculation.',
    icon: 'shield',
  },
  {
    title: 'Executive summaries',
    body: 'A professional readout of key findings, growth drivers, and risks — generated from the underlying data.',
    icon: 'doc',
  },
  {
    title: 'Full financial dashboards',
    body: 'Income statement, balance sheet, cash flow, growth, and profitability — in one interactive, shareable view.',
    icon: 'grid',
  },
  {
    title: 'Export-ready reports',
    body: 'One click exports a clean, print-ready PDF dashboard you can attach to your research notes.',
    icon: 'export',
  },
  {
    title: 'Ask questions',
    body: 'Chat with the research: every answer is grounded in the filings it came from, with source chips you can check.',
    icon: 'chat',
  },
];

export const steps = [
  {
    index: '01',
    title: 'Ask',
    body: 'Type a company name, ask a question, or just say hello — Finora figures out the rest.',
  },
  {
    index: '02',
    title: 'Research',
    body: 'Finora locates annual and quarterly reports from public filings and financial databases.',
  },
  {
    index: '03',
    title: 'Verify',
    body: 'Every metric is recomputed from raw statement values, with sources and page numbers attached.',
  },
  {
    index: '04',
    title: 'Export',
    body: 'Review the dashboard, ask follow-up questions, and export a professional PDF.',
  },
];

export type TrustIcon = 'shield' | 'calc' | 'doc' | 'export';

export const trustCards: { title: string; body: string; icon: TrustIcon }[] = [
  {
    title: 'Source Verification',
    body: 'Every metric links to the exact SEC document, page, and raw values it was computed from — nothing is estimated.',
    icon: 'shield',
  },
  {
    title: 'Institutional Metrics',
    body: 'ROE, ROIC, FCF conversion, margins, and growth — computed with standard, disclosed definitions analysts already use.',
    icon: 'calc',
  },
  {
    title: 'Explainable Calculations',
    body: 'Each KPI opens its formula, its inputs, and a plain-English walkthrough of exactly how the number is derived.',
    icon: 'doc',
  },
  {
    title: 'Downloadable Reports',
    body: 'Export print-ready PDF dashboards with the full verification trail embedded — ready for notes, desks, or clients.',
    icon: 'export',
  },
];

export const faqs = [
  {
    q: 'Where does the financial data come from?',
    a: 'Finora reads public filings — annual and quarterly reports (10-K / 10-Q), earnings press releases, and SEC EDGAR disclosures. Every figure is tied to the document and page it came from.',
  },
  {
    q: 'How does verification work?',
    a: 'Each metric is recomputed from the raw statement values. The verification panel shows the formula, the exact inputs, the source document, and the page number, so you can audit any number in seconds.',
  },
  {
    q: 'Is this investment advice?',
    a: 'No. Finora is a research tool: it organizes and computes data from public filings. It does not provide recommendations, valuations, or predictions about future performance.',
  },
  {
    q: 'Which companies are covered?',
    a: 'Finora works with any public company that files with the SEC — currently US-listed issuers, with international coverage on the roadmap.',
  },
  {
    q: 'Can I export the dashboard?',
    a: 'Yes. The dashboard exports to a clean, print-ready PDF, and every table can be copied as tabular data for your own models.',
  },
  {
    q: 'How many questions can I ask?',
    a: 'You can send up to 15 chat messages per rolling 24-hour period. Each answer is grounded in the source filings, with citations you can open and verify.',
  },
];

export const permissionItems = [
  {
    title: 'Access public financial reports',
    body: 'Read annual and quarterly filings available in the public domain via SEC EDGAR.',
  },
  {
    title: 'Extract financial statements',
    body: 'Parse income statement, balance sheet, and cash flow figures with page-level provenance.',
  },
  {
    title: 'Calculate financial metrics',
    body: 'Compute margins, returns, growth, and cash-flow metrics using standard definitions.',
  },
  {
    title: 'Generate executive summary',
    body: 'Produce a professional readout of key findings, growth drivers, and risks.',
  },
];

export const processingSteps = [
  { id: 'identify', label: 'Identifying company', detail: 'Microsoft Corporation · NASDAQ: MSFT' },
  { id: 'annual', label: 'Finding annual reports', detail: '10-K FY2024 · filed Jul 30, 2024' },
  { id: 'quarterly', label: 'Collecting quarterly reports', detail: '10-Q filings · FY2024–FY2025' },
  { id: 'extract', label: 'Extracting financial statements', detail: 'Income statement · Balance sheet · Cash flow' },
  { id: 'calculate', label: 'Calculating financial metrics', detail: '26 metrics · standard definitions' },
  { id: 'build', label: 'Building dashboard', detail: 'Overview · Statements · Ratios · Sources' },
];
