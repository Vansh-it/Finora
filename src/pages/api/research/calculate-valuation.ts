import type { APIRoute } from 'astro';

export const prerender = false;

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();

    const res = await fetch(`${BACKEND_URL}/api/research/calculate-valuation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: 'Backend unavailable' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } }
    );
  }
};
