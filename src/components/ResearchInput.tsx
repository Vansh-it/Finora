import { useState, type FormEvent } from "react";
import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import TickerChip from "./TickerChip";
import { isAuthenticated } from "../lib/auth";

const QUICK_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"];

export default function ResearchInput() {
  const [value, setValue] = useState("");
  const navigate = useNavigate();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const ticker = value.trim().toUpperCase() || "AAPL";
    if (!isAuthenticated()) {
      navigate("/auth", { state: { from: "/research" } });
      return;
    }
    navigate(`/research?ticker=${ticker}`);
  }

  return (
    <div className="w-full">
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-3 border-2 border-ink bg-paper p-2 shadow-[6px_6px_0_0_#111111] sm:flex-row sm:items-center sm:gap-0"
      >
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Research Microsoft, Apple, Walmart..."
          aria-label="Research a company"
          className="w-full flex-1 bg-transparent px-4 py-4 font-sans text-base text-ink placeholder:text-ink-3 focus:outline-none sm:text-lg"
        />
        <button
          type="submit"
          className="flex items-center justify-center gap-2 whitespace-nowrap bg-ink px-6 py-4 font-mono text-xs font-bold tracking-[0.15em] text-paper uppercase transition-colors hover:bg-ink-2"
        >
          Start Research
          <ArrowRight size={15} />
        </button>
      </form>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="mr-1 font-mono text-[10px] font-bold tracking-[0.2em] text-ink-3 uppercase">Try:</span>
        {QUICK_TICKERS.map((t) => (
          <TickerChip key={t} ticker={t} onClick={() => {
            if (!isAuthenticated()) {
              navigate("/auth", { state: { from: "/research" } });
              return;
            }
            navigate(`/research?ticker=${t}`);
          }} />
        ))}
      </div>
    </div>
  );
}
