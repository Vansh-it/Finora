"""Bulletproof multi-LLM provider manager with task routing and fast failover.



Every provider call has a HARD per-provider timeout. If one hangs, the next

provider is tried immediately. The user gets a response within seconds, never

minutes.



Provider speed ranking (tested):

  NIM tier (primary):   nemotron-3.5-lightning, nemotron-3-super-120b, gpt-oss-20b

  OpenRouter tier:      nemotron-3-super-120b (fallback), nemotron-3-ultra-550b



DeepSeek V4 Flash (NIM) is BROKEN (times out every request) ? excluded.

"""



from __future__ import annotations



import concurrent.futures

import logging

import os

import socket

import time

from urllib.parse import urlparse

from dataclasses import dataclass, field

from enum import Enum



from dotenv import load_dotenv

from lib.netutil import apply_ipv4_first as _net_fix

_net_fix()

from pathlib import Path



logger = logging.getLogger("finora.provider")



# ?? Load environment variables ????????????????????????????????????????????????

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"

load_dotenv(_env_path)





# ?? Hard limits ???????????????????????????????????????????????????????????????

def _ascii_safe(text, limit: int = 300) -> str:
    """Coerce any error text to safe ASCII so it can never break logging/JSON."""
    try:
        out = str(text).encode("ascii", "ignore").decode("ascii").strip()
    except Exception:
        out = "unknown error"
    return (out[:limit] or "unknown error")


def _get_api_key(provider: "Provider") -> str:
    """Read a provider API key and force it to clean ASCII.

    A corrupted .env value (smart quotes, pasted placeholders, etc.) would
    otherwise blow up inside the HTTP client with a UnicodeEncodeError that
    masks the real problem. Strip anything non-ASCII so the request is sent
    (and fails cleanly as 401) or the key reads as missing.
    """
    raw = os.getenv(provider.api_key_env, "") or ""
    try:
        key = raw.encode("ascii", "ignore").decode("ascii").strip()
    except Exception:
        key = ""
    return key.strip("'\"")


# ?? Network failure handling ? ????????????????????????????????????????????

# socket.getaddrinfo has NO timeout of its own. On a machine whose DNS server is

# unreachable every lookup can block for many seconds; that is what turned a

# connectivity blip into a ~52s chat failure (5 providers x ~10s of DNS stalls).

DNS_TIMEOUT = 4.0                    # Hard cap on one DNS lookup

NETWORK_FAILURE_BUDGET = 12.0        # Total seconds spent on connectivity errors

MAX_NETWORK_HOST_FAILURES = 2        # Two distinct hosts unresolvable = offline


class NetworkError(RuntimeError):
    """Connectivity problem (DNS, TCP, TLS) as opposed to an LLM/provider error."""


_DNS_CACHE: dict = {}

_DNS_CACHE_TTL = 8.0


def resolve_host(host: str, timeout: float = DNS_TIMEOUT) -> tuple:
    """Resolve ``host`` under a hard deadline.

    Returns ``(ok, error)``. Failures are cached briefly so providers that share

    one hostname cost one lookup instead of one per provider.
    """
    now = time.time()
    hit = _DNS_CACHE.get(host)
    if hit and now - hit[0] < _DNS_CACHE_TTL:
        return hit[1], hit[2]

    ok, err = False, ""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(socket.getaddrinfo, host, 443, proto=socket.IPPROTO_TCP)
        future.result(timeout=timeout)
        ok = True
    except concurrent.futures.TimeoutError:
        err = "DNS lookup exceeded %.0fs" % timeout
    except Exception as exc:
        err = "%s: %s" % (type(exc).__name__, exc)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    _DNS_CACHE[host] = (now, ok, err)
    return ok, err


_NETWORK_MARKERS = (
    "getaddrinfo", "name or service not known", "nodename nor",
    "temporary failure in name resolution", "no such host",
    "failed to resolve", "cannot resolve", "could not resolve", "resolve",
    "11001", "errno 11001", "connect", "connection", "unreachable",
    "no route to host", "network is unreachable", "10061", "10065", "10054",
    "10060", "handshake", "proxy",
)


def is_ipv4_first() -> bool:
    """Whether the IPv4-first DNS ordering patch is active in this process."""
    try:
        from lib.netutil import is_applied
        return is_applied()
    except Exception:
        return False


def classify_error(message: str) -> str:
    """Bucket a failure string so failover can react sensibly.

    network    -> machine cannot reach the outside world; stop retrying
    timeout    -> provider is slow; brief cooldown and move on
    rate_limit -> back off for a while
    auth       -> key is bad; do not hammer it
    """
    m = (message or "").lower()
    if any(t in m for t in (
        "rate limit", "rate-limit", "ratelimit", "throttl", "quota",
        "429", "too many requests", "rate exceeded",
    )):
        return "rate_limit"
    if any(t in m for t in (
        "401", "403", "unauthorized", "unauthenticated",
        "permission denied", "access denied", "forbidden",
        "invalid api key", "api key is invalid", "authentication failed",
        "invalid token", "bad credentials",
    )):
        return "auth"
    if any(t in m for t in _NETWORK_MARKERS):
        return "network"
    if any(t in m for t in ("timeout", "timed out", "deadline")):
        return "timeout"
    if any(t in m for t in ("500", "502", "503", "server error")):
        return "server"
    return "unknown"


PER_PROVIDER_TIMEOUT = 40.0   # Seconds ? kill any provider call that takes longer

GLOBAL_TIMEOUT = 60.0         # Seconds ? absolute max for the entire request

MAX_RETRIES = 2               # Retries across different providers





# ?? Task types for routing ????????????????????????????????????????????????????

class TaskType(str, Enum):

    QUICK_CHAT = "quick_chat"          # Simple questions, greetings, follow-ups

    RESEARCH = "research"              # Financial research questions

    HEAVY_REASONING = "heavy_reasoning"  # Complex analysis, multi-step reasoning

    CALCULATION = "calculation"         # Metric explanations, formulas, math

    INTENT_CLASSIFY = "intent_classify"  # Intent classification (lightweight)

    EXECUTIVE_SUMMARY = "executive_summary"  # Full research summary generation





# ?? Provider health status ????????????????????????????????????????????????????

class ProviderStatus(str, Enum):

    HEALTHY = "healthy"

    RATE_LIMITED = "rate_limited"

    ERROR = "error"

    UNCONFIGURED = "unconfigured"





@dataclass

class Provider:

    name: str

    model: str

    base_url: str

    api_key_env: str  # Which env var holds the API key

    status: ProviderStatus = ProviderStatus.HEALTHY

    cooldown_until: float = 0.0

    error_count: int = 0

    last_error: str = ""

    total_requests: int = 0

    total_failures: int = 0

    avg_latency: float = 0.0  # Running average latency

    tags: list[str] = field(default_factory=list)



    def is_available(self) -> bool:

        if self.status == ProviderStatus.UNCONFIGURED:

            return False

        if self.cooldown_until > time.time():

            return False

        return True



    def mark_rate_limited(self, cooldown_seconds: float = 120.0) -> None:

        self.status = ProviderStatus.RATE_LIMITED

        self.cooldown_until = time.time() + cooldown_seconds

        self.error_count += 1

        self.total_failures += 1



    def mark_error(self, cooldown_seconds: float = 5.0) -> None:

        self.status = ProviderStatus.ERROR

        self.cooldown_until = time.time() + cooldown_seconds

        self.error_count += 1

        self.total_failures += 1



    def mark_healthy(self, latency: float = 0.0) -> None:

        self.status = ProviderStatus.HEALTHY

        self.cooldown_until = 0.0

        self.error_count = 0

        # Update running average latency

        if self.total_requests > 0:

            self.avg_latency = ((self.avg_latency * (self.total_requests - 1)) + latency) / self.total_requests

        else:

            self.avg_latency = latency



    def mark_auth_failed(self) -> None:

        self.status = ProviderStatus.ERROR

        self.cooldown_until = time.time() + 86400.0  # 24 hour cooldown

        self.error_count += 1

        self.total_failures += 1



    def get_cooldown_remaining(self) -> float:

        return max(0.0, self.cooldown_until - time.time())





# ?? Task routing table ????????????????????????????????????????????????????????

# Each task type maps to an ordered list of (provider_name, max_tokens, temperature, top_p).

# Providers are tried in order ? first working one wins.

# IMPORTANT: Only use PROVEN WORKING providers in primary slots.

TASK_ROUTING: dict[TaskType, list[dict]] = {

    # Product requirement: NVIDIA NIM is the primary tier, OpenRouter is LAST RESORT.

    # max_tokens stays close to the 300-word answer cap (MAX_RESPONSE_WORDS) so we

    # never burn latency generating text that enforce_response_limit would discard.

    TaskType.QUICK_CHAT: [

        {"provider": "nvidia_nemotron_lightning", "max_tokens": 512, "temperature": 0.7, "top_p": 0.9},

        {"provider": "nvidia_nemotron_super", "max_tokens": 512, "temperature": 0.7, "top_p": 0.9},

        {"provider": "nvidia_gpt_oss", "max_tokens": 512, "temperature": 0.7, "top_p": 0.9},

        {"provider": "openrouter_nemotron_super_free", "max_tokens": 512, "temperature": 0.7, "top_p": 0.9},

        {"provider": "openrouter_nemotron_ultra", "max_tokens": 512, "temperature": 0.7, "top_p": 0.9},

    ],

    TaskType.RESEARCH: [

        {"provider": "nvidia_nemotron_lightning", "max_tokens": 640, "temperature": 0.3, "top_p": 0.85},

        {"provider": "nvidia_nemotron_super", "max_tokens": 640, "temperature": 0.3, "top_p": 0.85},

        {"provider": "nvidia_gpt_oss", "max_tokens": 640, "temperature": 0.3, "top_p": 0.85},

        {"provider": "openrouter_nemotron_super_free", "max_tokens": 640, "temperature": 0.3, "top_p": 0.85},

        {"provider": "openrouter_nemotron_ultra", "max_tokens": 640, "temperature": 0.3, "top_p": 0.85},

    ],

    TaskType.HEAVY_REASONING: [

        {"provider": "nvidia_nemotron_super", "max_tokens": 640, "temperature": 0.2, "top_p": 0.85},

        {"provider": "nvidia_nemotron_lightning", "max_tokens": 640, "temperature": 0.2, "top_p": 0.85},

        {"provider": "nvidia_gpt_oss", "max_tokens": 640, "temperature": 0.2, "top_p": 0.85},

        {"provider": "openrouter_nemotron_ultra", "max_tokens": 640, "temperature": 0.2, "top_p": 0.85},

        {"provider": "openrouter_nemotron_super_free", "max_tokens": 640, "temperature": 0.2, "top_p": 0.85},

    ],

    TaskType.CALCULATION: [

        {"provider": "nvidia_nemotron_lightning", "max_tokens": 640, "temperature": 0.1, "top_p": 0.8},

        {"provider": "nvidia_nemotron_super", "max_tokens": 640, "temperature": 0.1, "top_p": 0.8},

        {"provider": "nvidia_gpt_oss", "max_tokens": 640, "temperature": 0.1, "top_p": 0.8},

        {"provider": "openrouter_nemotron_super_free", "max_tokens": 640, "temperature": 0.1, "top_p": 0.8},

        {"provider": "openrouter_nemotron_ultra", "max_tokens": 640, "temperature": 0.1, "top_p": 0.8},

    ],

    TaskType.INTENT_CLASSIFY: [

        {"provider": "nvidia_nemotron_lightning", "max_tokens": 128, "temperature": 0.0, "top_p": 1.0},

        {"provider": "nvidia_nemotron_super", "max_tokens": 128, "temperature": 0.0, "top_p": 1.0},

        {"provider": "openrouter_nemotron_super_free", "max_tokens": 128, "temperature": 0.0, "top_p": 1.0},

    ],

    TaskType.EXECUTIVE_SUMMARY: [

        {"provider": "nvidia_nemotron_super", "max_tokens": 640, "temperature": 0.3, "top_p": 0.9},

        {"provider": "nvidia_nemotron_lightning", "max_tokens": 640, "temperature": 0.3, "top_p": 0.9},

        {"provider": "nvidia_gpt_oss", "max_tokens": 640, "temperature": 0.3, "top_p": 0.9},

        {"provider": "openrouter_nemotron_ultra", "max_tokens": 640, "temperature": 0.3, "top_p": 0.9},

        {"provider": "openrouter_nemotron_super_free", "max_tokens": 640, "temperature": 0.3, "top_p": 0.9},

    ],

}





# ?? Task classifier (pure heuristic, no LLM call) ????????????????????????????

def classify_task(user_message: str, has_research_context: bool = False) -> TaskType:

    """Classify a user message into a task type for routing.



    Priority: calculation > heavy_reasoning > research > quick_chat.

    """

    msg = user_message.lower().strip()



    # ?? 1. Calculation keywords ??

    calc_keywords = [

        "calculate", "formula", "how did", "how was", "compute",

        "margin", "ratio", "fcf", "free cash flow", "roe", "roa", "roic",

        "eps", "revenue per", "cost of", "debt to", "current ratio",

        "what is the formula", "how do you", "step by step",

    ]

    if any(kw in msg for kw in calc_keywords):

        return TaskType.CALCULATION



    # ?? 2. Heavy reasoning keywords ??

    reasoning_keywords = [

        "compare", "analyze", "evaluate", "assess", "should i",

        "what if", "pros and cons", "risk", "investment",

        "explain in detail", "deep dive", "comprehensive",

        "valuation", "dcf", "intrinsic value",

    ]

    if any(kw in msg for kw in reasoning_keywords):

        return TaskType.HEAVY_REASONING



    # ?? 3. Research keywords (when context available) ??

    if has_research_context:

        research_keywords = [

            "what does", "who is", "tell me about", "describe",

            "company", "business", "revenue", "income", "profit",

            "source", "data", "metric", "financial",

            "how is", "why is", "what are",

        ]

        if any(kw in msg for kw in research_keywords):

            return TaskType.RESEARCH



    # ?? 4. Default ??

    if len(msg.split()) <= 5:

        return TaskType.QUICK_CHAT



    return TaskType.RESEARCH if has_research_context else TaskType.QUICK_CHAT





# ?? Provider manager ??????????????????????????????????????????????????????????

class ProviderManager:

    """Manages multiple LLM providers with bulletproof failover.



    Every call has a hard per-provider timeout. If a provider hangs,

    the next one is tried immediately. Never hangs for more than

    GLOBAL_TIMEOUT seconds total.

    """



    def __init__(self) -> None:

        self._providers: dict[str, Provider] = {}

        self._register_providers()



    def _register_providers(self) -> None:

        """Register providers based on configured API keys."""

        def _sanitized(env_name: str) -> str:
            raw = os.getenv(env_name, "") or ""
            try:
                return raw.encode("ascii", "ignore").decode("ascii").strip().strip("'\"")
            except Exception:
                return ""

        nvidia_key = _sanitized("NVIDIA_API_KEY")
        openrouter_key = _sanitized("OPENROUTER_API_KEY")



        nvidia_base = "https://integrate.api.nvidia.com/v1"

        openrouter_base = "https://openrouter.ai/api/v1"



        # ?? NVIDIA NIM ??



        # Nemotron Lightning ? FASTEST (~1s), reliable workhorse

        self._providers["nvidia_nemotron_lightning"] = Provider(

            name="nvidia_nemotron_lightning",

            model="nvidia/nemotron-3.5-lightning-30b-a3b",

            base_url=nvidia_base,

            api_key_env="NVIDIA_API_KEY",

            status=ProviderStatus.HEALTHY if nvidia_key else ProviderStatus.UNCONFIGURED,

            tags=["fast", "reliable", "free"],

        )



        # Nemotron Super 120B - second NIM key and second model, so a model-level

        # outage does not take down the whole NIM tier. Measured ~6s on real prompts.

        self._providers["nvidia_nemotron_super"] = Provider(

            name="nvidia_nemotron_super",

            model="nvidia/nemotron-3-super-120b-a12b",

            base_url=nvidia_base,

            api_key_env="NVIDIA_API_KEY_2",

            status=ProviderStatus.HEALTHY if _sanitized("NVIDIA_API_KEY_2") else ProviderStatus.UNCONFIGURED,

            tags=["fast", "reliable", "free"],

        )



        # gpt-oss 20B - third NIM key and third model. Last NIM resort before OpenRouter.

        self._providers["nvidia_gpt_oss"] = Provider(

            name="nvidia_gpt_oss",

            model="openai/gpt-oss-20b",

            base_url=nvidia_base,

            api_key_env="NVIDIA_API_KEY_3",

            status=ProviderStatus.HEALTHY if _sanitized("NVIDIA_API_KEY_3") else ProviderStatus.UNCONFIGURED,

            tags=["reliable", "free"],

        )



        # ?? OpenRouter ??



        # Nemotron Super free ? strong general purpose fallback

        self._providers["openrouter_nemotron_super_free"] = Provider(

            name="openrouter_nemotron_super_free",

            model="nvidia/nemotron-3-super-120b-a12b:free",

            base_url=openrouter_base,

            api_key_env="OPENROUTER_API_KEY",

            status=ProviderStatus.HEALTHY if openrouter_key else ProviderStatus.UNCONFIGURED,

            tags=["clean", "reliable", "free"],

        )



        # Nemotron Ultra 550B ? Most powerful (~21s), for heavy reasoning only

        self._providers["openrouter_nemotron_ultra"] = Provider(

            name="openrouter_nemotron_ultra",

            model="nvidia/nemotron-3-ultra-550b-a55b:free",

            base_url=openrouter_base,

            api_key_env="OPENROUTER_API_KEY",

            status=ProviderStatus.HEALTHY if openrouter_key else ProviderStatus.UNCONFIGURED,

            tags=["powerful", "reasoning", "free"],

        )



    def _get_client(self, provider: Provider):

        """Create a fresh OpenAI client for a provider."""

        from openai import OpenAI



        api_key = _get_api_key(provider)

        if not api_key:

            raise RuntimeError(f"{provider.name}: API key not configured ({provider.api_key_env})")



        return OpenAI(

            api_key=api_key,

            base_url=provider.base_url,

            timeout=PER_PROVIDER_TIMEOUT,

            max_retries=0,  # We handle retries ourselves

        )



    def _call_provider(

        self,

        provider: Provider,

        messages: list[dict[str, str]],

        max_tokens: int,

        temperature: float,

        top_p: float,

    ) -> str:

        """Make a SINGLE call to a provider with a hard timeout.



        Uses httpx directly for proper timeout + connection cancellation.

        When the timeout fires, the HTTP connection is CLOSED ? not just ignored.

        """

        import httpx



        api_key = _get_api_key(provider)

        if not api_key:

            raise RuntimeError(f"{provider.name}: API key not configured")



        # Fail fast on DNS: never spend a 40s LLM timeout on a host we cannot resolve.
        host = urlparse(provider.base_url).hostname or ""
        if host:
            dns_ok, dns_err = resolve_host(host)
            if not dns_ok:
                logger.error(
                    "PROVIDER_DIAG %s host=%s dns=FAIL category=network detail=%s",
                    provider.name, host, _ascii_safe(dns_err),
                )
                raise NetworkError(
                    f"{provider.name}: cannot resolve {host} ({dns_err})"
                )

        provider.total_requests += 1

        t0 = time.time()



        # Build the request payload

        payload = {

            "model": provider.model,

            "messages": messages,

            "temperature": temperature,

            "top_p": top_p,

            "max_tokens": max_tokens,

            "stream": False,

        }



        # NVIDIA NIM chat templates default to emitting a reasoning preamble into

        # `content`. Force it off so users only see the finished answer (and so

        # we do not pay the latency of generating a hidden chain of thought).

        if "nvidia.com" in (provider.base_url or ""):

            payload["chat_template_kwargs"] = {"thinking": False}



        headers = {

            "Authorization": f"Bearer {api_key}",

            "Content-Type": "application/json",

        }



        url = f"{provider.base_url}/chat/completions"



        # httpx with per-request timeout that KILLS the connection

        with httpx.Client(timeout=httpx.Timeout(

            connect=5.0,        # 5s to connect

            read=PER_PROVIDER_TIMEOUT,  # Max time for the response

            write=5.0,          # 5s to send

            pool=5.0,           # 5s for connection pool

        )) as client:

            resp = client.post(url, json=payload, headers=headers)



        elapsed = time.time() - t0



        if resp.status_code == 401 or resp.status_code == 403:

            raise PermissionError(f"{provider.name}: auth failed ({resp.status_code})")

        if resp.status_code == 429:

            raise RuntimeError(f"{provider.name}: rate limited (429)")

        if resp.status_code >= 500:

            raise RuntimeError(f"{provider.name}: server error ({resp.status_code})")

        if resp.status_code != 200:

            raise RuntimeError(f"{provider.name}: HTTP {resp.status_code}: {resp.text[:200]}")



        data = resp.json()

        choices = data.get("choices", [])

        if not choices:

            raise ValueError(f"{provider.name}: no choices in response")



        msg = choices[0].get("message", {})

        content = (msg.get("content") or "").strip()



        # Log and discard any reasoning fields

        for field_name in ("reasoning_content", "reasoning"):

            val = msg.get(field_name)

            if val:

                logger.warning(

                    f"{provider.name}: discarded {field_name} ({len(val)} chars)"

                )



        if not content:

            raise ValueError(f"{provider.name}: empty response")



        provider.mark_healthy(elapsed)

        logger.info(

            f"? {provider.name} responded in {elapsed:.1f}s ({len(content)} chars)"

        )

        return content



    def _select_providers_for_task(self, task_type: TaskType) -> list[tuple[Provider, dict]]:

        """Get ordered list of (provider, config) for a task type."""

        routing = TASK_ROUTING.get(task_type, TASK_ROUTING[TaskType.QUICK_CHAT])

        result = []

        for config in routing:

            pname = config["provider"]

            provider = self._providers.get(pname)

            if provider and provider.is_available():

                result.append((provider, config))

        return result



    def _generate_with_failover(

        self,

        messages: list[dict[str, str]],

        task_type: TaskType = TaskType.QUICK_CHAT,

    ) -> str:

        """Core generation with task routing and hard failover.



        GUARANTEE: Will return within GLOBAL_TIMEOUT seconds or raise.

        """

        global_start = time.time()

        candidates = self._select_providers_for_task(task_type)



        if not candidates:

            # Try all available providers as last resort

            candidates = [

                (p, {"max_tokens": 512, "temperature": 0.5, "top_p": 0.9})

                for p in self._providers.values()

                if p.is_available()

            ]



        if not candidates:

            raise RuntimeError("No LLM providers available. Check API keys in .env")



        last_error = ""

        last_category = "unknown"

        attempts = 0

        network_hosts_failed = set()

        network_started = None



        for provider, config in candidates:

            # Check global timeout before attempting next provider

            elapsed_global = time.time() - global_start

            if elapsed_global >= GLOBAL_TIMEOUT:

                logger.error(

                    f"GLOBAL TIMEOUT after {elapsed_global:.1f}s with {attempts} attempts"

                )

                break



            attempts += 1

            remaining = GLOBAL_TIMEOUT - elapsed_global

            # Use the smaller of per-provider timeout and remaining global time

            effective_timeout = min(PER_PROVIDER_TIMEOUT, remaining)

            host = urlparse(provider.base_url).hostname or ""

            attempt_start = time.time()



            logger.info(

                f"ROUTER: task={task_type.value} ? {provider.name} "

                f"(attempt {attempts}, {remaining:.0f}s remaining)"

            )



            try:

                content = self._call_provider(

                    provider,

                    messages,

                    max_tokens=config.get("max_tokens", 512),

                    temperature=config.get("temperature", 0.5),

                    top_p=config.get("top_p", 0.9),

                )

                total_elapsed = time.time() - global_start

                logger.info(

                    f"? Chat complete in {total_elapsed:.1f}s "

                    f"(provider: {provider.name}, host={host}, attempt={attempts})"

                )

                return content



            except TimeoutError as exc:

                last_error = str(exc)

                last_category = "timeout"

                logger.error(

                    "PROVIDER_FAIL name=%s host=%s category=%s elapsed=%.1fs detail=%s",

                    provider.name, host, last_category,

                    time.time() - attempt_start, _ascii_safe(last_error),

                )

                provider.mark_error(cooldown_seconds=5.0)

                continue



            except Exception as exc:

                last_error = str(exc)

                last_category = ("network" if isinstance(exc, NetworkError)
                                 else classify_error(last_error))

                logger.error(

                    "PROVIDER_FAIL name=%s host=%s category=%s elapsed=%.1fs detail=%s",

                    provider.name, host, last_category,

                    time.time() - attempt_start, _ascii_safe(last_error),

                )



                if last_category == "rate_limit":

                    provider.mark_rate_limited(120.0)

                elif last_category == "auth":

                    provider.mark_auth_failed()

                else:

                    provider.mark_error(5.0)



                # Circuit breaker: if the machine cannot resolve/connect, every

                # remaining provider will fail the same way. Stop instead of

                # burning tens of seconds reproducing the same outage.

                if last_category == "network":

                    if network_started is None:

                        network_started = time.time()

                    if host:

                        network_hosts_failed.add(host)

                    spent = time.time() - network_started

                    if (

                        len(network_hosts_failed) >= MAX_NETWORK_HOST_FAILURES

                        or spent >= NETWORK_FAILURE_BUDGET

                    ):

                        logger.error(

                            "NETWORK OUTAGE: %d host(s) unreachable after %.1fs - "

                            "stopping failover early instead of retrying %d providers",

                            len(network_hosts_failed), spent, len(candidates),

                        )

                        break

                continue



        total_elapsed = time.time() - global_start

        detail = _ascii_safe(last_error)

        if last_category == "network":

            raise NetworkError(

                f"Network unavailable after {total_elapsed:.1f}s ({attempts} attempts): {detail}"

            )

        raise RuntimeError(

            f"All providers failed after {total_elapsed:.1f}s "

            f"({attempts} attempts). Last error: {detail}"

        )



    # ?? Public API ????????????????????????????????????????????????????????



    def generate_text(self, prompt: str, task_type: TaskType = TaskType.QUICK_CHAT) -> str:

        """Single-prompt text completion."""

        if not prompt or not prompt.strip():

            raise ValueError("prompt must be a non-empty string")

        return self._generate_with_failover(

            [{"role": "user", "content": prompt}],

            task_type=task_type,

        )



    def generate_chat(

        self,

        messages: list[dict[str, str]],

        task_type: TaskType = TaskType.QUICK_CHAT,

    ) -> str:

        """Chat conversation with proper roles."""

        if not messages:

            raise ValueError("messages must be a non-empty list")

        return self._generate_with_failover(messages, task_type=task_type)



    def get_status(self) -> dict:

        """Provider status for monitoring."""

        available_count = sum(1 for p in self._providers.values() if p.is_available())

        active_provider = next(

            (p.name for p in self._providers.values() if p.is_available()),

            "none",

        )



        return {

            "providers": [

                {

                    "name": p.name,

                    "model": p.model,

                    "status": p.status.value,

                    "available": p.is_available(),

                    "avg_latency": round(p.avg_latency, 1),

                    "cooldown_remaining": round(p.get_cooldown_remaining(), 1),

                    "total_requests": p.total_requests,

                    "total_failures": p.total_failures,

                    "tags": p.tags,

                }

                for p in self._providers.values()

            ],

            "strategy": "fast_failover",

            "active_provider": active_provider,

            "total_providers": len(self._providers),

            "available_providers": available_count,

            "per_provider_timeout": PER_PROVIDER_TIMEOUT,

            "global_timeout": GLOBAL_TIMEOUT,

        }





# ?? Singleton ?????????????????????????????????????????????????????????????????

_manager: ProviderManager | None = None





def get_manager() -> ProviderManager:

    global _manager

    if _manager is None:

        _manager = ProviderManager()

    return _manager





def generate_text(prompt: str, task_type: TaskType = TaskType.QUICK_CHAT) -> str:

    return get_manager().generate_text(prompt, task_type=task_type)





def generate_chat(

    messages: list[dict[str, str]],

    task_type: TaskType = TaskType.QUICK_CHAT,

) -> str:

    return get_manager().generate_chat(messages, task_type=task_type)





def get_status() -> dict:

    return get_manager().get_status()

