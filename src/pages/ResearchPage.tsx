import { useSearchParams } from "react-router-dom";
import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import ResearchInput from "../components/ResearchInput";
import Annotation from "../components/Annotation";
import PaperTexture from "../components/PaperTexture";
import ResearchProcessingPage from "./ResearchProcessingPage";

export default function ResearchPage() {
  const [params] = useSearchParams();
  const ticker = params.get("ticker");

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

        <p className="mt-6 max-w-lg text-base leading-relaxed text-ink-2">
          Enter a company name or ticker. Finora will locate its authoritative SEC filings, extract the
          financial statements, calculate institutional-grade metrics, and verify every figure against
          independent sources.
        </p>

        <div className="mt-10 max-w-2xl">
          <ResearchInput />
        </div>

        <div className="mt-16 grid grid-cols-1 gap-6 border-t border-ink/15 pt-10 sm:grid-cols-3">
          <Annotation label="Step 01" value="Identify the filer & CIK" />
          <Annotation label="Step 02" value="Read 10-K / 10-Q / 8-K" tone="blue" />
          <Annotation label="Step 03" value="Verify & explain" tone="red" />
        </div>
      </div>
    </div>
  );
}
