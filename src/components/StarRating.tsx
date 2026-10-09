import { useState } from "react";
import { Star } from "lucide-react";
import { cn } from "../utils/cn";

interface StarRatingProps {
  rating: number;
  size?: number;
  className?: string;
}

export default function StarRating({ rating, size = 14, className }: StarRatingProps) {
  return (
    <div className={cn("flex items-center gap-0.5", className)} aria-label={`${rating} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          size={size}
          className={n <= rating ? "fill-highlight text-highlight" : "text-ink/30"}
          aria-hidden
        />
      ))}
    </div>
  );
}

interface StarRatingInputProps {
  value: number;
  onChange: (rating: number) => void;
  id?: string;
}

export function StarRatingInput({ value, onChange, id }: StarRatingInputProps) {
  const [hovered, setHovered] = useState(0);
  const active = hovered || value;

  return (
    <div id={id} className="flex items-center gap-3" role="radiogroup" aria-label="Star rating">
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${n} star${n > 1 ? "s" : ""}`}
            onClick={() => onChange(n)}
            onMouseEnter={() => setHovered(n)}
            onMouseLeave={() => setHovered(0)}
            onFocus={() => setHovered(n)}
            onBlur={() => setHovered(0)}
            className="p-0.5 transition-transform hover:scale-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-annotate-blue"
          >
            <Star
              size={24}
              className={n <= active ? "fill-highlight text-highlight" : "text-ink/30"}
              aria-hidden
            />
          </button>
        ))}
      </div>
      <span className="font-mono text-xs tracking-wider text-ink-3 uppercase">
        {value > 0 ? `${value} / 5` : "tap to rate"}
      </span>
    </div>
  );
}
