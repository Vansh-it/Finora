import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import ResearchInput from "../components/ResearchInput";
import Annotation from "../components/Annotation";
import PaperTexture from "../components/PaperTexture";
import ResearchProcessingPage from "./ResearchProcessingPage";
import { getToken } from "../lib/auth";

export default function ResearchPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const ticker = params.get("ticker");
  const [remaining, setRemaining] = useState<number | null>(null);
  const [limit, setLimit] = useState(5);
  const [exhausted, setExhausted] = useState(false);
  const [resetsAt, setResetsAt] = useState<number>(0);

  useEffect(() => {
    const token = getToken();
    if (!token) return;

    fetch("/api/auth/profile", { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.usage) {
          setRemaining(data.usage.remaining);
          setLimit(data.usage.limit);
          setResetsAt(data.usage.resets_at || 0);
          if (data.usage.remaining <= 0) setExhausted(true);
        }
      })
      .catch(() => {});
  }, []);

  function resetCountdown(): string {
    if (!resetsAt) return "in 24 hours";
    const ms = resetsAt * 1000 - Date.now();
    if (ms <= 0) return "any moment now";
    const h = Math.floor(ms / 3_600_000);
    const m = Math.floor((ms % 3_600_000) / 60_000);
    return h > 0 ? `in ${h}h ${m}m` : `in ${m}m`;
  }

  if (ticker) return <ResearchProcessingPage />;

  return (
    <div className="relative">
      <PaperTexture />
      <div className="mx-auto max-w-4xl px-4 py-20 sm:px-6 lg:px-0">
        <p className="mb-4 font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">New Research File</p>
        <EditorialHeading size="md">
          What company should
          <br />
          <HighlightText>Finora investigate?</HighlightText>
        </EditorialHeading>

        {exhausted ? (
          <div className="mt-8 max-w-lg border-2 border-ink/20 bg-paper p-8">
            <h3 className="font-serif text-2xl font-semibold text-ink">Research limit reached.</h3>
            <p className="mt-3 text-sm leading-relaxed text-ink-2">
              You have used all {limit} researches available in this Finora preview.
              You are out of researches for now — but don't worry: your quota
              resets in 24 hours, so you can research again tomorrow.
            </p>
            <p className="mt-3 font-mono text-xs font-bold text-ink">
              Resets {resetCountdown()}
            </p>
            <p className="mt-2 font-mono text-xs text-ink-3">
              All {limit} completed researches stay open in your history below.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={() => navigate("/history")}
                className="border-2 border-ink bg-ink px-6 py-3 font-mono text-xs font-bold tracking-wider text-paper uppercase transition-colors hover:bg-ink-2"
              >
                View History
              </button>
              <button
                onClick={() => navigate("/")}
                className="border-2 border-ink/25 bg-paper px-6 py-3 font-mono text-xs font-bold tracking-wider text-ink uppercase transition-colors hover:border-ink"
              >
                Back to Home
              </button>
            </div>
            <button
              onClick={() => navigate("/limit")}
              className="mt-5 font-mono text-xs font-bold tracking-wider text-ink-3 underline underline-offset-4 uppercase transition-colors hover:text-ink"
            >
              Read a letter from the developer →
            </button>
          </div>
        ) : (
          <>
            <p className="mt-6 max-w-lg text-base leading-relaxed text-ink-2">
              Enter a company name or ticker. Finora will locate its authoritative SEC filings, extract the
              financial statements, calculate institutional-grade metrics, and verify every figure against
              independent sources.
            </p>

            {remaining !== null && (
              <p className="mt-3 font-mono text-xs text-ink-3">
                {remaining} of {limit} researches remaining
              </p>
            )}

            <div className="mt-10 max-w-2xl">
              <ResearchInput />
            </div>
          </>
        )}

        <div className="mt-16 grid grid-cols-1 gap-6 border-t border-ink/15 pt-10 sm:grid-cols-3">
          <Annotation label="Step 01" value="Identify the filer & CIK" />
          <Annotation label="Step 02" value="Read 10-K / 10-Q / 8-K" tone="blue" />
          <Annotation label="Step 03" value="Verify & explain" tone="red" />
        </div>
      </div>
    </div>
  );
}
