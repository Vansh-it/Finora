import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowRight, Heart } from "lucide-react";
import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import PaperTexture from "../components/PaperTexture";
import Annotation from "../components/Annotation";
import { getToken } from "../lib/auth";
import { getResearchQuota } from "../lib/api";

const TIPS = [
  { n: "01", text: "Use this downtime to plan your next move. Sketch ideas on paper. Let your brain marinate. 🧠" },
  { n: "02", text: "Check out the docs or tutorials. There's always something new to learn." },
  { n: "03", text: "Drink water. Touch grass. Come back fresh tomorrow. 🌱" },
  { n: "04", text: "And hey — if you're feeling generous, share Finora with someone who'd vibe with it. The more people who use it responsibly, the stronger the case gets to upgrade the infra." },
];

function resetCountdown(resetsAt: number): string {
  if (!resetsAt) return "in 24 hours";
  const ms = resetsAt * 1000 - Date.now();
  if (ms <= 0) return "any moment now";
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  return h > 0 ? `in ${h}h ${m}m` : `in ${m}m`;
}

export default function LetterPage() {
  const location = useLocation();
  const stateResetsAt = (location.state as { resets_at?: number } | null)?.resets_at || 0;
  const [resetsAt, setResetsAt] = useState<number>(stateResetsAt);
  // Arriving straight from a 429 means the user is definitely exhausted
  const [exhausted, setExhausted] = useState<boolean | null>(stateResetsAt > 0 ? true : null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    getResearchQuota(token)
      .then((q) => {
        setResetsAt(q.resets_at);
        setExhausted(q.remaining <= 0);
      })
      .catch(() => setExhausted(false));
  }, []);

  return (
    <div className="relative">
      <PaperTexture />

      {/* ── Letter header ─────────────────────────────────────────── */}
      <section className="border-b border-ink/15">
        <div className="mx-auto max-w-3xl px-4 pt-16 pb-10 sm:px-6 lg:px-0">
          <p className="mb-4 font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">
            A letter from the developer
          </p>
          <EditorialHeading size="md">
            Hey Finora Fam <span className="whitespace-nowrap">💜</span>
          </EditorialHeading>

          {exhausted && (
            <div className="mt-8 border-2 border-ink bg-paper-2 p-5">
              <p className="font-mono text-xs font-bold tracking-[0.2em] text-ink uppercase">
                You are out of researches
              </p>
              <p className="mt-2 text-sm leading-relaxed text-ink-2">
                Your 5 free researches for this window are used up. Your quota
                resets{" "}
                <span className="font-semibold text-ink">
                  {resetCountdown(resetsAt)}
                </span>{" "}
                — you can research again then. Everything below is why. 💜
              </p>
            </div>
          )}

          <div className="mt-6 flex flex-wrap gap-4 font-mono text-xs font-bold tracking-widest uppercase">
            <Link
              to="/"
              className="inline-flex items-center gap-2 border-2 border-ink px-5 py-3 text-ink transition-colors hover:bg-ink hover:text-paper"
            >
              Back to Home <ArrowRight size={13} />
            </Link>
            <Link
              to="/history"
              className="inline-flex items-center gap-2 border-2 border-ink/25 px-5 py-3 text-ink-2 transition-colors hover:border-ink hover:text-ink"
            >
              View History <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── The letter ────────────────────────────────────────────── */}
      <section className="mx-auto max-w-3xl px-4 py-14 sm:px-6 lg:px-0">
        <div className="border-2 border-ink bg-paper p-6 shadow-[8px_8px_0_0_#111111] sm:p-10">
          {/* Opening */}
          <p className="font-serif text-xl leading-relaxed text-ink first-letter:float-left first-letter:mt-1 first-letter:mr-3 first-letter:font-serif first-letter:text-6xl first-letter:leading-[0.8] first-letter:font-semibold">
            First off — huge love for being here. Seriously. Every time you open
            Finora, you're not just using an app; you're part of the vibe we're
            trying to build. And that means everything.
          </p>

          <p className="mt-6 font-serif text-lg leading-[1.8] text-ink">
            So, real talk for a sec: Finora started as a late-night, chai-fueled
            passion project. I didn't have a big team, fancy investors, or a war
            chest of cash. Just a laptop, some free-tier cloud credits,
            open-source libraries, and way too much caffeine. 🫠 I built this
            thing from the ground up using only free resources — because I
            believed (and still do) that powerful tools shouldn't be locked
            behind paywalls.
          </p>

          <div className="my-8 flex items-center gap-4">
            <span className="h-px flex-1 bg-ink/15" />
            <span className="font-mono text-[10px] font-bold tracking-[0.3em] text-ink-3 uppercase">
              The hard truth
            </span>
            <span className="h-px flex-1 bg-ink/15" />
          </div>

          <p className="font-serif text-lg leading-[1.8] text-ink">
            But here's the thing about free resources: they come with limits.
            Like, <em>hard</em> limits. Think of it like a free mobile hotspot —
            it works great until you hit the data cap, and then… poof. You're
            stuck buffering. 😅
          </p>

          <p className="mt-5 font-serif text-lg leading-[1.8] text-ink">
            That's exactly what's happening now. The servers running Finora are
            on free tiers, which means they can only handle so many requests per
            day. And thanks to all of you amazing humans using it, we've hit
            that ceiling. Again. (Honestly? Kinda a flex. Y'all are crushing it.
            🔥)
          </p>

          <div className="mt-6 border-l-4 border-highlight bg-paper-2 p-5">
            <p className="font-serif text-lg leading-[1.7] text-ink">
              So if you're seeing the{" "}
              <span className="font-mono text-sm font-bold tracking-wide">
                "Try again in 24 hours"
              </span>{" "}
              message, don't panic. It's not you. It's not a bug. It's just the
              reality of running a labor-of-love project on a student budget.
              The system auto-resets every 24 hours, so come back tomorrow and
              you'll be good to go.
            </p>
          </div>

          <p className="mt-6 font-serif text-lg leading-[1.8] text-ink">
            I know it's frustrating. You're in the flow, you've got ideas
            popping off, and suddenly — wall. I feel that. I've been there. But
            please know this isn't me gatekeeping or trying to annoy you. It's
            literally the max the current setup can handle without crashing for
            everyone.
          </p>

          <p className="mt-5 font-serif text-lg leading-[1.8] text-ink">
            Here's the dream, though: if Finora keeps growing, and if more of you
            stick around, I wanna level this up. Imagine no limits. Faster
            speeds. More features. Maybe even a pro tier that helps fund the
            free tier so it stays free forever. That's the endgame. But we're
            not there yet.
          </p>

          <p className="mt-5 font-serif text-lg leading-[1.8] text-ink">
            Until then, thank you for your patience, your feedback, and your
            energy. You're not just "users." You're the reason this exists. Every
            bug report, every DM, every time you share Finora with a friend — it
            all matters.
          </p>

          {/* Tips */}
          <div className="my-8 border-t border-b border-ink/15 py-8">
            <p className="mb-5 font-mono text-[10px] font-bold tracking-[0.3em] text-ink-3 uppercase">
              A few quick tips while you wait
            </p>
            <ul className="space-y-4">
              {TIPS.map((tip) => (
                <li key={tip.n} className="flex gap-4">
                  <span className="mt-1 font-mono text-xs font-bold text-ink-3">
                    {tip.n}
                  </span>
                  <span className="font-serif text-base leading-relaxed text-ink">
                    {tip.text}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <p className="font-serif text-xl leading-relaxed text-ink">
            This isn't goodbye. It's just{" "}
            <HighlightText>"see you in 24."</HighlightText> 💜
          </p>

          {/* Signature */}
          <div className="mt-10 border-t border-ink/15 pt-8">
            <p className="font-serif text-lg italic leading-relaxed text-ink">
              With love, code, and way too many all-nighters,
              <br />
              <span className="not-italic font-semibold">
                — The Dev Behind Finora
              </span>
            </p>

            <p className="mt-6 font-serif text-base leading-relaxed text-ink-2">
              <span className="font-mono text-xs font-bold tracking-[0.2em] text-ink-3 uppercase">
                P.S.
              </span>{" "}
              No, I'm not a corporation. Yes, I'm one person (for now). Yes, I
              read every message. Yes, I'm working on making this better.
              Promise. 🤞
            </p>
          </div>

          {/* Colophon */}
          <div className="mt-10 flex items-start gap-3 border-2 border-ink bg-paper-2 p-5">
            <Heart size={16} className="mt-0.5 shrink-0 text-red-500" />
            <p className="font-mono text-xs leading-relaxed tracking-wide text-ink">
              Built with ❤️, free tiers, and the belief that tools should
              empower — not exclude.
            </p>
          </div>

          {/* Big sign-off */}
          <div className="mt-10 text-right">
            <p className="font-serif text-3xl leading-tight font-semibold text-ink sm:text-4xl">
              — vansh chaurasia
            </p>
            <p className="mt-1 font-mono text-xs font-bold tracking-[0.3em] text-ink-3 uppercase">
              developer
            </p>
            <div className="mt-4 flex justify-end">
              <Annotation label="Signed" value="Finora, with love" tone="blue" />
            </div>
          </div>
        </div>

        {/* Footer CTA */}
        <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-ink/15 pt-8">
          <p className="font-mono text-xs text-ink-3">
            Your researches reset automatically every 24 hours.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 border-2 border-ink bg-ink px-6 py-3 font-mono text-xs font-bold tracking-widest text-paper uppercase transition-colors hover:bg-ink-2"
          >
            Back to researching <ArrowRight size={13} />
          </Link>
        </div>
      </section>
    </div>
  );
}
