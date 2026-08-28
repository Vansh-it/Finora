import type { APIRoute } from 'astro';
import { getUserFromToken } from '../../lib/server/auth';
import { createSession, canUseResearch } from '../../lib/server/research-sessions';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  try {
    const authHeader = request.headers.get('authorization') || '';
    const token = authHeader.replace('Bearer ', '');

    if (!token) {
      return new Response(
        JSON.stringify({ error: 'Missing Authorization header' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }

    const user = getUserFromToken(token);
    if (!user) {
      return new Response(
        JSON.stringify({ error: 'Invalid or expired session' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // Check research quota
    const quota = canUseResearch(user.user_id);
    if (!quota.allowed) {
      return new Response(
        JSON.stringify({
          error: `You've used all ${quota.limit} research runs available in this Finora preview.`,
          quota_exhausted: true,
          remaining: 0,
          limit: quota.limit,
        }),
        { status: 429, headers: { 'Content-Type': 'application/json' } },
      );
    }

    const body = await request.json();
    const company = body.company ?? '';

    if (!company || typeof company !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Missing or invalid company' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    let periodMode = body.period_mode ?? 'latest';
    if (periodMode !== 'specified' && periodMode !== 'latest') periodMode = 'latest';

    const session = createSession(user.user_id, company, {
      period_mode: periodMode,
      start_year: body.start_year ?? null,
      end_year: body.end_year ?? null,
      objective: body.objective ?? '',
    });

    return new Response(
      JSON.stringify({
        session_id: session.session_id,
        company: session.company,
        status: session.status,
        period_mode: session.period_mode,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message || 'Failed to grant permission' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
