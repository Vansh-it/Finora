import type { APIRoute } from 'astro';
import { getUserFromToken } from '../../../lib/server/auth';
import { recordChatMessage } from '../../../lib/server/chat-usage';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  const authHeader = request.headers.get('Authorization') ?? '';
  const token = authHeader.replace('Bearer ', '');

  if (!token) {
    return new Response(JSON.stringify({ error: 'Missing Authorization header' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const user = await getUserFromToken(token);
    if (!user) {
      return new Response(JSON.stringify({ error: 'Invalid or expired session' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const usage = await recordChatMessage(user.user_id);
    return new Response(JSON.stringify(usage), {
      status: usage.allowed ? 200 : 429,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message || 'Failed to record message' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
