/**
 * LLM — single model: NVIDIA Nemotron 3.5.
 * Clean and fast. No failover needed.
 */

import 'dotenv/config';
import OpenAI from 'openai';

const NVIDIA_BASE = 'https://integrate.api.nvidia.com/v1';
const MODEL = 'nvidia/nemotron-3.5-lightning-30b-a3b';
const TIMEOUT_MS = 15_000;

function getApiKey(): string {
  return process.env.NVIDIA_API_KEY || '';
}

export async function generateText(prompt: string): Promise<{ text: string; provider: string }> {
  if (!prompt?.trim()) throw new Error('prompt must be a non-empty string');

  const apiKey = getApiKey();
  if (!apiKey) throw new Error('NVIDIA_API_KEY not set. Add it to your .env file.');

  const client = new OpenAI({
    apiKey,
    baseURL: NVIDIA_BASE,
    timeout: TIMEOUT_MS,
  });

  const completion = await client.chat.completions.create({
    model: MODEL,
    messages: [{ role: 'user', content: prompt }],
    temperature: 1.0,
    top_p: 0.95,
    max_tokens: 1024,
  });

  const msg = completion.choices[0]?.message;
  if (!msg) throw new Error('empty response');

  const content = msg.content ?? '';
  const reasoning = (msg as any).reasoning_content ?? '';
  const text = content || reasoning;
  if (!text) throw new Error('empty response from API');

  return { text, provider: 'nvidia_nemotron' };
}

export function getProviderStatus() {
  const hasKey = !!getApiKey();
  return {
    providers: [{
      name: 'nvidia_nemotron',
      model: MODEL,
      status: hasKey ? 'healthy' : 'unconfigured',
      available: hasKey,
    }],
    strategy: MODEL,
    active_provider: hasKey ? 'nvidia_nemotron' : 'none',
    available_count: hasKey ? 1 : 0,
  };
}
