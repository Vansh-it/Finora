import type { APIRoute } from 'astro';

export const prerender = false;

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

export const GET: APIRoute = async ({ params }) => {
  const sessionId = params.session_id;
  if (!sessionId) {
    return new Response(JSON.stringify({ error: 'Missing session_id' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/research/result/${sessionId}`);
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    // Fallback to Astro's own session store if Flask is unavailable
    try {
      const { getSession } = await import('../../../../lib/server/research-sessions');
      const session = getSession(sessionId);
      if (!session) {
        return new Response(JSON.stringify({ error: 'Session not found' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (session.status === 'cancelled') {
        return new Response(JSON.stringify({ error: 'Session has been cancelled' }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (session.status === 'error') {
        return new Response(
          JSON.stringify({ error: session.error || 'Research encountered an error' }),
          { status: 500, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (!session.financial_statements) {
        return new Response(
          JSON.stringify({ error: 'Research not yet complete. Please wait.' }),
          { status: 202, headers: { 'Content-Type': 'application/json' } },
        );
      }
      return new Response(
        JSON.stringify({
          session_id: session.session_id,
          company: session.company,
          status: session.status,
          company_meta: session.company_meta,
          financial_statements: session.financial_statements,
          calculated_metrics: session.calculated_metrics,
          executive_summary: session.executive_summary,
          market_data: session.market_data,
          valuation_metrics: session.valuation_metrics,
          source_registry: session.source_registry,
          verification_results: session.verification_results,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    } catch {
      return new Response(
        JSON.stringify({ error: 'Backend unavailable' }),
        { status: 502, headers: { 'Content-Type': 'application/json' } },
      );
    }
  }
};
