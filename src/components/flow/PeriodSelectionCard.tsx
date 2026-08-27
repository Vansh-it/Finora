import { useState, useCallback } from 'react';

const FISCAL_YEARS = ['2020', '2021', '2022', '2023', '2024', '2025', '2026'];

interface PeriodSelectionCardProps {
  company: string;
  initialMode?: 'latest' | 'specified';
  initialStartYear?: number | null;
  initialEndYear?: number | null;
  onConfirm: (periodMode: 'latest' | 'specified', startYear: number | null, endYear: number | null) => void;
  onCancel: () => void;
}

export default function PeriodSelectionCard({
  company,
  initialMode = 'latest',
  initialStartYear = null,
  initialEndYear = null,
  onConfirm,
  onCancel,
}: PeriodSelectionCardProps) {
  const [mode, setMode] = useState<'latest' | 'specified'>(initialMode);
  const [startYear, setStartYear] = useState<string>(
    initialStartYear != null ? String(initialStartYear) : '2023',
  );
  const [endYear, setEndYear] = useState<string>(
    initialEndYear != null ? String(initialEndYear) : '2025',
  );
  const [error, setError] = useState<string | null>(null);

  const validate = useCallback((): boolean => {
    if (mode === 'latest') {
      setError(null);
      return true;
    }

    const sy = parseInt(startYear, 10);
    const ey = parseInt(endYear, 10);

    if (isNaN(sy) || isNaN(ey)) {
      setError('Please select valid fiscal years.');
      return false;
    }

    if (sy < 2000 || sy > 2030 || ey < 2000 || ey > 2030) {
      setError('Fiscal years must be between 2000 and 2030.');
      return false;
    }

    if (sy > ey) {
      setError('Start year cannot be greater than end year.');
      return false;
    }

    setError(null);
    return true;
  }, [mode, startYear, endYear]);

  const handleConfirm = useCallback(() => {
    if (!validate()) return;
    if (mode === 'latest') {
      onConfirm('latest', null, null);
    } else {
      onConfirm('specified', parseInt(startYear, 10), parseInt(endYear, 10));
    }
  }, [mode, startYear, endYear, validate, onConfirm]);

  return (
    <div className="rounded-lg bg-canvas p-8 shadow-l3 md:p-10">
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <rect x="2.5" y="3.5" width="15" height="13" rx="2" stroke="currentColor" strokeWidth="1.5" />
            <path d="M6.5 2v3M13.5 2v3M2.5 8.5h15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <div>
          <p className="font-mono text-caption-mono uppercase tracking-wide text-accent">// research period</p>
          <h2 className="mt-2 text-display-sm text-ink">Choose research period for {company}</h2>
          <p className="mt-2 text-body-sm text-body">
            Select whether to use the latest available financial data or a specific fiscal-year range.
          </p>
        </div>
      </div>

      {/* Period mode selection */}
      <div className="mt-8 space-y-3">
        <button
          type="button"
          onClick={() => { setMode('latest'); setError(null); }}
          className={
            'w-full rounded-md border p-4 text-left transition-colors ' +
            (mode === 'latest'
              ? 'border-ink bg-ink/5'
              : 'border-hairline bg-canvas hover:border-hairline-strong')
          }
        >
          <div className="flex items-center gap-3">
            <span
              className={
                'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ' +
                (mode === 'latest'
                  ? 'border-ink bg-ink text-canvas'
                  : 'border-hairline')
              }
              aria-hidden="true"
            >
              {mode === 'latest' && (
                <span className="h-2 w-2 rounded-full bg-canvas" />
              )}
            </span>
            <div>
              <p className="text-body-sm-strong text-ink">Latest available</p>
              <p className="mt-0.5 text-caption text-body">
                Use the newest authoritative financial reporting data available.
              </p>
            </div>
          </div>
        </button>

        <button
          type="button"
          onClick={() => setMode('specified')}
          className={
            'w-full rounded-md border p-4 text-left transition-colors ' +
            (mode === 'specified'
              ? 'border-ink bg-ink/5'
              : 'border-hairline bg-canvas hover:border-hairline-strong')
          }
        >
          <div className="flex items-center gap-3">
            <span
              className={
                'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ' +
                (mode === 'specified'
                  ? 'border-ink bg-ink text-canvas'
                  : 'border-hairline')
              }
              aria-hidden="true"
            >
              {mode === 'specified' && (
                <span className="h-2 w-2 rounded-full bg-canvas" />
              )}
            </span>
            <div>
              <p className="text-body-sm-strong text-ink">Specific period</p>
              <p className="mt-0.5 text-caption text-body">
                Analyze filings covering a selected fiscal-year range.
              </p>
            </div>
          </div>
        </button>
      </div>

      {/* Fiscal year selectors (shown when specific period is selected) */}
      {mode === 'specified' && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 animate-fade-up">
          <div>
            <label htmlFor="period-from" className="text-body-sm-strong text-ink">
              From fiscal year
            </label>
            <select
              id="period-from"
              name="period-from"
              value={startYear}
              onChange={(e) => setStartYear(e.target.value)}
              className="mt-2 h-11 w-full rounded-sm border border-hairline bg-canvas px-3 text-body-md text-ink focus:border-hairline-strong"
            >
              {FISCAL_YEARS.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="period-to" className="text-body-sm-strong text-ink">
              To fiscal year
            </label>
            <select
              id="period-to"
              name="period-to"
              value={endYear}
              onChange={(e) => setEndYear(e.target.value)}
              className="mt-2 h-11 w-full rounded-sm border border-hairline bg-canvas px-3 text-body-md text-ink focus:border-hairline-strong"
            >
              {FISCAL_YEARS.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mt-4 rounded-sm border border-error/20 bg-error-soft p-4">
          <p className="text-body-sm text-error">{error}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={handleConfirm}
          className="inline-flex h-12 flex-1 items-center justify-center rounded-pill bg-ink px-6 text-button-lg text-canvas transition-opacity hover:opacity-90"
        >
          Continue
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex h-12 flex-1 items-center justify-center rounded-pill border border-hairline bg-canvas px-6 text-button-lg text-ink transition-colors hover:bg-canvas-soft"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
