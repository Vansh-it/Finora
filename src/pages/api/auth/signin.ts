import type { APIRoute } from 'astro';
import { signIn } from '../../../lib/server/auth';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const email = body.email ?? '';
    const password = body.password ?? '';

    if (!email || !password) {
      return new Response(
        JSON.stringify({ error: 'Email and password are required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    const result = await signIn(email, password);
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message || 'Sign in failed' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
