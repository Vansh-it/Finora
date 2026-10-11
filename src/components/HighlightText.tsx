import { cn } from "../utils/cn";
import type { ReactNode } from "react";

interface HighlightTextProps {
  children: ReactNode;
  as?: "span" | "div";
  className?: string;
  solid?: boolean;
}

/** Renders text with a fluorescent-yellow highlighter strip behind it, like a physical marker. */
export default function HighlightText({ children, className, solid = false }: HighlightTextProps) {
  if (solid) {
    return (
      <span className={cn("mark-highlight-solid inline-block -rotate-[0.4deg] px-2 py-0.5", className)}>
        {children}
      </span>
    );
  }
  return <span className={cn("mark-highlight", className)}>{children}</span>;
}
