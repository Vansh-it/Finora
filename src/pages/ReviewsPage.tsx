import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Quote } from "lucide-react";
import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import PaperTexture from "../components/PaperTexture";
import StarRating, { StarRatingInput } from "../components/StarRating";
import { getReviews, submitReview, type Review } from "../lib/api";

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "";
  }
}

const REVIEW_MIN = 10;
const REVIEW_MAX = 2000;

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [rating, setRating] = useState(0);
  const [review, setReview] = useState("");
  const [honeypot, setHoneypot] = useState("");
  const [pending, setPending] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getReviews(50)
      .then((res) => setReviews(res.reviews))
      .catch(() => setReviews([]))
      .finally(() => setLoading(false));
  }, []);

  function validateClientSide(): string | null {
    if (name.trim().length < 2) return "Please enter your name (at least 2 characters).";
    if (company.trim().length > 80) return "Company is too long (max 80 characters).";
    if (rating < 1 || rating > 5) return "Please choose a star rating from 1 to 5.";
    if (review.trim().length < REVIEW_MIN) return `Please write at least ${REVIEW_MIN} characters.`;
    if (review.trim().length > REVIEW_MAX) return `Review is too long (max ${REVIEW_MAX} characters).`;
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (pending) return;
    setSuccess("");
    setError("");

    const problem = validateClientSide();
    if (problem) {
      setError(problem);
      return;
    }

    setPending(true);
    try {
      const res = await submitReview({
        name: name.trim(),
        company: company.trim(),
        rating,
        review: review.trim(),
        ...(honeypot ? { website: honeypot } : {}),
      });
      setSuccess(res.message || "Thanks! Your review is live.");
      if (res.review) {
        setReviews((prev) => [res.review, ...prev]);
      }
      setName("");
      setCompany("");
      setRating(0);
      setReview("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong — please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      {/* Header */}
      <section className="relative border-b border-ink/15">
        <PaperTexture />
        <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6 lg:px-0">
          <p className="mb-4 font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">
            Reviews
          </p>
          <EditorialHeading size="md">
            What readers
            <br />
            <HighlightText>actually say.</HighlightText>
          </EditorialHeading>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-ink-2">
            Every review below was written by a real Finora reader and posted to our shared
            review sheet — unedited, in the order they arrived.
          </p>
        </div>
      </section>

      {/* Review list */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-0">
        {loading ? (
          <div className="py-20 text-center">
            <div className="inline-block h-6 w-6 animate-spin border-2 border-ink border-t-transparent" />
            <p className="mt-4 font-mono text-sm text-ink-3">Loading reviews...</p>
          </div>
        ) : reviews.length === 0 ? (
          <div className="border border-ink/20 bg-paper-2 p-10 text-center">
            <p className="font-serif text-xl text-ink">Be the first to review Finora.</p>
            <p className="mt-2 text-sm text-ink-2">
              Share what works, what doesn't, and what you'd like to see next.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {reviews.map((r) => (
              <article key={r.timestamp + r.name} className="flex flex-col border border-ink/20 bg-paper p-6">
                <Quote size={16} className="text-ink-3" aria-hidden />
                <p className="mt-3 flex-1 font-serif text-base leading-relaxed text-ink italic">{r.review}</p>
                <div className="mt-5 border-t border-ink/15 pt-4">
                  <StarRating rating={r.rating} />
                  <div className="mt-2 flex items-baseline justify-between gap-2">
                    <p className="font-mono text-xs font-bold tracking-wide text-ink">
                      {r.name}
                      {r.company ? <span className="font-normal text-ink-3"> · {r.company}</span> : null}
                    </p>
                    <p className="font-mono text-[10px] text-ink-3">{formatDate(r.timestamp)}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Submit form */}
      <section className="border-t border-ink/15 bg-paper-2">
        <PaperTexture />
        <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-0">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-[1fr_1.4fr]">
            <div>
              <EditorialHeading size="md">
                Write
                <br />
                <HighlightText>yours.</HighlightText>
              </EditorialHeading>
              <p className="mt-6 max-w-sm text-sm leading-relaxed text-ink-2">
                No account needed. Reviews appear on this page the moment they're posted —
                five per hour per network, plain text only.
              </p>
              <Link
                to="/research"
                className="mt-6 inline-flex items-center gap-2 border-b-2 border-ink pb-1 font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase transition-colors hover:border-highlight"
              >
                Try a research first <ArrowRight size={14} />
              </Link>
            </div>

            <form
              onSubmit={handleSubmit}
              className="border-2 border-ink bg-paper p-6 sm:p-8"
              noValidate
            >
              {success && (
                <div className="mb-6 flex items-start gap-3 border border-annotate-green bg-paper-2 p-4">
                  <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-annotate-green" />
                  <div>
                    <p className="font-mono text-xs font-bold tracking-[0.15em] text-annotate-green uppercase">
                      Review published
                    </p>
                    <p className="mt-1 text-sm text-ink-2">{success}</p>
                  </div>
                </div>
              )}
              {error && (
                <div className="mb-6 border border-annotate-red bg-paper-2 p-4">
                  <p className="font-mono text-xs font-bold tracking-[0.15em] text-annotate-red uppercase">
                    Hold on
                  </p>
                  <p className="mt-1 text-sm text-ink-2">{error}</p>
                </div>
              )}

              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <label className="block">
                  <span className="font-mono text-[11px] font-bold tracking-[0.15em] text-ink-2 uppercase">
                    Your name *
                  </span>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    maxLength={80}
                    placeholder="Jane Analyst"
                    className="mt-2 w-full border border-ink/40 bg-paper px-3 py-2.5 text-sm text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
                  />
                </label>
                <label className="block">
                  <span className="font-mono text-[11px] font-bold tracking-[0.15em] text-ink-2 uppercase">
                    Company / role
                  </span>
                  <input
                    type="text"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    maxLength={80}
                    placeholder="Optional"
                    className="mt-2 w-full border border-ink/40 bg-paper px-3 py-2.5 text-sm text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
                  />
                </label>
              </div>

              <div className="mt-5">
                <span className="font-mono text-[11px] font-bold tracking-[0.15em] text-ink-2 uppercase">
                  Rating *
                </span>
                <div className="mt-2">
                  <StarRatingInput value={rating} onChange={setRating} />
                </div>
              </div>

              <label className="mt-5 block">
                <span className="flex items-baseline justify-between">
                  <span className="font-mono text-[11px] font-bold tracking-[0.15em] text-ink-2 uppercase">
                    Your review *
                  </span>
                  <span className="font-mono text-[10px] text-ink-3">
                    {review.trim().length} / {REVIEW_MAX}
                  </span>
                </span>
                <textarea
                  value={review}
                  onChange={(e) => setReview(e.target.value)}
                  rows={5}
                  maxLength={REVIEW_MAX}
                  placeholder="What worked, what didn't, and what you'd tell a colleague about Finora..."
                  className="mt-2 w-full resize-y border border-ink/40 bg-paper px-3 py-2.5 text-sm leading-relaxed text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
                />
              </label>

              {/* Honeypot — invisible to humans, irresistible to bots */}
              <div
                className="absolute overflow-hidden"
                aria-hidden
                style={{ position: "absolute", top: "-9999px", left: "-9999px", height: 0, width: 0 }}
              >
                <label>
                  Leave this field empty
                  <input
                    type="text"
                    value={honeypot}
                    onChange={(e) => setHoneypot(e.target.value)}
                    tabIndex={-1}
                    autoComplete="off"
                  />
                </label>
              </div>

              <button
                type="submit"
                disabled={pending}
                className="mt-6 inline-flex items-center gap-2 border-2 border-ink bg-ink px-6 py-3 font-mono text-xs font-bold tracking-[0.15em] text-paper uppercase transition-colors hover:bg-paper hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
              >
                {pending ? (
                  <>
                    <span className="inline-block h-3.5 w-3.5 animate-spin border-2 border-paper border-t-transparent" />
                    Posting...
                  </>
                ) : (
                  <>
                    Post review <ArrowRight size={14} />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
}
