"""SSRF (Server-Side Request Forgery) protection.

Finora reads external URLs through Jina / web-reading functionality.  Before
any external URL is handed to a fetcher, it MUST pass :func:`validate_url` so
users cannot trick the server into reaching:

  - localhost / 127.0.0.1 / ::1
  - private RFC1918 networks (10/8, 172.16/12, 192.168/16)
  - link-local, loopback, and multicast ranges
  - cloud metadata endpoints (169.254.169.254 and friends)
  - internal services (e.g. 0.0.0.0, metadata IPs)
  - file://, gopher://, dict:// and other unsupported schemes
  - DNS rebinding hazards are mitigated by validating the resolved IP set.

External URLs fed to fetchers should come from trusted discovery (SEC,
Tavily results filtered to known-good domains) rather than arbitrary client
input.  This guard is a hard backstop regardless of source.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("finora.ssrf")

# Schemes that are always rejected
_BLOCKED_SCHEMES = {"file", "gopher", "dict", "ftp", "ldap", "tftp", "jar", "ws", "wss"}
# Schemes we never treat as fetchable HTTP content
_ALLOWED_SCHEMES = {"http", "https"}

# Hostnames / prefixes that resolve to local/private targets
_BLOCKED_HOSTNAME_EXACT = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "metadata.google.internal",
    "metadata",
}
_BLOCKED_HOSTNAME_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa")

# IPv4 link-local block (includes cloud metadata 169.254.169.254)
_LINK_LOCAL = ipaddress.ip_network("169.254.0.0/16")
# Reserved/unspecified/docs/benchmark ranges that should never be fetched
_SPECIAL_NETS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),   # CGNAT
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),    # TEST-NET-1
    ipaddress.ip_network("198.18.0.0/15"),   # benchmarking
    ipaddress.ip_network("198.51.100.0/24"), # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),     # multicast
    ipaddress.ip_network("240.0.0.0/4"),     # reserved
    ipaddress.ip_network("255.255.255.255/32"),
]


def _is_private_ipv4(addr: ipaddress.IPv4Address) -> bool:
    if addr.is_private or addr.is_loopback or addr.is_link_local:
        return True
    for net in _SPECIAL_NETS:
        if addr in net:
            return True
    return False


def _is_private_ipv6(addr: ipaddress.IPv6Address) -> bool:
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast:
        return True
    # ULA (fc00::/7) is not flagged private by is_private on all platforms
    if addr in ipaddress.ip_network("fc00::/7"):
        return True
    # IPv4-mapped addresses (::ffff:1.2.3.4) must be checked as IPv4
    if addr.ipv4_mapped is not None:
        return _is_private_ipv4(addr.ipv4_mapped)
    return False


def _is_safe_ip(ip_str: str) -> bool:
    """Check a single IP literal / resolved address."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if addr.version == 4:
        return not _is_private_ipv4(addr)
    return not _is_private_ipv6(addr)


def _host_is_suspicious(hostname: str) -> bool:
    """Reject obviously local/internal hostnames without a DNS lookup."""
    host = hostname.strip().lower().rstrip(".")
    if not host:
        return True
    if host in _BLOCKED_HOSTNAME_EXACT:
        return True
    if host.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.",
                        "172.19.", "172.2", "172.30.", "172.31.", "169.254.", "0.")):
        return True
    if host.startswith("fc") and host.startswith("fd"):
        # heuristic — exact checks happen after resolution too
        pass
    for suffix in _BLOCKED_HOSTNAME_SUFFIXES:
        if host.endswith(suffix):
            return True
    # Reject bare IPs that are unsafe (must be a valid IP literal)
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Not an IP literal — hostname is fine at this level (DNS check happens later)
        return False
    return not _is_safe_ip(str(addr))


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """Validate a URL for safe outbound fetching.

    Parameters
    ----------
    url : str
        The absolute URL to validate.

    Returns
    -------
    (ok, reason)
        ``ok`` is True and ``reason`` None when the URL may be fetched.
        ``ok`` is False with a human-readable reason otherwise.
    """
    if not isinstance(url, str) or not url.strip():
        return False, "URL is empty"
    url = url.strip()

    try:
        parsed = urlparse(url)
    except ValueError:
        return False, "Malformed URL"

    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        return False, f"Scheme '{scheme or 'none'}' is not allowed"
    if scheme in _BLOCKED_SCHEMES:
        return False, f"Scheme '{scheme}' is blocked"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL has no host"

    # Quick hostname-level rejection (no DNS)
    if _host_is_suspicious(hostname):
        return False, f"Host '{hostname}' is not a permitted target"

    # DNS-level check: resolve all A/AAAA records and verify EVERY address.
    # Use a short timeout to avoid hanging on broken IPv6 routes.
    try:
        default_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5.0)
        try:
            infos = socket.getaddrinfo(hostname, parsed.port or (443 if scheme == "https" else 80),
                                       proto=socket.IPPROTO_TCP)
        finally:
            socket.setdefaulttimeout(default_timeout)
    except OSError:
        # Cannot resolve — fail closed for a fetch target
        return False, f"Could not resolve host '{hostname}'"
    except Exception:
        return False, f"Could not resolve host '{hostname}'"

    if not infos:
        return False, f"Host '{hostname}' resolved to no addresses"

    for info in infos:
        addr = info[4][0]
        if not _is_safe_ip(addr):
            return False, f"Host '{hostname}' resolves to a blocked address ({addr})"

    return True, None


def assert_safe_url(url: str) -> None:
    """Raise :class:`ValueError` when a URL is unsafe for fetching."""
    ok, reason = validate_url(url)
    if not ok:
        raise ValueError(f"Blocked URL: {reason}")


def safe_url_or_none(url: str) -> Optional[str]:
    """Return the URL if safe to fetch, else None (never raises)."""
    ok, _ = validate_url(url)
    return url if ok else None
