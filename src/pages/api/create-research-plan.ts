import type { APIRoute } from 'astro';

export const prerender = false;

const SOURCE_MAP: Record<string, string[]> = {
  financial: ['Annual Report', 'Quarterly Reports', 'Earnings Releases'],
  revenue: ['Annual Report', 'Quarterly Reports', '10-K Filing'],
  stock: ['10-K Filing', 'Earnings Releases', 'SEC EDGAR Filings'],
  growth: ['Annual Report', 'Quarterly Reports', 'Industry Analyst Reports'],
  overview: ['Annual Report', 'Company Website', 'Press Releases'],
};

const DEFAULT_SOURCES = ['Annual Report', 'Quarterly Reports', 'Earnings Releases'];

function pickSources(objective: string): string[] {
  const lower = objective.toLowerCase();
  for (const [keyword, sources] of Object.entries(SOURCE_MAP)) {
    if (lower.includes(keyword)) return [...sources];
  }
  return [...DEFAULT_SOURCES];
}

function formatPeriod(startYear: number | null, endYear: number | null, periodMode: string): string {
  if (startYear && endYear) {
    if (startYear === endYear) return `FY${startYear}`;
    return `FY${startYear}–FY${endYear}`;
  }
  if (startYear) return `FY${startYear}`;
  if (endYear) return `FY${endYear}`;
  if (periodMode === 'latest') return 'Latest available financial reporting data';
  return 'Unspecified Period';
}

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const intent = body?.intent;
    if (!intent || typeof intent !== 'object') {
      return new Response(JSON.stringify({ error: "Missing or invalid 'intent' object" }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const company = String(intent.company ?? '').trim();
    if (!company) throw new Error("Intent must include a non-empty 'company' field");

    let periodMode = intent.period_mode ?? 'latest';
    if (periodMode !== 'specified' && periodMode !== 'latest') periodMode = 'latest';

    const startYear = intent.start_year != null ? Number(intent.start_year) : null;
    const endYear = intent.end_year != null ? Number(intent.end_year) : null;
    const objective = String(intent.objective ?? '').trim();

    const objectiveTitle = objective ? objective.split(' ').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') : 'General Research';

    return new Response(
      JSON.stringify({
        status: 'awaiting_permission',
        company,
        period: formatPeriod(startYear, endYear, periodMode),
        period_mode: periodMode,
        start_year: startYear,
        end_year: endYear,
        objective: objectiveTitle,
        required_sources: pickSources(objective),
        next_action: 'request_permission',
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
