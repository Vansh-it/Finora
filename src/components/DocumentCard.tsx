import { cn } from "../utils/cn";
import type { ReactNode } from "react";

interface DocumentCardProps {
  children: ReactNode;
  className?: string;
  rotate?: number;
}

/** A small paper/document clipping fragment used in editorial collages. */
export default function DocumentCard({ children, className, rotate = 0 }: DocumentCardProps) {
  return (
    <div
      className={cn("border border-ink/25 bg-paper p-4 shadow-[3px_3px_0_0_rgba(17,17,17,0.15)]", className)}
      style={{ transform: `rotate(${rotate}deg)` }}
    >
      {children}
    </div>
  );
}
