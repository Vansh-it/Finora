import { useState, useEffect, useRef, type FormEvent } from "react";
import { ArrowRight, AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import TickerChip from "./TickerChip";
import { isAuthenticated } from "../lib/auth";

const QUICK_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"];

export default function ResearchInput() {
  const [value, setValue] = useState("");
  const [showError, setShowError] = useState(false);
  const [shaking, setShaking] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const navigate = useNavigate();

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  function triggerError() {
    if (timerRef.current) clearTimeout(timerRef.current);
    setShowError(true);
    setShaking(true);
    setTimeout(() => setShaking(false), 500);
    timerRef.current = setTimeout(() => setShowError(false), 4000);
    inputRef.current?.focus();
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const ticker = value.trim().toUpperCase();
    if (!ticker) {
      triggerError();
      return;
    }
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
        className={`relative flex flex-col gap-3 border-2 bg-paper p-2 shadow-[6px_6px_0_0_#111111] transition-shadow duration-300 sm:flex-row sm:items-center sm:gap-0 ${
          showError
            ? "border-red-500 shadow-[6px_6px_0_0_#ef4444]"
            : "border-ink"
        } ${shaking ? "animate-[shake_0.5s_ease-in-out]" : ""}`}
      >
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            if (showError) setShowError(false);
          }}
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

      {/* Premium validation toast */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-out ${
          showError ? "mt-3 max-h-20 opacity-100" : "mt-0 max-h-0 opacity-0"
        }`}
      >
        <div className="flex items-center gap-3 border border-red-200 bg-gradient-to-r from-red-50 to-orange-50 px-4 py-3 shadow-sm">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500/10">
            <AlertCircle size={16} className="text-red-500" />
          </div>
          <div className="flex-1">
            <p className="font-sans text-sm font-semibold text-red-700">
              Company name or ticker required
            </p>
            <p className="mt-0.5 font-sans text-xs text-red-500/80">
              Enter a company name or ticker symbol to begin your research.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setShowError(false);
              inputRef.current?.focus();
            }}
            className="shrink-0 rounded border border-red-200 bg-white px-3 py-1.5 font-mono text-[10px] font-bold tracking-[0.1em] text-red-600 uppercase transition-colors hover:bg-red-50"
          >
            Dismiss
          </button>
        </div>
      </div>

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
