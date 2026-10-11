import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import Annotation from "../components/Annotation";
import PaperTexture from "../components/PaperTexture";
import DocumentCard from "../components/DocumentCard";

const SECTIONS = [
  {
    n: "01",
    title: "The Sources",
    body:
      "Finora treats SEC EDGAR filings — 10-K, 10-Q, 8-K, and DEF 14A — as factual authority. Company investor-relations pages and earnings releases corroborate context that filings alone cannot always capture.",
    tag: "SEC = FACTUAL AUTHORITY",
  },
  {
    n: "02",
    title: "The Statements",
    body:
      "Every income statement, balance sheet, and cash flow statement is normalized from raw XBRL tags into a consistent schema, so figures are comparable across years and companies.",
    tag: "XBRL → NORMALIZED SCHEMA",
  },
  {
    n: "03",
    title: "The Calculations",
    body:
      "Ratios and derived metrics — margins, returns, valuation multiples — are computed with documented, auditable Python formulas. No metric is estimated by a language model.",
    tag: "PYTHON = CALCULATION ENGINE",
  },
  {
    n: "04",
    title: "The Verification",
    body:
      "Figures are cross-checked against corroborating sources, such as earnings releases and market data providers, to flag any material mismatch before it reaches your dashboard.",
    tag: "CROSS-CHECK = TRUST",
  },
  {
    n: "05",
    title: "The AI",
    body:
      "Finora's AI is used strictly for interpretation and plain-language explanation — never for inventing numbers. Every AI-authored sentence that references a figure links back to its evidence.",
    tag: "AI = INTERPRETATION, NOT FABRICATION",
  },
];

export default function MethodologyPage() {
  return (
    <div>
      <section className="relative border-b border-ink/15">
        <PaperTexture />
        <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6 lg:px-0">
          <p className="mb-4 font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">Methodology</p>
          <EditorialHeading size="xl">
            How
            <br />
            <HighlightText>Finora knows.</HighlightText>
          </EditorialHeading>
          <p className="mt-8 max-w-xl text-base leading-relaxed text-ink-2">
            Finora's research philosophy is simple: don't trust the number, trace the number. Here is exactly how a
            figure travels from a public filing to your dashboard.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-0">
        <div className="space-y-16">
          {SECTIONS.map((s) => (
            <div key={s.n} className="grid grid-cols-1 gap-8 border-t border-ink/15 pt-10 lg:grid-cols-[120px_1fr_260px]">
              <div className="font-mono text-5xl font-bold text-ink/15">{s.n}</div>
              <div>
                <h3 className="font-serif text-3xl font-semibold text-ink">{s.title}</h3>
                <p className="mt-4 max-w-xl text-base leading-relaxed text-ink-2">{s.body}</p>
              </div>
              <div className="flex items-start justify-start lg:justify-end">
                <DocumentCard rotate={s.n === "03" ? -2 : 1.5} className="w-full max-w-[240px]">
                  <Annotation label="Principle" tone={s.n === "05" ? "red" : "blue"} />
                  <div className="mt-2 font-mono text-xs leading-relaxed text-ink">{s.tag}</div>
                </DocumentCard>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-ink/15 bg-paper-2">
        <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-0">
          <h3 className="font-serif text-3xl font-semibold text-ink">Source → Fact → Calculation → Verification → Interpretation</h3>
          <div className="mt-8 flex flex-wrap items-center gap-3 font-mono text-xs font-bold tracking-widest uppercase">
            {["Source", "Fact", "Calculation", "Verification", "Interpretation"].map((step, i, arr) => (
              <span key={step} className="flex items-center gap-3">
                <span className="border border-ink px-3 py-2">{step}</span>
                {i < arr.length - 1 && <span className="text-ink-3">→</span>}
              </span>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
