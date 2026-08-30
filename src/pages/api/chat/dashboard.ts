import type { APIRoute } from 'astro';

export const prerender = false;

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

export const POST: APIRoute = async ({ request }) => {
  const authHeader = request.headers.get('Authorization') ?? '';
  let body: any;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/chat/dashboard`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(60000), // 60s for LLM responses
    });

    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    if (err?.name === 'TimeoutError' || err?.name === 'AbortError') {
      return new Response(JSON.stringify({
        error: 'Finora is thinking deeply. Please try again — the analysis may take a moment.',
        status: 'timeout',
      }), {
        status: 504,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    return new Response(JSON.stringify({
      error: 'Unable to connect to Finora research backend. Please try again.',
      status: 'error',
    }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
