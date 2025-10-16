"""Rate limiting utilities using SlowAPI with in-memory storage.

For serverless/low-traffic deployments, we use in-memory rate limiting
instead of Redis to reduce costs and complexity.
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Disable rate limiting in test environment
enabled = os.getenv("TESTING") != "1"

# Initialize rate limiter with in-memory storage (no Redis needed)
# For serverless: rate limits are per Lambda instance, which is acceptable
# for low traffic. If you need distributed rate limiting across instances,
# consider using PostgreSQL-backed storage instead.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",  # In-memory storage (no Redis)
    enabled=enabled
)
