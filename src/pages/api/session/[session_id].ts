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
    const res = await fetch(`${BACKEND_URL}/api/session/${sessionId}`);
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message || 'Failed to connect to backend' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
