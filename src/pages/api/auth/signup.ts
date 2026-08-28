import type { APIRoute } from 'astro';
import { signUp } from '../../../lib/server/auth';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const email = body.email ?? '';
    const password = body.password ?? '';
    const name = body.name ?? '';

    if (!email || !password) {
      return new Response(
        JSON.stringify({ error: 'Email and password are required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    const result = signUp(email, password, name);
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    const status = err.message?.includes('already exists') ? 409 : 400;
    return new Response(
      JSON.stringify({ error: err.message || 'Sign up failed' }),
      { status, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
