import SourceCitation from "./SourceCitation";
import HighlightText from "./HighlightText";

export interface ChatMessageData {
  role: "user" | "assistant";
  headline?: string;
  content: string;
  bold?: string[];
  source?: string;
  followUps?: string[];
}

function renderWithBold(text: string, bolds?: string[]) {
  if (!bolds || bolds.length === 0) return text;
  let parts: (string | { bold: string })[] = [text];
  bolds.forEach((b) => {
    parts = parts.flatMap((p) => {
      if (typeof p !== "string") return [p];
      const split = p.split(b);
      const out: (string | { bold: string })[] = [];
      split.forEach((s, i) => {
        out.push(s);
        if (i < split.length - 1) out.push({ bold: b });
      });
      return out;
    });
  });
  return parts.map((p, i) =>
    typeof p === "string" ? <span key={i}>{p}</span> : <HighlightText key={i}>{p.bold}</HighlightText>
  );
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
      <p className="text-sm leading-relaxed text-ink-2">{renderWithBold(message.content, message.bold)}</p>
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
