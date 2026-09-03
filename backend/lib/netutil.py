"""Network utilities: IPv4-first resolution.

This machine (and many VPN/corporate networks) has a broken or unroutable
IPv6 path: TCP connects to IPv6 addresses hang for tens of seconds while the
IPv4 path answers in ~1s.  Python's :mod:`urllib` (and older ``httpx``
configurations) try addresses in ``getaddrinfo`` order, so a v6-first result
list makes every outbound call (SEC, Tavily, Jina, Twelve Data, LLM
providers) appear to hang or intermittently time out.

This module reorders ``socket.getaddrinfo`` results so IPv4 addresses are
always attempted first.  IPv6 addresses are still returned (kept after IPv4)
so hosts that only serve over IPv6 remain reachable.

Call :func:`apply_ipv4_first()` once from each HTTP client module import
(it is idempotent and cheap).
"""

from __future__ import annotations

import socket as _socket
from typing import Any

_ORIGINAL_GETADDRINFO = _socket.getaddrinfo
_applied = False


def _ipv4_first_getaddrinfo(*args: Any, **kwargs: Any) -> list:
    """getaddrinfo wrapper that orders IPv4 (AF_INET) results first."""
    try:
        results = _ORIGINAL_GETADDRINFO(*args, **kwargs)
    except Exception:
        raise
    # Stability matters: only reorder, never drop entries.
    return sorted(results, key=lambda r: 0 if r[0] == _socket.AF_INET else 1)


def apply_ipv4_first() -> None:
    """Force IPv4-first DNS ordering for this process (idempotent)."""
    global _applied
    if _applied:
        return
    _socket.getaddrinfo = _ipv4_first_getaddrinfo  # type: ignore[assignment]
    _applied = True


def is_applied() -> bool:
    """Whether the IPv4-first patch is active."""
    return _applied


def reset() -> None:
    """Restore the original getaddrinfo (tests only)."""
    global _applied
    _socket.getaddrinfo = _ORIGINAL_GETADDRINFO  # type: ignore[assignment]
    _applied = False
