import { Link } from "react-router-dom";
import { ArrowRight, TrendingUp, CheckCircle2, FileText } from "lucide-react";
import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import ResearchInput from "../components/ResearchInput";
import Annotation from "../components/Annotation";
import SourceStamp from "../components/SourceStamp";
import DocumentCard from "../components/DocumentCard";
import PaperTexture from "../components/PaperTexture";

const PIPELINE = [
  { n: "01", title: "Identify", desc: "Resolve the company & ticker to an authoritative filer.", icon: "card" },
  { n: "02", title: "Read", desc: "Parse SEC 10-K, 10-Q and 8-K filings line by line.", icon: "clip" },
  { n: "03", title: "Normalize", desc: "Map disclosures into a consistent financial schema.", icon: "table" },
  { n: "04", title: "Calculate", desc: "Derive ratios and metrics with documented formulas.", icon: "formula" },
  { n: "05", title: "Verify", desc: "Cross-check figures against independent sources.", icon: "verify" },
  { n: "06", title: "Explain", desc: "Produce a plain-language research memo.", icon: "memo" },
];

export default function HomePage() {
  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden border-b border-ink/15">
        <PaperTexture />
        <div className="mx-auto max-w-[1440px] px-4 pt-14 pb-20 sm:px-6 lg:px-10 lg:pt-20 lg:pb-28">
          <div className="grid grid-cols-1 gap-12 lg:grid-cols-[1.3fr_0.9fr] lg:gap-8">
            {/* Left: headline + input */}
            <div className="relative">
              <p className="mb-5 font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">
                AI Financial Research &amp; Intelligence
              </p>
              <h1 className="font-serif text-[13vw] leading-[0.94] font-medium tracking-tight text-ink sm:text-[8vw] lg:text-[4.6vw]">
                Research
                <br />
                the company.
                <br />
                <HighlightText className="inline-block">Verify the numbers.</HighlightText>
              </h1>

              <p className="mt-8 max-w-xl text-base leading-relaxed text-ink-2 sm:text-lg">
                Finora turns public filings into financial statements, institutional-grade metrics, valuation
                analysis and explainable research — with every important figure traced back to its source.
              </p>

              <div className="mt-10 max-w-2xl">
                <ResearchInput />
              </div>

              <div className="mt-10 flex flex-wrap gap-x-10 gap-y-4">
                <Annotation label="Source 01" value="SEC EDGAR" />
                <Annotation label="Source 02" value="Company IR" tone="blue" />
                <Annotation label="Market" value="Twelve Data" />
                <Annotation label="Analysis" value="Finora AI" tone="red" />
              </div>
            </div>

            {/* Right: editorial collage */}
            <div className="relative hidden min-h-[560px] lg:block">
              <DocumentCard rotate={-3} className="absolute top-0 right-4 w-64">
                <div className="font-mono text-[9px] tracking-[0.2em] text-ink-3 uppercase">Form 10-K · Annual Report</div>
                <div className="mt-2 font-serif text-sm leading-snug text-ink">
                  "Net sales increased 2% during fiscal 2025 compared to fiscal 2024..."
                </div>
                <div className="mark-highlight mt-2 inline-block font-mono text-xs font-bold">$398.8B revenue</div>
                <FileText size={14} className="mt-3 text-ink-3" />
              </DocumentCard>

              <DocumentCard rotate={2} className="absolute top-[190px] left-0 w-52">
                <Annotation label="ROIC Formula" tone="blue" />
                <div className="mt-2 font-mono text-xs leading-relaxed text-ink">
                  ROIC =<br />
                  NOPAT / Invested Capital
                </div>
              </DocumentCard>

              <DocumentCard rotate={-1.5} className="absolute top-[230px] right-0 w-60">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">NASDAQ · AAPL</span>
                  <TrendingUp size={14} className="text-annotate-green" />
                </div>
                <svg viewBox="0 0 120 40" className="mt-2 h-10 w-full">
                  <polyline
                    points="0,32 15,28 30,30 45,20 60,22 75,12 90,15 105,6 120,8"
                    fill="none"
                    stroke="#111111"
                    strokeWidth="1.5"
                  />
                </svg>
                <div className="mt-1 font-mono text-lg font-bold text-ink">$231.40</div>
              </DocumentCard>

              <div className="absolute top-[420px] left-8">
                <SourceStamp tone="blue">SEC Verified</SourceStamp>
              </div>

              <DocumentCard rotate={1} className="absolute bottom-0 right-10 w-56">
                <Annotation label="Cross-Verification" tone="red" />
                <div className="mt-2 flex items-center gap-2 font-mono text-xs text-ink">
                  <CheckCircle2 size={14} className="text-annotate-green" />
                  9 sources · 7 cross-verified
                </div>
              </DocumentCard>

              {/* hand-drawn connecting line */}
              <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 400 560" fill="none">
                <path
                  d="M 260 90 C 220 130, 190 150, 150 190"
                  stroke="#3978FF"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <path d="M 150 190 l 8 -4 l -2 9 z" fill="#3978FF" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* HOW FINORA THINKS */}
      <section className="relative border-b border-ink/15 bg-paper-2">
        <PaperTexture />
        <div className="mx-auto max-w-[1440px] px-4 py-20 sm:px-6 lg:px-10">
          <EditorialHeading size="md">
            One question. Multiple sources.
            <br />
            <HighlightText>One research record.</HighlightText>
          </EditorialHeading>

          <div className="mt-14 grid grid-cols-2 gap-x-6 gap-y-12 sm:grid-cols-3 lg:grid-cols-6 lg:gap-4">
            {PIPELINE.map((step, i) => (
              <div key={step.n} className="relative">
                <div className="font-mono text-xs font-bold text-ink-3">{step.n}</div>
                <div className="mt-2 flex h-20 w-full items-center justify-center border border-ink/25 bg-paper">
                  <PipelineIcon type={step.icon} />
                </div>
                <h3 className="mt-3 font-serif text-lg font-semibold text-ink">{step.title}</h3>
                <p className="mt-1 text-xs leading-snug text-ink-2">{step.desc}</p>
                {i < PIPELINE.length - 1 && (
                  <ArrowRight size={16} className="absolute top-6 -right-5 hidden text-ink-3 lg:block" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* EVERY NUMBER HAS A RECEIPT */}
      <section className="relative border-b border-ink/15">
        <PaperTexture />
        <div className="mx-auto max-w-[1440px] px-4 py-20 sm:px-6 lg:px-10">
          <div className="grid grid-cols-1 gap-14 lg:grid-cols-2">
            <div>
              <EditorialHeading size="md">
                Every number
                <br />
                <HighlightText>has a receipt.</HighlightText>
              </EditorialHeading>
              <p className="mt-6 max-w-md text-base leading-relaxed text-ink-2">
                Finora doesn't just show you a metric — it shows the calculation, the underlying filing, and the
                exact XBRL concept that produced it. No black boxes.
              </p>
              <Link
                to="/dashboard"
                className="mt-8 inline-flex items-center gap-2 border-b-2 border-ink pb-1 font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase transition-colors hover:border-highlight"
              >
                See it in the dashboard <ArrowRight size={14} />
              </Link>
            </div>

            <div className="border border-ink/20 bg-paper p-6 sm:p-8">
              <Annotation label="Metric" value="Free Cash Flow · Apple Inc. · FY2025" />
              <div className="mt-6 flex flex-col gap-4 font-mono text-sm">
                <div className="flex items-center justify-between border-b border-dashed border-ink/30 pb-3">
                  <span className="text-ink-2">Operating Cash Flow</span>
                  <span className="font-bold text-ink">$125.4B</span>
                </div>
                <div className="flex items-center justify-between border-b border-dashed border-ink/30 pb-3">
                  <span className="text-ink-2">− Capital Expenditure</span>
                  <span className="font-bold text-ink">$16.6B</span>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="font-semibold text-ink">= Free Cash Flow</span>
                  <HighlightText className="font-mono text-lg font-bold">$108.8B</HighlightText>
                </div>
              </div>

              <div className="mt-8 flex flex-wrap gap-6 border-t border-ink/15 pt-6">
                <Annotation label="Source" value="SEC 10-K, FY2025" />
                <Annotation
                  label="XBRL Concept"
                  value="NetCashProvidedByUsedInOperatingActivities"
                  className="max-w-[220px]"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative bg-ink text-paper">
        <div className="mx-auto max-w-[1440px] px-4 py-20 text-center sm:px-6 lg:px-10">
          <p className="font-mono text-xs font-semibold tracking-[0.3em] text-paper/60 uppercase">
            Don't trust the number.
          </p>
          <h2 className="mt-4 font-serif text-4xl font-medium sm:text-5xl lg:text-6xl">Trace the number.</h2>
          <div className="mt-10 flex justify-center">
            <Link
              to="/research"
              className="inline-flex items-center gap-2 bg-highlight px-8 py-4 font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase transition-transform hover:-translate-y-0.5"
            >
              Start Research <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function PipelineIcon({ type }: { type: string }) {
  const common = "text-ink";
  switch (type) {
    case "card":
      return <div className={`h-8 w-6 border-2 border-ink ${common}`} />;
    case "clip":
      return <FileText size={22} className={common} />;
    case "table":
      return (
        <div className="grid h-8 w-10 grid-cols-2 grid-rows-2 gap-0.5">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="border border-ink" />
          ))}
        </div>
      );
    case "formula":
      return <span className="font-mono text-sm font-bold text-ink">x÷y</span>;
    case "verify":
      return <CheckCircle2 size={22} className="text-annotate-green" />;
    default:
      return <div className="h-8 w-8 border-2 border-dashed border-ink" />;
  }
}
