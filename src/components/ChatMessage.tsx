import Markdown from "react-markdown";
import SourceCitation from "./SourceCitation";
import type { ChatSource } from "../lib/api";

export interface ChatMessageData {
  role: "user" | "assistant";
  headline?: string;
  content: string;
  bold?: string[];
  source?: string;
  followUps?: string[];
  sources?: ChatSource[];
}

function SourceCard({ source }: { source: ChatSource }) {
  const host = (() => {
    try {
      return new URL(source.url).hostname.replace(/^www\./, "");
    } catch {
      return source.publisher || "source";
    }
  })();
  const letter = (source.publisher || host || "?").replace(/^www\./, "").charAt(0).toUpperCase();
  const date = source.published_at
    ? new Date(source.published_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-start gap-2.5 border border-ink/15 bg-paper-2/40 px-3 py-2 transition-colors hover:border-ink/45"
    >
      <span
        aria-hidden
        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border border-ink/25 bg-paper font-mono text-[10px] font-bold text-ink-2 group-hover:border-ink/50"
      >
        {letter}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-2">
          <span className="truncate font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">
            {source.publisher || host}
          </span>
          {date && <span className="shrink-0 text-[10px] text-ink-3">{date}</span>}
        </span>
        <span className="mt-0.5 block text-xs leading-snug text-ink-2 group-hover:text-ink">
          {source.title}
        </span>
      </span>
    </a>
  );
}

export function SourceCards({ sources }: { sources?: ChatSource[] }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-4 border-t border-ink/12 pt-3">
      <p className="mb-2 font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">
        Sources
      </p>
      <div className="flex flex-col gap-1.5">
        {sources.map((s) => (
          <SourceCard key={s.url} source={s} />
        ))}
      </div>
    </div>
  );
}

export default function ChatMessage({
  message,
  onFollowUp,
}: {
  message: ChatMessageData;
  onFollowUp?: (q: string) => void;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-ink px-5 py-3 text-sm text-paper sm:max-w-[70%]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[95%] border border-ink/20 bg-paper p-4 sm:max-w-full sm:p-5">
      {message.headline && (
        <h3 className="mb-2 font-serif text-xl font-semibold text-ink">{message.headline}</h3>
      )}
      <div className="prose-chat text-sm leading-relaxed text-ink-2">
        <Markdown
          components={{
            h1: ({ children }) => (
              <h1 className="mb-1 mt-3 font-serif text-lg font-bold text-ink">{children}</h1>
            ),
            h2: ({ children }) => (
              <h2 className="mb-1 mt-3 font-serif text-base font-bold text-ink">{children}</h2>
            ),
            h3: ({ children }) => (
              <h3 className="mb-1 mt-2 font-serif text-sm font-bold text-ink">{children}</h3>
            ),
            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
            ul: ({ children }) => <ul className="mb-2 list-disc pl-5">{children}</ul>,
            ol: ({ children }) => <ol className="mb-2 list-decimal pl-5">{children}</ol>,
            li: ({ children }) => <li className="mb-0.5">{children}</li>,
            strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
            code: ({ children, className }) => {
              const isInline = !className;
              return isInline ? (
                <code className="bg-ink/8 px-1 py-0.5 font-mono text-xs">{children}</code>
              ) : (
                <code className="block overflow-x-auto bg-ink/8 p-3 font-mono text-xs">
                  {children}
                </code>
              );
            },
            table: ({ children }) => (
              <div className="my-2 overflow-x-auto">
                <table className="w-full border-collapse text-xs">{children}</table>
              </div>
            ),
            thead: ({ children }) => (
              <thead className="border-b border-ink/15">{children}</thead>
            ),
            th: ({ children }) => (
              <th className="px-2 py-1 text-left font-mono font-semibold text-ink">{children}</th>
            ),
            td: ({ children }) => (
              <td className="border-b border-ink/8 px-2 py-1">{children}</td>
            ),
            blockquote: ({ children }) => (
              <blockquote className="my-2 border-l-2 border-ink/20 pl-3 text-ink-3 italic">
                {children}
              </blockquote>
            ),
          }}
        >
          {message.content}
        </Markdown>
      </div>
      <SourceCards sources={message.sources} />
      {message.source && (
        <div className="mt-4">
          <SourceCitation label={message.source} />
        </div>
      )}
      {message.followUps && message.followUps.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-ink/12 pt-4">
          {message.followUps.map((q) => (
            <button
              key={q}
              onClick={() => onFollowUp?.(q)}
              className="border border-ink/30 px-3 py-1.5 text-left font-mono text-[11px] text-ink-2 transition-colors hover:border-ink hover:text-ink"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
