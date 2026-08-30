import { useState, useRef, useEffect } from 'react';
import { X, ArrowUp, Sparkles } from 'lucide-react';
import { getToken } from '../../lib/auth';
import SourceCitation from '../ui/SourceCitation';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const SUGGESTED = [
  'How did you calculate ROIC?',
  'Why did margins change?',
  'Explain this company simply.',
  'What are the biggest risks?',
  'Which numbers were cross-verified?',
  'What does this valuation mean?',
];

export default function DashboardChat({ sessionId, open, onToggle }: { sessionId: string; open: boolean; onToggle: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function ask(question: string) {
    if (!question.trim() || loading) return;
    const userMsg: ChatMessage = { role: 'user', content: question };
    setMessages((m) => [...m, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const token = getToken();
      const res = await fetch('/api/chat/dashboard', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: question, session_id: sessionId, history: messages.slice(-8) }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { role: 'assistant', content: data.response || data.error || 'No response.' }]);
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: 'Unable to connect to Finora. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {/* FAB */}
      <button
        onClick={onToggle}
        className="fixed right-5 bottom-5 z-40 flex items-center gap-2 bg-ink px-5 py-3.5 font-mono text-xs font-bold tracking-widest text-paper uppercase shadow-[4px_4px_0_0_#E9FF32] transition-transform hover:-translate-y-0.5 sm:right-8 sm:bottom-8"
      >
        <Sparkles size={14} />
        Ask Finora
      </button>

      {/* Drawer */}
      {open && (
        <div className="fixed inset-0 z-[70] flex justify-end">
          <button aria-label="Close chat" className="absolute inset-0 bg-ink/30" onClick={onToggle} />
          <div className="relative flex h-full w-full max-w-lg flex-col border-l-2 border-ink bg-paper">
            <div className="flex items-center justify-between border-b border-ink/15 p-5">
              <div>
                <p className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Finora Research Assistant</p>
                <h2 className="font-serif text-xl font-semibold text-ink">Ask About This Research</h2>
              </div>
              <button onClick={onToggle} aria-label="Close" className="text-ink-2 hover:text-ink">
                <X size={20} />
              </button>
            </div>

            <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
              {messages.length === 0 && (
                <div>
                  <p className="mb-3 font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">
                    Suggested Questions
                  </p>
                  <div className="flex flex-col gap-2">
                    {SUGGESTED.map((q) => (
                      <button
                        key={q}
                        onClick={() => ask(q)}
                        className="border border-ink/25 px-4 py-3 text-left text-sm text-ink-2 transition-colors hover:border-ink hover:text-ink"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i}>
                  {m.role === 'user' ? (
                    <div className="flex justify-end">
                      <div className="max-w-[85%] bg-ink px-5 py-3 text-sm text-paper sm:max-w-[70%]">{m.content}</div>
                    </div>
                  ) : (
                    <div className="max-w-[95%] border border-ink/20 bg-paper p-5 sm:max-w-[80%] sm:p-6">
                      <p className="text-sm leading-relaxed text-ink-2">{m.content}</p>
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="border border-ink/20 bg-paper px-5 py-3">
                    <span className="font-mono text-xs text-ink-3 animate-pulse">Thinking&hellip;</span>
                  </div>
                </div>
              )}
            </div>

            <form
              onSubmit={(e) => { e.preventDefault(); ask(input); }}
              className="flex items-center gap-2 border-t border-ink/15 p-4"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about this research..."
                className="flex-1 border border-ink/25 bg-paper px-4 py-3 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:border-ink"
              />
              <button
                type="submit"
                aria-label="Send"
                disabled={loading || !input.trim()}
                className="flex h-11 w-11 items-center justify-center bg-ink text-paper transition-colors hover:bg-ink-2 disabled:opacity-50"
              >
                <ArrowUp size={16} />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
