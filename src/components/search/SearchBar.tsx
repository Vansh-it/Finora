import { useState, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import PeriodSelectionCard from '../flow/PeriodSelectionCard';
import type { HeroExample } from '../../data/site';

const BACKEND_URL = '';

interface Props {
  examples: HeroExample[];
  id?: string;
}

interface IntentResult {
  intent: string;
  company?: string;
  period_mode?: string;
  start_year?: number | null;
  end_year?: number | null;
  objective?: string;
  confidence?: number;
}

interface ResearchPlan {
  status: string;
  company: string;
  period: string;
  period_mode: string;
  start_year: number | null;
  end_year: number | null;
  objective: string;
  required_sources: string[];
  next_action: string;
}

type Phase = 'idle' | 'interpreting' | 'period-selection' | 'plan' | 'chat' | 'error';

const INTERPRETATION_STEPS = [
  'Understanding your request…',
  'Identifying company and research period…',
  'Preparing research plan…',
];

export default function SearchBar({ examples, id = 'hero-search' }: Props) {
  const { token, user } = useAuth();
  const [query, setQuery] = useState('');
  const [phase, setPhase] = useState<Phase>('idle');
  const [stepIndex, setStepIndex] = useState(0);
  const [intentResult, setIntentResult] = useState<IntentResult | null>(null);
  const [researchPlan, setResearchPlan] = useState<ResearchPlan | null>(null);
  const [chatMessage, setChatMessage] = useState('');
  const [error, setError] = useState('');
  const [permissionLoading, setPermissionLoading] = useState(false);

  const animateSteps = useCallback((): Promise<void> => {
    return new Promise((resolve) => {
      let idx = 0;
      const interval = setInterval(() => {
        idx++;
        setStepIndex(idx);
        if (idx >= INTERPRETATION_STEPS.length - 1) {
          clearInterval(interval);
          resolve();
        }
      }, 600);
    });
  }, []);

  const createPlan = useCallback(
    async (periodMode: 'latest' | 'specified', startYear: number | null, endYear: number | null) => {
      if (!intentResult || !intentResult.company) return;

      try {
        const planRes = await fetch(`${BACKEND_URL}/api/create-research-plan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            intent: {
              intent: 'research',
              company: intentResult.company,
              period_mode: periodMode,
              start_year: startYear,
              end_year: endYear,
              objective: intentResult.objective || 'Financial research',
            },
          }),
        });

        const planData: ResearchPlan = await planRes.json();

        if (!planRes.ok) {
          throw new Error('Failed to create research plan');
        }

        setResearchPlan(planData);
        setPhase('plan');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Something went wrong');
        setPhase('error');
      }
    },
    [intentResult],
  );

  const handleSubmit = useCallback(
    async (value: string) => {
      const trimmed = value.trim();
      if (!trimmed) return;

      if (!token) {
        window.location.href = '/signin';
        return;
      }

      setError('');
      setPhase('interpreting');
      setStepIndex(0);

      const animationPromise = animateSteps();

      try {
        let intentRes: Response;
        try {
          intentRes = await fetch(`${BACKEND_URL}/api/classify-intent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: trimmed }),
          });
        } catch {
          throw new Error('Unable to connect to the server. Please make sure the backend is running on port 8000.');
        }

        const intentData: IntentResult = await intentRes.json();

        if (!intentRes.ok) {
          throw new Error(intentData.company || 'Classification failed');
        }

        await animationPromise;

        if (intentData.intent === 'research' && intentData.company) {
          setIntentResult(intentData);
          setPhase('period-selection');
        } else {
          setChatMessage(
            'Looks like you want to chat rather than start company research.'
          );
          setPhase('chat');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Something went wrong');
        setPhase('error');
      }
    },
    [animateSteps, token],
  );

  const handlePeriodConfirm = useCallback(
    async (periodMode: 'latest' | 'specified', startYear: number | null, endYear: number | null) => {
      await createPlan(periodMode, startYear, endYear);
    },
    [createPlan],
  );

  const handlePeriodCancel = useCallback(() => {
    setPhase('idle');
    setIntentResult(null);
    setQuery('');
    setStepIndex(0);
  }, []);

  const handleGrantPermission = useCallback(async () => {
    if (!researchPlan || permissionLoading) return;
    if (!token) {
      window.location.href = '/signin';
      return;
    }
    setPermissionLoading(true);
    try {
      let res: Response;
      try {
        res = await fetch(`${BACKEND_URL}/api/grant-permission`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            company: researchPlan.company,
            start_year: researchPlan.start_year,
            end_year: researchPlan.end_year,
            period_mode: researchPlan.period_mode,
            objective: researchPlan.objective,
          }),
        });
      } catch {
        throw new Error('Unable to connect to the server. Please make sure the backend is running on port 8000.');
      }
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 429 && data.quota_exhausted) {
          throw new Error(data.error || 'You\'ve used all 5 research runs available in this Finora preview.');
        }
        throw new Error(data.error || 'Failed to grant permission');
      }
      sessionStorage.setItem('finora_session_id', data.session_id);
      sessionStorage.setItem('finora_company', data.company);

      const params = new URLSearchParams({
        company: researchPlan.company,
        from: String(researchPlan.start_year ?? ''),
        to: String(researchPlan.end_year ?? ''),
        objective: researchPlan.objective,
        session_id: data.session_id,
      });
      if (researchPlan.period_mode === 'latest') {
        params.set('period_mode', 'latest');
      }
      window.location.href = `/processing?${params.toString()}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setPermissionLoading(false);
    }
  }, [researchPlan, token, permissionLoading]);

  const handleCancel = useCallback(() => {
    setPhase('idle');
    setIntentResult(null);
    setResearchPlan(null);
    setQuery('');
    setStepIndex(0);
  }, []);

  const handleExampleClick = useCallback(
    (ex: HeroExample) => {
      setQuery(`${ex.label} ${ex.objective}`.trim());
      handleSubmit(`${ex.label} ${ex.objective}`.trim());
    },
    [handleSubmit],
  );

  // ── Interpretation state ──────────────────────────────────────────────────
  if (phase === 'interpreting') {
    return (
      <div id={id} className="w-full">
        <div className="rounded-xl border border-hairline bg-canvas p-8 shadow-l3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-soft">
              <svg className="animate-spin text-accent" width="20" height="20" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="2" opacity="0.25" />
                <path d="M10 2a8 8 0 0 1 8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
            <div>
              <p className="font-mono text-caption-mono uppercase tracking-wide text-accent">// interpreting</p>
              <p className="mt-1 text-body-md text-ink transition-all duration-300">
                {INTERPRETATION_STEPS[Math.min(stepIndex, INTERPRETATION_STEPS.length - 1)]}
              </p>
            </div>
          </div>
          <div className="mt-4 flex gap-1.5">
            {INTERPRETATION_STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                  i <= stepIndex ? 'bg-accent' : 'bg-canvas-soft'
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Period selection state ────────────────────────────────────────────────
  if (phase === 'period-selection' && intentResult) {
    return (
      <div id={id} className="w-full">
        <PeriodSelectionCard
          company={intentResult.company || 'Company'}
          initialMode={(intentResult.period_mode as 'latest' | 'specified') || 'latest'}
          initialStartYear={intentResult.start_year}
          initialEndYear={intentResult.end_year}
          onConfirm={handlePeriodConfirm}
          onCancel={handlePeriodCancel}
        />
      </div>
    );
  }

  // ── Research plan / permission state ──────────────────────────────────────
  if (phase === 'plan' && researchPlan) {
    const periodDisplay = researchPlan.period_mode === 'latest'
      ? 'Latest available financial reporting data'
      : researchPlan.period;

    return (
      <div id={id} className="w-full">
        <div className="rounded-xl border border-hairline bg-canvas p-8 shadow-l3">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 2.2l6 2.3v4.7c0 3.7-2.5 6.1-6 7.3-3.5-1.2-6-3.6-6-7.3V4.5l6-2.3z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                <path d="M7.2 10l2 2 3.6-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="font-mono text-caption-mono uppercase tracking-wide text-accent">// permission</p>
              <h2 className="mt-2 text-display-sm text-ink">Grant permission to research {researchPlan.company}</h2>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between rounded-sm bg-canvas-soft px-4 py-3">
              <span className="text-body-sm text-body">Company</span>
              <span className="text-body-sm-strong text-ink">{researchPlan.company}</span>
            </div>
            <div className="flex items-center justify-between rounded-sm bg-canvas-soft px-4 py-3">
              <span className="text-body-sm text-body">Period</span>
              <span className="text-body-sm-strong text-ink">{periodDisplay}</span>
            </div>
            <div className="flex items-center justify-between rounded-sm bg-canvas-soft px-4 py-3">
              <span className="text-body-sm text-body">Objective</span>
              <span className="text-body-sm-strong text-ink">{researchPlan.objective}</span>
            </div>
          </div>

          {user && (
            <div className="mt-4 flex items-center justify-between rounded-sm bg-accent-soft px-4 py-3">
              <span className="text-body-sm text-accent">Research runs remaining</span>
              <span className="text-body-sm-strong text-accent">
                {Math.max(0, user.research_runs_limit - user.research_runs_used)} of {user.research_runs_limit}
              </span>
            </div>
          )}

          <div className="mt-4 rounded-sm bg-canvas-soft p-4">
            <p className="text-body-sm-strong text-ink">Planned sources</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {researchPlan.required_sources.map((source) => (
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

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={handleGrantPermission}
              disabled={permissionLoading}
              className="inline-flex h-12 flex-1 items-center justify-center rounded-pill bg-ink px-6 text-button-lg text-canvas transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {permissionLoading ? 'Starting…' : !token ? 'Sign in to continue' : 'Grant Permission'}
            </button>
            <button
              type="button"
              onClick={handleCancel}
              disabled={permissionLoading}
              className="inline-flex h-12 flex-1 items-center justify-center rounded-pill border border-hairline bg-canvas px-6 text-button-lg text-ink transition-colors hover:bg-canvas-soft disabled:opacity-50"
            >
              Cancel
            </button>
          </div>

          {!token && (
            <p className="mt-3 text-center text-caption text-mute">
              You'll need to sign in before we can start the research.
            </p>
          )}
        </div>
      </div>
    );
  }

  // ── Chat redirect state ───────────────────────────────────────────────────
  if (phase === 'chat') {
    return (
      <div id={id} className="w-full">
        <div className="rounded-xl border border-hairline bg-canvas p-8 shadow-l3 text-center">
          <div className="flex justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent">
              <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
                <path d="M4 4h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7L4 15.5v-2.5H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
          <p className="mt-4 font-mono text-caption-mono uppercase tracking-wide text-accent">// chat</p>
          <h2 className="mt-2 text-body-lg text-ink">{chatMessage}</h2>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <a
              href="/chat"
              className="inline-flex h-12 items-center justify-center rounded-pill bg-ink px-8 text-button-lg text-canvas transition-opacity hover:opacity-90"
            >
              Open Finora Chat
            </a>
            <button
              type="button"
              onClick={handleCancel}
              className="inline-flex h-12 items-center justify-center rounded-pill border border-hairline bg-canvas px-8 text-button-lg text-ink transition-colors hover:bg-canvas-soft"
            >
              Start research instead
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (phase === 'error') {
    return (
      <div id={id} className="w-full">
        <div className="rounded-xl border border-error/20 bg-error-soft p-8 shadow-l3 text-center">
          <p className="text-body-sm text-error">{error}</p>
          <button
            type="button"
            onClick={handleCancel}
            className="mt-4 inline-flex h-10 items-center rounded-pill bg-ink px-6 text-button-md text-canvas transition-opacity hover:opacity-90"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  // ── Default idle state ────────────────────────────────────────────────────
  return (
    <form
      id={id}
      className="w-full"
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit(query);
      }}
      role="search"
      aria-label="Research a public company"
    >
      <div className="flex items-center gap-2 rounded-xl border border-hairline bg-canvas p-2 shadow-l3 transition-[border-color,box-shadow] duration-200 focus-within:border-hairline-strong focus-within:shadow-l4">
        <svg className="ml-3 shrink-0 text-mute" width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="9" cy="9" r="6" stroke="currentColor" strokeWidth="1.6" />
          <path d="M13.5 13.5L17 17" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          name="prompt"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Research any company, ask about financials, or start a conversation…"
          aria-label="Research prompt"
          autoComplete="off"
          spellCheck={false}
          className="h-14 w-full min-w-0 bg-transparent text-body-md text-ink outline-none placeholder:text-mute"
        />
        <button
          type="submit"
          className="btn-press inline-flex h-11 shrink-0 items-center gap-2 rounded-lg bg-ink px-6 text-button-md text-canvas hover:opacity-90"
        >
          Analyze
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {examples.length > 0 && (
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
          <span className="mr-1 font-mono text-caption-mono uppercase tracking-wide text-mute">Try</span>
          {examples.map((ex) => (
            <button
              key={ex.label}
              type="button"
              onClick={() => handleExampleClick(ex)}
              className="btn-press group inline-flex items-center gap-2 rounded-full border border-hairline bg-canvas px-4 py-2 text-caption text-body hover:border-hairline-strong hover:text-ink"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-accent opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" />
              {ex.label}
              <svg
                className="text-mute transition-transform duration-200 group-hover:translate-x-0.5"
                width="11"
                height="11"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
