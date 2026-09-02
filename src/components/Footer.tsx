import { Link } from "react-router-dom";

const NAV_LINKS = [
  { label: "Research", to: "/research" },
  { label: "Dashboard", to: "/dashboard" },
  { label: "History", to: "/history" },
  { label: "Methodology", to: "/methodology" },
];

export default function Footer() {
  return (
    <footer className="px-4 py-4 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-[1440px] rounded-3xl bg-ink px-8 py-14 sm:px-12 lg:px-16">
        <div className="flex flex-col items-center justify-center gap-12 md:flex-row md:items-center md:justify-between">
          {/* Left: Brand + Navigation (centered vertically & horizontally) */}
          <div className="flex flex-col items-center justify-center gap-10 sm:flex-row sm:items-center sm:gap-16">
            {/* Brand */}
            <div className="text-center sm:text-left">
              <div className="flex items-center justify-center gap-2 font-serif text-3xl font-semibold tracking-tight text-paper sm:justify-start">
                <span className="inline-block h-3.5 w-3.5 bg-highlight" aria-hidden />
                Finora
              </div>
              <p className="mx-auto mt-4 max-w-[240px] font-mono text-xs leading-relaxed tracking-wide text-paper/50 sm:mx-0">
                AI financial research. Every number traced back to its source.
              </p>
            </div>

            {/* Navigation Links - 2x2 Symmetrical Grid */}
            <div>
              <div className="grid grid-cols-2 gap-x-12 gap-y-4 text-center sm:text-left">
                {NAV_LINKS.map((l) => (
                  <Link
                    key={l.label}
                    to={l.to}
                    className="font-mono text-sm text-paper/70 transition-colors hover:text-paper"
                  >
                    {l.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Who We Are */}
          <div className="text-center md:text-right">
            <h4 className="mb-5 font-mono text-[11px] font-bold tracking-[0.25em] text-paper/40 uppercase">
              Who We Are
            </h4>
            <p className="font-serif text-lg leading-snug font-medium text-paper">
              Institutional-grade research, verified line by line.
            </p>
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
