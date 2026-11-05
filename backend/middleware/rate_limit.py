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
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — imported by routers that need it
limiter = Limiter(key_func=get_remote_address)

# Named limit strings used in @limiter.limit() decorators
AUTH_LIMIT = "10/minute"
MERCHANT_LIMIT = "100/minute"
DRIVER_LIMIT = "100/minute"
ADMIN_LIMIT = "500/minute"
TRACKING_LIMIT = "1000/minute"
