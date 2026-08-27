import { useState, useCallback } from 'react';
import { getToken } from '../../lib/auth';

const BACKEND_URL = '';

interface PermissionCardProps {
  company: string;
  fromYear: string;
  toYear: string;
  objective: string;
  periodMode?: string;
  requiredSources?: string[];
}

export default function PermissionCard({
  company,
  fromYear,
  toYear,
  objective,
  periodMode = 'specified',
  requiredSources = ['Annual Report', 'Quarterly Reports', 'Earnings Releases'],
}: PermissionCardProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGrant = useCallback(async () => {
    if (loading) return; // prevent duplicate clicks
    setLoading(true);
    setError(null);

    try {
      let res: Response;
      try {
        const token = getToken();
        res = await fetch(`${BACKEND_URL}/api/grant-permission`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            company,
            start_year: parseInt(fromYear) || null,
            end_year: parseInt(toYear) || null,
            objective,
          }),
        });
      } catch {
        throw new Error('Unable to connect to the server. Please make sure the backend is running on port 8000.');
      }

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Failed to grant permission');
      }

      // Store session info and navigate to processing
      sessionStorage.setItem('finora_session_id', data.session_id);
      sessionStorage.setItem('finora_company', data.company);
      const processingParams = new URLSearchParams({
        company: encodeURIComponent(company),
        from: fromYear,
        to: toYear,
        objective: encodeURIComponent(objective),
        session_id: data.session_id,
      });
      if (periodMode === 'latest') {
        processingParams.set('period_mode', 'latest');
      }
      window.location.href = `/processing?${processingParams.toString()}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoading(false);
    }
  }, [company, fromYear, toYear, objective, loading]);

  const handleCancel = useCallback(() => {
    window.location.href = '/';
  }, []);

  const period = periodMode === 'latest'
    ? 'Latest available financial reporting data'
    : `FY${fromYear}–FY${toYear}`;

  return (
    <div className="rounded-lg bg-canvas p-8 shadow-l3 md:p-10">
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M10 2.2l6 2.3v4.7c0 3.7-2.5 6.1-6 7.3-3.5-1.2-6-3.6-6-7.3V4.5l6-2.3z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M7.2 10l2 2 3.6-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div>
          <p className="font-mono text-caption-mono uppercase tracking-wide text-accent">// permission</p>
          <h1 className="mt-2 text-display-md text-ink">Grant permission to research {company}</h1>
          <p className="mt-2 text-body-sm text-body">
            To build your dashboard, Finora needs access to publicly available
            documents. Nothing private, nothing sold, and nothing stored
            beyond your research session.
          </p>
        </div>
      </div>

      <ul className="mt-8 space-y-4">
        <li className="flex items-start gap-4 rounded-md border border-hairline p-4">
          <svg className="mt-0.5 shrink-0 text-up" width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div>
            <h2 className="text-body-sm-strong text-ink">Access public financial reports</h2>
            <p className="mt-1 text-caption text-body">Read annual and quarterly filings available in the public domain via SEC EDGAR.</p>
          </div>
        </li>
        <li className="flex items-start gap-4 rounded-md border border-hairline p-4">
          <svg className="mt-0.5 shrink-0 text-up" width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div>
            <h2 className="text-body-sm-strong text-ink">Extract financial statements</h2>
            <p className="mt-1 text-caption text-body">Parse income statement, balance sheet, and cash flow figures with page-level provenance.</p>
          </div>
        </li>
        <li className="flex items-start gap-4 rounded-md border border-hairline p-4">
          <svg className="mt-0.5 shrink-0 text-up" width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div>
            <h2 className="text-body-sm-strong text-ink">Calculate financial metrics</h2>
            <p className="mt-1 text-caption text-body">Compute margins, returns, growth, and cash-flow metrics using standard definitions.</p>
          </div>
        </li>
        <li className="flex items-start gap-4 rounded-md border border-hairline p-4">
          <svg className="mt-0.5 shrink-0 text-up" width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div>
            <h2 className="text-body-sm-strong text-ink">Generate executive summary</h2>
            <p className="mt-1 text-caption text-body">Produce a professional readout of key findings, growth drivers, and risks.</p>
          </div>
        </li>
      </ul>

      <div className="mt-8 rounded-sm bg-canvas-soft p-4 font-mono text-caption-mono text-mute">
        <span className="text-body-sm-strong text-ink">{company}</span>
        {' · '}
        <span>{period}</span>
        {' · '}
        <span>{objective || 'Standard metrics'}</span>
      </div>

      <div className="mt-4 rounded-sm bg-canvas-soft p-4">
        <p className="text-body-sm-strong text-ink">Planned sources</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {requiredSources.map((source) => (
            <span
              key={source}
              className="inline-flex items-center rounded-full border border-hairline bg-canvas px-3 py-1 text-caption text-body"
            >
              {source}
            </span>
          ))}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-sm border border-error/20 bg-error-soft p-4">
          <p className="text-body-sm text-error">{error}</p>
        </div>
      )}

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={handleGrant}
          disabled={loading}
          className="inline-flex h-12 flex-1 items-center justify-center rounded-pill bg-ink px-6 text-button-lg text-canvas transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? 'Starting…' : 'Grant Permission'}
        </button>
        <button
          type="button"
          onClick={handleCancel}
          disabled={loading}
          className="inline-flex h-12 flex-1 items-center justify-center rounded-pill border border-hairline bg-canvas px-6 text-button-lg text-ink transition-colors hover:bg-canvas-soft disabled:cursor-not-allowed disabled:opacity-50"
        >
          Back to research
        </button>
      </div>

      <p className="mt-6 text-center text-caption text-mute">
        You can revoke access at any time. Finora never sells or shares your research.
      </p>
    </div>
  );
}
