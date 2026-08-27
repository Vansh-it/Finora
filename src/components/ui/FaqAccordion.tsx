import { useState } from 'react';

interface Props {
  items: { q: string; a: string }[];
}

export default function FaqAccordion({ items }: Props) {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="divide-y divide-hairline rounded-lg bg-canvas shadow-l2">
      {items.map((item, i) => {
        const isOpen = open === i;
        return (
          <div key={item.q}>
            <h3>
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : i)}
                aria-expanded={isOpen}
                aria-controls={`faq-panel-${i}`}
                id={`faq-button-${i}`}
                className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
              >
                <span className="text-body-md-strong text-ink">{item.q}</span>
                <svg
                  className={'shrink-0 text-mute transition-transform duration-200 ' + (isOpen ? 'rotate-180' : '')}
                  width="14"
                  height="14"
                  viewBox="0 0 16 16"
                  fill="none"
                  aria-hidden="true"
                >
                  <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </h3>
            <div
              id={`faq-panel-${i}`}
              role="region"
              aria-labelledby={`faq-button-${i}`}
              className={
                'grid transition-[grid-template-rows,opacity] duration-300 ease-out ' +
                (isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0')
              }
            >
              <div className="overflow-hidden">
                <p className="max-w-2xl px-6 pb-5 text-body-sm text-body">{item.a}</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
