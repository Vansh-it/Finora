import type { APIRoute } from 'astro';

export const prerender = false;

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

/**
 * Grant permission endpoint — proxies to Flask to keep sessions unified.
 *
 * The research pipeline runs on Flask and needs to find the session.
 * So session creation must happen on Flask, not in Astro storage.
 */
export const POST: APIRoute = async ({ request }) => {
  try {
    const authHeader = request.headers.get('authorization') || '';
    const body = await request.json();

    const res = await fetch(`${BACKEND_URL}/api/grant-permission`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify(body),
    });

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
