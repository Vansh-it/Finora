import { useState } from 'react';

interface Props {
  links: { label: string; href: string }[];
}

export default function MobileMenu({ links }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open menu"
        aria-expanded={open}
        className="flex h-7 w-7 items-center justify-center rounded-sm border border-hairline bg-canvas text-ink md:hidden"
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M2 4.5h12M2 8h12M2 11.5h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Menu"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            aria-label="Close menu"
            tabIndex={-1}
          />
          <div className="absolute inset-x-3 top-3 rounded-lg bg-canvas p-4 shadow-l5">
            <div className="flex items-center justify-between">
              <span className="text-body-sm-strong text-ink">Menu</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close menu"
                className="flex h-7 w-7 items-center justify-center rounded-sm border border-hairline bg-canvas text-ink"
              >
                <svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
            </div>
            <nav aria-label="Mobile" className="mt-4">
              <ul className="space-y-1">
                {links.map((link) => (
                  <li key={link.href}>
                    <a
                      href={link.href}
                      onClick={() => setOpen(false)}
                      className="block rounded-md px-3 py-2.5 text-body-md text-body transition-colors hover:bg-canvas-soft-2 hover:text-ink"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
            <div className="mt-4 border-t border-hairline pt-4">
              <a
                href="/#hero-search"
                onClick={() => setOpen(false)}
                className="flex h-10 items-center justify-center rounded-md bg-ink text-button-md text-canvas"
              >
                Start a research
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
