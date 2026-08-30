import { useState } from 'react';
import { cn } from '../../lib/utils';
import type { ValuationMetric } from '../../lib/dashboardAdapter';

interface ValuationGridProps {
  metrics: ValuationMetric[];
  marketData?: {
    price: number | null;
    price_date: string;
    percent_change: number | null;
    source: string;
  };
  isFinancial?: boolean;
}

export default function ValuationGrid({ metrics, marketData, isFinancial }: ValuationGridProps) {
  const headline = metrics.filter((m) => ['share_price', 'market_cap', 'enterprise_value'].includes(m.metric_id));
  const multiples = metrics.filter((m) => !['share_price', 'market_cap', 'enterprise_value'].includes(m.metric_id));

  return (
    <div className="space-y-8">
      {/* Market data header */}
      {marketData?.price && (
        <div className="border border-ink/20 bg-paper p-6">
          <div className="flex items-baseline gap-4">
            <span className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Share Price</span>
            {marketData.percent_change !== null && marketData.percent_change !== undefined && (
              <span className={cn('font-mono text-xs font-semibold', marketData.percent_change >= 0 ? 'text-annotate-green' : 'text-annotate-red')}>
                {marketData.percent_change >= 0 ? '+' : ''}{marketData.percent_change.toFixed(2)}%
              </span>
            )}
          </div>
          <div className="mt-2 font-serif text-5xl font-semibold text-ink tabular-nums">
            ${typeof marketData.price === 'number' ? marketData.price.toFixed(2) : '—'}
          </div>
          {marketData.price_date && (
            <p className="mt-2 font-mono text-[10px] tracking-widest text-ink-3 uppercase">
              As of {marketData.price_date} · {marketData.source || 'Twelve Data'}
            </p>
          )}
        </div>
      )}

      {/* Headline metrics */}
      {headline.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {headline.map((m, i) => {
            const isNA = m.status === 'unavailable' || m.applicability === 'not_applicable';
            return (
              <div key={i} className={cn('border bg-paper p-5', isNA ? 'border-dashed border-ink/30' : 'border-ink/20')}>
                <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{m.name}</span>
                <div className={cn('mt-2 font-mono text-2xl font-bold tabular-nums', isNA ? 'text-ink-3' : 'text-ink')}>
                  {isNA ? '—' : (m.display_value || '—')}
                </div>
                {isNA && m.reason && (
                  <div className="mt-1 font-mono text-[10px] tracking-widest text-ink-3 uppercase">{m.reason}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Multiples */}
      {multiples.length > 0 && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {multiples.map((m, i) => {
            const isNA = m.status === 'unavailable' || m.applicability === 'not_applicable';
            return (
              <div key={i} className={cn('border bg-paper p-5', isNA ? 'border-dashed border-ink/30' : 'border-ink/20')}>
                <span className="font-mono text-[10px] font-semibold tracking-[0.15em] text-ink-3 uppercase">{m.name}</span>
                <div className={cn('mt-2 font-mono text-xl font-bold tabular-nums', isNA ? 'text-ink-3' : 'text-ink')}>
                  {isNA ? '—' : (m.display_value || '—')}
                </div>
                {isNA && (
                  <div className="mt-1 font-mono text-[10px] tracking-widest text-ink-3 uppercase">
                    {m.applicability === 'not_applicable' ? 'Not Applicable' : 'Data Unavailable'}
                  </div>
                )}
                {!isNA && m.formula && (
                  <div className="mt-2 font-mono text-[9px] text-ink-3 leading-tight">{m.formula}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Financial institution note */}
      {isFinancial && (
        <div className="border border-dashed border-ink/25 bg-paper-2/30 p-4">
          <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">
            Note: Finora applies adjusted methodology for financial institutions. Conventional industrial metrics may not be shown where economically inappropriate.
          </p>
        </div>
      )}

      {!metrics.length && !marketData?.price && (
        <div className="border border-dashed border-ink/25 bg-paper-2/30 p-6 text-center">
          <p className="font-mono text-[10px] tracking-widest text-ink-3 uppercase">Valuation data unavailable for this research session.</p>
        </div>
      )}
    </div>
  );
}
