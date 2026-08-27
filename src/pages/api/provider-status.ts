import type { APIRoute } from 'astro';
import { getProviderStatus } from '../../lib/llm';

export const prerender = false;

export const GET: APIRoute = async () => {
  return new Response(JSON.stringify(getProviderStatus()), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
