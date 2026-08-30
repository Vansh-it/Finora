"""LLM provider with automatic failover between multiple providers.

When one provider hits rate limits or errors, the system automatically
switches to the next available provider — the user never sees an interruption.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv
from pathlib import Path

# ── Load environment variables ────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

MODEL_NEMOTRON = "nvidia/nemotron-3.5-lightning-30b-a3b"
MODEL_KIMI = "moonshotai/kimi-k3"


# ── Provider health status ────────────────────────────────────────────────────
class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"


@dataclass
class Provider:
    name: str
    model: str
    status: ProviderStatus = ProviderStatus.HEALTHY
    cooldown_until: float = 0.0
    error_count: int = 0
    last_error: str = ""
    total_requests: int = 0
    total_failures: int = 0

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

    def mark_healthy(self) -> None:
        self.status = ProviderStatus.HEALTHY
        self.cooldown_until = 0.0
        self.error_count = 0

    def mark_auth_failed(self) -> None:
        self.status = ProviderStatus.ERROR
        self.cooldown_until = time.time() + 86400.0
        self.error_count += 1
        self.total_failures += 1

    def get_cooldown_remaining(self) -> float:
        return max(0.0, self.cooldown_until - time.time())


# ── Provider manager with failover ────────────────────────────────────────────
class ProviderManager:
    """Manages LLM providers with automatic failover.

    Tries providers in order. On rate limit/error, marks provider unavailable
    and switches to next available. Cycles through providers on successive failures.
    """

    def __init__(self) -> None:
        self._providers: list[Provider] = []
        self._current_index = 0

        # Provider 1: NVIDIA Nemotron
        api_key1 = os.getenv("NVIDIA_API_KEY", "")
        if api_key1:
            self._providers.append(
                Provider(name="nvidia_nemotron", model=MODEL_NEMOTRON)
            )
        else:
            self._providers.append(
                Provider(
                    name="nvidia_nemotron", model=MODEL_NEMOTRON,
                    status=ProviderStatus.UNCONFIGURED,
                )
            )

        # Provider 2: Kimi-K3 (from user's axios config)
        api_key2 = os.getenv("NVIDIA_API_KEY_KIMI", "")
        if api_key2:
            self._providers.append(
                Provider(name="kimi_k3", model=MODEL_KIMI)
            )
        else:
            self._providers.append(
                Provider(
                    name="kimi_k3", model=MODEL_KIMI,
                    status=ProviderStatus.UNCONFIGURED,
                )
            )

    def _get_next_available_provider(self) -> int:
        """Find the next available provider, skipping unavailable ones."""
        original_index = self._current_index
        attempts = 0
        while attempts < len(self._providers):
            provider = self._providers[self._current_index]
            if provider.is_available():
                return self._current_index
            self._current_index = (self._current_index + 1) % len(self._providers)
            attempts += 1
        # All providers unavailable; reset to first and return it
        self._current_index = 0
        return 0

    def generate_text(self, prompt: str) -> str:
        """Send prompt to LLM with automatic failover between providers."""
        if not prompt or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        # Try providers with failover
        for _ in range(len(self._providers)):
            idx = self._get_next_available_provider()
            provider = self._providers[idx]

            # Mark this provider as attempted (move index forward for next time)
            self._current_index = (idx + 1) % len(self._providers)

            if not provider.is_available():
                continue

            try:
                from openai import OpenAI

                # Choose base URL and model based on provider
                if provider.name == "kimi_k3":
                    base_url = "https://integrate.api.nvidia.com/v1"
                    api_key = os.getenv("NVIDIA_API_KEY_KIMI", "")
                else:
                    base_url = "https://integrate.api.nvidia.com/v1"
                    api_key = os.getenv("NVIDIA_API_KEY", "")

                if not api_key:
                    provider.mark_auth_failed()
                    continue

                self._provider = provider  # Set as current for status tracking
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=30.0,
                )

                completion = client.chat.completions.create(
                    model=provider.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1.0,
                    top_p=0.95,
                    max_tokens=1024,
                )
                msg = completion.choices[0].message
                reasoning = getattr(msg, "reasoning_content", None)
                content = msg.content or ""
                if content:
                    provider.mark_healthy()
                    return content
                if reasoning:
                    provider.mark_healthy()
                    return reasoning
                raise RuntimeError(f"{provider.model}: empty response from API")

            except RuntimeError as exc:
                exc_msg = str(exc).lower()
                # Rate limit/quota -> mark rate limited and try next
                if any(t in exc_msg for t in ("rate", "quota", "429", "limit")):
                    provider.mark_rate_limited(120.0)
                    continue
                # Auth errors -> mark auth failed and try next
                elif any(t in exc_msg for t in ("auth", "invalid", "permission", "401", "403")):
                    provider.mark_auth_failed()
                    continue
                # Other errors -> mark error and try next
                else:
                    provider.mark_error(5.0)
                    continue
            except Exception as exc:
                provider.mark_error(5.0)
                continue

        # All providers exhausted
        raise RuntimeError("All LLM providers are currently unavailable")

    def get_status(self) -> dict:
        """Return provider status for monitoring/debugging."""
        available_count = sum(
            1 for p in self._providers if p.is_available()
        )
        active_name = (
            self._providers[0].name if available_count > 0 else "none"
        )

        # Find first available provider as "active"
        active_provider = "none"
        for p in self._providers:
            if p.is_available():
                active_provider = p.name
                break

        return {
            "providers": [
                {
                    "name": p.name,
                    "model": p.model,
                    "status": p.status.value,
                    "available": p.is_available(),
                    "cooldown_remaining": p.get_cooldown_remaining(),
                    "total_requests": p.total_requests,
                    "total_failures": p.total_failures,
                    "error_count": p.error_count,
                }
                for p in self._providers
            ],
            "strategy": "failover",
            "active_provider": active_provider,
            "total_providers": len(self._providers),
        }


# ── Singleton instance ────────────────────────────────────────────────────────
_manager: ProviderManager | None = None


def get_manager() -> ProviderManager:
    """Get or create the singleton ProviderManager."""
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager


def generate_text(prompt: str) -> str:
    """Convenience function — delegates to the singleton manager."""
    return get_manager().generate_text(prompt)


def get_status() -> dict:
    """Convenience function — delegates to the singleton manager."""
    return get_manager().get_status()
