import type { APIRoute } from 'astro';

export const prerender = false;

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const authHeader = request.headers.get('authorization') || '';

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
      JSON.stringify({ error: err.message || 'Failed to grant permission' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
