import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Quote } from "lucide-react";
import EditorialHeading from "./EditorialHeading";
import HighlightText from "./HighlightText";
import PaperTexture from "./PaperTexture";
import StarRating from "./StarRating";
import { getReviews, type Review } from "../lib/api";

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "";
  }
}

export default function ReviewsSection() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getReviews(3)
      .then((res) => setReviews(res.reviews))
      .catch(() => setReviews([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="relative border-b border-ink/15 bg-paper-2">
      <PaperTexture />
      <div className="mx-auto max-w-[1440px] px-4 py-20 sm:px-6 lg:px-10">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <EditorialHeading size="md">
            What readers
            <br />
            <HighlightText>actually say.</HighlightText>
          </EditorialHeading>
          <Link
            to="/reviews"
            className="inline-flex shrink-0 items-center gap-2 border-b-2 border-ink pb-1 font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase transition-colors hover:border-highlight"
          >
            Read all reviews <ArrowRight size={14} />
          </Link>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {loading ? (
            [0, 1, 2].map((i) => (
              <div key={i} className="h-44 animate-pulse border border-ink/20 bg-paper" />
            ))
          ) : reviews.length === 0 ? (
            <div className="border border-ink/20 bg-paper p-8 md:col-span-3">
              <p className="font-serif text-lg text-ink-2">
                No reviews yet — be the first to tell the world what Finora gets right.
              </p>
              <Link
                to="/reviews"
                className="mt-4 inline-flex items-center gap-2 border-b-2 border-ink pb-1 font-mono text-xs font-bold tracking-[0.15em] text-ink uppercase transition-colors hover:border-highlight"
              >
                Write a review <ArrowRight size={14} />
              </Link>
            </div>
          ) : (
            reviews.map((r) => (
              <article key={r.timestamp + r.name} className="flex flex-col border border-ink/20 bg-paper p-6">
                <Quote size={16} className="text-ink-3" aria-hidden />
                <p className="mt-3 flex-1 font-serif text-base leading-relaxed text-ink italic">
                  {r.review}
                </p>
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
            ))
          )}
        </div>
      </div>
    </section>
  );
}
