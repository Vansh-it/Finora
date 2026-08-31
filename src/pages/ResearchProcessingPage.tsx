import { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import EditorialHeading from "../components/EditorialHeading";
import Annotation from "../components/Annotation";
import { cn } from "../utils/cn";
import { getToken } from "../lib/auth";
import {
  grantPermission,
  fetchFilings,
  extractFinancials,
  calculateMetrics,
  discoverSources,
  readVerifySources,
  generateSummary,
  calculateValuation,
  cancelSession,
  type GrantPermissionResponse,
} from "../lib/api";

const STAGES = [
  { key: "grant", title: "Permission Granted", detail: "Creating research session and validating inputs." },
  { key: "filings", title: "SEC Filings Located", detail: "Resolving company CIK and locating 10-K, 10-Q and 8-K filings via EDGAR." },
  { key: "financials", title: "Financial Statements", detail: "Extracting income statement, balance sheet & cash flow from XBRL CompanyFacts." },
  { key: "metrics", title: "Metrics Calculated", detail: "Deriving profitability, growth, efficiency and valuation metrics." },
  { key: "sources", title: "Sources Discovered", detail: "Searching for authoritative company financial sources via Tavily + SEC." },
  { key: "verify", title: "Source Verification", detail: "Reading sources with Jina and cross-checking figures against SEC data." },
  { key: "summary", title: "Analysis Generated", detail: "Generating the plain-language executive research memo." },
  { key: "valuation", title: "Valuation Complete", detail: "Fetching market data and calculating valuation multiples." },
  { key: "complete", title: "Research File Complete", detail: "Assembling the final research record." },
];

type StageStatus = "pending" | "active" | "done" | "error";

export default function ResearchProcessingPage() {
  const [params] = useSearchParams();
  const ticker = (params.get("ticker") || "AAPL").toUpperCase();
  const navigate = useNavigate();
  const [activeStage, setActiveStage] = useState(0);
  const [stageStatuses, setStageStatuses] = useState<StageStatus[]>(
    () => STAGES.map(() => "pending" as StageStatus)
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const startedRef = useRef(false);

  // Run the full research pipeline
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    let cancelled = false;

    async function runPipeline() {
      try {
        // Step 1: Grant permission
        updateStage(0, "active");
        let session: GrantPermissionResponse;
        try {
          session = await grantPermission(ticker, "latest", undefined, undefined, getToken() || undefined);
        } catch (err) {
          // If backend is down, show error
          updateStage(0, "error");
          setErrorMsg(
            err instanceof Error
              ? err.message
              : "Could not connect to the Finora backend. Make sure the backend is running."
          );
          return;
        }
        if (cancelled) return;
        setSessionId(session.session_id);
        updateStage(0, "done");

        // Step 2: Fetch filings
        updateStage(1, "active");
        await fetchFilings(session.session_id);
        if (cancelled) return;
        updateStage(1, "done");

        // Step 3: Extract financials
        updateStage(2, "active");
        await extractFinancials(session.session_id);
        if (cancelled) return;
        updateStage(2, "done");

        // Step 4: Calculate metrics
        updateStage(3, "active");
        await calculateMetrics(session.session_id);
        if (cancelled) return;
        updateStage(3, "done");

        // Step 5: Discover sources
        updateStage(4, "active");
        await discoverSources(session.session_id);
        if (cancelled) return;
        updateStage(4, "done");

        // Step 6: Read + verify sources
        updateStage(5, "active");
        await readVerifySources(session.session_id);
        if (cancelled) return;
        updateStage(5, "done");

        // Step 7: Generate summary
        updateStage(6, "active");
        await generateSummary(session.session_id);
        if (cancelled) return;
        updateStage(6, "done");

        // Step 8: Calculate valuation
        updateStage(7, "active");
        await calculateValuation(session.session_id);
        if (cancelled) return;
        updateStage(7, "done");

        // Step 9: Complete
        updateStage(8, "done");

        // Navigate to dashboard after a short delay
        setTimeout(() => {
          if (!cancelled) {
            navigate(`/dashboard?session_id=${session.session_id}`);
          }
        }, 700);
      } catch (err) {
        console.error("Pipeline error:", err);
        if (!cancelled) {
          setErrorMsg(
            err instanceof Error ? err.message : "Research pipeline failed"
          );
        }
      }
    }

    runPipeline();

    return () => {
      cancelled = true;
      // Cancel session if component unmounts
      if (sessionId) {
        cancelSession(sessionId).catch(() => {});
      }
    };
  }, [ticker, navigate, sessionId]);

  function updateStage(index: number, status: StageStatus) {
    setStageStatuses((prev) => {
      const next = [...prev];
      next[index] = status;
      return next;
    });
    setActiveStage(index);
  }

  return (
    <div className="mx-auto min-h-[80vh] max-w-3xl px-4 py-16 sm:px-6 lg:px-0">
      <p className="font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">
        Research in progress
      </p>
      <EditorialHeading className="mt-4" size="md">
        Building
        <br />
        the research file.
      </EditorialHeading>

      <div className="mt-8 flex items-center gap-4 border border-ink/20 bg-paper p-4">
        <div className="flex h-10 w-10 items-center justify-center border border-ink font-mono text-sm font-bold">
          {ticker.slice(0, 2)}
        </div>
        <div>
          <div className="font-serif text-lg font-semibold text-ink uppercase">{ticker}</div>
          <Annotation label="NASDAQ" value={ticker} />
        </div>
      </div>

      {errorMsg && (
        <div className="mt-6 border-2 border-red-500 bg-red-50 p-4">
          <p className="font-mono text-sm font-bold text-red-700">Error</p>
          <p className="mt-1 text-sm text-red-600">{errorMsg}</p>
          <button
            onClick={() => navigate("/research")}
            className="mt-3 font-mono text-xs font-bold text-red-700 underline hover:text-red-900"
          >
            ← Back to Research
          </button>
        </div>
      )}

      <div className="mt-10 space-y-0">
        {STAGES.map((stage, i) => {
          const status = stageStatuses[i];
          const done = status === "done";
          const active = status === "active";
          const error = status === "error";

          return (
            <div key={stage.key} className="relative flex gap-4 pb-8 last:pb-0">
              {i < STAGES.length - 1 && (
                <div className="absolute top-8 left-[15px] h-full w-px bg-ink/15">
                  <div
                    className={cn(
                      "w-px bg-highlight transition-all duration-500",
                      done ? "h-full" : "h-0"
                    )}
                  />
                </div>
              )}
              <div
                className={cn(
                  "z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 font-mono text-xs font-bold transition-colors",
                  done && "border-ink bg-ink text-paper",
                  active && "border-annotate-blue text-annotate-blue",
                  error && "border-red-500 bg-red-500 text-white",
                  !done && !active && !error && "border-ink/25 text-ink-3"
                )}
              >
                {done ? (
                  <CheckCircle2 size={16} />
                ) : active ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : error ? (
                  <XCircle size={16} />
                ) : (
                  i + 1
                )}
              </div>
              <div
                className={cn(
                  "pt-0.5 transition-opacity",
                  !done && !active && !error && "opacity-40"
                )}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "font-mono text-[10px] font-bold tracking-widest uppercase",
                      done ? "text-ink-3" : active ? "text-annotate-blue" : error ? "text-red-500" : "text-ink-3"
                    )}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <h3
                    className={cn(
                      "font-serif text-lg font-semibold text-ink",
                      done && "relative"
                    )}
                  >
                    {stage.title}
                    {done && (
                      <span
                        className="mark-highlight absolute inset-0 -z-10 block"
                        aria-hidden
                      />
                    )}
                  </h3>
                  {active && (
                    <span className="font-mono text-xs text-annotate-blue">
                      processing...
                    </span>
                  )}
                  {error && (
                    <span className="font-mono text-xs text-red-500">failed</span>
                  )}
                </div>
                <p className="mt-1 text-sm text-ink-2">{stage.detail}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
