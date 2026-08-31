import Markdown from "react-markdown";
import SourceCitation from "./SourceCitation";

export interface ChatMessageData {
  role: "user" | "assistant";
  headline?: string;
  content: string;
  bold?: string[];
  source?: string;
  followUps?: string[];
}

export default function ChatMessage({ message, onFollowUp }: { message: ChatMessageData; onFollowUp?: (q: string) => void }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-ink px-5 py-3 text-sm text-paper sm:max-w-[70%]">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="max-w-[95%] border border-ink/20 bg-paper p-5 sm:max-w-[80%] sm:p-6">
      {message.headline && <h3 className="mb-2 font-serif text-xl font-semibold text-ink">{message.headline}</h3>}
      <div className="prose-chat text-sm leading-relaxed text-ink-2">
        <Markdown
          components={{
            h1: ({ children }) => <h1 className="mb-1 mt-3 font-serif text-lg font-bold text-ink">{children}</h1>,
            h2: ({ children }) => <h2 className="mb-1 mt-3 font-serif text-base font-bold text-ink">{children}</h2>,
            h3: ({ children }) => <h3 className="mb-1 mt-2 font-serif text-sm font-bold text-ink">{children}</h3>,
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
                <code className="block overflow-x-auto bg-ink/8 p-3 font-mono text-xs">{children}</code>
              );
            },
            table: ({ children }) => (
              <div className="my-2 overflow-x-auto">
                <table className="w-full border-collapse text-xs">{children}</table>
              </div>
            ),
            thead: ({ children }) => <thead className="border-b border-ink/15">{children}</thead>,
            th: ({ children }) => <th className="px-2 py-1 text-left font-mono font-semibold text-ink">{children}</th>,
            td: ({ children }) => <td className="border-b border-ink/8 px-2 py-1">{children}</td>,
            blockquote: ({ children }) => (
              <blockquote className="my-2 border-l-2 border-ink/20 pl-3 text-ink-3 italic">{children}</blockquote>
            ),
          }}
        >
          {message.content}
        </Markdown>
      </div>
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
