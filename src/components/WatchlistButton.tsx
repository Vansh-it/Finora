import { useWatchlist } from "../hooks/useWatchlist";

export default function WatchlistButton({
  ticker,
  name,
  sessionId,
}: {
  ticker: string;
  name: string;
  sessionId?: string;
}) {
  const { add, remove, isWatching } = useWatchlist();
  const watching = isWatching(ticker);

  return (
    <button
      onClick={() =>
        watching ? remove(ticker) : add(ticker, name, sessionId)
      }
      className="border border-ink/30 bg-paper px-4 py-2 font-mono text-xs font-bold tracking-widest text-ink uppercase transition-colors hover:border-ink hover:bg-ink hover:text-paper"
    >
      {watching ? "✓ Watching" : "+ Watchlist"}
    </button>
  );
}
