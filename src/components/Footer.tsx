import { useState } from "react";
import { Link } from "react-router-dom";

const NAV_LINKS = [
  { label: "Research", to: "/research" },
  { label: "Dashboard", to: "/dashboard" },
  { label: "History", to: "/history" },
  { label: "Methodology", to: "/methodology" },
];

function XIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

export default function Footer() {
  const [email, setEmail] = useState("");

  return (
    <footer className="px-4 py-4 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-[1440px] rounded-3xl bg-ink px-8 py-14 sm:px-12 lg:px-16">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-[1.5fr_1fr_1.5fr_1fr]">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 font-serif text-3xl font-semibold tracking-tight text-paper">
              <span className="inline-block h-3.5 w-3.5 bg-highlight" aria-hidden />
              Finora
            </div>
            <p className="mt-4 max-w-[220px] font-mono text-xs leading-relaxed tracking-wide text-paper/50">
              AI financial research. Every number traced back to its source.
            </p>
          </div>

          {/* Navigation */}
          <div>
            <h4 className="mb-5 font-mono text-[11px] font-bold tracking-[0.25em] text-paper/40 uppercase">
              Navigation
            </h4>
            <ul className="space-y-3">
              {NAV_LINKS.map((l) => (
                <li key={l.label}>
                  <Link
                    to={l.to}
                    className="font-mono text-sm text-paper/70 transition-colors hover:text-paper"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Who We Are + Subscribe */}
          <div>
            <h4 className="mb-5 font-mono text-[11px] font-bold tracking-[0.25em] text-paper/40 uppercase">
              Who We Are
            </h4>
            <p className="font-serif text-lg leading-snug font-medium text-paper">
              Institutional-grade research, verified line by line.
            </p>

            <h4 className="mb-3 mt-8 font-mono text-[11px] font-bold tracking-[0.25em] text-paper/40 uppercase">
              Get Updates
            </h4>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setEmail("");
              }}
              className="flex items-center overflow-hidden border border-paper/20"
            >
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="E-MAIL"
                className="flex-1 bg-transparent px-4 py-3 font-mono text-xs tracking-widest text-paper placeholder:text-paper/30 focus:outline-none"
              />
              <button
                type="submit"
                className="bg-highlight px-6 py-3 font-mono text-xs font-bold tracking-widest text-ink uppercase transition-colors hover:bg-highlight/90"
              >
                Subscribe
              </button>
            </form>
          </div>

          {/* Socials + SEC Verified */}
          <div>
            <h4 className="mb-5 font-mono text-[11px] font-bold tracking-[0.25em] text-paper/40 uppercase">
              Socials
            </h4>
            <div className="flex items-center gap-4">
              <a href="https://x.com" target="_blank" rel="noreferrer" className="text-paper/60 transition-colors hover:text-paper">
                <XIcon className="h-5 w-5" />
              </a>
              <a href="https://linkedin.com" target="_blank" rel="noreferrer" className="text-paper/60 transition-colors hover:text-paper">
                <LinkedInIcon className="h-5 w-5" />
              </a>
              <a href="https://github.com" target="_blank" rel="noreferrer" className="text-paper/60 transition-colors hover:text-paper">
                <GitHubIcon className="h-5 w-5" />
              </a>
            </div>

            <div className="mt-8">
              <span className="inline-block border border-highlight/60 px-5 py-2.5 font-mono text-[11px] font-bold tracking-[0.2em] text-highlight uppercase">
                SEC Verified
              </span>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-14 flex flex-col gap-3 border-t border-paper/10 pt-6 text-xs text-paper/30 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono tracking-wide">
            © 2025 · Finora · AI financial research, verified.
          </p>
          <div className="flex items-center gap-1 font-mono tracking-wide">
            <Link to="/privacy" className="transition-colors hover:text-paper/60">
              Privacy Policy
            </Link>
            <span>·</span>
            <Link to="/terms" className="transition-colors hover:text-paper/60">
              Terms of Service
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
