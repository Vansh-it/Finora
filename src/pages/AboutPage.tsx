import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import Annotation from "../components/Annotation";
import PaperTexture from "../components/PaperTexture";

const SECTIONS = [
  {
    title: "What Finora Is",
    body: "Finora is a financial research platform that turns public company filings into structured financial statements, institutional-grade metrics, valuation analysis, and explainable research. Every figure traces back to its source.",
  },
  {
    title: "Source Hierarchy",
    body: "Finora follows an authoritative source hierarchy. SEC EDGAR filings (10-K, 10-Q, 8-K) are the primary financial authority. Business Quant provides structured secondary data to fill gaps when SEC values are missing. Twelve Data supplies market data. Tavily and Jina read official company materials for context and verification. Nemotron interprets and explains the results.",
    tag: "SEC > Business Quant > Company IR > Market Data",
  },
  {
    title: "SEC-First Methodology",
    body: "Every financial statement is normalized from raw XBRL tags into a consistent schema, making figures comparable across years and companies. Business Quant may supplement missing inputs but never overwrites authoritative SEC data.",
  },
  {
    title: "Python Calculations",
    body: "Ratios and derived metrics — margins, returns, valuation multiples — are computed with documented, auditable Python formulas. No metric is estimated by a language model. The calculation engine is deterministic and traceable.",
    tag: "PYTHON = CALCULATION ENGINE",
  },
  {
    title: "AI Interpretation",
    body: "Finora's AI (Nemotron) is used strictly for interpretation and plain-language explanation — never for inventing numbers. Every AI-authored sentence that references a figure is grounded in the research data. The Read is a personalized editorial briefing generated for each researched company.",
    tag: "AI = INTERPRETATION, NOT FABRICATION",
  },
  {
    title: "Source Transparency",
    body: "Every displayed metric includes evidence: its formula, underlying inputs, source filing, and verification status. Unavailable metrics explain why they couldn't be calculated and which sources were checked. Nothing is hidden.",
  },
  {
    title: "Research Limitations",
    body: "Finora covers US-listed public companies with SEC EDGAR filings. Data is derived from public filings and market sources — it is not investment advice. Financial data accuracy depends on the quality of source filings. Some metrics may be unavailable for companies with limited disclosures.",
  },
];

export default function AboutPage() {
  return (
    <div>
      <section className="relative border-b border-ink/15">
        <PaperTexture />
        <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6 lg:px-0">
          <p className="mb-4 font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">About</p>
          <EditorialHeading size="xl">
            Financial research
            <br />
            <HighlightText>with receipts.</HighlightText>
          </EditorialHeading>
          <p className="mt-8 max-w-xl text-base leading-relaxed text-ink-2">
            Finora turns public filings into explainable financial research — with every important figure traced
            back to its source. Here's how it works and why it exists.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-0">
        <div className="space-y-16">
          {SECTIONS.map((s, i) => (
            <div key={s.title} className="grid grid-cols-1 gap-8 border-t border-ink/15 pt-10 lg:grid-cols-[1fr_280px]">
              <div>
                <h3 className="font-serif text-3xl font-semibold text-ink">{s.title}</h3>
                <p className="mt-4 max-w-xl text-base leading-relaxed text-ink-2">{s.body}</p>
              </div>
              {s.tag && (
                <div className="flex items-start justify-start lg:justify-end">
                  <div className="border border-ink/20 bg-paper-2 p-4">
                    <Annotation label="Principle" tone="blue" />
                    <div className="mt-2 font-mono text-xs leading-relaxed text-ink">{s.tag}</div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-ink/15 bg-paper-2">
        <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-0">
          <h3 className="font-serif text-3xl font-semibold text-ink">Data Sources</h3>
          <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { name: "SEC EDGAR", desc: "10-K, 10-Q, 8-K filings. Primary financial authority.", tier: "PRIMARY" },
              { name: "Business Quant", desc: "Structured financial data. Secondary fallback for missing values.", tier: "SECONDARY" },
              { name: "Twelve Data", desc: "Stock prices, market data, share counts.", tier: "MARKET DATA" },
              { name: "Tavily", desc: "Web search for official company materials and earnings releases.", tier: "DISCOVERY" },
              { name: "Jina", desc: "Web page content extraction for reading source documents.", tier: "READING" },
              { name: "Nemotron", desc: "AI interpretation and plain-language explanation of research results.", tier: "INTERPRETATION" },
            ].map((src) => (
              <div key={src.name} className="border border-ink/20 bg-paper p-5">
                <span className="font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">{src.tier}</span>
                <h4 className="mt-2 font-serif text-lg font-semibold text-ink">{src.name}</h4>
                <p className="mt-1 text-sm text-ink-2">{src.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
