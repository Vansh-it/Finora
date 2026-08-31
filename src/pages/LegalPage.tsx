import { useState } from "react";
import EditorialHeading from "../components/EditorialHeading";

interface Article {
  id: string;
  title: string;
  body: string[];
}

export default function LegalPage({ title, updated, articles }: { title: string; updated: string; articles: Article[] }) {
  const [active, setActive] = useState(articles[0]?.id);

  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-0">
      <p className="font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">Legal</p>
      <EditorialHeading size="md" className="mt-4">
        {title}
      </EditorialHeading>
      <p className="mt-4 font-mono text-xs text-ink-3">Last updated {updated}</p>

      <div className="mt-14 grid grid-cols-1 gap-10 lg:grid-cols-[240px_1fr]">
        <nav className="thin-scroll flex gap-3 overflow-x-auto border-b border-ink/15 pb-3 lg:sticky lg:top-24 lg:flex-col lg:gap-1 lg:self-start lg:border-b-0 lg:pb-0">
          {articles.map((a) => (
            <button
              key={a.id}
              onClick={() => setActive(a.id)}
              className={`shrink-0 border-l-2 px-3 py-2 text-left font-mono text-xs whitespace-nowrap uppercase ${
                active === a.id ? "border-highlight text-ink font-bold" : "border-transparent text-ink-3"
              }`}
            >
              {a.title}
            </button>
          ))}
        </nav>

        <div className="max-w-2xl space-y-14">
          {articles.map((a) => (
            <div key={a.id} id={a.id}>
              <h3 className="font-serif text-2xl font-semibold text-ink">{a.title}</h3>
              <div className="mt-4 space-y-4 text-sm leading-relaxed text-ink-2">
                {a.body.map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
