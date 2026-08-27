import type { APIRoute } from 'astro';
import { generateText } from '../../lib/llm';

export const prerender = false;

// ── Known companies ─────────────────────────────────────────────────────────
const KNOWN_COMPANIES: Record<string, string> = {
  microsoft: 'Microsoft', msft: 'Microsoft',
  apple: 'Apple', aapl: 'Apple',
  google: 'Alphabet', alphabet: 'Alphabet', googl: 'Alphabet', goog: 'Alphabet',
  amazon: 'Amazon', amzn: 'Amazon',
  nvidia: 'NVIDIA', nvda: 'NVIDIA',
  meta: 'Meta', facebook: 'Meta', 'meta platforms': 'Meta',
  tesla: 'Tesla', tsla: 'Tesla',
  netflix: 'Netflix', nflx: 'Netflix',
  adobe: 'Adobe', adbe: 'Adobe',
  salesforce: 'Salesforce', crm: 'Salesforce',
  oracle: 'Oracle', orcl: 'Oracle',
  ibm: 'IBM',
  intel: 'Intel', intc: 'Intel',
  amd: 'AMD',
  broadcom: 'Broadcom', avgo: 'Broadcom',
  qualcomm: 'Qualcomm', qcom: 'Qualcomm',
  cisco: 'Cisco', csco: 'Cisco',
  palantir: 'Palantir', pltr: 'Palantir',
  snowflake: 'Snowflake', snow: 'Snowflake',
  uber: 'Uber', lyft: 'Lyft',
  shopify: 'Shopify', shop: 'Shopify',
  spotify: 'Spotify', spot: 'Spotify',
  'palo alto': 'Palo Alto Networks', panw: 'Palo Alto Networks',
  servicenow: 'ServiceNow', now: 'ServiceNow',
  intuit: 'Intuit', intu: 'Intuit',
  paypal: 'PayPal', pypl: 'PayPal',
  block: 'Block', square: 'Block', sq: 'Block',
  twilio: 'Twilio', twlo: 'Twilio',
  cloudflare: 'Cloudflare', net: 'Cloudflare',
  zoom: 'Zoom', zm: 'Zoom',
  dell: 'Dell', hp: 'HP',
  jpmorgan: 'JPMorgan Chase', 'jpmorgan chase': 'JPMorgan Chase', jpm: 'JPMorgan Chase',
  goldman: 'Goldman Sachs', 'goldman sachs': 'Goldman Sachs', gs: 'Goldman Sachs',
  'morgan stanley': 'Morgan Stanley', ms: 'Morgan Stanley',
  'bank of america': 'Bank of America', bac: 'Bank of America',
  citigroup: 'Citigroup', citi: 'Citigroup', c: 'Citigroup',
  'wells fargo': 'Wells Fargo', wfc: 'Wells Fargo',
  visa: 'Visa', v: 'Visa',
  mastercard: 'Mastercard', ma: 'Mastercard',
  berkshire: 'Berkshire Hathaway', 'berkshire hathaway': 'Berkshire Hathaway', brk: 'Berkshire Hathaway',
  blackrock: 'BlackRock', blk: 'BlackRock',
  'charles schwab': 'Charles Schwab', schwab: 'Charles Schwab', schw: 'Charles Schwab',
  barclays: 'Barclays', hsbc: 'HSBC', ubs: 'UBS',
  'deutsche bank': 'Deutsche Bank',
  'johnson': 'Johnson & Johnson', 'johnson & johnson': 'Johnson & Johnson', jj: 'Johnson & Johnson',
  'unitedhealth': 'UnitedHealth Group', unh: 'UnitedHealth Group',
  pfizer: 'Pfizer', pfe: 'Pfizer',
  moderna: 'Moderna', mrna: 'Moderna',
  abbvie: 'AbbVie', abbv: 'AbbVie',
  merck: 'Merck', mrk: 'Merck',
  amgen: 'Amgen', amgn: 'Amgen',
  gilead: 'Gilead Sciences', gild: 'Gilead Sciences',
  'eli lilly': 'Eli Lilly', lilly: 'Eli Lilly', lly: 'Eli Lilly',
  abbott: 'Abbott Laboratories', abt: 'Abbott Laboratories',
  'coca-cola': 'Coca-Cola', 'coca cola': 'Coca-Cola', ko: 'Coca-Cola',
  pepsi: 'PepsiCo', pepsico: 'PepsiCo', pep: 'PepsiCo',
  'procter': 'Procter & Gamble', 'procter & gamble': 'Procter & Gamble', pg: 'Procter & Gamble',
  walmart: 'Walmart', wmt: 'Walmart',
  costco: 'Costco', cost: 'Costco',
  mcdonald: "McDonald's", mcdonalds: "McDonald's", mcd: "McDonald's",
  starbucks: 'Starbucks', sbux: 'Starbucks',
  nike: 'Nike', nke: 'Nike',
  disney: 'Disney', dis: 'Disney',
  comcast: 'Comcast', cmcsa: 'Comcast',
  exxon: 'ExxonMobil', exxonmobil: 'ExxonMobil', xom: 'ExxonMobil',
  chevron: 'Chevron', cvx: 'Chevron',
  shell: 'Shell', shel: 'Shell',
  bp: 'BP',
  boeing: 'Boeing', ba: 'Boeing',
  lockheed: 'Lockheed Martin', 'lockheed martin': 'Lockheed Martin', lmt: 'Lockheed Martin',
  caterpillar: 'Caterpillar', cat: 'Caterpillar',
  'taiwan semiconductor': 'TSMC', tsmc: 'TSMC', tsm: 'TSMC',
  samsung: 'Samsung', toyota: 'Toyota', tm: 'Toyota',
  airbnb: 'Airbnb', abnb: 'Airbnb',
  doordash: 'DoorDash', dash: 'DoorDash',
  coinbase: 'Coinbase', coin: 'Coinbase',
  arm: 'ARM Holdings', 'arm holdings': 'ARM Holdings',
  sofi: 'SoFi Technologies', 'sofi technologies': 'SoFi Technologies',
  rivian: 'Rivian', rivn: 'Rivian',
  lucid: 'Lucid', lcid: 'Lucid', nio: 'NIO',
  snap: 'Snap', snapchat: 'Snap',
  pinterest: 'Pinterest', pins: 'Pinterest',
  crowdstrike: 'CrowdStrike', crwd: 'CrowdStrike',
  'at&t': 'AT&T', att: 'AT&T', t: 'AT&T',
  verizon: 'Verizon', vz: 'Verizon',
  't-mobile': 'T-Mobile', tmus: 'T-Mobile',
};

// ── Chat patterns ────────────────────────────────────────────────────────────
const CHAT_EXACT = new Set([
  'hi', 'hello', 'hey', 'howdy', 'sup', 'yo', 'hola', 'thanks', 'thank you',
  'thx', 'ty', 'please', 'ok', 'okay', 'yes', 'no', 'sure', 'cool', 'nice',
  'bye', 'goodbye', 'see you', 'good morning', 'good afternoon', 'good evening',
  "what's up", 'how are you', 'how are you doing', 'help',
]);

const CHAT_STARTS = [
  'what is ', "what's ", 'what are ', 'what does ', 'how do ', 'how does ',
  'how to ', 'can you ', 'could you ', 'tell me about ', 'explain ',
  'define ', 'what do you ', 'do you ', 'is it ', 'are you ',
  'what happened ', 'why do ', 'why is ', "what's the difference ",
  "what's a ", 'what is a ', 'what are the ', 'how much ',
  'who are ', 'how are ', 'who is ', 'tell me ', 'say ', 'give me ',
];

const RESEARCH_VERBS = [
  'research', 'analyze', 'analyse', 'investigate', 'examine', 'study',
  'evaluate', 'assess', 'review', 'get', 'build', 'show', 'display',
  'create', 'generate', 'find', 'look up', 'pull up', 'fetch',
  'prepare', 'compile', 'summarize', 'summarise', 'compare',
];

const RESEARCH_NOUNS = [
  'financial', 'financials', 'revenue', 'earnings', 'income', 'profit',
  'loss', 'balance sheet', 'cash flow', 'metrics', 'ratio', 'ratios',
  'valuation', 'market cap', 'stock', 'share price', 'dividend',
  'filing', '10-k', '10-q', 'sec', 'edgar', 'fiscal',
  'annual report', 'quarterly', 'dashboard', 'report',
];

// ── Year extraction ──────────────────────────────────────────────────────────
const YEAR_RANGE_RE = /(?:fy|fiscal\s+year\s+)?(\d{4})\s*[-–—to]+\s*(?:fy|fiscal\s+year\s+)?(\d{4})/i;
const SINGLE_YEAR_RE = /(?:fy|fiscal\s+year\s+)?(\d{4})/i;

function extractYears(text: string): { startYear: number | null; endYear: number | null; periodMode: string } {
  const rangeMatch = text.match(YEAR_RANGE_RE);
  if (rangeMatch) {
    const y1 = parseInt(rangeMatch[1]), y2 = parseInt(rangeMatch[2]);
    if (y1 >= 2000 && y1 <= 2099 && y2 >= 2000 && y2 <= 2099) {
      return { startYear: y1, endYear: y2, periodMode: 'specified' };
    }
  }
  const singleMatch = text.match(SINGLE_YEAR_RE);
  if (singleMatch) {
    const y = parseInt(singleMatch[1]);
    if (y >= 2000 && y <= 2099) {
      return { startYear: y, endYear: y, periodMode: 'specified' };
    }
  }
  return { startYear: null, endYear: null, periodMode: 'latest' };
}

// ── Company extraction ───────────────────────────────────────────────────────
function extractCompany(text: string, knownOnly = false): string {
  let lower = text.toLowerCase().trim();

  // Remove common prefixes
  const prefixes = [
    'research ', 'analyze ', 'analyse ', 'investigate ', 'examine ',
    'study ', 'evaluate ', 'assess ', 'review ', 'get ', 'build ',
    'show ', 'display ', 'create ', 'generate ', 'find ',
    'look up ', 'pull up ', 'fetch ', 'prepare ', 'compile ',
    'summarize ', 'summarise ', 'compare ', 'company ', 'stock ',
    'financials for ', 'financials of ', 'report on ', 'report for ',
    'dashboard for ', 'dashboard of ',
  ];
  for (const prefix of prefixes) {
    if (lower.startsWith(prefix)) {
      lower = lower.slice(prefix.length);
      break;
    }
  }

  // Remove year patterns
  lower = lower.replace(YEAR_RANGE_RE, '').trim();
  lower = lower.replace(SINGLE_YEAR_RE, '').trim();

  // Remove trailing research words
  const suffixes = [
    ' financials', ' financial', ' research', ' analysis',
    ' latest', ' report', ' dashboard', ' earnings',
    ' stock', ' income', ' revenue', ' fiscal',
  ];
  for (const suffix of suffixes) {
    if (lower.endsWith(suffix)) {
      lower = lower.slice(0, -suffix.length).trim();
      break;
    }
  }

  // Remove possessive
  lower = lower.replace(/'s\b/, '').trim();
  if (lower.endsWith('s') && lower.length > 3) lower = lower.replace(/s$/, '').trim();

  lower = lower.replace(/\s+/g, ' ').trim().replace(/[,.!?;:]+$/, '');
  if (!lower) return '';

  // Direct match
  if (KNOWN_COMPANIES[lower]) return KNOWN_COMPANIES[lower];

  // Substring match with word boundaries for short tickers
  let bestMatch = '';
  let bestName = '';
  for (const [key, name] of Object.entries(KNOWN_COMPANIES)) {
    if (key.length <= 2) {
      const re = new RegExp(`\\b${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`);
      if (re.test(lower) && key.length > bestMatch.length) {
        bestMatch = key;
        bestName = name;
      }
    } else if (lower.includes(key) && key.length > bestMatch.length) {
      bestMatch = key;
      bestName = name;
    }
  }
  if (bestMatch) return bestName;

  // Fallback: guess company from remaining words (only if not knownOnly)
  if (!knownOnly) {
    const cleaned = text.toLowerCase();
    const companyWords: string[] = [];
    const skipWords = new Set(['the', 'a', 'an', 'for', 'of', 'on', 'about', 'latest', 'fy', 'fiscal', 'year', 'years']);
    for (const w of cleaned.split(/\s+/)) {
      const wl = w.replace(/[,.!?;:]/g, '').toLowerCase();
      if (skipWords.has(wl)) continue;
      if (/^\d{4}$/.test(wl)) break;
      companyWords.push(wl);
    }
    if (companyWords.length > 0) {
      const guessed = companyWords.join(' ');
      if (KNOWN_COMPANIES[guessed]) return KNOWN_COMPANIES[guessed];
      return guessed.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }
  }

  return '';
}

// ── Deterministic local classifier ───────────────────────────────────────────
function localClassify(prompt: string): { intent: string; company?: string; period_mode?: string; start_year?: number | null; end_year?: number | null; objective?: string; confidence: number } | null {
  if (!prompt || !prompt.trim()) {
    return { intent: 'chat', confidence: 1.0 };
  }

  const text = prompt.trim();
  const lower = text.toLowerCase().trim();
  const lowerClean = lower.replace(/[.!?;:]+$/, '');

  // 1. Exact chat matches
  if (CHAT_EXACT.has(lowerClean) || CHAT_EXACT.has(lower)) {
    return { intent: 'chat', confidence: 0.99 };
  }

  // 2. Research verb detection
  const hasResearchVerb = RESEARCH_VERBS.some(v => new RegExp(`\\b${v}\\b`, 'i').test(lower));

  // 3. Company extraction (known companies only for classification)
  const companyName = extractCompany(text, true);
  const hasCompany = !!companyName;

  // 4. Period extraction
  const { startYear, endYear, periodMode } = extractYears(text);

  // 5. Strong: research verb + company
  if (hasResearchVerb && hasCompany) {
    return { intent: 'research', company: companyName, period_mode: periodMode, start_year: startYear, end_year: endYear, objective: extractObjective(text), confidence: 0.95 };
  }

  // 6. Company + research noun
  const hasResearchNoun = RESEARCH_NOUNS.some(n => lower.includes(n));
  if (hasCompany && hasResearchNoun) {
    return { intent: 'research', company: companyName, period_mode: periodMode, start_year: startYear, end_year: endYear, objective: extractObjective(text), confidence: 0.90 };
  }

  // 7. Ticker symbol alone
  if (/^[A-Z]{1,5}$/.test(text.trim())) {
    const tickerLower = text.trim().toLowerCase();
    if (KNOWN_COMPANIES[tickerLower]) {
      return { intent: 'research', company: KNOWN_COMPANIES[tickerLower], period_mode: 'latest', confidence: 0.90 };
    }
  }

  // 8. Chat starters
  for (const starter of CHAT_STARTS) {
    if ((lower.startsWith(starter) || lowerClean.startsWith(starter)) && !hasCompany) {
      return { intent: 'chat', confidence: 0.85 };
    }
  }

  // 9. Very short without research signals
  if (lower.split(/\s+/).length <= 2 && !hasCompany) {
    return { intent: 'chat', confidence: 0.80 };
  }

  // 10. Company name alone
  if (hasCompany && !hasResearchVerb && periodMode === 'latest') {
    return { intent: 'research', company: companyName, period_mode: 'latest', confidence: 0.75 };
  }

  return null; // ambiguous
}

function extractObjective(text: string): string {
  let lower = text.toLowerCase().trim();
  for (const verb of RESEARCH_VERBS) {
    lower = lower.replace(new RegExp(`\\b${verb}\\b`, 'gi'), '');
  }
  lower = lower.replace(YEAR_RANGE_RE, '').replace(SINGLE_YEAR_RE, '').replace(/\s+/g, ' ').trim().replace(/[,.!?;:]+$/, '');
  return lower.length > 5 ? lower.slice(0, 100) : 'Financial research';
}

// ── LLM fallback with timeout ────────────────────────────────────────────────
const CLASSIFY_PROMPT = `You are an intent classifier. Given the user's message, classify it into one of exactly two intents: "chat" or "research".

Rules:
- "chat" = greetings, small talk, thank you, jokes, generic conversation.
- "research" = any request about a specific company, financial data, metrics, analysis, or business intelligence.
- NEVER produce markdown. NEVER explain your reasoning.
- NEVER answer the user's question — only classify it.

Output ONLY valid JSON with no trailing text.

For "research" intents, extract:
  "company"        — the company name (string)
  "period_mode"    — "specified" if the user mentions specific years, "latest" if no years are mentioned
  "start_year"     — the start year if mentioned, otherwise null
  "end_year"       — the end year if mentioned, otherwise null
  "objective"      — a short description of what they want to research
  "confidence"     — a float 0-1 indicating your certainty

For "chat" intents:
  "confidence"     — a float 0-1

Examples:

User: Hello
{"intent":"chat","confidence":0.99}

User: Research Microsoft between 2024 and 2025
{"intent":"research","company":"Microsoft","period_mode":"specified","start_year":2024,"end_year":2025,"objective":"financial research","confidence":0.99}

User: Analyze NVIDIA
{"intent":"research","company":"NVIDIA","period_mode":"latest","start_year":null,"end_year":null,"objective":"financial analysis","confidence":0.95}

User: What's the weather like?
{"intent":"chat","confidence":0.95}`;

function stripMarkdownFences(text: string): string {
  return text.trim().replace(/^```(?:json)?\s*\n?/, '').replace(/\n?```\s*$/, '').trim();
}

function stripTrailingCommas(text: string): string {
  return text.replace(/,\s*([}\]])/g, '$1');
}

function extractJson(text: string): Record<string, any> {
  text = stripMarkdownFences(text);
  text = stripTrailingCommas(text);
  try { return JSON.parse(text); } catch { /* continue */ }
  const match = text.match(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/s);
  if (match) {
    try { return JSON.parse(stripTrailingCommas(match[0])); } catch { /* continue */ }
  }
  throw new Error(`Could not parse JSON from LLM output: ${text}`);
}

async function llmClassify(prompt: string, timeoutMs = 8000): Promise<Record<string, any> | null> {
  try {
    const fullPrompt = `${CLASSIFY_PROMPT}\n\nUser: ${prompt.trim()}`;
    const result = await Promise.race([
      generateText(fullPrompt),
      new Promise<never>((_, reject) => setTimeout(() => reject(new Error('timeout')), timeoutMs)),
    ]);
    return extractJson(result.text);
  } catch {
    return null;
  }
}

// ── API endpoint ─────────────────────────────────────────────────────────────
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const prompt = body?.prompt ?? '';

    if (!prompt || typeof prompt !== 'string') {
      return new Response(JSON.stringify({ error: "Missing 'prompt' field" }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const trimmed = prompt.slice(0, 5000);

    // Step 1: Deterministic local classification (instant)
    const localResult = localClassify(trimmed);
    if (localResult) {
      console.log(`[classify-intent] LOCAL intent=${localResult.intent} company=${localResult.company ?? '-'} latency=<1ms`);
      return new Response(JSON.stringify(localResult), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Step 2: Ambiguous — try LLM with timeout
    console.log(`[classify-intent] LLM_CALL prompt="${trimmed.slice(0, 50)}..."`);
    const llmResult = await llmClassify(trimmed, 8000);
    if (llmResult) {
      const intent = llmResult.intent ?? 'chat';
      if (intent === 'research') {
        const company = String(llmResult.company ?? '').trim();
        if (!company) {
          return new Response(JSON.stringify({ intent: 'chat', confidence: 0.5 }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        let periodMode = llmResult.period_mode ?? 'latest';
        if (periodMode !== 'specified' && periodMode !== 'latest') periodMode = 'latest';
        const startYear = llmResult.start_year != null ? Number(llmResult.start_year) : null;
        const endYear = llmResult.end_year != null ? Number(llmResult.end_year) : null;
        const confidence = Math.max(0, Math.min(1, Number(llmResult.confidence ?? 0)));
        return new Response(JSON.stringify({
          intent: 'research', company, period_mode: periodMode,
          start_year: startYear, end_year: endYear,
          objective: String(llmResult.objective ?? '').trim(), confidence,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      const confidence = Math.max(0, Math.min(1, Number(llmResult.confidence ?? 1)));
      return new Response(JSON.stringify({ intent: 'chat', confidence }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    }

    // Step 3: LLM failed — try local best-effort with full company list
    const company = extractCompany(trimmed, false);
    if (company) {
      const { startYear, endYear, periodMode } = extractYears(trimmed);
      console.log(`[classify-intent] LOCAL_FALLBACK intent=research company=${company}`);
      return new Response(JSON.stringify({
        intent: 'research', company, period_mode: periodMode,
        start_year: startYear, end_year: endYear,
        objective: extractObjective(trimmed), confidence: 0.60,
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // Truly ambiguous — default chat
    return new Response(JSON.stringify({ intent: 'chat', confidence: 0.50 }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    console.error('[classify-intent] ERROR:', err?.message ?? err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
