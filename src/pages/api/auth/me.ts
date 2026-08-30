import type { APIRoute } from 'astro';
import { getUserFromToken } from '../../../lib/server/auth';

export const prerender = false;

export const GET: APIRoute = async ({ request }) => {
  try {
    const authHeader = request.headers.get('Authorization') || '';
    const token = authHeader.replace('Bearer ', '');
    if (!token) {
      return new Response(
        JSON.stringify({ error: 'Missing Authorization header' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }

    const user = await getUserFromToken(token);
    if (!user) {
      return new Response(
        JSON.stringify({ error: 'Invalid or expired session' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }

    return new Response(
      JSON.stringify({
        user_id: user.user_id,
        email: user.email,
        name: user.name,
        research_runs_used: user.research_runs_used,
        research_runs_limit: user.research_runs_limit,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message || 'Failed to get user' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
