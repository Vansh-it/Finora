export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  cites?: string[];
}

export default function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={'flex animate-fade-up ' + (isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={
          'max-w-[85%] rounded-lg px-4 py-3 shadow-l1 sm:max-w-[75%] ' +
          (isUser ? 'bg-ink' : 'bg-canvas')
        }
      >
        <p className={'text-body-sm ' + (isUser ? 'text-canvas' : 'text-ink')}>{message.text}</p>
        {message.cites && message.cites.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            <span
              className={
                'inline-flex items-center gap-1 font-mono text-caption-mono ' +
                (isUser ? 'text-white/80' : 'text-accent')
              }
            >
              {isUser ? null : 'Sources:'}
            </span>
            {message.cites.map((c) => (
              <span
                key={c}
                className={
                  'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-caption-mono transition-colors ' +
                  (isUser ? 'bg-white/15 text-white/80' : 'bg-accent-soft text-accent hover:bg-accent/20')
                }
              >
                <svg width="10" height="10" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M2 10.5V4L7 1.8 12 4v6.5" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                  <path d="M4.5 10.5V6.5h5v4" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                </svg>
                {c}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
