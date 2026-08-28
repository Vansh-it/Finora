import type { APIRoute } from 'astro';
import { signOut } from '../../../lib/server/auth';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  try {
    const authHeader = request.headers.get('Authorization') || '';
    const token = authHeader.replace('Bearer ', '');
    if (!token) {
      return new Response(
        JSON.stringify({ error: 'Missing Authorization header' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }
    signOut(token);
    return new Response(JSON.stringify({ status: 'signed_out' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message || 'Sign out failed' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
