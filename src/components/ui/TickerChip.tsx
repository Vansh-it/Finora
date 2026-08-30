import { cn } from '../../lib/utils';

interface TickerChipProps {
  ticker: string;
  onClick?: () => void;
  active?: boolean;
  className?: string;
}

export default function TickerChip({ ticker, onClick, active, className }: TickerChipProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'border border-ink/70 px-3 py-1.5 font-mono text-xs font-semibold tracking-wider text-ink transition-all hover:-translate-y-0.5 hover:bg-ink hover:text-paper',
        active && 'bg-ink text-paper',
        className
      )}
    >
      {ticker}
    </button>
  );
}
