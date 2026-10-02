# -*- coding: utf-8 -*-
"""Failed-login throttle: MAX_ATTEMPTS per WINDOW_SECONDS per client IP.

Deliberately dependency-free (in-memory) - it protects ``/login`` only, while
flask-limiter keeps covering the general per-IP API budget. State is lost on
restart, which is fine for a throttle.
"""
import time
from collections import defaultdict, deque

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60

_failures = defaultdict(deque)  # ip -> deque of failure timestamps


def client_ip(request) -> str:
    """Resolve the client IP for throttling.

    Relies on ``request.remote_addr``, which ProxyFix (one trusted hop) has
    already rebuilt from X-Forwarded-For. Reading the raw header here would let
    an attacker mint a fresh identity per request and brute-force forever.
    """
    return request.remote_addr or "unknown"


def _prune(attempts: deque, now: float) -> None:
    while attempts and now - attempts[0] >= WINDOW_SECONDS:
        attempts.popleft()


def register_failure(ip: str, now: "float | None" = None) -> int:
    """Record a failed attempt; returns the number of failures in the window."""
    now = time.time() if now is None else now
    attempts = _failures[ip]
    _prune(attempts, now)
    attempts.append(now)
    return len(attempts)


def is_locked(ip: str, now: "float | None" = None) -> bool:
    now = time.time() if now is None else now
    attempts = _failures.get(ip)
    if not attempts:
        return False
    _prune(attempts, now)
    if not attempts:
        _failures.pop(ip, None)
        return False
    return len(attempts) >= MAX_ATTEMPTS


def seconds_left(ip: str, now: "float | None" = None) -> int:
    """Seconds until the oldest failure leaves the window (0 if not locked)."""
    now = time.time() if now is None else now
    attempts = _failures.get(ip)
    if not attempts:
        return 0
    _prune(attempts, now)
    if len(attempts) < MAX_ATTEMPTS:
        return 0
    return max(1, int(WINDOW_SECONDS - (now - attempts[0])))


def reset(ip: str) -> None:
    """Clear failures after a successful login."""
    _failures.pop(ip, None)
