import { useState, useRef, useEffect, useCallback } from "react";
import { X, ArrowUp, Loader2, RotateCw, AlertTriangle } from "lucide-react";
import ChatMessage, { type ChatMessageData } from "./ChatMessage";
import {
  streamChatMessage,
  getChatUsage,
  type ChatHistoryMessage,
  type ChatStage,
  type ChatUsage,
} from "../lib/api";
import { getToken } from "../lib/auth";

const LOGO = "/apple-touch-icon.png";

const STAGE_UI: Record<ChatStage, { active: string; done: string }> = {
  understanding: { active: "Understanding your question…", done: "Question understood" },
  internal: { active: "Checking Finora's financial data…", done: "Financial data checked" },
  searching: { active: "Researching current sources…", done: "Sources found" },
  comparing: { active: "Comparing recent information…", done: "Evidence compared" },
  synthesizing: { active: "Preparing answer…", done: "Answer prepared" },
};

const SUGGESTED_COMPANY = [
  "Why did margins change?",
  "What are the biggest risks?",
  "How profitable is this company?",
  "What does the valuation mean?",
];

const SUGGESTED_GENERAL = [
  "What are the latest developments at Tesla?",
  "Why are semiconductor stocks falling?",
  "Explain EV/EBITDA simply.",
  "What is the current interest-rate outlook?",
];

interface AskFinoraDrawerProps {
  sessionId?: string | null;
}

export default function AskFinoraDrawer({ sessionId }: AskFinoraDrawerProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failedQuestion, setFailedQuestion] = useState<string | null>(null);
  const [stages, setStages] = useState<ChatStage[]>([]);
  const [usage, setUsage] = useState<ChatUsage | null>(null);
  const [quotaBlocked, setQuotaBlocked] = useState<string | null>(null);

  const chatHistoryRef = useRef<ChatHistoryMessage[]>([]);
  const lastModeRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const suggested = sessionId ? SUGGESTED_COMPANY : SUGGESTED_GENERAL;
  const placeholder = sessionId
    ? "Ask Finora anything about this company…"
    : "Ask Finora about markets, companies, financials or recent developments…";

  const refreshUsage = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      setUsage(await getChatUsage(token));
    } catch {
      // usage display is best-effort; enforcement is server-side
    }
  }, []);

  useEffect(() => {
    if (open) refreshUsage();
  }, [open, refreshUsage]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, stages, error]);

  const limitReached =
    quotaBlocked !== null ||
    (usage !== null && (usage.messages_remaining <= 0 || usage.words_remaining <= 0));
  const lowOnMessages = usage !== null && !limitReached && usage.messages_remaining <= 5;

  async function ask(question: string) {
    const q = question.trim();
    if (!q || loading || limitReached) return;

    const userMsg: ChatMessageData = { role: "user", content: q };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);
    setFailedQuestion(null);
    setStages([]);

    chatHistoryRef.current.push({ role: "user", content: q });

    try {
      const token = getToken() || undefined;
      await streamChatMessage({
        message: q,
        history: chatHistoryRef.current.slice(-10),
        sessionId: sessionId ?? null,
        previousMode: lastModeRef.current,
        token,
        handlers: {
          onStatus: (stage) =>
            setStages((prev) => (prev[prev.length - 1] === stage ? prev : [...prev, stage])),
          onAnswer: (data) => {
            const assistantMsg: ChatMessageData = {
              role: "assistant",
              content: data.response,
              sources: data.sources,
            };
            setMessages((m) => [...m, assistantMsg]);
            chatHistoryRef.current.push({ role: "assistant", content: data.response });
            if (data.research?.mode) lastModeRef.current = data.research.mode;
            if (data.usage) {
              setUsage({
                messages_used: data.usage.messages_used ?? 0,
                messages_limit: data.usage.messages_limit ?? 25,
                messages_remaining: data.usage.messages_remaining ?? 0,
                words_used: data.usage.words_used ?? 0,
                words_limit: data.usage.words_limit ?? 7500,
                words_remaining: data.usage.words_remaining ?? 0,
                reset_at: data.usage.reset_at ?? "",
              });
            }
          },
          onError: (message) => {
            setError(message);
            setFailedQuestion(q);
          },
        },
      });
    } catch (err) {
      const e = err as Error & { status?: number };
      if (e.status === 429) {
        setQuotaBlocked(e.message);
        await refreshUsage();
      } else {
        setError(e.message || "Failed to get response");
        setFailedQuestion(q);
      }
      chatHistoryRef.current.pop();
    } finally {
      setLoading(false);
      setStages([]);
    }
  }

  function dismissUserEcho() {
    // on retry the question is re-sent; drop the trailing user echo duplicate
    setMessages((m) => (m.length > 0 && m[m.length - 1].role === "user" ? m.slice(0, -1) : m));
  }

  return (
    <>
      {/* ── Launcher ─────────────────────────────────────────────────────── */}
      <button
        onClick={() => setOpen(true)}
        aria-label="Open Finora assistant"
        className={`fixed right-5 bottom-5 z-40 transition-transform hover:-translate-y-0.5 sm:right-8 sm:bottom-8 ${
          open ? "hidden" : ""
        }`}
      >
        <span className="relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-full border-2 border-ink bg-paper shadow-[0_6px_20px_rgba(17,17,17,0.22)]">
          <img
            src={LOGO}
            alt="Finora"
            className="h-full w-full object-cover"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
          {!limitReached && (
            <span className="absolute right-0.5 bottom-0.5 h-3 w-3 rounded-full border-2 border-paper bg-highlight" />
          )}
        </span>
      </button>

      {open && (
        <div className="fixed inset-0 z-[70] pointer-events-none">
          <div className="pointer-events-auto absolute inset-0 bg-ink/20" onClick={() => setOpen(false)} />

          {/* ── Chat card ────────────────────────────────────────────────── */}
          <div className="pointer-events-auto absolute inset-x-0 bottom-0 flex max-h-[88vh] flex-col border-t-2 border-ink bg-paper shadow-[0_-8px_30px_rgba(17,17,17,0.18)] sm:inset-x-auto sm:right-6 sm:bottom-6 sm:max-h-[72vh] sm:w-[400px] sm:border-2 sm:shadow-[0_12px_40px_rgba(17,17,17,0.25)]">
            {/* Header */}
            <div className="flex items-start justify-between gap-3 border-b border-ink/15 px-4 py-3">
              <div className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border border-ink/30 bg-paper">
                  <img
                    src={LOGO}
                    alt=""
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display = "none";
                    }}
                  />
                </span>
                <div>
                  <p className="font-serif text-sm leading-tight font-semibold text-ink">Finora</p>
                  <p className="font-mono text-[9px] tracking-[0.18em] text-ink-3 uppercase">
                    AI Financial Research Assistant
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {usage && (
                  <span className="border border-ink/20 px-1.5 py-0.5 font-mono text-[9px] tracking-wide text-ink-3">
                    {usage.messages_used} / {usage.messages_limit} today
                  </span>
                )}
                <button
                  onClick={() => setOpen(false)}
                  aria-label="Close chat"
                  className="text-ink-2 transition-colors hover:text-ink"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
              {messages.length === 0 && !loading && (
                <div>
                  <p className="mb-4 text-sm leading-relaxed text-ink-2 italic">
                    “Ask me about this company, financials, markets or recent developments.”
                  </p>
                  <p className="mb-2 font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">
                    Try asking
                  </p>
                  <div className="flex flex-col gap-2">
                    {suggested.map((q) => (
                      <button
                        key={q}
                        onClick={() => ask(q)}
                        disabled={loading || limitReached}
                        className="border border-ink/25 px-3 py-2.5 text-left text-sm text-ink-2 transition-colors hover:border-ink hover:text-ink disabled:opacity-50"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <ChatMessage key={i} message={m} />
              ))}

              {/* Research status */}
              {loading && stages.length > 0 && (
                <div className="space-y-1.5 border border-ink/15 bg-paper-2/40 px-3 py-2.5">
                  {stages.map((stage, i) => {
                    const isLast = i === stages.length - 1;
                    const ui = STAGE_UI[stage];
                    return (
                      <p
                        key={`${stage}-${i}`}
                        className={`flex items-center gap-2 font-mono text-[11px] ${
                          isLast ? "text-ink" : "text-ink-3"
                        }`}
                      >
                        {isLast ? (
                          <Loader2 size={12} className="shrink-0 animate-spin" />
                        ) : (
                          <span className="w-3 shrink-0 text-center text-green-700">✓</span>
                        )}
                        {isLast ? ui.active : ui.done}
                      </p>
                    );
                  })}
                </div>
              )}

              {loading && stages.length === 0 && (
                <p className="flex items-center gap-2 font-mono text-xs text-ink-3">
                  <Loader2 size={13} className="animate-spin" />
                  Finora is thinking…
                </p>
              )}

              {/* Error + retry */}
              {error && !loading && (
                <div className="flex items-start gap-2 border border-red-300 bg-red-50 px-3 py-2.5 text-sm text-red-800">
                  <AlertTriangle size={15} className="mt-0.5 shrink-0" />
                  <div className="flex-1">
                    <p>{error}</p>
                    {failedQuestion && (
                      <button
                        onClick={() => {
                          const q = failedQuestion;
                          dismissUserEcho();
                          chatHistoryRef.current.pop();
                          setError(null);
                          setFailedQuestion(null);
                          ask(q);
                        }}
                        className="mt-2 inline-flex items-center gap-1.5 border border-red-400 px-2.5 py-1 font-mono text-[11px] font-semibold tracking-wide uppercase transition-colors hover:bg-red-100"
                      >
                        <RotateCw size={12} /> Retry
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Quota footer */}
            {usage && (
              <div className="border-t border-ink/10 px-4 pt-2 pb-1">
                <p className="font-mono text-[9px] tracking-wide text-ink-3">
                  {usage.messages_used} / {usage.messages_limit} messages ·{" "}
                  {usage.words_used.toLocaleString()} / {usage.words_limit.toLocaleString()} words
                  {lowOnMessages && (
                    <span className="text-amber-700">
                      {" "}
                      · {usage.messages_remaining} message
                      {usage.messages_remaining === 1 ? "" : "s"} remaining today
                    </span>
                  )}
                </p>
              </div>
            )}

            {/* Limit reached */}
            {limitReached && (
              <div className="border-t border-ink/15 bg-paper-2/60 px-4 py-4">
                <p className="text-sm font-semibold text-ink">Daily chat limit reached.</p>
                <p className="mt-1 text-sm text-ink-2">
                  You've used your Finora research allowance for today. Your chat access will
                  reset tomorrow.
                </p>
              </div>
            )}

            {/* Input */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                ask(input);
              }}
              className="flex items-end gap-2 border-t border-ink/15 p-3"
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    ask(input);
                  }
                }}
                rows={1}
                placeholder={limitReached ? "Limit reached — back tomorrow" : placeholder}
                disabled={loading || limitReached}
                aria-label="Message Finora"
                className="max-h-28 min-h-10 flex-1 resize-none border border-ink/25 bg-paper px-3 py-2.5 text-sm text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none disabled:opacity-50"
              />
              <button
                type="submit"
                aria-label="Send"
                disabled={loading || limitReached || !input.trim()}
                className="flex h-10 w-10 shrink-0 items-center justify-center bg-ink text-paper transition-colors hover:bg-ink-2 disabled:opacity-40"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} />}
              </button>
            </form>

            <p className="px-4 pb-2.5 font-mono text-[9px] tracking-wide text-ink-3">
              Finora can research the web when needed.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
