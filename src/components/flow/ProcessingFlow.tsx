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
  timeoutMs: number;
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
  'researching': 0, 'resolving_company': 0, 'company_resolved': 0, 'fetching_filings': 0, 'filings_found': 0,
  'fetching_xbrl': 1, 'extracting_financials': 1, 'validating_financials': 1, 'financials_extracted': 1, 'ready_for_calculation': 1,
  'calculating_metrics': 2, 'validating_metrics': 2, 'metrics_calculated': 2, 'ready_for_analysis': 2,
  'fetching_market_data': 3, 'calculating_valuation': 3, 'validating_valuation': 3, 'valuation_complete': 3,
  'discovering_sources': 4, 'filtering_sources': 4, 'validating_sources': 4, 'sources_discovered': 4, 'ready_for_reading': 4,
  'reading_sources': 5, 'extracting_source_facts': 5, 'cross_checking_sources': 5, 'verification_complete': 5,
  'generating_analysis': 6, 'validating_analysis': 6, 'analysis_complete': 6, 'ready_for_dashboard': 7,
};

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (controller.signal.aborted) throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
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
  const abortRef = useRef(false);
  const pipelineStartedRef = useRef(false);

  const runPipeline = useCallback(async () => {
    if (!sessionId || pipelineStartedRef.current) return;
    pipelineStartedRef.current = true;
    abortRef.current = false;
    setRunning(true);

    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    let coreComplete = false;
    const failedSteps: string[] = [];

    for (let i = 0; i < PIPELINE_STEPS.length; i++) {
      if (abortRef.current) return;
      const step = PIPELINE_STEPS[i];
      setCurrentStep(i);
      setStepProgress(0);

      try {
        const res = await fetchWithTimeout(`${BACKEND_URL}${step.apiEndpoint}`, {
          method: 'POST', headers, body: JSON.stringify({ session_id: sessionId }),
        }, step.timeoutMs);

        if (abortRef.current) return;
        if (!res.ok) {
          const errData = await res.json().catch(() => ({ error: 'Unknown error' }));
          throw new Error(errData.error || `Step failed with HTTP ${res.status}`);
        }

        const data = await res.json();
        setStepProgress(1);
        if (data.document_registry?.documents) setFilingsCount(data.document_registry.documents.length);
        if (step.id === 'valuation') coreComplete = true;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'An unknown error occurred';
        if (step.optional || (err instanceof DOMException && err.name === 'AbortError')) {
          failedSteps.push(step.label);
          setStepProgress(1);
          continue;
        }
        if (!coreComplete) { setError(`Failed at "${step.label}": ${msg}`); setRunning(false); return; }
        failedSteps.push(step.label);
        setStepProgress(1);
      }
    }

    if (abortRef.current) return;
    setDone(true);
    setRunning(false);
  }, [sessionId]);

  useEffect(() => { if (sessionId) runPipeline(); return () => { abortRef.current = true; }; }, [sessionId, runPipeline]);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsed(Date.now() - startedAt), 100);
    return () => window.clearInterval(timer);
  }, [startedAt]);

  useEffect(() => {
    if (!sessionId || done || error) return;
    const poll = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/session/${sessionId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === 'cancelled') { setError('Research was cancelled.'); return; }
        if (data.status === 'error') { setError(data.error || 'An error occurred.'); return; }
        const stepIdx = STATUS_TO_STEP[data.status] ?? 0;
        if (stepIdx > currentStep) { setCurrentStep(stepIdx); setStepProgress(1); }
        if (data.document_registry?.documents) setFilingsCount(data.document_registry.documents.length);
        if (data.status === 'ready_for_dashboard') setDone(true);
      } catch {}
    };
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [sessionId, done, error, currentStep]);

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
  const percent = done ? 100 : Math.min(95, Math.round(((currentStep + stepProgress) / totalSteps) * 100));
  const states: StepState[] = PIPELINE_STEPS.map((_, i) => done ? 'done' : i < currentStep ? 'done' : i === currentStep ? 'active' : 'pending');

  const formatElapsed = (ms: number) => {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
  };

  return (
    <div className="mx-auto w-full max-w-xl">
      <div className="border border-ink/20 bg-paper p-8 md:p-10">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="font-serif text-2xl font-semibold text-ink">
              {error ? 'Research failed' : done ? 'Research complete' : `Analyzing ${company}…`}
            </h2>
            <p className="mt-1 truncate font-mono text-[10px] tracking-wider text-ink-3">
              {error ? error : done ? `Found ${filingsCount} relevant filing${filingsCount !== 1 ? 's' : ''} — preparing results.` : PIPELINE_STEPS[currentStep]?.detail || 'Starting research…'}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="font-mono text-[10px] tracking-wider text-ink-3 tabular-nums">{formatElapsed(elapsed)}</span>
            <span className="font-mono text-xs font-bold text-ink tabular-nums">{percent}%</span>
          </div>
        </div>

        <div className="mt-6 h-1.5 w-full overflow-hidden bg-paper-3" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
          <div className="relative h-full w-full origin-left bg-annotate-blue transition-transform duration-300 ease-out" style={{ transform: `scaleX(${percent / 100})` }}>
            <span className="animate-shimmer-bar absolute inset-0" aria-hidden="true" />
          </div>
        </div>

        <ol className="mt-9 space-y-6" aria-live="polite">
          {PIPELINE_STEPS.map((step, i) => (
            <ProgressStep
              key={step.id}
              index={i}
              label={step.label + (step.optional ? ' •' : '')}
              detail={i === currentStep && !done && !error ? PIPELINE_STEPS[currentStep].detail : i < currentStep || done ? `${step.detail} ✓` : step.detail}
              state={states[i]}
              progress={i === currentStep && !done ? stepProgress : 0}
              isLast={i === PIPELINE_STEPS.length - 1}
              lineState={done || states[i + 1] !== 'pending' ? 'fill' : 'idle'}
            />
          ))}
        </ol>

        {error && (
          <div className="mt-8 border border-annotate-red/20 bg-annotate-red/5 p-4">
            <p className="text-sm text-annotate-red">{error}</p>
            <div className="mt-3 flex gap-3">
              <button onClick={() => { setError(''); setDone(false); setRunning(false); setCurrentStep(0); setStepProgress(0); abortRef.current = false; pipelineStartedRef.current = false; }} className="inline-flex h-9 items-center bg-ink px-4 font-mono text-xs font-bold tracking-wider text-paper uppercase hover:bg-ink-2">Retry</button>
              <button onClick={() => { window.location.href = '/'; }} className="inline-flex h-9 items-center border border-ink/40 bg-paper px-4 font-mono text-xs font-bold tracking-wider text-ink uppercase hover:bg-paper-2">Back</button>
            </div>
          </div>
        )}

        {done && !error && (
          <div className="mt-8 border border-annotate-green/20 bg-annotate-green/5 p-4">
            <p className="font-mono text-xs font-bold tracking-wider text-annotate-green">Metrics calculated — ready for analysis.</p>
            <p className="mt-1 font-mono text-[10px] tracking-wider text-annotate-green/80">Taking you to the results dashboard.</p>
          </div>
        )}
      </div>

      <p className="mt-6 text-center font-mono text-[10px] font-semibold tracking-[0.2em] text-ink-3 uppercase">
        {error ? 'Research encountered an error.' : done ? 'Taking you to results…' : 'Do not close this tab — analysis is in progress.'}
      </p>
    </div>
  );
}
