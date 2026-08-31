import { Link } from "react-router-dom";

export default function ErrorState({
  title = "We lost the paper trail.",
  message = "We couldn't retrieve the required filing.",
  actionLabel = "Try Again",
  onAction,
}: {
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-6 py-24 text-center">
      <span className="mb-4 -rotate-2 border-2 border-annotate-red px-2 py-0.5 font-mono text-[10px] font-bold tracking-widest text-annotate-red uppercase">
        Source Unavailable
      </span>
      <h2 className="font-serif text-3xl font-semibold text-ink sm:text-4xl">{title}</h2>
      <p className="mt-4 text-sm text-ink-2">{message}</p>
      {onAction && (
        <button
          onClick={onAction}
          className="mt-8 border border-ink px-6 py-3 font-mono text-xs font-bold tracking-widest text-ink uppercase transition-colors hover:bg-ink hover:text-paper"
        >
          {actionLabel}
        </button>
      )}
      <Link to="/" className="mt-4 font-mono text-xs text-ink-3 underline underline-offset-4 hover:text-ink">
        Return to Finora
      </Link>
    </div>
  );
}
