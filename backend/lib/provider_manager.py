"""LLM provider — single model: NVIDIA Nemotron 3.5.

Clean and simple. No failover needed — one provider that works.
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

MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


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


# ── Provider manager ──────────────────────────────────────────────────────────
class ProviderManager:
    """Manages LLM provider with retry on transient errors."""

    def __init__(self) -> None:
        api_key = os.getenv("NVIDIA_API_KEY", "")
        if api_key:
            self._provider = Provider(name="nvidia_nemotron", model=MODEL)
        else:
            self._provider = Provider(
                name="nvidia_nemotron", model=MODEL,
                status=ProviderStatus.UNCONFIGURED,
            )

    def generate_text(self, prompt: str) -> str:
        """Send prompt to NVIDIA Nemotron. Retries once on transient errors."""
        if not prompt or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        if not self._provider.is_available():
            cooldown = self._provider.get_cooldown_remaining()
            if cooldown > 0:
                raise RuntimeError(
                    f"nvidia_nemotron is rate-limited. Retry in {cooldown:.0f}s."
                )
            raise RuntimeError("nvidia_nemotron is not configured. Set NVIDIA_API_KEY in .env.")

        from openai import OpenAI

        api_key = os.getenv("NVIDIA_API_KEY", "")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY not configured")

        last_error: Exception | None = None

        for attempt in range(2):
            try:
                self._provider.total_requests += 1
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://integrate.api.nvidia.com/v1",
                    timeout=30.0,
                )
                completion = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1.0,
                    top_p=0.95,
                    max_tokens=1024,
                )
                msg = completion.choices[0].message
                reasoning = getattr(msg, "reasoning_content", None)
                content = msg.content or ""
                if content:
                    self._provider.mark_healthy()
                    return content
                if reasoning:
                    self._provider.mark_healthy()
                    return reasoning
                raise RuntimeError(f"{MODEL}: empty response from API")
            except RuntimeError as exc:
                last_error = exc
                msg = str(exc).lower()
                if any(t in msg for t in ("rate", "quota", "429", "limit")):
                    self._provider.mark_rate_limited(120.0)
                    break
                elif any(t in msg for t in ("auth", "invalid", "permission", "401", "403")):
                    self._provider.mark_auth_failed()
                    break
                else:
                    self._provider.mark_error(5.0)
            except Exception as exc:
                last_error = exc
                self._provider.mark_error(5.0)

        raise RuntimeError(f"nvidia_nemotron failed: {last_error}")

    def get_status(self) -> dict:
        """Return provider status for monitoring/debugging."""
        return {
            "providers": [
                {
                    "name": self._provider.name,
                    "model": self._provider.model,
                    "status": self._provider.status.value,
                    "available": self._provider.is_available(),
                    "cooldown_remaining": self._provider.get_cooldown_remaining(),
                    "total_requests": self._provider.total_requests,
                    "total_failures": self._provider.total_failures,
                    "error_count": self._provider.error_count,
                }
            ],
            "strategy": self._provider.name,
            "active_provider": self._provider.name if self._provider.is_available() else "none",
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
