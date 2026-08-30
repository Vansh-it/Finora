import { useEffect, useState, useRef, useCallback } from 'react';
import ProgressStep from './ProgressStep';
import type { StepState } from './ProgressStep';
import { getToken } from '../../lib/auth';

const BACKEND_URL = '';

interface ProcessingFlowProps {
  company?: string;
  sessionId?: string;
}

interface PipelineStep {
  id: string;
  label: string;
  detail: string;
  apiEndpoint: string;
  /** Hard timeout in ms. 0 = no timeout (not recommended). */
  timeoutMs: number;
  /** If true, failure is non-blocking — pipeline continues. */
  optional: boolean;
}

const CORE_STEPS: PipelineStep[] = [
  { id: 'resolve', label: 'Resolving SEC entity', detail: 'Looking up company in SEC database', apiEndpoint: '/api/research/fetch-filings', timeoutMs: 30_000, optional: false },
  { id: 'extract', label: 'Reading latest 10-K filings', detail: 'Normalizing XBRL financial statements', apiEndpoint: '/api/research/extract-financials', timeoutMs: 60_000, optional: false },
  { id: 'calculate', label: 'Calculating profitability metrics', detail: 'Computing margins, returns, growth, and cash flow', apiEndpoint: '/api/research/calculate-metrics', timeoutMs: 15_000, optional: false },
  { id: 'valuation', label: 'Fetching current market price', detail: 'Computing P/E, EV/EBITDA, and valuation multiples', apiEndpoint: '/api/research/calculate-valuation', timeoutMs: 30_000, optional: false },
];

const ENRICHMENT_STEPS: PipelineStep[] = [
  { id: 'discover', label: 'Cross-checking official sources', detail: 'Discovering investor relations and earnings reports', apiEndpoint: '/api/research/discover-sources', timeoutMs: 20_000, optional: true },
  { id: 'verify', label: 'Reading and verifying source data', detail: 'Reading reports via Jina and cross-referencing against SEC', apiEndpoint: '/api/research/read-verify-sources', timeoutMs: 30_000, optional: true },
  { id: 'summary', label: 'Generating executive analysis', detail: 'AI interpreting financial research findings', apiEndpoint: '/api/research/generate-summary', timeoutMs: 30_000, optional: true },
];

const PIPELINE_STEPS = [...CORE_STEPS, ...ENRICHMENT_STEPS];

const STATUS_TO_STEP: Record<string, number> = {
  'researching': 0,
  'resolving_company': 0,
  'company_resolved': 0,
  'fetching_filings': 0,
  'filings_found': 0,
  'fetching_xbrl': 1,
  'extracting_financials': 1,
  'validating_financials': 1,
  'financials_extracted': 1,
  'ready_for_calculation': 1,
  'calculating_metrics': 2,
  'validating_metrics': 2,
  'metrics_calculated': 2,
  'ready_for_analysis': 2,
  'fetching_market_data': 3,
  'calculating_valuation': 3,
  'validating_valuation': 3,
  'valuation_complete': 3,
  'discovering_sources': 4,
  'filtering_sources': 4,
  'validating_sources': 4,
  'sources_discovered': 4,
  'ready_for_reading': 4,
  'reading_sources': 5,
  'extracting_source_facts': 5,
  'cross_checking_sources': 5,
  'verification_complete': 5,
  'generating_analysis': 6,
  'validating_analysis': 6,
  'analysis_complete': 6,
  'ready_for_dashboard': 7,
};

function logStage(label: string, phase: 'START' | 'END', elapsedMs?: number) {
  const tag = `⏱️ [pipeline] ${label}`;
  if (phase === 'START') {
    console.log(`${tag} START`);
  } else {
    console.log(`${tag} END (${elapsedMs != null ? `${elapsedMs}ms` : 'unknown'})`);
  }
}

/** Fetch with timeout via AbortController */
async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  signal?: AbortSignal,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Link to external abort signal if provided
  if (signal) {
    signal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    return res;
  } catch (err) {
    if (controller.signal.aborted && !(signal?.aborted)) {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export default function ProcessingFlow({ company = 'Microsoft', sessionId }: ProcessingFlowProps) {
  const [startedAt] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);
  const [done, setDone] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [stepProgress, setStepProgress] = useState(0);
  const [error, setError] = useState('');
  const [filingsCount, setFilingsCount] = useState(0);
  const [running, setRunning] = useState(false);

  // Separate refs: abortRef is ONLY toggled on actual unmount
  const abortRef = useRef(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pipelineStartedRef = useRef(false);

  const runPipeline = useCallback(async () => {
    if (!sessionId || pipelineStartedRef.current) return;
    pipelineStartedRef.current = true;
    abortRef.current = false;

    console.log(`⏱️ [pipeline] Pipeline started for session ${sessionId.slice(0, 8)}...`);
    const pipelineStart = Date.now();

    setRunning(true);
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    let coreComplete = false;
    const failedSteps: string[] = [];

    for (let i = 0; i < PIPELINE_STEPS.length; i++) {
      if (abortRef.current) {
        console.log(`⏱️ [pipeline] ABORTED at step ${i}`);
        return;
      }

      const step = PIPELINE_STEPS[i];
      setCurrentStep(i);
      setStepProgress(0);

      const stepStart = Date.now();
      logStage(step.label, 'START');

      try {
        const res = await fetchWithTimeout(
          `${BACKEND_URL}${step.apiEndpoint}`,
          {
            method: 'POST',
            headers,
            body: JSON.stringify({ session_id: sessionId }),
          },
          step.timeoutMs,
        );

        if (abortRef.current) return;

        const elapsedStep = Date.now() - stepStart;
        logStage(step.label, 'END', elapsedStep);

        if (!res.ok) {
          const errData = await res.json().catch(() => ({ error: 'Unknown error' }));
          throw new Error(errData.error || `Step failed with HTTP ${res.status}`);
        }

        const data = await res.json();
        setStepProgress(1);

        if (data.document_registry?.documents) {
          setFilingsCount(data.document_registry.documents.length);
        }

        // Mark core complete after valuation step
        if (step.id === 'valuation') {
          coreComplete = true;
          console.log(`⏱️ [pipeline] Core pipeline complete in ${Date.now() - pipelineStart}ms`);
        }
      } catch (err) {
        const elapsedStep = Date.now() - stepStart;
        const msg = err instanceof Error ? err.message : 'An unknown error occurred';

        if (step.optional || err instanceof DOMException && err.name === 'AbortError') {
          // Non-critical step failed — log and continue
          console.warn(`⏱️ [pipeline] ENRICHMENT FAILED: ${step.label} (${elapsedStep}ms): ${msg}`);
          failedSteps.push(step.label);
          setStepProgress(1); // visually mark as done
          continue;
        }

        // Critical step failed
        logStage(step.label, 'END', elapsedStep);
        console.error(`⏱️ [pipeline] CRITICAL FAILURE: ${step.label}: ${msg}`);

        if (!coreComplete) {
          // Core pipeline failed — hard error
          setError(`Failed at step "${step.label}": ${msg}`);
          setRunning(false);
          return;
        }
        // Core is done but enrichment step failed — log and continue to dashboard
        console.warn(`⏱️ [pipeline] Enrichment step failed after core complete: ${step.label}: ${msg}`);
        failedSteps.push(step.label);
        setStepProgress(1);
        continue;
      }
    }

    if (abortRef.current) return;
    const totalTime = Date.now() - pipelineStart;
    console.log(`⏱️ [pipeline] All steps complete in ${totalTime}ms. Failed enrichment: ${failedSteps.length ? failedSteps.join(', ') : 'none'}`);
    setDone(true);
    setRunning(false);
  }, [sessionId]);

  // Start pipeline on mount — cleanup only on unmount
  useEffect(() => {
    if (sessionId) {
      runPipeline();
    }
    // Only abort on actual component unmount (not re-render)
    return () => {
      abortRef.current = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [sessionId, runPipeline]);

  // Elapsed timer
  useEffect(() => {
    const timer = window.setInterval(() => {
      setElapsed(Date.now() - startedAt);
    }, 100);
    return () => window.clearInterval(timer);
  }, [startedAt]);

  // Poll session status for UI updates (backup)
  useEffect(() => {
    if (!sessionId || done || error) return;

    const poll = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/session/${sessionId}`);
        if (!res.ok) return;
        const data = await res.json();

        if (data.status === 'cancelled') {
          setError('Research was cancelled.');
          if (pollRef.current) clearInterval(pollRef.current);
          return;
        }

        if (data.status === 'error') {
          setError(data.error || 'An error occurred during research.');
          if (pollRef.current) clearInterval(pollRef.current);
          return;
        }

        const stepIdx = STATUS_TO_STEP[data.status] ?? 0;
        if (stepIdx > currentStep) {
          setCurrentStep(stepIdx);
          setStepProgress(1);
        }

        if (data.document_registry?.documents) {
          setFilingsCount(data.document_registry.documents.length);
        }

        if (data.status === 'ready_for_dashboard') {
          setDone(true);
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // Backend might be busy with pipeline step
      }
    };

    pollRef.current = setInterval(poll, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [sessionId, done, error, currentStep]);

  // Navigate to dashboard on completion
  useEffect(() => {
    if (done) {
      const t = window.setTimeout(() => {
        const params = new URLSearchParams();
        if (sessionId) params.set('session_id', sessionId);
        params.set('company', company);
        window.location.href = `/dashboard?${params.toString()}`;
      }, 3000);
      return () => window.clearTimeout(t);
    }
  }, [done, company, sessionId]);

  const totalSteps = PIPELINE_STEPS.length;
  const percent = done ? 100 : Math.min(95, Math.round(
    ((currentStep + stepProgress) / totalSteps) * 100
  ));

  const states: StepState[] = PIPELINE_STEPS.map((_, i) =>
    done ? 'done' : i < currentStep ? 'done' : i === currentStep ? 'active' : 'pending',
  );

  const formatElapsed = (ms: number) => {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  return (
    <div className="mx-auto w-full max-w-xl">
      <div className="rounded-lg bg-canvas p-8 shadow-l4 md:p-10">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-display-sm text-ink">
              {error
                ? 'Research failed'
                : done
                  ? 'Research complete'
                  : `Analyzing ${company}\u2026`}
            </h2>
            <p className="mt-1 truncate font-mono text-caption-mono text-mute">
              {error
                ? error
                : done
                  ? `Found ${filingsCount} relevant filing${filingsCount !== 1 ? 's' : ''} \u2014 preparing results.`
                  : PIPELINE_STEPS[currentStep]?.detail || 'Starting research\u2026'}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="font-mono text-caption-mono text-mute tabular-nums">
              {formatElapsed(elapsed)}
            </span>
            <span className="font-mono text-caption-mono text-ink tabular-nums">{percent}%</span>
          </div>
        </div>

        <div
          className="mt-6 h-1.5 w-full overflow-hidden rounded-full bg-canvas-soft-2"
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Research progress"
        >
          <div
            className="relative h-full w-full origin-left rounded-full bg-accent transition-transform duration-300 ease-out"
            style={{ transform: `scaleX(${percent / 100})` }}
          >
            <span className="animate-shimmer-bar absolute inset-0 rounded-full" aria-hidden="true" />
          </div>
        </div>

        <ol className="mt-9 space-y-6" aria-live="polite">
          {PIPELINE_STEPS.map((step, i) => (
            <ProgressStep
              key={step.id}
              index={i}
              label={step.label + (step.optional ? ' \u2022' : '')}
              detail={
                i === currentStep && !done && !error
                  ? PIPELINE_STEPS[currentStep].detail
                  : i < currentStep || done
                    ? `${step.detail} \u2713`
                    : step.detail
              }
              state={states[i]}
              progress={i === currentStep && !done ? stepProgress : 0}
              isLast={i === PIPELINE_STEPS.length - 1}
              lineState={done || states[i + 1] !== 'pending' ? 'fill' : 'idle'}
            />
          ))}
        </ol>

        {error && (
          <div className="animate-pop mt-8 rounded-sm border border-error/20 bg-error-soft p-4">
            <p className="text-body-sm text-error">{error}</p>
            <div className="mt-3 flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setError('');
                  setDone(false);
                  setRunning(false);
                  setCurrentStep(0);
                  setStepProgress(0);
                  abortRef.current = false;
                  pipelineStartedRef.current = false;
                }}
                className="inline-flex h-9 items-center rounded-pill bg-ink px-4 text-button-md text-canvas hover:opacity-90"
              >
                Retry
              </button>
              <button
                type="button"
                onClick={() => { window.location.href = '/'; }}
                className="inline-flex h-9 items-center rounded-pill border border-hairline bg-canvas px-4 text-button-md text-ink hover:bg-canvas-soft"
              >
                Back to research
              </button>
            </div>
          </div>
        )}

        {done && !error && (
          <div className="animate-pop mt-8 rounded-sm border border-up/20 bg-up/10 p-4">
            <p className="text-body-sm-strong text-up">
              Metrics calculated \u2014 ready for analysis.
            </p>
            <p className="mt-1 text-caption text-up/80">
              Taking you to the results dashboard.
            </p>
          </div>
        )}
      </div>

      <p className="mt-6 text-center font-mono text-caption-mono text-mute">
        {error
          ? 'Research encountered an error.'
          : done
            ? 'Taking you to results\u2026'
            : 'Do not close this tab \u2014 analysis is in progress.'}
      </p>
    </div>
  );
}
