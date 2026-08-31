import { Link } from "react-router-dom";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Research", to: "/research" },
      { label: "Dashboard", to: "/dashboard" },
      { label: "Chat", to: "/chat" },
    ],
  },
  {
    title: "Research",
    links: [
      { label: "Methodology", to: "/methodology" },
      { label: "Data Sources", to: "/dashboard?tab=SOURCES" },
    ],
  },
  {
    title: "Company",
    links: [{ label: "About", to: "/methodology" }],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", to: "/privacy" },
      { label: "Terms", to: "/terms" },
      { label: "Disclaimers", to: "/terms" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-ink/15 bg-paper-2">
      <div className="mx-auto max-w-[1440px] px-4 py-14 sm:px-6 lg:px-10">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div>
            <div className="flex items-center gap-2 font-serif text-4xl font-semibold tracking-tight text-ink">
              <span className="inline-block h-3.5 w-3.5 bg-highlight" aria-hidden />
              Finora.
            </div>
            <p className="mt-3 max-w-xs font-mono text-xs tracking-[0.1em] text-ink-3 uppercase">
              Financial research with receipts.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="mb-4 font-mono text-xs font-bold tracking-[0.2em] text-ink uppercase">{col.title}</h4>
              <ul className="space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <Link to={l.to} className="text-sm text-ink-2 transition-colors hover:text-ink hover:underline">
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 flex flex-col gap-3 border-t border-ink/15 pt-6 text-xs text-ink-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono tracking-wide">© 2026 FINORA LABS</p>
          <p className="max-w-md">Research tool only — not investment advice. Data derived from public filings and market sources.</p>
        </div>
      </div>
    </footer>
  );
}
