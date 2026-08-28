import type { APIRoute } from 'astro';
import { generateText } from '../../../lib/llm';

export const prerender = false;

const FINORA_SYSTEM_PROMPT =
  'You are Finora, a professional financial analyst AI assistant. ' +
  'You help users understand public companies, financial statements, SEC filings, ' +
  'accounting, markets, and research. ' +
  'Identify yourself as Finora. Be concise and professional. ' +
  'Never fabricate financial figures. ' +
  'Never claim access to private or company-confidential information. ' +
  'Never pretend a research operation has been completed when it has not. ' +
  'You are especially useful for finance, company analysis, and research.';

const MAX_MESSAGE_LENGTH = 2000;

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const message = body?.message ?? '';
    const history = body?.history ?? [];

    if (!message || typeof message !== 'string' || !message.trim()) {
      return new Response(JSON.stringify({ error: 'Missing or empty message' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const trimmed = message.trim();
    if (trimmed.length > MAX_MESSAGE_LENGTH) {
      return new Response(
        JSON.stringify({ error: `Message too long. Maximum ${MAX_MESSAGE_LENGTH} characters.` }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // Build prompt with history
    const promptParts: string[] = [`System: ${FINORA_SYSTEM_PROMPT}`];
    const limitedHistory = Array.isArray(history) ? history.slice(-10) : [];
    for (const msg of limitedHistory) {
      const role = msg.role === 'assistant' ? 'Assistant' : 'User';
      const content = String(msg.content ?? '').slice(0, 500);
      promptParts.push(`${role}: ${content}`);
    }
    promptParts.push(`User: ${trimmed}`);
    promptParts.push('Assistant:');
    const prompt = promptParts.join('\n');

    const startTime = Date.now();
    const result = await generateText(prompt);
    const elapsedMs = Date.now() - startTime;

    return new Response(
      JSON.stringify({
        response: result.text,
        model_used: result.provider,
        status: 'success',
        elapsed_ms: elapsedMs,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  } catch (err: any) {
    return new Response(
      JSON.stringify({
        error: 'Finora is temporarily unable to respond. Please try again shortly.',
        status: 'error',
      }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
