import { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { cn } from "../utils/cn";

/* ── FAQ data ──────────────────────────────────────────────────────────────── */

const FAQ_ITEMS = [
  {
    id: "01",
    question: "Where does Finora get its financial data?",
    answer:
      "Finora researches public-company information from sources such as SEC filings, structured XBRL data, company disclosures, and connected financial-data providers. Wherever possible, metrics remain connected to their underlying source so users can inspect where a number came from instead of simply trusting a black-box output.",
  },
  {
    id: "02",
    question:
      "Does Finora just show financial data, or does it actually analyze it?",
    answer:
      "Finora does both. It collects and structures company data, calculates financial metrics and ratios, identifies trends, and uses its research intelligence layer to explain what those numbers mean. The goal is to turn filings and raw financial data into research that both analysts and everyday users can understand.",
  },
  {
    id: "03",
    question: "How can I know how Finora calculated a metric?",
    answer:
      "Finora is designed around the principle that every number should have a receipt. Calculated metrics can expose their formula, underlying inputs, fiscal period, calculation, and supporting source. If an input is unavailable, Finora should explain why the metric could not be calculated rather than inventing a value.",
  },
  {
    id: "04",
    question:
      "Can I ask Finora questions about the company I'm researching?",
    answer:
      "Yes. Ask Finora is connected to the active research session, so users can ask follow-up questions about the company, financial statements, ratios, trends, calculations, sources, or individual dashboard metrics without starting the research process again.",
  },
  {
    id: "05",
    question: "Is Finora giving investment advice?",
    answer:
      "No. Finora is a financial research and analysis tool, not an investment adviser. It helps users investigate public-company information, understand financial metrics, inspect calculations, and explore research findings. Investment decisions remain entirely with the user.",
  },
];

/* ── Formula demo for FAQ #3 ──────────────────────────────────────────────── */

function FormulaDemo({ visible }: { visible: boolean }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!visible) {
      setStep(0);
      return;
    }
    setStep(0);
    const timers = [
      setTimeout(() => setStep(1), 200),
      setTimeout(() => setStep(2), 600),
      setTimeout(() => setStep(3), 1000),
      setTimeout(() => setStep(4), 1400),
      setTimeout(() => setStep(5), 1800),
    ];
    return () => timers.forEach(clearTimeout);
  }, [visible]);

  return (
    <div className="mt-6 border-t border-ink/10 pt-6">
      <div className="flex flex-col gap-3 font-mono text-sm sm:flex-row sm:items-center sm:gap-4">
        {/* OCF */}
        <div
          className={cn(
            "border border-ink/20 bg-paper px-4 py-3 transition-all duration-500",
            step >= 1
              ? "translate-y-0 opacity-100"
              : "translate-y-2 opacity-0"
          )}
        >
          <div className="text-[10px] tracking-[0.15em] text-ink-3 uppercase">
            Operating Cash Flow
          </div>
          <div className="mt-1 text-lg font-bold tabular-nums">$125.4B</div>
        </div>

        {/* minus */}
        <div
          className={cn(
            "font-mono text-xl font-bold text-ink-3 transition-all duration-300",
            step >= 2
              ? "translate-y-0 opacity-100"
              : "translate-y-2 opacity-0"
          )}
        >
          −
        </div>

        {/* CAPEX */}
        <div
          className={cn(
            "border border-ink/20 bg-paper px-4 py-3 transition-all duration-500",
            step >= 3
              ? "translate-y-0 opacity-100"
              : "translate-y-2 opacity-0"
          )}
        >
          <div className="text-[10px] tracking-[0.15em] text-ink-3 uppercase">
            Capital Expenditure
          </div>
          <div className="mt-1 text-lg font-bold tabular-nums">$16.6B</div>
        </div>

        {/* equals */}
        <div
          className={cn(
            "font-mono text-xl font-bold text-ink-3 transition-all duration-300",
            step >= 4
              ? "translate-y-0 opacity-100"
              : "translate-y-2 opacity-0"
          )}
        >
          =
        </div>

        {/* FCF */}
        <div
          className={cn(
            "relative border border-highlight/60 bg-paper px-4 py-3 transition-all duration-500",
            step >= 5
              ? "translate-y-0 opacity-100"
              : "translate-y-2 opacity-0"
          )}
        >
          <div className="text-[10px] tracking-[0.15em] text-ink-3 uppercase">
            Free Cash Flow
          </div>
          <div className="mt-1 text-lg font-bold tabular-nums">
            <span className="mark-highlight">$108.8B</span>
          </div>
        </div>
      </div>

      {/* Formula label */}
      <div
        className={cn(
          "mt-4 border-t border-ink/10 pt-4 transition-all duration-500",
          step >= 5
            ? "translate-y-0 opacity-100"
            : "translate-y-2 opacity-0"
        )}
      >
        <div className="font-mono text-[10px] tracking-[0.15em] text-ink-3 uppercase">
          Formula
        </div>
        <div className="mt-1 font-mono text-xs text-ink">
          FCF = Operating Cash Flow − Capital Expenditure
        </div>
      </div>
    </div>
  );
}

/* ── Single accordion row ──────────────────────────────────────────────────── */

function FAQRow({
  item,
  index,
  isOpen,
  onToggle,
}: {
  item: (typeof FAQ_ITEMS)[number];
  index: number;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (contentRef.current) {
      setHeight(contentRef.current.scrollHeight);
    }
  }, [isOpen]);

  return (
    <div
      className={cn(
        "group/faq border-b border-ink/15 transition-colors duration-300",
        isOpen ? "bg-ink/[0.015]" : "bg-transparent"
      )}
    >
      {/* Trigger row */}
      <button
        onClick={onToggle}
        aria-expanded={isOpen}
        aria-controls={`faq-answer-${item.id}`}
        className="flex w-full items-center gap-4 py-5 text-left sm:py-6"
      >
        {/* Number */}
        <span
          className={cn(
            "w-10 shrink-0 font-mono text-xs font-bold tabular-nums transition-colors duration-300 sm:w-12",
            isOpen
              ? "text-highlight"
              : "text-ink-3 group-hover/faq:text-highlight"
          )}
        >
          {item.id}
        </span>

        {/* Question */}
        <span
          className={cn(
            "flex-1 font-serif text-base leading-snug font-medium text-ink transition-all duration-300 sm:text-xl",
            isOpen ? "text-ink" : "group-hover/faq:translate-x-1"
          )}
        >
          {item.question}
        </span>

        {/* Plus icon */}
        <span
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center transition-all duration-300",
            isOpen
              ? "rotate-45 text-ink"
              : "rotate-0 text-ink-3 group-hover/faq:rotate-90"
          )}
          aria-hidden
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <line x1="7" y1="0" x2="7" y2="14" />
            <line x1="0" y1="7" x2="14" y2="7" />
          </svg>
        </span>
      </button>

      {/* Answer container */}
      <div
        id={`faq-answer-${item.id}`}
        role="region"
        aria-labelledby={`faq-question-${item.id}`}
        className="overflow-hidden"
        style={{
          height: isOpen ? `${height}px` : "0px",
          transition: "height 420ms cubic-bezier(0.22, 1, 0.36, 1)",
        }}
      >
        <div
          ref={contentRef}
          className={cn(
            "pb-6 pl-10 pr-4 sm:pb-8 sm:pl-12 sm:pr-12",
            isOpen
              ? "translate-y-0 opacity-100 transition-all duration-400 delay-75"
              : "translate-y-2 opacity-0 transition-all duration-200"
          )}
        >
          <p className="max-w-3xl text-sm leading-relaxed text-ink-2 sm:text-base">
            {item.answer}
          </p>

          {/* Formula demo for FAQ #3 */}
          {item.id === "03" && <FormulaDemo visible={isOpen} />}

          {/* Lime accent line under active question */}
          <div
            className={cn(
              "mt-6 h-[1px] origin-left transition-all duration-500",
              isOpen
                ? "scale-x-100 bg-highlight"
                : "scale-x-0 bg-transparent"
            )}
          />
        </div>
      </div>
    </div>
  );
}

/* ── Intersection observer hook ────────────────────────────────────────────── */

function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return { ref, inView };
}

/* ── Main FAQ component ────────────────────────────────────────────────────── */

export default function FinoraFAQ() {
  const [openId, setOpenId] = useState<string | null>(null);
  const { ref: sectionRef, inView } = useInView(0.1);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const toggle = useCallback(
    (id: string) => {
      setOpenId((prev) => (prev === id ? null : id));
    },
    []
  );

  /* stagger delays for entrance */
  const stagger = (i: number) => ({
    transitionDelay: reducedMotion ? "0ms" : `${80 + i * 75}ms`,
  });

  return (
    <section
      ref={sectionRef}
      className="relative border-t border-ink/15 bg-paper"
    >
      <div className="mx-auto max-w-[1440px] px-4 py-20 sm:px-6 sm:py-28 lg:px-10 lg:py-32">
        {/* ── Eyebrow ── */}
        <p
          className={cn(
            "mb-3 font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase transition-all duration-600",
            inView
              ? "translate-y-0 opacity-100"
              : "translate-y-3 opacity-0"
          )}
          style={stagger(0)}
        >
          FINORA / QUESTIONS, ANSWERED
        </p>

        {/* ── Heading ── */}
        <h2
          className={cn(
            "font-serif text-4xl font-medium tracking-tight text-ink sm:text-5xl lg:text-6xl transition-all duration-700",
            inView
              ? "translate-y-0 opacity-100"
              : "translate-y-3 opacity-0"
          )}
          style={stagger(1)}
        >
          Before you trust
          <br />
          the numbers.
        </h2>

        {/* ── Subheading ── */}
        <p
          className={cn(
            "mt-5 max-w-2xl text-base leading-relaxed text-ink-2 sm:text-lg transition-all duration-700",
            inView
              ? "translate-y-0 opacity-100"
              : "translate-y-3 opacity-0"
          )}
          style={stagger(2)}
        >
          Five things worth knowing about how Finora researches, calculates,
          verifies, and explains public-company financials.
        </p>

        {/* ── FAQ Rows ── */}
        <div className="mt-14 border-t border-ink/15">
          {FAQ_ITEMS.map((item, i) => (
            <div
              key={item.id}
              className={cn(
                "transition-all duration-600",
                inView
                  ? "translate-y-0 opacity-100"
                  : "translate-y-3.5 opacity-0"
              )}
              style={stagger(3 + i)}
            >
              <FAQRow
                item={item}
                index={i}
                isOpen={openId === item.id}
                onToggle={() => toggle(item.id)}
              />
            </div>
          ))}
        </div>

        {/* ── Bottom CTA ── */}
        <div
          className={cn(
            "mt-14 text-center transition-all duration-600",
            inView
              ? "translate-y-0 opacity-100"
              : "translate-y-3 opacity-0"
          )}
          style={stagger(8)}
        >
          <p className="font-mono text-[11px] font-bold tracking-[0.25em] text-ink-3 uppercase">
            STILL CURIOUS?
          </p>
          <p className="mt-3 max-w-lg mx-auto text-sm leading-relaxed text-ink-2 sm:text-base">
            Ask Finora while researching a company and get answers grounded in
            the active research.
          </p>
          <Link
            to="/research"
            className="mt-6 inline-flex items-center gap-2 border-2 border-ink bg-ink px-7 py-3.5 font-mono text-xs font-bold tracking-[0.15em] text-paper uppercase transition-colors hover:bg-ink-2"
          >
            START A RESEARCH <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </section>
  );
}
