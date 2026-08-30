import { useEffect, useRef, useState, useCallback } from 'react';
import { getToken } from '../../lib/auth';

const BACKEND_URL = '';

interface DashboardChatProps {
  sessionId: string;
  companyName: string;
  ticker: string;
  isOpen: boolean;
  onClose: () => void;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export default function DashboardChat({ sessionId, companyName, ticker, isOpen, onClose }: DashboardChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollToBottom();
  }, [messages.length, scrollToBottom]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    const userMsg: ChatMessage = { role: 'user', content: text, timestamp: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setSending(true);

    try {
      const token = getToken();
      const res = await fetch(`${BACKEND_URL}/api/chat/dashboard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          history: messages.slice(-8).map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      const data = await res.json();
      if (data.error) {
        setMessages((prev) => [...prev, {
          role: 'assistant',
          content: `Sorry, I couldn't process that: ${data.error}`,
          timestamp: Date.now(),
        }]);
      } else {
        setMessages((prev) => [...prev, {
          role: 'assistant',
          content: data.response,
          timestamp: Date.now(),
        }]);
      }
    } catch {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Sorry, Finora is temporarily unable to respond. Please try again shortly.',
        timestamp: Date.now(),
      }]);
    } finally {
      setSending(false);
    }
  }, [input, sending, messages, sessionId]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[70] bg-black/30 backdrop-blur-sm md:hidden"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Chat panel */}
      <div
        className={`
          fixed z-[75] bg-canvas shadow-l5 flex flex-col
          inset-x-0 bottom-0 top-[15vh] rounded-t-xl
          md:inset-y-0 md:left-auto md:right-0 md:top-0 md:bottom-0 md:w-[420px] md:rounded-t-none md:rounded-l-xl
          transition-transform duration-300 ease-out
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-3 border-b border-hairline px-5 py-4">
          <div className="min-w-0">
            <h3 className="text-body-sm-strong text-ink truncate">Ask Finora</h3>
            <p className="text-caption text-mute truncate">
              {companyName} ({ticker}) · Session context active
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn-press flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-hairline bg-canvas text-body hover:text-ink"
            aria-label="Close chat"
          >
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <p className="mt-3 text-body-sm-strong text-ink">Ask about {companyName}</p>
              <p className="mt-1 text-caption text-mute">Finora knows this company's financials, metrics, and sources.</p>

              <div className="mt-6 space-y-2 w-full max-w-xs">
                {[
                  'Why is ROE high?',
                  'How was free cash flow calculated?',
                  'Explain this dashboard simply.',
                ].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => { setInput(q); }}
                    className="w-full rounded-lg border border-hairline bg-canvas px-3 py-2 text-left text-caption text-body hover:border-accent hover:bg-accent-soft hover:text-ink transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-4 py-3 text-body-sm ${
                  msg.role === 'user'
                    ? 'bg-ink text-canvas'
                    : 'bg-canvas-soft text-body shadow-l1'
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="rounded-lg bg-canvas-soft px-4 py-3 shadow-l1">
                <div className="flex items-center gap-2 text-caption text-mute">
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent [animation-delay:150ms]" />
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-hairline px-5 py-4">
          <div className="flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask about ${companyName}...`}
              rows={1}
              className="flex-1 resize-none rounded-lg border border-hairline bg-canvas-soft px-3 py-2.5 text-body-sm text-ink placeholder:text-mute focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              maxLength={2000}
            />
            <button
              type="button"
              onClick={sendMessage}
              disabled={!input.trim() || sending}
              className="btn-press flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-ink text-canvas hover:opacity-90 disabled:opacity-40"
              aria-label="Send message"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <p className="mt-2 text-caption text-mute">
            Contextual to this research session · Powered by Finora AI
          </p>
        </div>
      </div>
    </>
  );
}
