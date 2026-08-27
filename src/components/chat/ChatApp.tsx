import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth, getToken } from '../../lib/auth';
import ChatBubble from './ChatBubble';
import type { ChatMessage } from './ChatBubble';

const BACKEND_URL = '';

// System prompt is now handled server-side in the backend /api/chat endpoint.

export default function ChatApp() {
  const { user, loading: authLoading } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [remaining, setRemaining] = useState(15);
  const [typing, setTyping] = useState(false);
  const [thinkingText, setThinkingText] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load usage from backend on mount
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    fetch(`${BACKEND_URL}/api/chat/usage`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.remaining !== undefined) setRemaining(data.remaining);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, typing, thinkingText]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || remaining <= 0 || typing) return;

    const token = getToken();
    if (!token) {
      window.location.href = '/signin';
      return;
    }

    // Record message via backend
    try {
      const res = await fetch(`${BACKEND_URL}/api/chat/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      if (!res.ok) {
        setRemaining(0);
        return;
      }
      setRemaining(data.remaining);
    } catch {
      // If backend unreachable, still allow locally
    }

    const userMsg: ChatMessage = { role: 'user', text };
    setMessages((m) => [...m, userMsg]);
    setInput('');
    setTyping(true);
    // Cycle through thinking messages
    const thinkingMsgs = ['Analyzing your question…', 'Reading financial data…', 'Generating response…'];
    let thinkIdx = 0;
    const thinkInterval = setInterval(() => {
      thinkIdx = (thinkIdx + 1) % thinkingMsgs.length;
      setThinkingText(thinkingMsgs[thinkIdx]);
    }, 1200);
    setThinkingText(thinkingMsgs[0]);

    try {
      // Build history from previous messages only (system prompt is server-side)
      const history = messages.map((m) => ({
        role: m.role,
        content: m.text,
      }));

      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history,
        }),
      });

      const data = await response.json();
      if (data.error && !data.response) {
        throw new Error(data.error);
      }
      const replyText = data.response || 'Sorry, I could not generate a response.';

      setThinkingText('');
      setMessages((m) => [...m, { role: 'assistant', text: replyText }]);
    } catch (err) {
      setThinkingText('');
      const msg = err instanceof Error ? err.message : '';
      const friendly = msg.includes('temporarily unable')
        ? msg
        : 'Finora is temporarily unable to respond. Please try again shortly.';
      setMessages((m) => [
        ...m,
        { role: 'assistant', text: friendly },
      ]);
    } finally {
      clearInterval(thinkInterval);
      setThinkingText('');
      setTyping(false);
    }
  }, [input, remaining, typing, messages]);

  // Show sign-in prompt if not authenticated
  if (!authLoading && !user) {
    return (
      <div className="mx-auto max-w-2xl text-center">
        <div className="rounded-lg bg-canvas p-10 shadow-l2">
          <div className="flex justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent">
              <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
                <path d="M4 4h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7L4 15.5v-2.5H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
          <h2 className="mt-4 text-body-lg text-ink">Sign in to start chatting</h2>
          <p className="mt-2 text-body-sm text-body">
            Ask about any public company, financial metrics, or SEC filings.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <a
              href="/signin"
              className="inline-flex h-12 items-center justify-center rounded-pill bg-ink px-8 text-button-lg text-canvas transition-opacity hover:opacity-90"
            >
              Sign In
            </a>
            <a
              href="/signup"
              className="inline-flex h-12 items-center justify-center rounded-pill border border-hairline bg-canvas px-8 text-button-lg text-ink transition-colors hover:bg-canvas-soft"
            >
              Create Account
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col rounded-lg bg-canvas-soft shadow-l2" style={{ minHeight: '600px' }}>
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-hairline bg-canvas px-5 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent-soft text-accent">
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M4 4h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7L4 15.5v-2.5H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-body-sm-strong text-ink">Finora Financial Analyst</p>
            <p className="text-caption text-mute">Ask about any public company</p>
          </div>
        </div>
        <span
          className={
            'inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-mono text-caption-mono tabular-nums ' +
            (remaining === 0
              ? 'bg-error-soft text-error-deep'
              : remaining <= 5
                ? 'bg-warning-soft text-warning-deep'
                : 'bg-canvas-soft-2 text-body')
          }
        >
          {remaining === 0 ? 'Limit reached' : `${remaining} of 15 remaining`}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-5 overflow-y-auto p-5" aria-live="polite">
        {messages.length === 0 && !typing && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-soft text-accent">
              <svg width="28" height="28" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="7" r="4" stroke="currentColor" strokeWidth="1.5" />
                <path d="M3 17.5c0-3.9 3.1-7 7-7s7 3.1 7 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
            <h3 className="mt-4 text-body-lg text-ink">What can I help you with?</h3>
            <p className="mt-2 max-w-sm text-body-sm text-body">
              Ask about any public company's financials, SEC filings, metrics, or business analysis.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {[
                'What are Microsoft\'s key financial metrics?',
                'Compare NVIDIA vs AMD revenue growth',
                'Explain Apple\'s free cash flow trends',
              ].map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => {
                    setInput(q);
                  }}
                  className="rounded-full border border-hairline bg-canvas px-4 py-2 text-caption text-body transition-colors hover:border-hairline-strong hover:text-ink"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <ChatBubble key={i} message={m} />
        ))}

        {typing && (
          <div className="flex animate-fade-up justify-start">
            <div className="max-w-[85%] rounded-lg bg-canvas px-4 py-3 shadow-l1 sm:max-w-[75%]">
              <div className="flex items-center gap-3">
                <div className="flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:300ms]" />
                </div>
                <span className="text-body-sm text-mute">{thinkingText}</span>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Limit banner */}
      {remaining === 0 && (
        <div className="flex items-center justify-between gap-3 border-t border-hairline bg-canvas-soft px-5 py-3">
          <p className="text-caption text-body">
            You've used today's 15 Finora Chat messages. Your allowance resets automatically.
          </p>
          <a
            href="/"
            className="btn-press inline-flex h-8 shrink-0 items-center rounded-sm bg-ink px-3 text-button-md text-canvas hover:opacity-90"
          >
            Start research
          </a>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-hairline bg-canvas p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <div
            className={
              'flex items-center gap-2 rounded-lg border bg-canvas p-2 shadow-l1 transition-[border-color,box-shadow] duration-200 focus-within:shadow-l2 ' +
              (remaining > 0 ? 'border-hairline focus-within:border-hairline-strong' : 'border-hairline/60')
            }
          >
            <input
              type="text"
              name="question"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={remaining > 0 ? 'Ask about any public company…' : 'Daily limit reached'}
              disabled={remaining <= 0}
              autoComplete="off"
              spellCheck={false}
              aria-label="Ask a question"
              className="h-10 w-full min-w-0 bg-transparent px-2 text-body-sm text-ink placeholder:text-mute outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={remaining <= 0 || typing || !input.trim()}
              aria-label="Send message"
              className="btn-press group flex h-9 shrink-0 items-center gap-1.5 rounded-md bg-ink px-4 text-button-md text-canvas hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Send
              <svg
                className="transition-transform duration-200 group-hover:translate-x-0.5"
                width="13"
                height="13"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path d="M2.5 8h10M8.5 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </form>
        <p className="mt-2.5 text-center text-caption text-mute">
          Finora only answers questions about finance, companies, and investing.
        </p>
      </div>
    </div>
  );
}
