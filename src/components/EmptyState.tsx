import { Link } from "react-router-dom";
import { FileText } from "lucide-react";

export default function EmptyState({
  title = "No research on the desk.",
  message = "Start with a public company.",
  actionLabel = "Start Research",
  actionTo = "/research",
}: {
  title?: string;
  message?: string;
  actionLabel?: string;
  actionTo?: string;
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-6 py-24 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center border-2 border-dashed border-ink/30">
        <FileText className="text-ink-3" size={26} />
      </div>
      <h2 className="font-serif text-3xl font-semibold text-ink sm:text-4xl">{title}</h2>
      <p className="mt-4 text-sm text-ink-2">{message}</p>
      <Link
        to={actionTo}
        className="mt-8 bg-ink px-6 py-3 font-mono text-xs font-bold tracking-widest text-paper uppercase transition-colors hover:bg-ink-2"
      >
        {actionLabel}
      </Link>
    </div>
  );
}
