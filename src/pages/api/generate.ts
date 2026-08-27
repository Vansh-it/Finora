import type { APIRoute } from 'astro';
import { generateText } from '../../lib/llm';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const prompt = body?.prompt ?? 'Say hello in one short sentence.';

    const startTime = Date.now();
    const result = await generateText(prompt);
    const elapsedMs = Date.now() - startTime;

    return new Response(
      JSON.stringify({
        model: result.provider,
        response: result.text,
        elapsed_ms: elapsedMs,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
