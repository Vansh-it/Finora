import type { APIRoute } from 'astro';

export const prerender = false;

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

export const GET: APIRoute = async ({ request }) => {
  const authHeader = request.headers.get('Authorization') ?? '';
  if (!authHeader) {
    return new Response(JSON.stringify({ error: 'Missing Authorization header' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/chat/usage`, {
      headers: { Authorization: authHeader },
    });
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message || 'Unable to connect to backend' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
