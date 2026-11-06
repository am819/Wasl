"""
Rate limiting configuration using slowapi (in-memory).

Limits per SECURITY.md:
  Auth endpoints  : 10 req/min per IP (login, register, refresh)
  Merchant group  : 100 req/min per IP
  Driver group    : 100 req/min per IP
  Admin group     : 500 req/min per IP
  Public tracking : 1000 req/min per IP

In-memory storage is used for the MVP (no Redis required).
In production, replace with Redis storage via limits.storage.RedisStorage.

Proxy IP safety
---------------
Behind Railway (or any reverse proxy), the real client IP arrives in the
X-Forwarded-For header, e.g.:

    X-Forwarded-For: <client>, <proxy1>, <proxy2>

The *last* value is appended by the nearest trusted proxy and cannot be
spoofed by the client. Taking the *first* value is unsafe because a client
can prepend arbitrary IPs.

We use the *last* entry. If the header is absent we fall back to
request.client.host (direct connection, e.g. local development).

NUMBER_OF_PROXIES controls how many trusted proxy hops sit in front of the
app. Railway uses 1. Adjust via the NUMBER_OF_PROXIES environment variable
if the topology changes.
"""

import os

from fastapi import Request
from slowapi import Limiter

_NUM_PROXIES = int(os.getenv("NUMBER_OF_PROXIES", "1"))


def _get_client_ip(request: Request) -> str:
    """
    Return the real client IP, safe for use behind a reverse proxy.

    Strategy:
    - Read X-Forwarded-For and strip the rightmost _NUM_PROXIES entries
      (those were added by our own infrastructure).
    - The entry immediately to the left of those is the client IP.
    - Fall back to request.client.host when the header is absent.
    """
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        # Split, strip whitespace, remove empty strings
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            # The rightmost _NUM_PROXIES entries are our infra; the entry
            # just before them is the real client.
            idx = max(0, len(parts) - _NUM_PROXIES - 1)
            return parts[idx]

    # No XFF header — direct connection (local dev, CI, etc.)
    if request.client:
        return request.client.host
    return "unknown"


# Shared limiter instance — imported by routers that need it
limiter = Limiter(key_func=_get_client_ip)

# Named limit strings used in @limiter.limit() decorators
AUTH_LIMIT = "10/minute"
MERCHANT_LIMIT = "100/minute"
DRIVER_LIMIT = "100/minute"
ADMIN_LIMIT = "500/minute"
TRACKING_LIMIT = "1000/minute"
